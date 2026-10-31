from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.erp_models import User
from app.schemas import UserResponse, Token, UserCreate
# Importamos la dependencia de admin
from app.core.security import get_password_hash, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_active_admin, get_current_user
from datetime import timedelta

router = APIRouter(prefix="/auth", tags=["Seguridad (RF-19)"])

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # ... (Este código se mantiene igual, el login es público) ...
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Usuario desactivado")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
def current_profile(user: User = Depends(get_current_user)):
    return user

# --- RUTA PROTEGIDA: Solo Admins pueden registrar nuevos usuarios ---
@router.post("/register", response_model=UserResponse)
def register_user(
    user: UserCreate, 
    db: Session = Depends(get_db), 
    # ESTA LÍNEA ES LA CLAVE DE LA SEGURIDAD:
    current_user: User = Depends(get_current_active_admin) 
):
    """
    Registra un nuevo usuario en el sistema.
    Requiere Token de Administrador.
    """
    db_user = db.query(User).filter((User.username == user.username) | (User.email == user.email)).first()
    if db_user:
        raise HTTPException(status_code=400, detail="El usuario o email ya existe")
    
    hashed_pwd = get_password_hash(user.password)
    new_user = User(username=user.username, email=user.email, hashed_password=hashed_pwd, role=user.role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

