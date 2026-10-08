# Validación de Maryruss

## Actualización del 8 de octubre de 2026

- 71 pruebas de Django satisfactorias, incluidos categorías personalizadas, permisos, migración de una base anterior con aprobaciones intactas y Planificador.
- 147 comprobaciones de Chromium satisfactorias: 21 del recorrido operativo, 82 de temas/presupuesto/categorías y 44 del Planificador. Sin errores JavaScript.
- Selector claro/oscuro/sistema persistente en acceso y todas las pantallas, sincronización de pestañas y cambios de apariencia del dispositivo.
- Formulario de presupuesto con ayudas por teclado y toque, cálculo decimal compatible, costos por prenda y lote y actualización de categorías sin perder los campos escritos.
- Planificador: creación de productos y variantes, vista previa sin guardar, stock y objetivos separados, tres propuestas, evidencia con días disponibles, versiones aprobadas, comparación, CSV coincidente e impresión.
- Móviles de 390 px en ambos temas sin desbordamiento del documento. Las variantes editables se presentan como tarjetas; otras tablas conservan desplazamiento dentro de su contenedor.
- Presupuestos inviables, bloqueos, mínimos, múltiplos, capacidad, plazos, merma, costos faltantes y conciliación de centavos entre caja y stock comprobados.
- Se compararon registros de producción, presupuestos, gastos, pagos y usuarios de las bases anteriores con las migradas: idénticos. Las nuevas tablas no modificaron esas operaciones.
- Recuperación de una copia de datos con proyectos, variantes, evidencia, versiones y categorías: registros idénticos e integridad de relaciones comprobada.
- Conector Tavily probado con respuestas controladas, caché, duplicados, errores y contenido escapado. No hubo consulta real porque no se configuró una clave. La interpretación avanzada de tendencias no está implementada.

Los comandos de prueba están en README. El alcance disponible y pendientes del nuevo módulo se detallan en PLANIFICADOR.md. La validación sigue correspondiendo a esta máquina Linux; no demuestra ejecución en Windows ni despliegue público.

## Primera versión (registro histórico)

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
