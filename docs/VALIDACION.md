# Validación de la adaptación

Una prueba integral automatizada con FastAPI TestClient y SQLite temporal pasó tras los cambios.

Comprueba:
- Configuración inicial, cinco recetas y páginas principales.
- Cantidades inválidas y productos sin receta rechazados.
- Fabricación de lavanda, cítrico, avena, sales y kit; escalado correcto según cantidad base de la receta.
- Consumo de insumos, liberación mediante inspección aprobada y alta de lote terminado.
- Bloqueo de salto y repetición de estados; cierre sin duplicar producción.
- Venta de kit, referencia a lote, trazabilidad y etapas de entrega.
- Registro del cobro y consulta de finanzas.
- Compras, recepciones parciales y rechazo de excesos, fracciones y lotes vencidos.
- Concordancia final entre stock agregado, lotes y ubicaciones.
- Protección frente a una segunda carga de catálogo y retiro del demo agroindustrial.

Se comprobó sintaxis de Python y JavaScript. Se probaron respuestas HTML mediante TestClient.

No se completó la inspección visual en navegador: el entorno no tenía Chromium y su descarga no produjo un archivo válido. La adaptación reutiliza el layout existente; la presentación visual de escritorio y móvil requiere revisión al abrirla localmente.

El BAT de Windows y PostgreSQL no se ejecutaron en este entorno Linux. No se afirma que el sistema completo haya sido certificado para producción ni que las recetas tengan validación cosmética comercial.

Las pruebas anteriores recibidas en el Markdown se conservan como texto en docs/pruebas_originales; sus contratos y supuestos agroindustriales no corresponden a esta versión y no se ejecutan como pruebas vigentes.
