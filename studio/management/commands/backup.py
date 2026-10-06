import os
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from studio.backup import create_backup

class Command(BaseCommand):
    help = 'Crea un respaldo SQLite consistente, incluso con el servidor activo.'

    def add_arguments(self, parser):
        parser.add_argument('--output')

    def handle(self, *args, **options):
        path = Path(options['output']) if options['output'] else settings.DATA_DIR / 'backups' / f'maryruss-{timezone.localtime():%Y%m%d-%H%M%S}.zip'
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            payload = create_backup()
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(payload)
        except (OSError, ValueError) as error:
            raise CommandError(str(error))
        self.stdout.write(f'Respaldo creado: {path}')
