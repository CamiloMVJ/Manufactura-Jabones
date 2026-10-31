# Espuma: jabonería y productos de baño

Adaptación del proyecto Python recibido. Nombre comercial provisional: **Espuma**. Puedes cambiarlo en las plantillas y en `data/catalogo.json`.

## Qué contiene

- Tres jabones de 100 g: lavanda, cítrico y avena sin perfume.
- Sales de baño sin perfume en bolsa de 250 g.
- Jabonera de bambú de reventa.
- Kit: jabón de lavanda, jabón de avena, jabonera y caja de regalo.
- Recetas con ingredientes y empaques, rutas, almacenes, compras, producción, inspección, ventas, cobros y trazabilidad.
- Pantalla **Recetas y costos**, disponible en `/recetas`.

Las fórmulas de jabón usan bases comerciales ya preparadas. No requieren calcular ni manipular sosa cáustica. El jabón con avena usa una base que ya contiene avena. No se agregan agua, leche ni ingredientes frescos.

## Iniciar en Windows

1. Extrae TODO el ZIP a una carpeta nueva, por ejemplo `C:\Proyectos\Espuma`. No lo pegues encima del proyecto original.
2. Instala Python 3.10 o posterior y habilita `Add Python to PATH`.
3. Abre `INICIAR_WINDOWS.bat`. La primera ejecución necesita Internet para instalar dependencias.
4. Elige **1** para practicar con insumos ficticios o **2** para trabajar con inventario inicial en cero.
5. Crea tu administrador. Al escribir la contraseña no aparecerán caracteres en la consola.
6. Abre <http://127.0.0.1:8000> e inicia sesión con las credenciales que acabas de elegir.
7. Mantén abierta la consola. Detén con Ctrl+C y vuelve a usar el mismo BAT para iniciar después.

El instalador vuelve a utilizar el catálogo y usuarios existentes; no recarga ni borra datos al reiniciar. No trae una contraseña universal ni la base original exportada como texto en el Markdown.

### Instalación por consola

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe preparar.py
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

`DATABASE_URL` apunta por defecto a `sqlite:///./jaboneria.sqlite`. No necesitas instalar PostgreSQL para usar esta versión local.

## Primera práctica completa

Selecciona el modo 1 al preparar la base. Encontrarás insumos y jaboneras, pero los jabones, sales y kits empiezan con stock cero.

1. Abre **Recetas y costos** para revisar las cantidades y los controles.
2. En **Manufactura**, crea una orden de **10 jabones de lavanda**. Deja vacío el lote preferido para que el sistema asigne lotes liberados por vencimiento (FEFO, primero el vencimiento más cercano; sin fecha al final).
3. Avanza Borrador → Planificado → Disponibilidad verificada → En producción → Control de calidad. Al iniciar, se consumen **990 g de base, 10 g de fragancia, 10 envolturas y 10 etiquetas**.
4. Anota el **ID** que aparece junto al código de la orden.
5. En **Calidad**, registra una inspección del mismo producto con ese ID de orden, resultado aprobado y mediciones. En una demostración puedes registrar datos simulados; en operación real debes medir de verdad.
6. Vuelve a Manufactura y avanza a Completado. Se generan 10 unidades y un lote terminado. Sin inspección aprobada, la operación se bloquea.
7. En **Clientes**, usa el cliente de prueba o crea uno propio.
8. En **Pedidos**, vende dos jabones. El sistema registra los lotes y descuenta dos unidades. Avanza las etapas de entrega.
9. En **Finanzas**, registra el cobro. Entregar un pedido no equivale a cobrarlo.
10. En **Inventario y trazabilidad**, consulta el lote terminado para ver la producción, las inspecciones y la venta.

Para el kit, fabrica primero lavanda y avena, y recibe jaboneras. Una orden de dos kits consume dos jabones de cada tipo, dos jaboneras, dos cajas, 20 g de papel y dos etiquetas. Los productos componentes dejan de estar disponibles individualmente cuando se ensamblan.

## Compras e inventario real

Elige modo 2 para empezar sin existencias ficticias. Actualiza los proveedores de ejemplo antes de comprar. Sus nombres son marcadores; no representan empresas investigadas ni cotizaciones.

- Crea la orden de compra desde Compras e indica precio por unidad de inventario.
- Si compras 1 kg de base a C$220, registra **1000 g** a **C$0.22/g**. Para 1 kg de fragancia a C$1800, registra 1000 g a C$1.80/g.
- Registra recepción, almacén, lote interno único y vencimiento del proveedor cuando esté documentado. Cada recepción crea un lote nuevo. Puedes incluir el lote externo y sufijo de recepción en su código.
- Las cantidades deben ser enteras: gramos para materias primas, unidades para empaques y artículos terminados. Usa balanza con resolución suficiente para pesar fragancias; este sistema no admite fracciones de gramo.
- Una recepción no puede superar el saldo de la compra. Se permiten recepciones parciales.
- Las ventas solo admiten Jabones, Sales de baño, Accesorios y Kits. No se venden materias primas ni empaques.
- No ajustes existencias con el antiguo botón de stock: las entradas deben mantener lotes y ubicaciones consistentes.
- Un producto nuevo se registra con stock cero. Para fabricar un producto adicional necesitas definir una receta y ruta; esta versión las carga mediante la configuración y no incluye un editor de recetas.

El estado “Disponibilidad verificada” comprueba existencias en ese momento; **no constituye una reserva física**. Al iniciar producción se vuelven a validar y se descuentan en una transacción. Si otra orden o venta consumió antes esos insumos, la producción se bloquea.

## Recetas y costos

Consulta `docs/RECETAS_Y_NEGOCIO.md` para procedimientos, equipos, fichas de lote, costos, condiciones de fabricación y etiquetado.

- `data/catalogo.json`: fuente de configuración inicial y supuestos de costos mostrados en Recetas.
- Productos: precios de venta actuales en la base.
- Manufactura: receta operativa BOM y ruta en la base.

Son tres representaciones distintas. Editar el JSON **no modifica automáticamente** las recetas o precios ya cargados en la base. La configuración inicial se bloquea si ya hay catálogo para no pisar datos. Para cambios posteriores se necesita una actualización controlada de las recetas en la base; no vuelvas a cargar encima.

Los costos de Recetas son estimaciones de planificación, no costos contables reales ni un cálculo automático desde facturas de compra. Cambiar un precio de venta en Productos no modifica esos supuestos.

## Roles

- Administrador: configuración de usuarios, compras, fabricación, calidad, ventas y cobros.
- Vendedor: clientes, catálogo, pedidos y cobros; no modifica compras, fabricación, aprobaciones ni calidad.
- Repartidor: seguimiento de pedidos y estados de reparto según las reglas existentes.

Para empezar, el administrador puede llevar la operación del pequeño taller. Los roles adicionales de producción/calidad existentes en el modelo original no se habilitaron como perfiles nuevos en este paquete.

## Respaldo

Con el servidor detenido, copia `jaboneria.sqlite`, `.env` y `.secret_key` a una ubicación segura. Conserva también esta versión del código. No compartas los archivos de claves ni tu base con información real de clientes.

Para pasar de práctica a operación real, conserva una copia de la base demo y cambia `DATABASE_URL` en `.env` a `sqlite:///./jaboneria_real.sqlite`. Vuelve a iniciar y elige modo 2. Es una base independiente: tendrás que crear su administrador.

## Verificación y límites

Prueba integral aislada:

```powershell
.\.venv\Scripts\python.exe -m pip install httpx
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_jaboneria.py -v
```

Se verificó con SQLite y Python 3.12 en Linux. El BAT está preparado para Windows; no se ejecutó en un equipo Windows. No se verificó PostgreSQL ni despliegue público.

El sistema sirve como ERP interno de taller y ventas; no incluye tienda pública, pagos bancarios automáticos, facturación fiscal certificada, devoluciones/cancelaciones con reversión, registro de mermas reales, costos contables por lote ni editor de recetas. El flujo de pedidos conserva la entrega por etapas del proyecto original.

Los indicadores de OEE, merma, cobertura y otros valores que eran constantes de demostración se muestran sin medición cuando falta información. El valor de inventario del panel usa precios del catálogo: en insumos son costos de ejemplo, en terminados son precios de venta; **no es una valoración contable**. Las alertas conservan el umbral genérico de 10 unidades de inventario y deben ajustarse a consumos reales en una etapa posterior.

Las recetas son pilotos. Antes de vender, valida compatibilidad, pesos, pérdidas, estabilidad y calidad del producto terminado; documenta la vida útil. No se asigna automáticamente una caducidad ficticia a la producción. Los lotes sin fecha no se consideran automáticamente vencidos.

## Si aparecen JabÃ³n o baÃ±o

La carga de catálogo y su consulta especifican ahora UTF-8. Para una instalación que ya tiene textos dañados:

1. Detén el servidor con Ctrl+C.
2. Copia de este paquete actualizado `configurar_jaboneria.py`, `app/api/enterprise_routes.py`, `reparar_textos.py` y `REPARAR_TEXTOS_WINDOWS.bat` a las mismas rutas en tu carpeta instalada.
3. Ejecuta `REPARAR_TEXTOS_WINDOWS.bat`. Crea automáticamente un respaldo de SQLite y corrige nombres, categorías y textos de las rutas sin recargar datos.
4. Reinicia con `INICIAR_WINDOWS.bat` y actualiza el navegador con Ctrl+F5.

No borres tu base ni vuelvas a cargar el catálogo. La reparación puede ejecutarse otra vez: los textos correctos permanecen iguales.
