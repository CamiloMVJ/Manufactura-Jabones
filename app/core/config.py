"""Configuración compartida; las rutas no dependen del directorio de ejecución."""
import os
import secrets
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")
APP_ENV = os.getenv("APP_ENV", "development")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))
CORS_ORIGINS = [value.strip() for value in os.getenv("CORS_ORIGINS", "").split(",") if value.strip()]


@lru_cache
def get_secret_key() -> str:
    configured = os.getenv("SECRET_KEY", "").strip()
    if configured:
        if len(configured) < 32:
            raise RuntimeError("SECRET_KEY debe tener al menos 32 caracteres")
        return configured
    if APP_ENV == "production":
        raise RuntimeError("Configura SECRET_KEY antes de iniciar en producción")
    path = BASE_DIR / ".secret_key"
    try:
        with path.open("x", encoding="utf-8") as file:
            file.write(secrets.token_urlsafe(48))
    except FileExistsError:
        pass
    key = path.read_text(encoding="utf-8").strip()
    if len(key) < 32:
        raise RuntimeError("La clave local .secret_key no es válida")
    return key

