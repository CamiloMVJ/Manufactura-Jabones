from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import BASE_DIR, CORS_ORIGINS, get_secret_key
from app.db.database import init_db, engine
from app.api import ws_routes, report_routes, product_routes, order_routes, auth_routes, client_routes, finance_routes, enterprise_routes

@asynccontextmanager
async def lifespan(app):
    get_secret_key()
    init_db()
    yield
    engine.dispose()

app = FastAPI(title="Pura CocosENTERPRISE SUITE", version="2.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=True, allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"], allow_headers=["Authorization", "Content-Type"])

for router in (auth_routes.router, ws_routes.router, report_routes.router, product_routes.router, order_routes.router, client_routes.router, finance_routes.router, enterprise_routes.router):
    app.include_router(router)

@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["X-Frame-Options"] = "DENY"
    if not request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store"
    return response

@app.get("/health", include_in_schema=False)
def health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok"}
    except SQLAlchemyError:
        return JSONResponse({"status": "unavailable"}, status_code=503)

@app.get("/login", include_in_schema=False)
def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

def page(template, page_id, title, subtitle):
    def render(request: Request):
        return templates.TemplateResponse(request=request, name=template, context={"page_id": page_id, "title": title, "subtitle": subtitle})
    return render

pages = [
    ("recetas.html", "recipes", "Recetas y costos", "Fórmulas piloto, insumos y procedimientos de la jabonería.", ["/recetas"]),
    ("dashboard.html", "dashboard", "Centro de operaciones", "Producción de jabones conectada: compras, manufactura, calidad, almacén y ventas.", ["/"]),
    ("clientes.html", "clients", "Clientes", "Relaciones comerciales y zonas de distribución.", ["/clientes", "/clientes.html"]),
    ("productos.html", "products", "Productos e inventario", "Tu catálogo, existencias y precios en un solo lugar.", ["/productos", "/productos.html"]),
    ("pedidos.html", "orders", "Pedidos y ventas", "Del primer producto a la última entrega con trazabilidad a lotes.", ["/pedidos", "/pedidos.html"]),
    ("facturizacion.html", "billing", "Facturación", "Consulta tus ventas y genera comprobantes de pedido.", ["/facturacion", "/facturacion.html", "/facturizacion", "/facturizacion.html"]),
    ("perfil.html", "profile", "Mi perfil", "Tu cuenta y permisos de acceso.", ["/perfil", "/perfil.html"]),
    ("finanzas.html", "finance", "Finanzas", "Cobros, gastos y cuentas por cobrar de tu jabonería.", ["/finanzas", "/finanzas.html"]),
    ("compras.html", "procurement", "Abastecimiento y compras", "Gestión integral de proveedores, solicitudes, órdenes de compra y recepción.", ["/compras", "/compras.html"]),
    ("inventario_suite.html", "inventory", "Inventario y trazabilidad", "Control de existencias multialmacén, movimientos y rastreo integral de lotes.", ["/inventario", "/inventario.html"]),
    ("manufactura.html", "manufacturing", "Manufactura y producción", "Listas de materiales (BOM), rutas de proceso, centros de trabajo y órdenes de fabricación.", ["/manufactura", "/manufactura.html"]),
    ("calidad.html", "quality", "Gestión de calidad", "Inspecciones de laboratorio, puntos de control y disposición de no conformidades.", ["/calidad", "/calidad.html"]),
    ("analitica.html", "analytics", "Analítica y métricas KPI", "OEE de planta, rotación de inventario, costos medios y eficiencia comercial.", ["/analitica", "/analitica.html"]),
    ("administracion.html", "admin", "Administración y monitores", "Monitoreo del sistema, auditoría de eventos, salud de datos y roles de acceso.", ["/administracion", "/administracion.html"]),
    ("proyecto.html", "project_logs", "Bitácora del proyecto", "Registro estructurado de contribuciones e incidencias para acreditación técnica.", ["/proyecto", "/proyecto.html"]),
]

for template, page_id, title, subtitle, paths in pages:
    for path in paths:
        app.add_api_route(path, page(template, page_id, title, subtitle), methods=["GET"], include_in_schema=False)


@app.exception_handler(ValueError)
async def invalid_operation(request, error):
    return JSONResponse(status_code=409, content={'detail': str(error)})
