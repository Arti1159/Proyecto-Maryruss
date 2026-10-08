# Revisión realista de la propuesta para Maryruss

Documento histórico de la revisión inicial, anterior al desarrollo. El alcance implementado actualmente se describe en README y docs/PLANIFICADOR.md; las capacidades propuestas aquí no se presentan como todas implementadas.

## Dictamen

La idea es viable como herramienta interna para un negocio pequeño si la primera entrega se centra en un recorrido operativo completo y comprobable. El documento original reúne buenos requisitos, pero su alcance se aproxima a un sistema de gestión empresarial especializado. Pedir todas las funciones a la vez aumenta el riesgo de recibir pantallas sin operaciones fiables.

La recomendación es comenzar con registro manual, una sola empresa, una moneda y un local de inventario; demostrar compras, materiales, producción parcial, inventario, ventas y costos; y ampliar después. Investigación asistida y distribución geométrica de moldes deben ser proyectos posteriores con validación propia.

El repositorio revisado durante la configuración anterior estaba vacío. No existe evidencia de una aplicación, tecnología elegida o integración que deba conservarse. La arquitectura propuesta es una recomendación para un proyecto nuevo, sujeta a comprobar nuevamente el repositorio antes de desarrollar.

## Cambios principales

| Tema | Problema o ambigüedad | Mejora propuesta |
| --- | --- | --- |
| Alcance | La fase 1 agrupa demasiadas operaciones sin establecer profundidad | Un recorrido completo con operaciones mínimas por módulo; funciones avanzadas separadas |
| Arquitectura | No define dónde persisten los datos ni cómo se ejecuta | Aplicación monolítica, base relacional, almacenamiento de adjuntos y procedimiento de respaldo |
| Stock | No define cuándo una reserva se convierte en consumo | Movimientos y reservas separados; consumo de una orden libera su propia reserva de forma atómica |
| Producción | Cantidades de etapas podrían sumarse como existencias distintas | Diferenciar avances por etapa, transferencias, rechazos, reprocesos y prendas ingresadas |
| Tallas y colores | Los porcentajes pueden producir totales incorrectos | Método de restos mayores y matriz de variantes; preservar exactamente el total aprobado |
| Compras | Mínimos y múltiplos carecen de una fórmula explícita | Compra cero cuando no hay faltante; redondeo al múltiplo solo sobre el faltante real |
| Consumo de tela | Pérdida, encogimiento y trazado pueden contarse dos veces | Registrar qué incluye cada consumo y prohibir ajustes duplicados |
| Unidades | Metros, kilogramos, rollos y unidades pueden mezclarse | Unidad base por material y conversiones autorizadas por lote |
| Costos | No se distingue claramente costo de fabricación y resultado de colección | Separar inventario, materiales consumidos, gastos y pagos; mostrar costos provisionales |
| Impuestos | Un cálculo genérico puede confundirse con cumplimiento tributario | Supuestos configurables; sin facturación electrónica ni afirmaciones de cumplimiento |
| Ventas | Faltan reglas para cambios, devoluciones y pagos | Venta, cobro, devolución e ingreso a stock como operaciones vinculadas y distintas |
| Historial | Modificar precios o cantidades podría alterar resultados previos | Versiones aprobadas y operaciones registradas inmutables; correcciones con reversión |
| Duplicados | La protección no está definida técnicamente | Transacciones, claves únicas e idempotencia en operaciones que cambian saldos |
| Acceso | “Protegido si se publica” llega tarde para una app con datos del negocio | Autenticación desde el MVP cuando sea accesible por red; dos perfiles simples |
| Respaldo | Exportar CSV no permite recuperar el sistema | Copia consistente de base de datos y adjuntos, y prueba de restauración |
| Investigación | Puede dar apariencia de certeza a hipótesis comerciales | Fuentes fechadas, sin promesas de venta; carga manual si no hay búsqueda verificable |
| Ploteos | Optimización y lectura de archivos son un subsistema CAD | Registro manual primero; análisis por formato después; motor geométrico opcional |
| Móvil | El uso en celular podría implicar funcionamiento sin conexión | Interfaz adaptable con conexión; sincronización sin conexión fuera del MVP |

## Qué conviene construir primero

Una colección con modelos y variantes; cantidades aprobadas; fichas de consumo; inventario inicial de materiales; faltantes y pedidos sencillos; una orden de producción; consumos y entregas parciales; control de calidad; ingreso de prendas; ventas manuales y un informe de presupuesto frente a realidad. Los registros deben persistir y tener trazabilidad.

No hacen falta microservicios, aplicación móvil nativa, un chat, un optimizador matemático de demanda, integraciones de ventas ni un motor de moldes para demostrar ese recorrido.

## Riesgos y decisiones que deben permanecer visibles

- El consumo real y el encogimiento requieren mediciones del taller. El software organiza y calcula esos datos; no los determina a partir de una foto sin escala.
- La rentabilidad depende de ventas, costos y gastos registrados. Un saldo de caja o una proyección no equivale a utilidad.
- El costo real puede estar incompleto mientras falten servicios o comprobantes. Debe figurar como provisional y conservar ajustes posteriores.
- Las ventas históricas pueden ser incompletas o poco representativas. La propuesta comercial debe mostrar esas limitaciones.
- SQLite es razonable para una instancia pequeña con pocas escrituras simultáneas. Varios talleres, múltiples instancias o mayor concurrencia justifican evaluar PostgreSQL.
- Publicar requiere persistencia en el alojamiento, HTTPS y respaldo fuera de la máquina. Un entorno de desarrollo configurado no demuestra esas capacidades en producción.

## Cómo evaluar una entrega

El documento mejorado incluye reglas de cálculo y un ejemplo con resultados esperados. La aceptación debe ejecutar ese ejemplo en una base de prueba, repetir operaciones para comprobar duplicados, reiniciar el servidor y restaurar una copia. No bastan capturas de pantalla, puertos abiertos o formularios que no afectan saldos.

No se fijan fechas ni costos de desarrollo sin conocer equipo, disponibilidad y alojamiento. Se recomienda estimar cada fase después de validar el recorrido anterior.

## Entregable

El archivo Prompt_herramienta_produccion_ropa_mejorado.md contiene la especificación revisada, lista para utilizar como encargo de desarrollo. Es una propuesta; esta revisión no ha implementado la aplicación ni validado datos reales, precios de mercado o normativa tributaria.
