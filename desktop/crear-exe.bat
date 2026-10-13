@echo off
setlocal
cd /d "%~dp0.."
py -3.12 -m venv .venv-windows
if errorlevel 1 goto error
.venv-windows\Scripts\python.exe -m pip install -r desktop\requirements-build.txt
if errorlevel 1 goto error
.venv-windows\Scripts\python.exe -m PyInstaller --noconfirm --clean desktop\Maryruss.spec
if errorlevel 1 goto error
.venv-windows\Scripts\python.exe desktop\smoke_check.py dist\Maryruss\Maryruss.exe
if errorlevel 1 goto error
copy /y desktop\LEEME.txt dist\Maryruss\LEEME.txt >nul
powershell -NoProfile -Command "Compress-Archive -Path 'dist\Maryruss' -DestinationPath 'dist\Maryruss-Windows11.zip' -Force"
if errorlevel 1 goto error
echo Listo: dist\Maryruss-Windows11.zip
pause
exit /b 0
:error
echo No se pudo generar el ejecutable. Revisa el error anterior.
pause
exit /b 1
