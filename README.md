# PURA COCOS · ERP de jabonería

Empieza por [LEEME_JABONERIA.md](LEEME_JABONERIA.md).

Recetas, costos y operación: [docs/RECETAS_Y_NEGOCIO.md](docs/RECETAS_Y_NEGOCIO.md).

Stack conservado: Python, FastAPI, SQLAlchemy, SQLite/PostgreSQL, Jinja2, JavaScript, CSS, JWT, WebSockets, pandas y ReportLab. La adaptación se verificó con SQLite.

## Carga inicial ampliada

Consulta [docs/CARGA_INICIAL.md](docs/CARGA_INICIAL.md). La carga incluye 34 artículos, 14 recetas, 24 clientes, 8 proveedores, 8 empleados e inventario de apertura configurable. No duplica existencias si se vuelve a ejecutar.

En Windows: `CARGAR_DATOS_INICIALES_WINDOWS.bat`. Contactos ficticios y precios/cantidades propuestos; revisar antes de emplearlos como datos reales.

Para retirar los datos DEMO antiguos sin reiniciar la base, ejecuta `LIMPIAR_DATOS_DEMO_WINDOWS.bat`. Detalles y vista previa: [docs/LIMPIEZA_DEMO.md](docs/LIMPIEZA_DEMO.md).
