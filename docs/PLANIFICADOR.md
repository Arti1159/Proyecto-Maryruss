# Planificador de colecciones: uso y alcance real

El área **Planificador**, en el menú principal, sirve para decidir qué fabricar antes de abrir una producción. Está basada en los requisitos del texto aportado por el usuario. Sus proyectos se guardan en SQLite y se incluyen en el respaldo general. No se guardan exclusivamente en el navegador.

## Primer plan

1. Entra a **Planificador → Nueva colección a planificar**. Registra mercado, ciudades de venta o reventa, público, estilo, canal, moneda y fechas. Define presupuesto total, reserva y gastos fijos, anotando qué incluye cada gasto fijo.
2. Añade uno o varios productos. Registra descripción, enlace opcional a una imagen/ficha, material, tabla de medidas manual, colores y tallas. Introduce un costo variable completo o elige calcularlo con un desglose de componentes. Cada componente tiene consumo por prenda, unidad de compra, precio y merma adicional. Si el consumo ya incluye merma, deja la merma en cero.
3. Confirma disponibilidad, costo y plazo. Configura mínimos por modelo y color, múltiplos por variante y capacidad. Vacío en capacidad significa sin límite declarado; cero significa que no puede fabricarse.
4. En la tabla o tarjetas de variantes, registra stock existente, demanda objetivo opcional y producción nueva. El objetivo incluye stock. Un objetivo de 30 con stock 10 propone 20 nuevas antes de mínimos y múltiplos. Puedes bloquear cantidades, incluido cero.
5. Añade evidencia: ventas propias, reservas pendientes, consultas, falta de stock, observaciones externas o supuestos. Para usar ventas en una variante, identifica color/talla, periodo y días con stock. No se convierten consultas ni publicaciones en ventas.
6. Guarda el borrador. **Proponer tres planes** guarda tres simulaciones sin cambiarlo. Abre cada propuesta para ver explicación, confianza, diferencias frente al borrador, conflictos y supuestos. **Cargar cantidades al borrador** reemplaza cantidades después de revisar, conservando la versión original.
7. Confirma cantidades, costos, disponibilidad y plazos. Guarda una versión de simulación o aprueba una versión revisada. Un plan sin costo confirmado o con restricciones incumplidas no puede aprobarse.
8. Desde una versión, descarga CSV del plan, de evidencia y de supuestos. **Imprimir resumen** usa la impresión de tu navegador y permite guardar un PDF. Los escenarios muestran el resultado bruto, caja y stock restante.

Los operadores pueden consultar; un administrador edita, propone, investiga y aprueba. La elección de tema claro/oscuro/sistema también funciona aquí.

## Reglas visibles de cantidades

- Primero se utiliza el objetivo que ingresaste. Es una decisión o supuesto manual, no una venta comprobada.
- Sin objetivo, se toma el registro más reciente de reservas pendientes de esa variante. Las reservas tampoco se presentan como ventas realizadas.
- Sin reservas, se toma el periodo de ventas propias más reciente con fechas y días con stock: ventas / días disponibles × días de venta del plan. No se suman periodos que podrían solaparse. Es una extrapolación, no una predicción.
- Sin datos utilizables, se propone una prueba mínima de confianza baja. Si ya hay stock y no hay objetivo nuevo, no se propone fabricar otra vez ese stock por defecto.
- Conservador aplica 0.60 al objetivo, Equilibrado 1.00 y Mayor exposición 1.30. Después se resta inventario. Estos factores son supuestos de exposición, no probabilidades de venta. Sin datos, los escenarios pueden coincidir en la misma prueba mínima; se indica esa razón.
- Las cantidades se distribuyen en paquetes enteros según objetivos de las variantes. Se reservan mínimos de colores que caben y se reparte el resto proporcionalmente a objetivos pendientes. Se priorizan modelos con reservas, después ventas propias y finalmente orden de alta.
- Es una heurística transparente; no garantiza la solución óptima global. Una propuesta puede omitir colores o modelos para no forzar un mínimo que exceda presupuesto o capacidad. Puedes editar y comparar el resultado.
- Las cantidades bloqueadas se conservan. Si superan presupuesto, múltiplos, capacidad o disponibilidad, se muestra el conflicto; no se recortan silenciosamente.
- Cada propuesta verifica producción + fijos + reserva frente al presupuesto. Si no hay un lote positivo factible, lo explica. No aumenta presupuesto para cumplir mínimos.

## Lectura de costos y escenarios

Todo el proyecto utiliza PEN, USD o EUR, según tu elección. Cambiar la moneda cambia la unidad nominal y **no realiza conversión de importes**; revisa valores. No se mezclan monedas en un proyecto.

Solo se suma el costo variable completo **o** el desglose, según el método elegido. Los gastos fijos se suman una vez y la reserva no se gasta. El costo por prenda con fijos distribuidos se muestra como referencia y no se vuelve a sumar al total.

La producción nueva es distinta del inventario existente. Los escenarios de venta se calculan únicamente sobre el lote nuevo, con 0%, tu supuesto editable y 100% vendido. Las unidades vendidas se redondean hacia abajo por variante. Un escenario de venta completa no garantiza que ocurra.

- Ingresos: precio ponderado minorista/mayorista, después del descuento, por unidades vendidas.
- Efectivo recuperado: ingresos menos comisiones y costos de venta por unidad.
- Efectivo invertido: costo variable de **todo** lo fabricado + gastos fijos. La reserva permanece separada.
- Resultado bruto estimado: efectivo recuperado − costo variable de lo vendido − gastos fijos de la colección.
- Diferencia de caja: efectivo recuperado − todo el efectivo invertido.
- Stock restante: costo variable pendiente, conciliado con los centavos invertidos en cada variante.
- Margen sobre venta: (precio descontado − costo variable) / precio descontado. Recargo sobre costo: (precio descontado − costo variable) / costo variable. Se muestran antes de comisiones y gastos fijos.

No se llama ganancia neta: pueden faltar gastos generales del negocio. La base de impuestos se documenta por el usuario; no hay una conclusión tributaria automática. Si faltan costos o precios, los resultados correspondientes quedan pendientes.

## Evidencia e investigación online

La evidencia manual funciona siempre. Se conserva URL, mercado, tipo de señal, fecha de publicación si se conoce, fecha de consulta, periodo, disponibilidad y limitaciones. Las observaciones externas se agrupan por campaña o URL, ignorando parámetros de seguimiento. Una fecha de consulta no prueba actualidad. Una referencia internacional no obtiene automáticamente confianza local alta.

Existe un conector real de búsqueda y lectura desde el servidor para **Tavily**. Si no hay clave, el área muestra **sin investigación actual online** y los botones no generan resultados ficticios.

Para habilitarlo, crea tu propia cuenta y clave en [Tavily](https://tavily.com/) y configura `TAVILY_API_KEY` o `MARYRUSS_RESEARCH_API_KEY` en el entorno del servidor. Nunca añadas la clave al repositorio ni la publiques en el navegador. En PowerShell, antes de iniciar el servidor:

```powershell
$env:TAVILY_API_KEY="TU_CLAVE_PRIVADA"
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

En un servidor publicado, usa su gestor de secretos. Reinicia el servidor después de cambiar la configuración. La clave no se escribe en modelos, plantillas, exportaciones ni mensajes de error.

**Analizar temporada** consulta el mercado, público, estilo, productos y ventana indicada. Usa búsqueda básica, hasta ocho resultados y texto de fuentes que el servicio pueda leer. Conserva las fuentes realmente devueltas, marca lectura completa no disponible si solo hay extracto y mantiene fecha de publicación desconocida cuando no se aporta. Hay caché de seis horas por consulta; **Actualizar investigación** hace una nueva llamada. Cada llamada puede consumir cuota o créditos de tu proveedor; no hay tareas recurrentes automáticas.

La ventana de 30 a 90 días forma parte de la consulta y del control de antigüedad manual; no garantiza que cada resultado publicado tenga esa edad. Revisa fechas y pertinencia. No se promete acceso a feeds privados, cuentas bloqueadas, métricas privadas, APIs de Pinterest/Google Trends o publicaciones no indexadas.

El conector busca y conserva fuentes; **no es un asistente de IA que predice ventas**. No hay clasificación automática de colores, siluetas, saturación, clima o subida/bajada de tendencias ni comparación climática histórica implementada. El informe distingue fuentes y límites, y permite completar la interpretación manualmente. Su estado de evolución permanece “evidencia insuficiente” cuando no existe análisis temporal verificable.

La integración se verificó con respuestas controladas y fallos de conexión. **No se ejecutó una consulta real de Tavily en esta entrega porque no se proporcionó una clave.** La disponibilidad y cuota reales se comprueban al conectar tu servicio.

## Versiones y conexión con producción

Una versión conserva datos del proyecto, productos, costos, cantidades, evidencia, supuestos, escenarios e investigación disponible en esa fecha. Editar el borrador, cambiar precios o añadir fuentes no modifica versiones anteriores. Cargar una propuesta se recalcula con datos actuales y no reemplaza cantidades bloqueadas incompatibles.

El planificador es un área previa e independiente: **no abre ni altera automáticamente un lote de producción**. Una vez revisado, puedes trasladar las cantidades y costos a los modelos de producción existentes. La transferencia automática está pendiente.

## Qué sigue pendiente del documento completo

Análisis de imágenes con IA y subida de archivos visuales; asistentes de interpretación de tendencias; búsqueda/comparación automática con la misma temporada del año anterior; conectores específicos de clima, calendarios, redes, Google Trends o Pinterest; curvas de demanda avanzadas y optimización global; importación masiva de ventas; unidades de material disponibles con inventario físico y restricciones de consumo agregadas; impuestos calculados; conversión monetaria y sincronización con otros dispositivos mediante alojamiento público; transferencia automática del plan a producción.

Un proyecto admite hasta 1 000 variantes y la creación de un producto genera hasta 60 combinaciones por vez. Estos límites evitan formularios ilimitados; no equivalen a una prueba de carga masiva.

El stock actual se registra por variante, no es un inventario comercial con entradas y ventas contabilizadas. Colores/tallas disponibles se declaran manualmente. Capacidad y fecha se verifican por modelo, sin programar recursos compartidos entre modelos. Estas limitaciones no se presentan como implementadas.
