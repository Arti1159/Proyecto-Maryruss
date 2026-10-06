import os
import secrets
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = 'Crea el primer administrador y guarda el acceso en un archivo privado. Nunca imprime contraseñas.'

    def handle(self, *args, **options):
        if settings.DEMO_MODE:
            raise CommandError('Usa seed_demo para la base de demostración.')
        User = get_user_model()
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write('Ya hay un administrador; no se modificaron su cuenta ni su contraseña.')
            return
        username = os.environ.get('MARYRUSS_ADMIN_USER', 'admin')
        if User.objects.filter(username=username).exists():
            raise CommandError('El nombre elegido ya existe. Usa otro MARYRUSS_ADMIN_USER; no se sobrescribirá la cuenta.')
        path = settings.DATA_DIR / 'acceso-inicial.txt'
        if path.exists():
            raise CommandError('Ya hay un archivo de acceso inicial. Consérvalo o muévelo antes de crear un nuevo acceso.')
        password = os.environ.get('MARYRUSS_ADMIN_PASSWORD') or secrets.token_urlsafe(24)
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        try:
            validate_password(password)
        except ValidationError as error:
            raise CommandError('; '.join(error.messages))
        User.objects.create_superuser(username=username, password=password)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as stream:
            stream.write('ACCESO PRIVADO A MARYRUSS\nNo compartas este archivo ni lo subas a Git.\n\n')
            stream.write(f'Usuario: {username}\nContraseña inicial: {password}\n\n')
            stream.write('Cambia la contraseña desde Mi cuenta después de ingresar.\n')
        self.stdout.write(f'Administrador creado. Acceso guardado únicamente en {path}.')
