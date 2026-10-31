from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.erp_models import User
from app.core.config import get_secret_key, ACCESS_TOKEN_EXPIRE_MINUTES

# Clave persistente en desarrollo y configurable para despliegues con varios procesos.
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# --- Funciones ---
def verify_password(plain_password, hashed_password):
    if len(plain_password.encode("utf-8")) > 72:
        return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except (ValueError, TypeError):
        return False

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta if expires_delta is not None else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, get_secret_key(), algorithm=ALGORITHM)

# --- Dependencias ---
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas o sesión expirada",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, get_secret_key(), algorithms=[ALGORITHM], options={"require_exp": True})
        username: str = payload.get("sub")
        if not isinstance(username, str) or not username:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Usuario desactivado")
    return user

def get_current_active_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "administrador":
        raise HTTPException(status_code=403, detail="Se requieren permisos de Administrador")
    return current_user

def get_current_sales_person(current_user: User = Depends(get_current_user)):
    if current_user.role not in ["administrador", "vendedor"]:
        raise HTTPException(status_code=403, detail="No tienes permisos para vender")
    return current_user


def check_role(allowed_roles: list):
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="No tienes permisos para esta operación")
        return current_user
    return role_checker

