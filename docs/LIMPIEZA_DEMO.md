# Quitar los datos antiguos DEMO

Actualiza `integracion-equipo`, detén el servidor con Ctrl+C y ejecuta:

```powershell
.\.venv\Scripts\python.exe limpiar_datos_demo.py
```

También puedes abrir `LIMPIAR_DATOS_DEMO_WINDOWS.bat` con doble clic.

El comando crea y verifica un respaldo de SQLite en `backups/antes-limpiar-demo-*.sqlite`. Si falla el respaldo, no ejecuta la limpieza. La carpeta backups ya está excluida de Git.

Para ver el resultado previsto sin guardar ningún cambio:

```powershell
.\.venv\Scripts\python.exe limpiar_datos_demo.py --ver
```

## Qué elimina

- Lotes `DEMO-*` que conservan la marca de origen de `configurar_jaboneria.py`, la misma cantidad inicial y un único movimiento de entrada ficticia.
- Las ubicaciones y el movimiento de entrada correspondientes a cada lote eliminado.
- El cliente `Cliente de prueba` / `cliente@example.test`, si no tiene operaciones ni datos de contacto añadidos.
- Los tres proveedores `Proveedor de bases por definir`, `Proveedor de fragancias por definir` y `Proveedor de empaques por definir`, si no tienen referencias ni información de contacto añadida.

Cada lote retirado descuenta su cantidad del stock agregado del artículo. La limpieza comprueba antes la concordancia entre stock, lotes y ubicaciones.

## Qué conserva

El catálogo compartido de productos e insumos, recetas, rutas, usuarios y los datos de la carga ampliada. No usa `example.test` como criterio general para borrar: los 24 clientes nuevos se conservan.

Un lote DEMO asociado a ventas, producción, inspecciones, reservas u otros movimientos se conserva y aparece en `conservados`, con el motivo. No elimina operaciones de forma recursiva ni cambia sus nombres para ocultarlas. Un texto que solo empiece por DEMO no basta para eliminarlo si no coincide con el origen del cargador conocido.

Toda la limpieza se aplica en una transacción y queda registrada en auditoría. Ejecutarla otra vez no vuelve a descontar las cantidades ya eliminadas.

## Después de la limpieza

Reinicia el sistema y actualiza el navegador. Los artículos cuyos únicos lotes eran DEMO quedan en stock cero; el script no inventa compras ni repone mercancía. Registra las entradas que correspondan desde Compras y recepción. La carga ampliada mantiene su control de aplicación única y no restituye existencias automáticamente.

La versión actual admite SQLite. No reinicia la base, no borra tablas ni elimina tu administrador.
