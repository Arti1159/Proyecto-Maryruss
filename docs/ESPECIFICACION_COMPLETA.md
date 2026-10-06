# Encargo de desarrollo: gestión de colecciones y producción para Maryruss

## 1. Objetivo y contexto

Construye una aplicación web en español para una tienda de ropa pequeña en Lima, Perú. Debe permitir gestionar una colección desde su planificación hasta su producción, inventario, ventas y evaluación económica, con operaciones persistentes y cálculos verificables.

Usa soles peruanos (PEN), fechas visibles según America/Lima y medidas explícitas en centímetros, metros, kilogramos o unidades, según el material. La interfaz debe funcionar en computadora y celular con conexión a internet. No se requiere una aplicación nativa ni funcionamiento sin conexión en la primera versión.

El éxito inicial es poder completar un recorrido real de una colección y explicar sus cantidades, materiales, gastos, existencias y ventas. Un dashboard, un chat o datos guardados únicamente en el navegador no satisfacen el encargo.

Antes de comenzar, vuelve a revisar el repositorio, sus instrucciones y los archivos existentes. Si está vacío, inicia un proyecto nuevo. No supongas que existe una aplicación por el nombre del repositorio. Conserva los archivos y cambios del usuario que encuentres.

## 2. Alcance y forma de trabajo

La versión inicial atenderá una empresa, una moneda, un local lógico de inventario y pocos usuarios. Permitirá registrar proveedores y talleres externos sin exigirles una cuenta. No será inicialmente un sistema contable, una plataforma de comercio electrónico ni un programa CAD.

Trabaja por entregas verticales: cada entrega debe incluir datos, reglas, interfaz y pruebas del recorrido que incorpora. Evita crear todos los módulos como pantallas vacías.

- Comienza por el modelo de datos y un recorrido pequeño de punta a punta.
- Usa decisiones reversibles y valores configurables cuando no exista un requisito indispensable.
- Pregunta solo por información que impida avanzar; documenta los supuestos restantes.
- Mantén una lista de funciones operativas, parciales y pendientes. No simules integraciones ni presentes una estimación como un resultado real.
- Separa los datos de demostración de los datos reales mediante bases de datos o espacios aislados. Identifica claramente el modo demostración.
- No copies automáticamente una propuesta, una simulación o un dato de ejemplo a una compra, venta o movimiento real.
- No prometas plazos, precios de desarrollo o rendimiento sin haber evaluado el proyecto y el alojamiento.

## 3. Arquitectura propuesta para un proyecto nuevo

Si no existe una tecnología que deba mantenerse, utiliza una aplicación monolítica con Django en una versión LTS soportada, vistas de servidor y JavaScript ligero para cálculos y operaciones interactivas. Usa su sistema de usuarios, migraciones y pruebas. Una alternativa está permitida si se justifica por el proyecto existente y mantiene las mismas garantías.

Para desarrollo y uso interno pequeño en una sola instancia, SQLite es un punto de partida razonable. La base de datos debe estar fuera de los archivos temporales del servidor. Antes de producción, comprueba las escrituras simultáneas y las capacidades del alojamiento. Usa PostgreSQL si se necesitan varias instancias, concurrencia relevante o si la plataforma no ofrece un disco persistente compatible.

Guarda adjuntos en almacenamiento persistente y referencias en la base de datos. No guardes archivos del negocio en el repositorio. El almacenamiento del navegador puede conservar preferencias de interfaz; no será la fuente principal de datos operativos.

Evita microservicios, colas de trabajo y servicios externos en el MVP salvo que una necesidad comprobada los justifique. Las operaciones de inventario deben confirmarse dentro de transacciones de base de datos. La configuración, rutas de almacenamiento y credenciales deben estar fuera del código.

Esta arquitectura es una recomendación de implementación, no una función que deba mostrarse al usuario en sus formularios de negocio.

## 4. Modelo de datos mínimo

Define entidades relacionadas, restricciones y migraciones. No concentres los módulos en un único objeto JSON sin integridad referencial.

| Entidad | Datos y relaciones mínimos |
| --- | --- |
| Colección | Nombre, temporada comercial, fechas, público objetivo, responsable, presupuesto, estado y notas |
| Modelo | Código único, descripción, ficha técnica, fotos, archivos y relación con colección |
| Variante | Modelo, color y talla; código único y posibilidad de archivo |
| Plan de colección | Versión, cantidades por variante, precios previstos, supuestos y aprobación |
| Ficha de consumo | Versión por modelo o variante, materiales, consumo, unidades y pérdidas incluidas |
| Material | Código, tipo, unidad base, especificaciones y estado |
| Lote de material | Material, proveedor, color, características físicas, costo, cantidad utilizable y observaciones |
| Reserva | Orden, lote o material específico, cantidad, vigencia y estado |
| Proveedor o taller | Identidad comercial, contacto y notas; sin datos innecesarios |
| Pedido de compra | Proveedor, líneas, unidades, precio acordado, estado y vínculos de colección |
| Recepción de compra | Pedido, lotes, cantidades aceptadas y rechazadas, costo y fecha |
| Pago o devolución de pago | Documento relacionado, importe, fecha y concepto |
| Orden de producción | Colección, versión aprobada, cantidades por variante, taller, fechas y estado |
| Evento de producción | Orden, variante, etapa, cantidad, fecha, responsable e incidencia |
| Movimiento de material | Lote, orden o documento origen, tipo, cantidad y costo registrado |
| Lote de prendas | Orden, variantes, ingresos aprobados y estado del costo |
| Movimiento de prenda | Variante, lote, ingreso, salida, devolución o ajuste |
| Venta | Fecha, líneas por variante y lote, cantidades, precio, descuento, impuestos configurados y estado |
| Devolución | Venta original, cantidades, importe y disposición de la prenda |
| Gasto o servicio | Colección u orden, categoría, importe, fecha, criterio y pagos asociados |
| Registro de auditoría | Usuario, fecha, operación, entidad, motivo y referencia de corrección |

En fases posteriores incorpora fuentes de investigación, propuestas, escenarios, importaciones y trazados. Define desde el inicio identificadores estables para poder relacionarlos.

Cada entidad operativa tendrá identificador, fecha de creación, fecha de actualización y autor cuando corresponda. Los códigos de negocio no deben cambiar silenciosamente al editar un nombre.

## 5. Estados, versiones y correcciones

Usa pocos estados, con reglas explícitas:

- Colección: borrador, aprobada, en producción, cerrada, archivada.
- Orden: borrador, autorizada, en curso, completada, cancelada.
- Compra: borrador, confirmada, recepción parcial, recibida, cancelada. El pago se informa por separado.
- Venta: borrador, registrada, anulada. Las devoluciones se relacionan con la venta registrada.
- Trazado: estimación manual, verificado, propuesta pendiente de validación; añade su aprobación para corte por separado.

Una aprobación guarda una versión de cantidades, consumos y supuestos. Si posteriormente se cambia un modelo, una tela o un precio, muestra la diferencia para operaciones futuras. No reescribas las órdenes ya autorizadas ni sus costos registrados.

Editar es apropiado para borradores. Después de registrar un movimiento que cambia saldos, corrige mediante una reversión o un ajuste relacionado, con motivo. Archivar no elimina historial. No borres registros referenciados por operaciones.

Cancelar una orden libera reservas pendientes, pero no devuelve materiales consumidos ni elimina prendas ingresadas. Esas operaciones requieren movimientos específicos. No canceles automáticamente pedidos relacionados.

## 6. Colecciones, modelos, variantes y cantidades

Permite crear, editar, archivar, buscar y filtrar colecciones y modelos. Cada variante debe corresponder a una combinación válida de modelo, color y talla. No generes combinaciones que el usuario haya excluido.

El plan mostrará cantidades previstas y aprobadas por variante. Las cantidades de prendas e insumos discretos serán enteros no negativos. Una aprobación debe rechazar un total incompatible con su distribución.

Para distribuir un total por porcentajes:

1. Valida que los porcentajes de las opciones seleccionadas sumen 100 %. No normalices valores incorrectos sin informar y confirmar la corrección.
2. Calcula las cuotas sin redondear y toma su parte entera inferior.
3. Reparte las unidades restantes según los mayores restos decimales; usa un orden estable para resolver empates.
4. Permite ajustes manuales, mostrando la diferencia hasta que el total coincida.

Si se usan porcentajes independientes de tallas y colores, distribuye primero por color y luego por talla dentro de cada color. Este método conserva el total, pero puede no producir simultáneamente las cuotas marginales exactas de tallas. Muestra la matriz final y esa limitación. Si el usuario exige ambos márgenes exactos, requiere una matriz explícita o un método adicional probado; no prometas que el redondeo simple lo garantiza.

Distingue planificado, aprobado para producir, cortado, confeccionado, aprobado por calidad, rechazado, disponible y vendido. Son conceptos diferentes; no los sumes como si fueran stocks independientes.

Los escenarios conservador, base y optimista serán copias de un plan con supuestos visibles. Ninguno se aprueba ni genera una compra por sí mismo.

## 7. Materiales, unidades, reservas y faltantes

Cada material tendrá una unidad base. Para telas puede ser metro o kilogramo; para insumos, unidad o una unidad de longitud. Registra unidad de compra y factor de conversión solo cuando sea válido y conocido.

Para tela registra, cuando esté disponible: composición, ancho total y útil, color, proveedor, lote, sentido, elasticidad, repetición de estampado, direccionalidad, encogimiento, defectos y si cada dato es medido o estimado. No obligues a inventar valores desconocidos; identifica qué cálculos quedan limitados.

Las reservas no consumen stock. La existencia utilizable se obtiene de movimientos aceptados; material defectuoso, en cuarentena o rechazado se excluye. Las reservas activas se restan para informar cuánto puede asignarse a una orden nueva.

Para una orden existente, su propio material reservado sigue estando disponible para esa orden. Al consumirlo, reduce existencia y libera la reserva correspondiente en la misma transacción. No restes esa reserva dos veces.

Para cada material compatible:

- Necesidad total = suma de cantidades por variante × consumo autorizado por variante.
- Necesidad restante = necesidad de las unidades aún por producir, descontando solo consumos y avances realmente aplicables.
- Cobertura = reservas propias todavía no consumidas + existencia libre que pueda asignarse.
- Faltante = máximo entre cero y necesidad restante menos cobertura.

En planes preliminares, muestra cobertura potencial sin reservarla. Al autorizar una orden, vuelve a validar y crear reservas. Dos usuarios u órdenes no deben asignarse el mismo saldo simultáneamente.

No consolides materiales distintos solo porque comparten descripción. Respeta composición, color, ancho, calidad y compatibilidad de lote. Una sustitución requiere aceptación y una nueva versión del cálculo pendiente.

Si el faltante es cero, compra sugerida es cero. Si es positivo y el proveedor exige mínimo M y múltiplo Q, usa Q × techo(máximo(faltante, M) / Q), con Q positivo. M y Q deben estar expresados en la unidad de compra. Si la compra es por rollos de longitud variable, registra el contenido real del rollo; no inventes una conversión fija.

Muestra cantidad sugerida, costo, mínimo aplicado, múltiplo y sobrante. Las sugerencias no modifican stock ni crean pedidos sin una acción explícita.

No conviertas kilogramos a metros sin ancho, gramaje y compatibilidad de las mediciones. Si se conoce un gramaje g en g/m² y ancho w en metros, metros = kilogramos × 1000 / (g × w). Registra que es una conversión teórica, sensible a las mediciones; para comprometer una compra o corte prefiere medición del lote o información validada del proveedor.

Representa dinero y cantidades con decimales exactos, no con números binarios de punto flotante. Define precisión por unidad, redondeo monetario final a céntimos y reglas de presentación. No confundas redondeo de visualización con redondeo de la compra.

## 8. Consumo, pérdidas y encogimiento

Cada consumo debe indicar su origen: manual estimado, medido en producción o calculado con trazado verificado. También debe indicar si incluye márgenes, pérdida de corte, encogimiento u otros ajustes.

No existe un porcentaje universal de merma. Si un consumo ya incorpora una pérdida, no la vuelvas a aplicar. Diferencia pérdida de planificación y desperdicio real registrado.

Para un margen operativo añadido sobre un consumo limpio c, una fórmula posible es c × (1 + p), únicamente si p está definido como recargo sobre ese consumo. Si p representa la fracción inutilizable del material comprado, la fórmula es c / (1 − p). No intercambies ambas interpretaciones.

Para encogimiento lineal s medido respecto de la longitud antes del tratamiento, una longitud útil L después del tratamiento exige L / (1 − s) antes del tratamiento. Exige 0 ≤ s < 1 y que el modelo sea aplicable. El encogimiento transversal también puede alterar el ancho útil y el trazado: no lo resuelvas aumentando únicamente el largo.

El MVP podrá usar consumos manuales ya ajustados y trazables. Aplicar encogimiento automáticamente solo será válido cuando estén definidos medición, tratamiento y relación con el trazado.

## 9. Compras, recepciones y pagos

En el MVP permite pedidos sencillos, recepciones parciales, anticipos y pagos. Las cotizaciones comparables, aprobaciones complejas y cuentas por pagar avanzadas pueden incorporarse después.

La confirmación de un pedido registra un compromiso; no aumenta stock. La recepción aceptada crea los lotes y movimientos de ingreso; la cantidad rechazada no queda disponible. El pago cambia caja o saldo del pedido; no crea otro ingreso de material.

Registra diferencias entre cantidad pedida, recibida y aceptada, y entre precio previsto y costo real. Una recepción repetida con la misma referencia operativa no puede duplicar stock.

Si una compra sirve a varias colecciones, registra asignaciones para los informes y comprueba que sumen el total asignable. No vuelvas a contar el pedido completo en cada colección.

El costo del lote debe indicar precio y costos de adquisición incluidos. No presupongas que un impuesto es recuperable. Si el costo todavía es desconocido, informa “pendiente”; no lo conviertas silenciosamente en cero.

## 10. Producción parcial, calidad e inventario

Una orden autorizada copia la versión aprobada de cantidades y consumos. Puede completarse mediante varias entregas y con materiales comprados en momentos diferentes.

Registra por variante eventos de corte, confección, acabado y calidad. Un avance debe estar limitado por la cantidad disponible en su etapa anterior, salvo un saldo inicial documentado. La misma prenda puede avanzar por varias etapas; eso no produce nuevas unidades en cada etapa.

Separa rechazos definitivos, prendas pendientes de revisión y reprocesos. Un reproceso no aumenta la producción de prendas nuevas. Registra desperdicios y devoluciones de material utilizable mediante movimientos distintos.

Para el MVP, el ingreso a inventario de prendas será una operación explícita, vinculada a una entrega aprobada por calidad. No ingreses automáticamente cantidades previstas, cortadas o confeccionadas. Una aprobación no puede ingresar dos veces las mismas unidades.

No permitas consumir más material utilizable que el disponible para la orden. Si el consumo real supera el estimado, registra una incidencia y el abastecimiento o ajuste necesario; no generes saldo negativo oculto.

Informa materiales limitantes y una producción parcial factible. Los máximos calculados por material de forma independiente no garantizan una distribución factible entre variantes: valida el conjunto elegido contra todos los materiales compartidos antes de autorizarlo.

Registra taller, responsable, fechas previstas y reales, incidencias y entregas parciales. Identifica atrasos a partir de fechas vencidas con cantidades pendientes, sin afirmar automáticamente su causa.

## 11. Ventas, cambios y devoluciones

La primera versión incluirá ventas manuales por variante y lote, descuentos, precio efectivo y cobros separados. No se requiere una integración comercial ni facturación electrónica.

Una venta registrada descuenta prendas disponibles una sola vez. No permite vender prendas pendientes de calidad ni más stock que el disponible. El cobro no descuenta otro stock.

Una devolución referencia la venta original y no puede superar lo vendido neto de devoluciones anteriores. Registra por separado el importe devuelto y la disposición física:

- Apta para venta: retorna al lote o a uno relacionado conservando trazabilidad.
- Pendiente de revisión: queda fuera del stock vendible.
- Defectuosa: registra pérdida o reproceso, sin devolverla automáticamente al stock disponible.

Un cambio puede representarse como devolución y nueva venta vinculadas. En el MVP no hacen falta reservas de clientes, crédito comercial ni reglas promocionales complejas.

## 12. Costos y presupuesto

Presenta costos previstos, aprobados y reales por separado. Distingue además si un costo real está completo o todavía es provisional.

Separa como mínimo:

- Materiales comprados y su inventario.
- Materiales realmente consumidos en una orden.
- Servicios y costos de fabricación de esa orden.
- Prendas terminadas en inventario y costo de las vendidas.
- Gastos de colección, como campaña o fotografías.
- Gastos generales registrados, como alquiler, si se incluyen en el informe.
- Pagos, anticipos y cobros, que afectan caja.

Comprar tela no implica consumirla ni vender prendas. Pagar una compra no es un segundo costo de fabricación. Un anticipo no equivale por sí mismo a un gasto adicional.

Para el MVP identifica el lote de material consumido y conserva su costo de adquisición registrado. En prendas, identifica el lote del que sale la venta. No uses el precio actual del catálogo para recalcular silenciosamente operaciones históricas.

El costo de fabricación incluye materiales consumidos y servicios atribuibles a las prendas. Los gastos comerciales de colección se muestran por separado en el resultado. Puede ofrecerse una vista de costo completo asignado por unidad para planificación, pero no debe restarse nuevamente un gasto ya distribuido.

Define el criterio de distribución de costos compartidos: unidades, consumo u otro criterio explícito. Usa unidades como valor inicial solo cuando resulte razonable para esos modelos. Guarda criterio y base aplicada. Si no hay prendas aprobadas, no dividas por cero; informa costo pendiente o producción en curso.

El costo de un lote puede ser provisional durante entregas parciales. Al cerrar sus costos, distribuye el costo atribuible entre las unidades buenas realmente ingresadas según el criterio elegido. Conserva estimaciones y costos registrados en ventas; registra un ajuste identificable para presentar el resultado actualizado. No alteres los movimientos originales ni presentes el resultado como definitivo antes del cierre.

Para mantener sencilla la primera versión, no implementes contabilidad general ni valoración avanzada de producción en curso. Muestra los costos asociados a órdenes todavía abiertas como pendientes de cierre, y explica su efecto sobre los informes.

El presupuesto inicial será un presupuesto de desembolsos de colección. Muestra:

- Presupuesto aprobado.
- Pagos imputados a la colección, incluidos anticipos.
- Compromisos confirmados pendientes de pago, netos de anticipos y cancelaciones.
- Saldo presupuestario = presupuesto aprobado − pagos imputados − compromisos pendientes de pago.
- Necesidades estimadas aún no comprometidas, en una línea separada.

No descuentes además el valor total de un pedido cuyo pago y saldo pendiente ya aparecen. Un saldo presupuestario negativo puede mostrarse como exceso; aprobar compromisos por encima del presupuesto debe ser una decisión explícita.

Para el flujo de caja de un período, muestra cobros y pagos efectivamente registrados. No lo denomines utilidad ni saldo bancario verificado si no existe conciliación bancaria.

## 13. Precios, impuestos y rentabilidad

Configura si el precio incluye impuestos, tasa aplicable, descuentos, comisiones y costos de venta. No elijas automáticamente un régimen tributario peruano. El uso de PEN no basta para determinar obligaciones fiscales.

En un caso simple con una sola tasa t incluida en el precio efectivo P, ingreso sin ese impuesto = P / (1 + t). Documenta que esta fórmula no modela todas las operaciones tributarias y debe validarse con el contador. El modo demostración puede usar tasa cero identificada como supuesto ficticio.

Define los indicadores y sus denominadores:

- Ventas netas: ingresos después de descuentos y devoluciones, excluyendo impuestos que corresponda separar según configuración.
- Costo de prendas vendidas: costo de las unidades efectivamente vendidas, ajustado por devoluciones aptas y por ajustes de costo identificados.
- Utilidad bruta = ventas netas − costo de prendas vendidas.
- Margen bruto sobre ventas = utilidad bruta / ventas netas.
- Recargo sobre costo = (precio neto unitario − costo unitario) / costo unitario, para una comparación homogénea.
- Contribución = ventas netas − costos variables de las unidades vendidas − costos variables de venta.
- Resultado después de gastos incluidos = utilidad bruta − costos de venta − gastos de colección y generales expresamente incluidos.

No llames utilidad neta al resultado si faltan gastos, tributos o ajustes relevantes. Denominadores cero o negativos requieren un resultado no aplicable o una explicación, no un porcentaje engañoso.

El punto de equilibrio en unidades, gastos fijos / contribución unitaria, solo aplica con contribución positiva y supuestos estables. Para varios modelos, muestra la mezcla de ventas asumida. No distribuyas una misma cantidad de gastos fijos entre cálculos independientes y luego sumes resultados incompatibles.

Las proyecciones deben especificar unidades vendidas, precio efectivo, descuentos, devoluciones y costos. Las unidades producidas no se consideran vendidas por defecto. Muestra por separado inventario pendiente, valor de ese inventario y entradas/salidas de caja. Material aún disponible y prendas sin vender representan existencias diferentes.

## 14. Dashboard e informes

El dashboard resumirá operaciones reales y permitirá abrir sus registros de origen. Separa la vista operativa actual de los informes de un período.

Incluye filtros por colección, fechas, modelo y estado cuando tengan sentido para el indicador. Especifica si un filtro de fecha usa fecha de venta, pago, producción o movimiento. No mezcles automáticamente pagos históricos y ventas del período.

Muestra presupuesto, compromisos, pagos, necesidades pendientes, producción por etapa, prendas disponibles, ventas, devoluciones, costos, utilidad bruta, resultado con gastos incluidos, faltantes y atrasos. Marca estimaciones, datos incompletos y costos provisionales.

Cada indicador tendrá definición, unidad, período y acceso a sus registros. Si no hay datos, presenta un estado vacío útil, no valores inventados.

Desde el MVP permite exportar los registros principales en CSV UTF-8 con identificadores y unidades, así como informes legibles. La exportación analítica no sustituye al respaldo completo.

## 15. Investigación, propuestas e importación: fase posterior

Permite definir temporada de venta, ubicación, cliente, estilo, precios objetivo, presupuesto y capacidad de taller. Para Lima distingue calendario comercial de condiciones climáticas; no asumas que las temporadas internacionales coinciden automáticamente con la demanda local.

El MVP tendrá un registro manual de referencias y notas. La investigación web asistida se incorpora únicamente cuando exista acceso verificable a búsqueda. Cada referencia tendrá enlace o archivo, fecha de consulta, mercado, observación y limitaciones. Separa evidencia, interpretación e hipótesis. No inventes precios ni extrapoles demanda a partir de popularidad en redes.

Las propuestas editables podrán incluir concepto, colores, modelos, telas, precios y cantidades piloto. Deben explicar supuestos y la relación con ventas, devoluciones y stock existentes. Sin historial suficiente, presenta escenarios, no pronósticos con certeza falsa. Una propuesta requiere revisión y aprobación antes de convertirse en un plan operativo.

En la fase 2 implementa importación de ventas e inventario por CSV. Añade Excel cuando se prueben sus formatos y restricciones. El proceso tendrá mapeo de columnas, vista previa, validación por fila, resumen de errores y confirmación final.

No confundas una carga de saldo inicial con movimientos de ventas. La carga inicial requiere fecha de corte y estado de conciliación; repetirla no suma el mismo stock.

Identifica registros por sistema de origen e identificador externo cuando existan. Una huella del archivo ayuda a detectar repeticiones exactas, pero no basta para archivos editados o exportaciones solapadas. Ante coincidencias ambiguas, solicita revisión y no importe movimientos automáticamente. Registra sesión, filas importadas y motivo de exclusión.

La repetición de una misma importación debe ser segura. Las transacciones y claves de operación también deben proteger ventas, recepciones e ingresos manuales ante doble clic o reintentos.

No prometas integraciones directas con plataformas sin comprobar acceso, API, condiciones y modelo de datos.

## 16. Moldes y trazados: alcance por niveles

En el MVP permite adjuntar archivos, describirlos y registrar manualmente medidas y composición del trazado. La carga de un PDF o imagen no implica extracción automática de geometrías ni verificación de escala.

Antes de un cálculo registra formato, unidad, escala o referencia, ancho útil, largo del trazado, prendas completas por talla y modelo, piezas espejadas, márgenes incluidos, tela abierta o al doble, capas y restricciones. Cada parámetro esencial desconocido limita el resultado a una estimación.

Una imagen sin escala verificable solo permite una estimación documentada. No debe generar un plano de corte aprobado ni una medida exacta para comprar. La persona técnica del taller verifica escala, piezas y viabilidad física.

Para un trazado confirmado, sin pérdidas duplicadas:

- Longitud de un tendido = largo del trazado + pérdidas de extremos no incluidas.
- Tela necesaria para varios tendidos = suma de longitud de cada tendido × sus capas.
- Prendas por variante = suma de prendas completas de esa variante representadas por capa × capas, aplicando la convención de tela abierta o doblada que se haya validado.
- Consumo promedio = tela total / prendas completas totales, si el denominador es positivo.

El promedio de un trazado con varios modelos no determina el consumo individual de cada modelo. Para asignarlo hace falta un criterio adicional registrado. Una mezcla de tallas produce la proporción del trazado, no necesariamente la del pedido; comprueba sobrantes y faltantes por variante.

No multipliques de nuevo por dos una convención de tela al doble ya incorporada en el trazado. Respeta límites de capas y altura del taller. En la fase de análisis, rechaza escala desconocida, piezas incompletas y cantidades inconsistentes para el estado verificado.

La fase 3 se divide en dos entregas independientes:

1. Análisis de trazados existentes para formatos delimitados y comprobados con archivos reales del taller. Empieza por metadatos y medición validada; desarrolla importadores específicos después.
2. Motor opcional de distribución a partir de geometrías vectoriales a escala. Su necesidad y viabilidad deben evaluarse antes de implementarlo.

El motor deberá respetar ancho útil, separación configurable, márgenes, hilo, rotaciones y espejo autorizados, direccionalidad, estampado y piezas obligatorias. Debe validar colisiones, límites y completitud. El aprovechamiento solo puede calcularse si se conocen las áreas de las piezas y la superficie útil del trazado.

Identifica soluciones aproximadas y restricciones no implementadas. Si el casado de estampado no está soportado, no liberes ese material mediante el optimizador. No uses imágenes generadas por IA como moldes. Una propuesta geométrica requiere aprobación técnica antes del corte; no garantiza el mínimo consumo ni sustituye la prueba del taller.

## 17. Acceso, archivos, respaldo y recuperación

Cuando la aplicación sea accesible por red y maneje datos reales, requiere autenticación desde el MVP. Usa perfiles simples: administrador y operador. Define qué operaciones puede aprobar, ajustar, exportar o restaurar cada uno. No permitas registro público de usuarios por defecto.

Usa mecanismos probados de contraseñas y sesiones, validación del servidor y protección de formularios. No construyas un sistema de autenticación propio si el framework ya lo ofrece. Antes de publicar configura HTTPS, secretos, restricciones de acceso y persistencia del alojamiento.

Limita tipos y tamaños de adjuntos, guarda nombres seguros y no ejecutes contenido cargado. Evita servir documentos privados mediante enlaces públicos previsibles. Conserva referencias a archivos faltantes y muestra errores claros.

El respaldo debe incluir base de datos, adjuntos y versión del esquema. No copies una base SQLite en escritura mediante un simple copiado del archivo; utiliza un mecanismo de copia consistente. Con PostgreSQL utiliza su procedimiento de respaldo soportado.

En el MVP ofrece al administrador un procedimiento documentado de respaldo y restauración. Antes de restaurar, realiza una copia del estado actual, valida compatibilidad y prueba en una base aislada. No combines automáticamente dos bases ni restauraciones incompatibles. Conserva exportaciones y respaldos fuera del alojamiento para resistir la pérdida de la máquina.

La frecuencia y retención se configuran según uso; como punto de partida propone copia diaria y copia antes de cambios importantes, sin afirmar que existen copias automáticas hasta haberlas configurado y comprobado.

## 18. Fases y condiciones de avance

### Fase 1A: recorrido operativo mínimo

Usuarios, colecciones, modelos, variantes, plan aprobado, consumos manuales, materiales por lote, saldos iniciales, faltantes, pedido sencillo, recepción, reservas, orden, consumos, entrega parcial, calidad, inventario y venta manual. Incluye costos básicos, devoluciones, auditoría y persistencia.

Debe permitir completar el caso numérico de la sección 19 sin editar directamente la base de datos. El resultado puede tener una interfaz sencilla, pero las operaciones y saldos deben ser correctos.

### Fase 1B: uso cotidiano fiable

Mejora formularios y navegación móvil; incorpora filtros, dashboard, pagos, presupuestos, exportación CSV, respaldo y restauración; completa permisos, correcciones y cierres de costo. El cálculo de compras debe contemplar reservas, mínimos, múltiplos y unidades.

Las fases 1A y 1B forman juntas el MVP apto para una prueba controlada con el negocio. La fase 1A por sí sola no se presenta como producto listo para uso diario.

### Fase 2: aprendizaje comercial

Importaciones revisables e idempotentes, comparación de colecciones, escenarios y referencias verificables. Añade propuestas asistidas solo cuando los datos, la búsqueda y sus limitaciones estén resueltos. La asistencia es opcional: no debe bloquear el uso operativo sin servicios de IA.

### Fase 3: trazados

Registro y análisis verificado de formatos reales; después, si se justifica, optimización geométrica. No demores el MVP esperando este motor ni anuncies el motor como terminado al mostrar una imagen.

### Fuera del alcance inicial

Facturación electrónica SUNAT, contabilidad completa, nómina, conciliación bancaria, múltiples monedas, múltiples almacenes con transferencias, aplicación nativa, sincronización sin conexión, integración automática con tiendas externas y predicción avanzada de demanda. Documenta estas exclusiones para que la primera entrega tenga un límite claro.

## 19. Caso de aceptación con resultados esperados

Todos los siguientes datos son ficticios y pertenecen exclusivamente al modo demostración. No representan precios de mercado ni configuración tributaria recomendada.

### A. Cantidades

Crea una colección con un modelo, colores azul y beige y tallas S, M y L. Total aprobado: 20 prendas. Colores: 60 % azul y 40 % beige. Tallas dentro de cada color: 25 %, 50 % y 25 %.

| Color | S | M | L | Total |
| --- | ---: | ---: | ---: | ---: |
| Azul | 3 | 6 | 3 | 12 |
| Beige | 2 | 4 | 2 | 8 |
| Total | 5 | 10 | 5 | 20 |

Prueba adicional de redondeo: total 7 con porcentajes 25 %, 50 % y 25 % debe dar 2, 3 y 2 mediante restos mayores. No debe producir 8 unidades.

### B. Materiales y compras

Consumo autorizado por prenda: 1,20 m de tela del color correspondiente y 4 botones. El consumo de tela ya incluye la pérdida de planificación; no apliques otra merma.

| Material | Stock utilizable inicial | Reservado para otra orden | Libre | Necesidad de esta colección |
| --- | ---: | ---: | ---: | ---: |
| Tela azul | 15 m | 3 m | 12 m | 14,40 m |
| Tela beige | 12 m | 2 m | 10 m | 9,60 m |
| Botones | 50 unidades | 10 unidades | 40 unidades | 80 unidades |

Tela azul: faltan 2,40 m. Compra mínima 5 m y múltiplo 1 m: sugerir 5 m; sobrante adicional previsto 2,60 m después de completar la necesidad. Tela beige: faltante cero y compra sugerida cero, aunque exista compra mínima.

Botones: faltan 40. Compra mínima 50 y múltiplo 10: sugerir 50; sobrante adicional previsto 10. No uses el stock reservado a la otra orden.

### C. Producción parcial y costos

Antes de recibir compras nuevas, registra una entrega parcial azul de 10 prendas: S = 3, M = 4, L = 3. Consumo real: 12 m de tela azul y 40 botones. Debe ser factible con la existencia libre y debe dejar las reservas ajenas intactas.

Avanza estas prendas por las etapas y apruébalas por calidad. Ingresa 10 a inventario una sola vez. Las 10 prendas restantes del plan todavía no son inventario terminado.

Asigna costos ficticios conocidos: tela S/ 10 por metro, botón S/ 0,50, confección S/ 8 por prenda y empaque S/ 1 por prenda. No existen otros costos de fabricación en este ejemplo. Consumo y servicios totalizan S/ 230; costo unitario de fabricación del lote parcial cerrado: S/ 23.

Tras esos consumos quedan 3 m de tela azul, todos reservados para la otra orden; 12 m de tela beige, de los cuales 2 están reservados; y 10 botones, todos reservados. Las sugerencias posteriores deben calcularse sobre lo que falta producir, sin volver a pedir materiales para las 10 prendas ya realizadas.

Registra aparte un gasto de colección de S/ 100. No lo incorpores al costo de fabricación de S/ 23 para luego restarlo una segunda vez.

### D. Venta y devolución

Vende 6 prendas del lote a S/ 50 cada una, sin descuentos ni comisiones. Usa tasa cero solo para este ejemplo de demostración. Con costo cerrado del lote:

- Ventas netas: S/ 300.
- Costo de prendas vendidas: S/ 138.
- Utilidad bruta: S/ 162.
- Margen bruto sobre ventas: 54 %.
- Recargo sobre costo unitario: aproximadamente 117,39 %.
- Resultado después del único gasto de colección incluido: S/ 62.
- Stock terminado: 4 prendas, valor de fabricación S/ 92.

Devuelve una de esas prendas en condición apta para vender y devuelve S/ 50 al cliente. Deben quedar ventas netas de S/ 250, costo vendido de S/ 115, utilidad bruta de S/ 135, resultado de S/ 35 y stock de 5 prendas valorado en S/ 115. Una devolución defectuosa debe tener un resultado de inventario diferente y explicable.

Este ejemplo no permite inferir la recuperación de caja: registra y verifica cobros y pagos por separado. Si las ventas no se cobraron, no aparecen como cobros.

### E. Presupuesto y recepción independientes

En otro caso aislado, presupuesto aprobado S/ 200; pedido confirmado S/ 75; anticipo pagado S/ 25. Compromiso pendiente de pago S/ 50 y saldo presupuestario S/ 125. Recibir materiales del pedido no descuenta otros S/ 75 del presupuesto.

Repetir la misma recepción confirmada debe conservar la misma existencia. Completar el pago cambia pagos acumulados a S/ 75, compromiso pendiente a cero y mantiene el saldo presupuestario en S/ 125, si no hay otras operaciones.

## 20. Validaciones obligatorias y entrega

Implementa pruebas de dominio e integración para operaciones que cambian saldos o resultados. La interfaz se comprobará con el recorrido completo, incluyendo una vista móvil. No sustituyas estas comprobaciones por pruebas que solo verifican que una página abre.

Debe haber evidencia de:

1. Redondeo con suma exacta, porcentajes inválidos y variantes excluidas.
2. Unidades compatibles e incompatibles; kg a m bloqueado sin datos; insumos discretos enteros.
3. Faltante cero, mínimo, múltiplo, stock insuficiente y reservas propias frente a reservas ajenas.
4. Dos operaciones que intentan usar el mismo saldo: la segunda se rechaza o recalcula sin stock negativo.
5. Compra parcial, recepción rechazada, anticipo y pago sin duplicar material ni gasto.
6. Producción parcial, límites entre etapas, rechazo, reproceso y único ingreso de prendas.
7. Venta con stock insuficiente, cobro separado, devolución apta y devolución defectuosa.
8. Cambio de precio o consumo sin alterar una versión aprobada; costo pendiente y ajuste identificable.
9. Repetición de recepciones, ventas e ingresos sin duplicar efectos. En fase 2, importación repetida y archivos solapados.
10. Cálculos económicos del ejemplo y denominadores cero correctamente tratados.
11. Datos conservados tras reiniciar el servidor, permisos de acceso y restauración de un respaldo en una base aislada.
12. En fase 3, escala, piezas completas, límites, separación y restricciones soportadas, usando archivos conocidos.

Entrega el código funcional y documentación con:

- Requisitos, versiones y comandos de instalación, migración, arranque y pruebas.
- Ubicación y configuración del almacenamiento persistente.
- Procedimiento seguro para crear el administrador, sin contraseñas fijas incluidas en el repositorio.
- Activación del modo demostración sin contaminación de los datos reales.
- Guía del recorrido de la colección, definiciones de indicadores y criterios de costo.
- Respaldo, restauración, configuración de acceso y requisitos antes de publicar.
- Pruebas ejecutadas y resultados, distinguiendo fallos, omisiones y funciones pendientes.
- Decisiones técnicas, supuestos de negocio y alcance de la siguiente fase.

No presentes como probado un comando que no se ejecutó ni una integración que no se verificó. Si falta una credencial o capacidad externa, completa el trabajo independiente y explica el requisito exacto. La primera entrega debe demostrar operaciones reales y trazables antes de ampliar la automatización.
