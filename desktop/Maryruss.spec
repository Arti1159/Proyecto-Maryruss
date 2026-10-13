import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

root = Path(SPECPATH).parent
sys.path.insert(0, str(root))
os.environ['DJANGO_SETTINGS_MODULE'] = 'maryruss.settings'
# Build tooling must never open the user's portable database.
os.environ['MARYRUSS_DATA_DIR'] = str(root / 'build' / 'settings-data')
hidden = []
for package in ('django', 'maryruss', 'studio', 'planner'):
    hidden += collect_submodules(package)
datas = collect_data_files('django')
datas += [(str(root / 'templates'), 'templates'), (str(root / 'static'), 'static')]
a = Analysis([str(root / 'desktop' / 'launcher.py')], pathex=[str(root)],
             binaries=[], datas=datas, hiddenimports=hidden,
             hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Maryruss',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='Maryruss')
