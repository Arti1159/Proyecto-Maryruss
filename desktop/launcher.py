"""Portable local application; never stores user data in the frozen bundle."""
import argparse
import os
from pathlib import Path
import socket
from socketserver import ThreadingMixIn
import sys
import threading
import webbrowser
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler, make_server

if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w', encoding='utf-8')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w', encoding='utf-8')

if not getattr(sys, 'frozen', False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class LocalServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


class QuietHandler(WSGIRequestHandler):
    def log_message(self, *args):
        pass  # Do not log URLs or private form data.


def prepare(data_dir):
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ.update(DJANGO_SETTINGS_MODULE='maryruss.settings',
                      MARYRUSS_DATA_DIR=str(data_dir), MARYRUSS_DEMO='0',
                      MARYRUSS_DEBUG='0', MARYRUSS_ALLOWED_HOSTS='127.0.0.1,localhost')
    # Keep the portable app independent of inherited development DB overrides.
    for name in ('MARYRUSS_DB', 'MARYRUSS_TRUST_PROXY'):
        os.environ.pop(name, None)
    import django
    django.setup()
    from django.conf import settings
    # This server binds exclusively to loopback and uses local HTTP.
    settings.SECURE_SSL_REDIRECT = False
    settings.SESSION_COOKIE_SECURE = False
    settings.CSRF_COOKIE_SECURE = False
    settings.SECURE_HSTS_SECONDS = 0
    from django.core.management import call_command
    call_command('migrate', interactive=False, verbosity=0)
    call_command('init_admin', verbosity=0)
    from django.contrib.staticfiles.handlers import StaticFilesHandler
    from django.core.wsgi import get_wsgi_application
    return StaticFilesHandler(get_wsgi_application())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--headless', action='store_true', help='For smoke checks only')
    parser.add_argument('--data-dir', type=Path)
    parser.add_argument('--ready-file', type=Path, help='For automated checks only')
    args = parser.parse_args()
    base = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[1]
    data = (args.data_dir or base / 'datos').resolve()
    lock = socket.socket()
    # One process per user-data directory. Closing/crashing releases the lock.
    import hashlib
    lock_port = 40000 + int(hashlib.sha256(str(data).casefold().encode()).hexdigest()[:8], 16) % 20000
    try:
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            lock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        lock.bind(('127.0.0.1', lock_port))
        lock.listen(1)
    except OSError:
        lock.close()
        raise RuntimeError('Maryruss ya está abierto, o su puerto está ocupado. Cierra la ventana anterior e inténtalo otra vez.')
    server = None
    try:
        application = prepare(data)
        server = make_server('127.0.0.1', 0, application, server_class=LocalServer, handler_class=QuietHandler)
        url = f'http://127.0.0.1:{server.server_port}/'
        if args.headless:
            if args.ready_file:
                args.ready_file.write_text(url, encoding='utf-8')
            if sys.stdout:
                print(url, flush=True)
            server.serve_forever()
            return
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.title('Maryruss')
        root.geometry('540x250')
        tk.Label(root, text='Maryruss está funcionando', font=('Segoe UI', 16)).pack(pady=18)
        tk.Label(root, text='Puedes cerrar el navegador y volver a abrirlo.\nPara apagar la aplicación, cierra esta ventana.').pack()
        tk.Button(root, text='Abrir Maryruss', command=lambda: webbrowser.open(url)).pack(pady=12)
        def credentials():
            path = data / 'acceso-inicial.txt'
            if path.exists():
                os.startfile(str(path))
            else:
                messagebox.showinfo('Acceso', 'Usa la cuenta existente. No se ha generado una contraseña nueva.')
        tk.Button(root, text='Ver acceso inicial (privado)', command=credentials).pack()
        tk.Label(root, text=f'Datos: {data}', wraplength=500).pack(pady=10)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        root.after(300, lambda: webbrowser.open(url))
        def close():
            server.shutdown()
            root.destroy()
        root.protocol('WM_DELETE_WINDOW', close)
        root.mainloop()
    finally:
        if server:
            server.server_close()
        lock.close()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        if '--headless' in sys.argv:
            raise
        import tkinter as tk
        from tkinter import messagebox
        window = tk.Tk()
        window.withdraw()
        messagebox.showerror('Maryruss no pudo iniciar', str(error))
        window.destroy()
