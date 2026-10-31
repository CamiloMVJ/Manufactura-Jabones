"""Carga no destructiva en una base nueva; no reemplaza los datos del proyecto original."""
import argparse, json
from datetime import date
from pathlib import Path
from app.db.database import init_db, SessionLocal
from app.models.erp_models import Product, BillOfMaterial, BOMItem, Routing, RoutingOperation, Warehouse, Location, WorkCenter, Supplier, Client, Lot, StockLocation, InventoryMovement
from app.services.soap_operations import code

CATALOG = json.loads((Path(__file__).parent/'data/catalogo.json').read_text(encoding='utf-8'))

def configure(demo=False):
 init_db()
 with SessionLocal() as db:
  if db.query(Product).count() or db.query(Warehouse).count():
   raise ValueError('La base contiene datos. Configura otra DATABASE_URL vacía; no se elimina ni mezcla el catálogo existente.')
  try:
   mp=Warehouse(code='MP',name='Insumos y empaques',address='Managua'); pt=Warehouse(code='PT',name='Productos terminados',address='Managua')
   db.add_all([mp,pt]);db.flush()
   db.add_all([Location(warehouse_id=mp.id,code='MP-01',name='Almacenamiento seco'),Location(warehouse_id=pt.id,code='PT-01',name='Productos liberados')])
   wc=WorkCenter(code='MESA-01',name='Mesa de elaboración y empaque',capacity_per_hour=20,cost_per_hour=60,status='operativo');db.add(wc);db.flush()
   for name,category in [('Proveedor de bases por definir','Bases cosméticas'),('Proveedor de fragancias por definir','Fragancias cosméticas'),('Proveedor de empaques por definir','Empaques')]:
    db.add(Supplier(name=name,category=category,payment_terms='Por acordar'))
   products={}
   for sku,name,category,cost,qty in CATALOG['insumos']:
    p=Product(name=name,category=category,price=cost,stock=0);db.add(p);products[sku]=p
   for data in CATALOG['productos']:
    p=Product(name=data['nombre'],category=data['categoria'],price=data['precio'],stock=0);db.add(p);products[data['sku']]=p
   db.flush()
   for data in CATALOG['productos']:
    if not data.get('ingredientes'): continue
    p=products[data['sku']]
    bom=BillOfMaterial(code='REC-'+data['sku'],finished_product_id=p.id,quantity=data['lote_base'],version='1.0',notes='Piloto nominal sin merma; consultar /recetas y validar antes de venta.')
    db.add(bom);db.flush()
    for sku,qty in data['ingredientes']:
     db.add(BOMItem(bom_id=bom.id,component_product_id=products[sku].id,quantity=qty,scrap_percentage=0))
    route=Routing(code='RUTA-'+data['sku'],name=data['nombre'],finished_product_id=p.id,description='Ver procedimiento completo en Recetas')
    db.add(route);db.flush()
    for index,step in enumerate(data['pasos'],1):
     db.add(RoutingOperation(routing_id=route.id,sequence=index*10,work_center_id=wc.id,operation_name=step[:200],standard_duration_minutes=15))
   if demo:
    db.add(Client(name='Cliente de prueba',email='cliente@example.test',zone='Managua'))
    stocks=[(row[0],row[4]) for row in CATALOG['insumos']]+[('JABONERA',20)]
    for sku,qty in stocks:
     p=products[sku];p.stock=qty
     lot=Lot(lot_number='DEMO-'+sku,product_id=p.id,initial_quantity=qty,current_quantity=qty,status='released',notes='Existencia ficticia para practicar; sin caducidad validada')
     db.add(lot);db.flush();warehouse=pt if sku=='JABONERA' else mp
     db.add(StockLocation(product_id=p.id,warehouse_id=warehouse.id,lot_id=lot.id,quantity=qty,reserved_quantity=0))
     db.add(InventoryMovement(code=code('INI'),product_id=p.id,lot_id=lot.id,movement_type='adjustment',dest_warehouse_id=warehouse.id,quantity=qty,notes='Carga ficticia de demostración'))
   db.commit()
  except Exception:
   db.rollback();raise
 print('Catálogo, recetas y rutas cargados. '+('Existencias DEMO agregadas.' if demo else 'Stock inicial cero: registra tus compras reales.'))

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--demo',action='store_true');args=parser.parse_args()
 try: configure(args.demo)
 except ValueError as e: parser.exit(1,str(e)+'\n')
