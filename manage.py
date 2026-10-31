"""Comandos locales: python manage.py create-admin (sin datos de demostración)."""
import argparse
from getpass import getpass
from sqlalchemy.exc import IntegrityError
from app.core.security import get_password_hash
from app.db.database import init_db, SessionLocal
from app.models.erp_models import User
from app.schemas import UserCreate

def create_admin():
    username = input("Usuario administrador: ").strip()
    email = input("Correo electrónico: ").strip()
    password = getpass("Contraseña (mínimo 8 caracteres): ")
    if password != getpass("Repite la contraseña: "):
        raise ValueError("Las contraseñas no coinciden")
    data = UserCreate(username=username, email=email, password=password, role="administrador")
    init_db()
    with SessionLocal() as db:
        if db.query(User).filter((User.username == data.username) | (User.email == data.email)).first():
            raise ValueError("El usuario o correo ya existe")
        db.add(User(username=data.username, email=data.email, role=data.role, is_active=True, hashed_password=get_password_hash(data.password)))
        try:
            db.commit()
        except IntegrityError as error:
            db.rollback()
            raise ValueError("El usuario o correo ya existe") from error
    print("Administrador creado. Ingresa en /login con tus credenciales.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Administración local de ESPUMA ERP")
    parser.add_argument("command", choices=["create-admin"])
    parser.parse_args()
    try:
        create_admin()
    except ValueError as error:
        parser.exit(1, str(error) + "\n")

