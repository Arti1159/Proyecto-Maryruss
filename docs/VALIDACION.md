# Validación de la primera versión

Realizada el 6 de octubre de 2026 en el entorno Linux de desarrollo, con Python 3.12 y Django 5.2.17. Las comprobaciones utilizan datos ficticios y bases aisladas.

## Comprobaciones realizadas

- 35 pruebas de dominio y de integración de Django satisfactorias: cálculos decimales, costos por unidad/lote, aprobaciones, versiones, límites de etapas, producción parcial, costos y pagos, reintentos, correcciones, archivo, permisos, CSRF, exportación y respaldo.
- Recorrido de navegador Chromium: 21 comprobaciones satisfactorias, sin errores de JavaScript. Creación de colección y modelo; cinco conceptos; aprobación de S/ 560 y 20 prendas; avance de 10 prendas por todas las etapas; costo S/ 330 y pago acumulado S/ 200.
- Dos solicitudes simultáneas de corte: una se registró y la excedente se rechazó, conservando 18 cortadas de un máximo de 20.
- Vista móvil de 390 px: dashboard, modelos, colecciones, costos, formulario de costo y ficha sin desbordamiento del documento. Las tablas anchas se desplazan dentro de su contenedor.
- Reinicio del servidor de prueba: se conservaron 18 cortadas, 10 prendas buenas, S/ 330 de costo y S/ 200 pagados.
- Descarga de respaldo desde el navegador y restauración en otra base: se verificaron unidades, presupuesto, avances y costos, además de integridad SQLite y cierre de sesiones.
- Acceso real con la cuenta inicial generada: correcto. La base real mantiene cero colecciones y modelos; no recibió los registros ficticios.
- Sesiones real y demo simultáneas: se mantienen separadas mediante nombres de cookies distintos.
- Instalación repetida: conserva las bases, el administrador y los registros demo, sin nuevas migraciones ni duplicados.
- Revisión de Django, coherencia de migraciones y dependencias instaladas: satisfactoria.

## Límites de la evidencia

La validación corresponde a esta máquina. No demuestra un despliegue externo, restauración en una nueva tarea de la plataforma, pruebas en Windows, carga masiva ni varios servidores. El servidor incluido es de desarrollo y escucha en loopback por defecto.

Los costos reales son acumulados registrados por el usuario y pueden estar incompletos. El costo por prenda buena permanece identificado como provisional. No se implementaron compras, stock de materiales, ventas, impuestos, importación ni ploteos en esta primera entrega.

La especificación completa y el documento de revisión conservan el alcance futuro; README describe únicamente lo que se puede usar ahora.
