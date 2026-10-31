"""Preparación interactiva sin contraseñas compartidas y sin borrar datos."""
from app.db.database import init_db, SessionLocal
from app.models.erp_models import Product, User
from cargar_datos_iniciales import load_initial_data
from manage import create_admin

def prepare():
 init_db()
 with SessionLocal() as db:
  products=db.query(Product).count();admins=db.query(User).filter_by(role='administrador',is_active=True).count()
 if not products:
  print('Pura Cocos: cargando catálogo ampliado e inventario de apertura propuesto.')
  print('Contactos ficticios y precios estimados. Revisa data/negocio_inicial.json antes de utilizarlo como inventario real.')
  load_initial_data(include_inventory=True)
 if not admins:
  print('Crea tu administrador; el sistema no trae una contraseña compartida.')
  create_admin()

if __name__=='__main__':
 try: prepare()
 except ValueError as error:raise SystemExit(str(error))
