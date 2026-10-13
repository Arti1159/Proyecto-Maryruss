import hashlib
import io
import json
import sqlite3
import tempfile
import zipfile
from contextlib import closing
from pathlib import Path
from django.conf import settings
from django.utils import timezone

def create_backup(db_path=None):
    source_path = Path(db_path or settings.DATABASES['default']['NAME'])
    if not source_path.is_file():
        raise ValueError('No se encontró una base de datos persistente.')
    with tempfile.TemporaryDirectory(prefix='maryruss-backup-') as directory:
        snapshot = Path(directory) / 'database.sqlite3'
        with closing(sqlite3.connect(source_path)) as source, closing(sqlite3.connect(snapshot)) as target:
            source.backup(target)
        data = snapshot.read_bytes()
    manifest = {'format': 'maryruss-backup', 'version': 1, 'created_at': timezone.now().isoformat(),
                'demo': settings.DEMO_MODE, 'sha256': hashlib.sha256(data).hexdigest(),
                'includes': ['database', 'users', 'audit'], 'attachments': False}
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('database.sqlite3', data)
        archive.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))
    return output.getvalue()

def validate_backup(payload):
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            if set(archive.namelist()) != {'database.sqlite3', 'manifest.json'}:
                raise ValueError('El respaldo no contiene los archivos esperados.')
            if archive.getinfo('database.sqlite3').file_size > 200 * 1024 * 1024 or archive.getinfo('manifest.json').file_size > 16384:
                raise ValueError('El respaldo supera el límite permitido.')
            manifest = json.loads(archive.read('manifest.json'))
            data = archive.read('database.sqlite3')
    except (zipfile.BadZipFile, json.JSONDecodeError, KeyError) as error:
        raise ValueError('El archivo no es un respaldo Maryruss válido.') from error
    if manifest.get('format') != 'maryruss-backup' or manifest.get('version') != 1:
        raise ValueError('Formato de respaldo incompatible.')
    if hashlib.sha256(data).hexdigest() != manifest.get('sha256'):
        raise ValueError('El respaldo está dañado: su comprobación de integridad no coincide.')
    with tempfile.TemporaryDirectory(prefix='maryruss-verify-') as directory:
        path = Path(directory) / 'check.sqlite3'
        path.write_bytes(data)
        with closing(sqlite3.connect(path)) as db:
            if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or db.execute('PRAGMA foreign_key_check').fetchall():
                raise ValueError('La base de datos del respaldo no supera la validación.')
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {'studio_collection', 'studio_garment', 'studio_expense', 'studio_productionevent', 'auth_user', 'django_migrations', 'django_session'} <= tables:
                raise ValueError('La base no corresponde a Maryruss.')
            required_fields = {'approved_snapshot', 'approved_units', 'approved_budget', 'planned_units'}
            if not required_fields <= {row[1] for row in db.execute('PRAGMA table_info(studio_garment)')}:
                raise ValueError('La estructura del respaldo es incompatible.')
    return manifest, data
