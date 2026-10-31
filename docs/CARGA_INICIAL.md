# Carga inicial ampliada de Pura Cocos

## Contenido en una base vacía

| Registro | Cantidad |
|---|---:|
| Materias primas y empaques | 17 |
| Productos de venta | 17 |
| Total de artículos en Productos | 34 |
| Recetas y rutas de fabricación | 14 de cada una |
| Clientes | 24 |
| Proveedores | 8 |
| Personal | 8 |
| Centros de trabajo | 5 |
| Almacenes | 2 |
| Ubicaciones | 6 |
| Lotes de apertura y movimientos iniciales | Hasta 34 de cada uno |

Productos de venta: ocho jabones de 100 g (lavanda, cítrico, avena, rosa, romero, coco, karité y transparente sin perfume), sales de baño de 100 y 250 g, tres accesorios (jabonera, esponja vegetal y bolsa de sisal) y cuatro kits.

Es una propuesta de catálogo e inventario inicial. Los contactos son ficticios; sus correos usan `example.test`, no se inventan teléfonos ni identificaciones fiscales. Los precios y las cantidades se deben reemplazar por cotizaciones y conteos verificados antes de usarlos en un negocio real. Cambiar un código para quitar la palabra DEMO no convierte un dato propuesto en una operación real.

## Ejecutar en una instalación existente

1. Detén el servidor con Ctrl+C.
2. Actualiza la rama `integracion-equipo` con `git pull --ff-only`.
3. Revisa `data/negocio_inicial.json`, especialmente las cantidades del bloque `inventario`.
4. Ejecuta `CARGAR_DATOS_INICIALES_WINDOWS.bat` desde la carpeta del proyecto.
5. Inicia el sistema y actualiza el navegador.

Desde PowerShell, la misma carga es:

```powershell
.\.venv\Scripts\python.exe cargar_datos_iniciales.py
```

Para agregar únicamente catálogos, sin existencias ni lotes:

```powershell
.\.venv\Scripts\python.exe cargar_datos_iniciales.py --sin-stock
```

Puedes ejecutar primero `--sin-stock` y más adelante ejecutar la apertura completa después de revisar las cantidades.

La base utilizada es la indicada por `DATABASE_URL` en tu `.env`, con las mismas reglas de conexión del sistema. El comando crea un respaldo de SQLite en `backups/` antes de escribir. Esa carpeta queda excluida de Git.

## Primera instalación

`INICIAR_WINDOWS.bat` llama a `preparar.py`. Si no hay productos, se aplica esta nueva carga inicial y después se solicita crear el administrador. Ya no se presenta la elección entre DEMO y negocio real. Para una base nueva sin existencias propuestas, ejecuta primero la carga por consola con `--sin-stock` y después inicia el sistema.

## Protección de datos existentes

- Es aditiva: reutiliza registros por su nombre, correo o código y agrega los faltantes.
- No cambia precios, cantidades, recetas ni datos de usuarios ya existentes.
- Si un artículo tiene stock, lotes, ubicaciones o movimientos previos, conserva su inventario y no le suma otra apertura. El resumen indica sus códigos en `existencias_preservadas`.
- Cada inventario de apertura se registra una sola vez en `initial_data_batches` y en auditoría.
- Volver a ejecutar no duplica lotes ni restaura mercancía que ya se vendió o consumió.
- Si cambias las cantidades del JSON después de aplicar la apertura, se rechaza su reaplicación. Las entradas posteriores se registran desde Compras y recepción; no se cambia la versión del lote para eludir este control.
- Si existen registros antiguos con texto mal codificado, ejecuta primero `REPARAR_TEXTOS_WINDOWS.bat`.
- Los lotes antiguos con nombre DEMO se conservan como parte de su historial. La nueva carga no los renombra ni elimina.

Los lotes nuevos usan `AP-AAAAMMDD-SKU` y los movimientos `INI-AAAAMMDD-SKU`. El origen se conserva como inventario inicial, sin facturas de compra, cobros, ventas ni inspecciones inventadas. El estado `released` del archivo es una declaración de apertura propuesta; usa `quarantine` para existencias que no deban venderse o consumirse hasta completar su revisión.

## Archivos de configuración

- `data/catalogo.json`: artículos, costos de referencia, precios propuestos, componentes y procedimientos. También alimenta la pantalla Recetas y costos.
- `data/negocio_inicial.json`: contactos, personal, centros, ubicaciones e inventario de apertura.
- `cargar_datos_iniciales.py`: validación y carga en una transacción.
- `CARGAR_DATOS_INICIALES_WINDOWS.bat`: acceso directo a esa carga.

Todos se leen como UTF-8. Editar los archivos no cambia los registros ya cargados: una modificación posterior de precios o recetas debe hacerse por un proceso de actualización específico.

Las recetas nuevas conservan el criterio de bases comerciales ya preparadas y fragancias compatibles con la base y su certificado IFRA. Son fórmulas nominales que requieren un piloto; no incluyen merma real ni una vida útil supuesta.

## Verificación

Pasaron ocho pruebas automatizadas con SQLite temporal: carga completa, repetición después de consumo, conservación de stock/precios/usuarios existentes, carga sin stock y apertura posterior, rechazo de inventario inválido, fabricación de las catorce recetas, reparación UTF-8 y flujo integrado de venta/cobro.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Las pruebas requieren `httpx`, como las pruebas existentes. No se ejecutó el BAT en Windows ni se verificó PostgreSQL en este entorno.
