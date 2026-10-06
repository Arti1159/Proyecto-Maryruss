import os
import sqlite3
import tempfile
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.utils import timezone
from studio.backup import create_backup, validate_backup

class Command(BaseCommand):
    help = 'Restaura un respaldo validado. Detén el servidor antes de reemplazar su base de datos.'

    def add_arguments(self, parser):
        parser.add_argument('archive')
        parser.add_argument('--target', help='Ruta de una nueva base aislada para probar la recuperación.')
        parser.add_argument('--confirm', action='store_true', help='Confirma restaurar con el servidor detenido.')

    def handle(self, *args, **options):
        if not options['confirm']:
            raise CommandError('Detén el servidor y añade --confirm. Para probar sin afectar datos, utiliza --target con una ruta nueva.')
        try:
            manifest, data = validate_backup(Path(options['archive']).read_bytes())
            if manifest['demo'] != settings.DEMO_MODE:
                raise ValueError('El respaldo demo y la base real están separados. Activa el mismo modo para restaurarlo.')
            target = Path(options['target'] or settings.DATABASES['default']['NAME']).resolve()
            if options['target'] and target.exists():
                raise ValueError('--target debe señalar una ruta nueva para no reemplazar datos durante una prueba.')
            target.parent.mkdir(parents=True, exist_ok=True)
            connections.close_all()
            if target.exists():
                backup_dir = settings.DATA_DIR / 'backups'
                backup_dir.mkdir(parents=True, exist_ok=True)
                preserved = backup_dir / f'antes-de-restaurar-{timezone.localtime():%Y%m%d-%H%M%S-%f}.zip'
                preserved.write_bytes(create_backup(target))
                preserved.chmod(0o600)
                self.stdout.write(f'Estado anterior preservado: {preserved}')
            fd, temporary = tempfile.mkstemp(prefix='maryruss-restore-', dir=target.parent)
            try:
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(data)
                with sqlite3.connect(temporary) as db:
                    db.execute('DELETE FROM django_session')
                os.replace(temporary, target)
            finally:
                if Path(temporary).exists():
                    Path(temporary).unlink()
            target.chmod(0o600)
        except (OSError, ValueError, sqlite3.DatabaseError, KeyError) as error:
            raise CommandError(f'No se restauró: {error}')
        self.stdout.write(f'Respaldo validado y restaurado: {target}. Las sesiones anteriores se cerraron.')
