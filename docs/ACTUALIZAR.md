# Actualizar Maryruss conservando tus datos

Esta actualización agrega un selector Claro / Oscuro / Sistema, ayudas y ejemplos en el presupuesto, Ajustes para administrar categorías de gasto, y el área Planificador para preparar colecciones, variantes, evidencia, propuestas y escenarios. Su uso y límites están en [PLANIFICADOR.md](PLANIFICADOR.md). Las categorías existentes se migran automáticamente; se conservan modelos, costos, pagos, usuarios e importes aprobados.

## Si descargaste el proyecto como ZIP (Windows)

1. En tu aplicación actual, entra a **Guía de uso → Descargar respaldo** y guarda ese ZIP fuera de la carpeta del proyecto. El respaldo de datos es distinto del ZIP del código que descargarás a continuación.
2. Detén el servidor con **Ctrl+C** en la terminal donde lo ejecutas. Si tienes también la demo abierta, detén su servidor.
3. Descarga y extrae el nuevo código: [descargar versión actual](https://github.com/Arti1159/Proyecto-Maryruss/archive/refs/heads/entrega/maryruss-mvp.zip).
4. Abre la carpeta extraída, donde está `manage.py`. **Copia su contenido dentro de tu carpeta anterior del proyecto**, también donde está `manage.py`, y acepta reemplazar los archivos de código. No copies la carpeta contenedora entera como una subcarpeta.
5. **Conserva `.data` y `.venv` de tu carpeta anterior.** El ZIP nuevo no contiene esas carpetas. No borres la carpeta anterior ni su base de datos. `.data` contiene tus registros y la configuración privada; `.venv` contiene el Python instalado.
6. En PowerShell, situado en **tu carpeta anterior ya actualizada**, ejecuta:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Abre `http://127.0.0.1:8000` e ingresa con **tu usuario y contraseña habituales**. No necesitas volver a crear el administrador. Comprueba tus colecciones y modelos; luego entra a **Ajustes** para crear categorías. Si el navegador muestra el diseño anterior, pulsa **Ctrl+F5**.

Si elegiste una carpeta nueva para ejecutar la aplicación, detén el servidor anterior y copia primero la carpeta **`.data` completa** de la carpeta anterior a la nueva. Después crea un nuevo entorno virtual allí, instala las dependencias y ejecuta `migrate`. Abrir una carpeta nueva sin copiar `.data` crea un negocio vacío, no recupera tus registros. Guarda siempre la carpeta anterior hasta verificar la nueva.

Para actualizar la demo, detén su servidor, establece `$env:MARYRUSS_DEMO="1"` y ejecuta `manage.py migrate` con el mismo Python. Después inicia su servidor en el puerto 8001. Para volver a ejecutar tu negocio en esa terminal, establece `$env:MARYRUSS_DEMO="0"`.

## Si usas Git y Linux / macOS

Con el servidor detenido y un respaldo descargado:

```bash
git pull --ff-only origin entrega/maryruss-mvp
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py migrate
MARYRUSS_DEMO=1 .venv/bin/python manage.py migrate
bash scripts/start.sh real
```

Los comandos asumen la rama `entrega/maryruss-mvp` sin cambios locales pendientes y las rutas de base de datos predeterminadas. Si personalizaste `MARYRUSS_DB` o `MARYRUSS_DATA_DIR`, conserva esa configuración y ejecuta la migración sobre la base correcta.

## Cómo usar las mejoras

- **Planificador:** abre el nuevo enlace del menú para crear una colección previa, definir productos y variantes, comparar propuestas y guardar versiones. No cambia automáticamente tus producciones actuales. La evidencia manual funciona sin conectar investigación online.

- **Tema:** el selector de la barra superior funciona en todas las pantallas, incluido el ingreso. También está en Ajustes. Sistema sigue la apariencia del dispositivo; la elección se guarda en cada navegador.
- **Presupuesto:** cada concepto estima un material o servicio. Por prenda multiplica consumo × precio × prendas del modelo. Por lote calcula cantidad × precio una sola vez y distribuye el total entre las prendas. Los iconos de información abren ejemplos y la vista previa separa costo por prenda y costo total.
- **Categorías:** como administrador, entra a Ajustes → Nueva categoría. Puedes cambiar nombre y explicación, archivar y reactivar. Una categoría archivada deja de ofrecerse para registros nuevos, conserva los anteriores y permite completar sus pagos. Renombrarla actualiza su nombre en reportes; no cambia importes ni presupuestos aprobados.
- **Durante un registro:** «Administrar categorías» abre Ajustes en otra pestaña. Después de crear una categoría, vuelve al formulario y pulsa «Actualizar lista»; tus cantidades y precios escritos se conservan.

## Recuperar un respaldo de una versión anterior

El comando `restore_backup` también acepta los respaldos anteriores. Con el servidor detenido, restaura el respaldo según README y **ejecuta `manage.py migrate` antes de iniciar el servidor**. La restauración recupera el esquema de la fecha del respaldo; la migración lo actualiza. Usa el modo real o demo correspondiente al respaldo. Si restauraste con `--target`, ejecuta la migración con `MARYRUSS_DB` apuntando a esa base aislada.
