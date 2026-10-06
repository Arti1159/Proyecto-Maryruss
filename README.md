# Maryruss · Estudio de producción

Aplicación web en español para seguir producciones por modelo y controlar presupuesto previsto, aprobado y real, por unidad y por total. Usa PEN y fechas de Lima. Los datos se conservan en SQLite, fuera del navegador.

Esta entrega prioriza el seguimiento y el presupuesto solicitado. La especificación completa revisada está en [docs/ESPECIFICACION_COMPLETA.md](docs/ESPECIFICACION_COMPLETA.md); sus funciones posteriores no se presentan como implementadas.

## Qué puedes usar

- Colecciones con presupuesto y fecha objetivo.
- Modelos con código, cantidad prevista, taller, colores y referencia de tallas.
- Presupuesto desglosado: consumo × precio por insumo, aplicado a cada prenda o una vez al lote.
- Totales y costos unitarios, con cálculo decimal y redondeo a céntimos.
- Aprobaciones con versiones conservadas; los cambios del plan no reemplazan silenciosamente lo aprobado.
- Corte, confección, acabados, calidad y rechazos; entregas parciales y límites entre etapas.
- Costos reales por categoría, proveedor y referencia, con pagos acumulados separados.
- Dashboard, filtros, alertas por exceso de costo o entrega vencida y registro de operaciones.
- CSV, respaldo consistente y restauración comprobada.
- Acceso protegido, administrador y operador, y demostración en una base separada.

## Inicio rápido

Requisitos: Python 3.12 o superior compatible con Django 5.2, módulo venv y acceso a PyPI para instalar las dependencias. La interfaz no descarga fuentes ni librerías de terceros.

Desde la raíz del proyecto:

```bash
bash scripts/install.sh
bash scripts/start.sh real
```

La aplicación real usa el puerto **8000** del equipo donde se ejecuta. La instalación crea una cuenta `admin` con contraseña aleatoria y la guarda únicamente en **.data/acceso-inicial.txt**, con permisos privados. Abre ese archivo en tu equipo para consultar el acceso, ingresa y cambia la contraseña desde el menú de la cuenta. No subas ese archivo a Git ni lo compartas.

Para probar con datos ficticios, en otra terminal:

```bash
bash scripts/start.sh demo
```

La demostración usa el puerto **8001**. En su pantalla de entrada pulsa **Entrar a la demostración**. Esta entrada sin contraseña existe únicamente en el modo demo; no está disponible en la base real. Ambas instancias usan cookies y bases de datos distintas.

Los servidores se detienen con Ctrl+C. Los procesos no sobreviven a una restauración del entorno: vuelve a ejecutar el arranque.

### Windows sin Bash

En PowerShell, desde la carpeta del proyecto:

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py init_admin
.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Para explorar la demostración en otra terminal, establece `$env:MARYRUSS_DEMO="1"`, ejecuta `manage.py migrate`, `manage.py seed_demo` y `manage.py runserver 127.0.0.1:8001` con el mismo Python de la carpeta Scripts. Las instrucciones Windows son equivalentes, pero no se han ejecutado en este entorno Linux.

## Primer recorrido con tus datos

1. Crea una colección y define su presupuesto disponible.
2. Añade un modelo, sus unidades y el taller.
3. Añade sus conceptos de costo. Por ejemplo, tela: 1.20 m por prenda a S/ 10 por metro. Para una entrega fija de S/ 100, elige “Una vez al lote”, cantidad 1 y precio 100.
4. Revisa el total y aprueba cantidades y presupuesto. Si supera el presupuesto de la colección, se requiere marcar explícitamente la autorización de exceso.
5. Registra avances adicionales: si ayer cortaste 10 y hoy 5, hoy ingresa solo 5. La etapa previa debe contar con suficientes unidades.
6. Registra costos atribuibles al modelo y cuánto pagaste. Actualizar el total pagado no crea un nuevo costo.
7. Consulta el modelo y el dashboard; exporta o respalda desde la guía.

Un administrador crea colecciones y modelos, edita planes, aprueba, archiva y anula. Un operador consulta y registra avances, costos y pagos. Para agregar operadores, utiliza el comando de Django siguiente, que solicita la contraseña sin mostrarla:

```bash
.venv/bin/python manage.py shell
```

En esa consola:

```python
from getpass import getpass
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
User = get_user_model()
password = getpass("Contraseña: ")
validate_password(password)
User.objects.create_user(username="operador", password=password)
```

Para otro responsable, utiliza `createsuperuser` en lugar de conceder permisos manualmente.

## Definiciones de los números

| Número | Cómo se calcula |
| --- | --- |
| Plan actual | Suma de conceptos: consumo × precio × unidades previstas, o cantidad × precio para costos fijos del lote |
| Presupuesto aprobado | Copia del plan al aprobar, con cantidades y conceptos incluidos |
| Costo unitario previsto | Total del plan dividido entre unidades previstas |
| Costo por unidad del plan aprobado | Costos reales registrados divididos entre unidades autorizadas |
| Costo por prenda buena | Costos reales registrados divididos entre unidades aprobadas por calidad; provisional durante producción parcial |
| Saldo del modelo | Presupuesto de referencia menos costos registrados; referencia aprobada si existe, prevista en caso contrario |
| Pagado | Suma de pagos acumulados de costos no anulados |
| Pendiente de pago | Costo registrado menos pagado |
| Avance | Prendas aprobadas por calidad / unidades del plan |
| Saldo de colección frente a costos | Presupuesto disponible menos costos registrados |

El costo unitario se muestra redondeado; multiplicarlo por cantidades puede diferir en céntimos del total exacto calculado por conceptos. El total es la suma de conceptos redondeados a céntimos. Los costos reales no se generan desde el presupuesto.

Presupuesto, costos y pagos son distintos. No registres una compra de materiales para stock general como consumo de un modelo, ni registres de nuevo su costo cuando pagas. Los gastos compartidos deben asignarse una sola vez a los modelos; esta versión no ofrece distribución automática de esos gastos ni contabilidad.

El dashboard incluye el historial de costos de modelos archivados dentro de colecciones activas. Una colección archivada sale de la vista general; sus datos siguen accesibles en el archivo y las exportaciones. Los CSV por colección incluyen su historial completo y registros anulados identificados; no reproducen todos los filtros de la pantalla.

## Caso numérico del MVP

20 prendas: tela 1.20 m × S/ 10, 4 botones × S/ 0.50, confección S/ 8, empaque S/ 1 y transporte fijo de lote S/ 100. Plan: **S/ 560 total y S/ 28 por prenda**.

Si hay 10 prendas buenas y se registran S/ 330 de costo real, se muestran **S/ 16.50 por unidad del plan de 20** y **S/ 33 por prenda buena de las 10 producidas**. Ambos denominadores se identifican; S/ 33 aún puede ser provisional. Registrar S/ 100 pagados deja S/ 230 pendientes. Actualizar el pagado acumulado a S/ 200 conserva el costo de S/ 330 y deja S/ 130 pendientes.

Las pruebas del navegador ejecutan este recorrido con registros nuevos en una base aislada.

## Persistencia y respaldo

Archivos locales, excluidos de Git:

- .data/maryruss.sqlite3: datos reales, usuarios e historial.
- .data/demo.sqlite3: datos ficticios.
- .data/secret-key: clave de sesiones local, generada una vez.
- .data/acceso-inicial.txt: acceso privado generado, que debes cambiar al ingresar.
- .data/backups/: respaldos creados desde consola.

La instalación es repetible: migra sin borrar información, conserva al administrador y no vuelve a sembrar una demo con datos existentes.

Respaldo desde interfaz: **Guía de uso → Descargar respaldo**, disponible al administrador. Desde consola, incluso con el servidor activo:

```bash
.venv/bin/python manage.py backup
```

El ZIP contiene una copia consistente de SQLite, usuarios y auditoría, con manifest y SHA-256. No contiene contraseñas en texto, clave de sesiones ni archivos de configuración. Conserva el ZIP fuera del equipo: los usuarios y datos del negocio son privados. No hay respaldo automático configurado.

Para verificar recuperación sin tocar los datos actuales:

```bash
.venv/bin/python manage.py restore_backup RUTA_DEL_RESPALDO.zip --target /tmp/maryruss-recuperada.sqlite3 --confirm
```

Para sustituir la base activa, **detén primero el servidor** y omite `--target`. El comando preserva el estado anterior en otro ZIP, comprueba integridad y estructura y cierra las sesiones recuperadas. No mezcla bases. Un respaldo demo solo se restaura en modo demo:

```bash
MARYRUSS_DEMO=1 .venv/bin/python manage.py restore_backup RESPALDO_DEMO.zip --target /tmp/demo-recuperada.sqlite3 --confirm
```

Si olvidas la contraseña del administrador, el comando local de Django permite restablecerla de forma interactiva:

```bash
.venv/bin/python manage.py changepassword admin
```

## Pruebas

```bash
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py test studio
.venv/bin/python -m pip check
```

Las pruebas cubren cálculos, aprobación y versiones, cantidades por etapa, producción parcial, idempotencia, pagos, anulación, permisos, CSRF, fechas, exportación y recuperación.

Prueba opcional de navegador: requiere Playwright y Chromium. Se utiliza una copia aislada, **nunca la base real**. Instala requirements-dev.txt y un navegador compatible si no están disponibles. Prepara la copia:

```bash
MARYRUSS_DEMO=1 .venv/bin/python manage.py backup --output /tmp/demo-para-pruebas.zip
MARYRUSS_DEMO=1 .venv/bin/python manage.py restore_backup /tmp/demo-para-pruebas.zip --target /tmp/demo-pruebas.sqlite3 --confirm
MARYRUSS_DEMO=1 MARYRUSS_DB=/tmp/demo-pruebas.sqlite3 MARYRUSS_PORT=8002 bash scripts/start.sh demo
```

En otra terminal:

```bash
.venv/bin/python scripts/browser_check.py
```

El script usa `/usr/bin/chromium` por defecto; configura CHROMIUM_PATH si está en otra ubicación. Guarda capturas y un informe en test-results/. Incluye dos operaciones simultáneas sobre el mismo modelo para comprobar límites de producción.

## Configuración y publicación

| Variable | Uso |
| --- | --- |
| MARYRUSS_DATA_DIR | Directorio persistente; por defecto .data |
| MARYRUSS_DB | Ruta SQLite alternativa, especialmente para pruebas aisladas |
| MARYRUSS_DEMO | 1 activa la base demo y su acceso de prueba; 0 usa la real |
| MARYRUSS_BIND / MARYRUSS_PORT | Interfaz y puerto del servidor de desarrollo |
| MARYRUSS_ALLOWED_HOSTS | Hosts admitidos separados por comas; por defecto solo loopback |
| MARYRUSS_CSRF_ORIGINS | Orígenes HTTPS confiables separados por comas, si el alojamiento los requiere |
| MARYRUSS_DEBUG | 0 para producción; activa cookies seguras y redirección HTTPS |
| MARYRUSS_SECRET_KEY | Clave privada alternativa; no guardarla en Git |
| MARYRUSS_TRUST_PROXY | 1 solo con un proxy propio que garantice el encabezado HTTPS |
| MARYRUSS_ADMIN_USER / MARYRUSS_ADMIN_PASSWORD | Opcionales para crear el primer acceso; no sustituyen cuentas existentes |

El arranque incluido es de desarrollo. Para publicar datos reales hace falta alojamiento con disco persistente, un dominio permitido, HTTPS y copias externas. No está desplegado un sitio público. No uses el acceso demo ni DEBUG en producción.

Gunicorn está instalado para un despliegue posterior. El proxy o alojamiento debe servir los archivos generados por `collectstatic`; no se sirven automáticamente con DEBUG=0. Antes de desplegar, ejecuta `check --deploy` con la configuración real. Estas condiciones de publicación no se han validado en un alojamiento externo.

SQLite y la serialización de las escrituras cubren el uso pequeño en una instancia. No se ha probado carga masiva, varias instancias o múltiples almacenes. Para crecimiento, evaluar PostgreSQL y medir antes de migrar.

## Próximas fases

1. Distribución validada por talla/color y órdenes por lote, con historial de versiones más completo.
2. Materiales, reservas, compras y consumo con unidades compatibles.
3. Inventario comercial, ventas, devoluciones e importaciones revisables.
4. Comparación de escenarios e investigación con fuentes.
5. Análisis de trazados y, solo con geometrías verificadas, optimización opcional.

Esta entrega no calcula rentabilidad de ventas, impuestos, inventario de telas o trazados. Las referencias de tallas y colores no constituyen un desglose automático. Las prendas aprobadas se cuentan para seguimiento, sin crear un inventario comercial. No hay carga de archivos ni integraciones externas en el MVP actual.
