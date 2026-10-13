# Portable para Windows 11

El lanzador inicia una instancia local, abre el navegador y ofrece una ventana
para volver a abrirlo o apagar la aplicación. Guarda los datos en `datos/`
junto a `Maryruss.exe`, fuera de los archivos empaquetados. No incluye datos,
cuentas ni claves del entorno de desarrollo. Usa una sola instancia por carpeta
de datos y escucha únicamente en loopback, con un puerto asignado por el sistema.

## Generar el ZIP en Windows

Requiere Windows 11 de 64 bits, Python 3.12 de python.org (con el lanzador `py`)
y acceso a PyPI. Desde una copia de este proyecto, haz doble clic en
`desktop/crear-exe.bat`. El resultado es `dist/Maryruss-Windows11.zip`.
Python solo hace falta para **generarlo**, no para usar el ZIP resultante.
Conserva toda la carpeta, incluido `_internal`; no es un EXE suelto.

También se puede generar mediante el workflow manual **Maryruss portable Windows**
de GitHub Actions, una vez que estos archivos estén subidos al repositorio.
El workflow comprueba el ejecutable y permite descargar el ZIP como artifact.
No publica releases ni sube datos privados.

Para validar manualmente el ejecutable generado:

```powershell
.venv-windows\Scripts\python.exe desktop\smoke_check.py dist\Maryruss\Maryruss.exe
```

La comprobación crea una carpeta temporal, prueba ingreso, pantallas, CSS,
descarga de respaldo y dos arranques conservando datos y cuenta. No usa tus datos.
Para comprobar el lanzador desde el código:

```bash
.venv/bin/python desktop/smoke_check.py
```

El empaquetado con PyInstaller debe ejecutarse en Windows; Linux no produce
ejecutables Windows con este procedimiento. El ZIP resultante no está firmado.
Consulta `LEEME.txt` para uso, actualizaciones y respaldo. No se debe usar este
servidor local para publicar la aplicación en Internet.
