"""Exercise source or frozen launcher with fresh, isolated persistent data."""
import http.cookiejar
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import zipfile
import io


def run(command):
    with tempfile.TemporaryDirectory(prefix='maryruss-portable-') as temporary:
        root = Path(temporary)
        data = root / 'datos'
        ready = root / 'ready.txt'
        credentials = None
        for iteration in range(2):
            ready.unlink(missing_ok=True)
            process = subprocess.Popen(command + ['--headless', '--data-dir', str(data), '--ready-file', str(ready)])
            try:
                deadline = time.monotonic() + 90
                while not ready.exists():
                    if process.poll() is not None:
                        raise RuntimeError(f'Launcher exited: {process.returncode}')
                    if time.monotonic() > deadline:
                        raise TimeoutError('Launcher did not become ready')
                    time.sleep(0.2)
                url = ready.read_text().rstrip('/')
                opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
                page = opener.open(url + '/ingresar/', timeout=10).read().decode()
                token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', page).group(1)
                private = (data / 'acceso-inicial.txt').read_text()
                if iteration:
                    assert private == credentials, 'Restart changed credentials'
                credentials = private
                login = {'csrfmiddlewaretoken': token,
                         'username': re.search(r'Usuario: (.+)', private).group(1),
                         'password': re.search(r'Contraseña inicial: (.+)', private).group(1)}
                response = opener.open(urllib.request.Request(url + '/ingresar/',
                    data=urllib.parse.urlencode(login).encode(), headers={'Referer': url + '/ingresar/'}), timeout=10)
                assert response.geturl() == url + '/', 'Login failed'
                for path in ('/', '/colecciones/', '/planificador/', '/guia/', '/static/studio.css'):
                    response = opener.open(url + path, timeout=10)
                    assert response.status == 200 and len(response.read()) > 100
                archive = opener.open(url + '/respaldo/', timeout=10).read()
                with zipfile.ZipFile(io.BytesIO(archive)) as backup:
                    assert backup.testzip() is None
                    assert any(name.endswith('.sqlite3') for name in backup.namelist())
                with sqlite3.connect(data / 'maryruss.sqlite3') as db:
                    assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
                    if not iteration:
                        db.execute('CREATE TABLE portable_persistence_check (value TEXT)')
                        db.execute("INSERT INTO portable_persistence_check VALUES ('conservado')")
                    else:
                        assert db.execute('SELECT value FROM portable_persistence_check').fetchone()[0] == 'conservado'
            finally:
                process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        print('Portable smoke check OK: login, pages, static, backup, restart and persistence.')


if __name__ == '__main__':
    command = [str(Path(sys.argv[1]).resolve())] if len(sys.argv) > 1 else [sys.executable, str(Path(__file__).with_name('launcher.py'))]
    run(command)
