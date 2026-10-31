"""Preparación interactiva sin contraseñas compartidas y sin borrar datos."""
from app.db.database import init_db, SessionLocal
from app.models.erp_models import Product, User
from configurar_jaboneria import configure
from manage import create_admin

def prepare():
 init_db()
 with SessionLocal() as db:
  products=db.query(Product).count();admins=db.query(User).filter_by(role='administrador',is_active=True).count()
 if not products:
  print('ESPUMA: elige el contenido inicial.')
  print('1. Práctica con insumos ficticios (no usar como inventario real).')
  print('2. Negocio real: catálogo y recetas, todas las existencias en cero.')
  choice=input('Opción [1/2]: ').strip()
  if choice not in ('1','2'):raise ValueError('Selecciona 1 o 2 y vuelve a iniciar.')
  configure(demo=choice=='1')
 if not admins:
  print('Crea tu administrador; el sistema no trae una contraseña compartida.')
  create_admin()

if __name__=='__main__':
 try: prepare()
 except ValueError as error:raise SystemExit(str(error))
