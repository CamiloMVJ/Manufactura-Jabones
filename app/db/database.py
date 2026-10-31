import os
from typing import Generator
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import BASE_DIR


# Variables de entorno (con valores por defecto)
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
POSTGRES_DB = os.getenv("POSTGRES_DB", "erp_db")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

# Construcción de la URL de conexión
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = URL.create(
        "postgresql+psycopg", username=POSTGRES_USER, password=POSTGRES_PASSWORD,
        host=POSTGRES_HOST, port=int(POSTGRES_PORT), database=POSTGRES_DB,
    ) if POSTGRES_PASSWORD else "sqlite:///./erp_db.sqlite"
url = make_url(DATABASE_URL)
if url.get_backend_name() == "sqlite" and url.database not in (None, "", ":memory:"):
    from pathlib import Path
    if not Path(url.database).is_absolute():
        url = url.set(database=str(BASE_DIR / url.database))

# Crear el motor (Engine)
connect_args = {"check_same_thread": False, "timeout": 30} if url.get_backend_name() == "sqlite" else {}
engine = create_engine(url, pool_pre_ping=True, connect_args=connect_args)
if url.get_backend_name() == "sqlite":
    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

# Crear la sesión
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base declarativa para los modelos
Base = declarative_base()

def get_db() -> Generator:
    """Generador de dependencias para FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db() -> None:
    """Crea las tablas si no existen y aplica migraciones seguras."""
    from app.models import erp_models 
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN permissions VARCHAR(500)"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE order_items ADD COLUMN lot_id INTEGER"))
        except Exception:
            pass

