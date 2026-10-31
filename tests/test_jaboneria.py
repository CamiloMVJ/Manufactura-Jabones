"""Prueba integral en una base temporal; nunca modifica la base de trabajo."""
import os, sys, tempfile, unittest
from pathlib import Path
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
TMP=tempfile.TemporaryDirectory()
os.environ['DATABASE_URL']='sqlite:///'+str(Path(TMP.name)/'test.sqlite')
os.environ['SECRET_KEY']='test-jaboneria-secret-at-least-32-characters'
from fastapi.testclient import TestClient
from app.db.database import SessionLocal
from app.models.erp_models import *
from app.core.security import get_password_hash
from configurar_jaboneria import configure, CATALOG
from main import app

class SoapTest(unittest.TestCase):
 def test_end_to_end(self):
  configure(demo=True)
  with SessionLocal() as db:
   db.add(User(username='tester',email='test@example.test',role='administrador',hashed_password=get_password_hash('test-pass-123')))
   db.add(User(username='sales',email='sales@example.test',role='vendedor',hashed_password=get_password_hash('test-pass-123')))
   db.commit()
  with TestClient(app) as api:
   login=api.post('/auth/login',data={'username':'tester','password':'test-pass-123'});self.assertEqual(login.status_code,200,login.text)
   api.headers['Authorization']='Bearer '+login.json()['access_token']
   def call(method,path,data=None,status=200):
    r=api.request(method,path,json=data);self.assertEqual(r.status_code,status,(path,r.text));return r.json()
   products=call('GET','/products/');byname={p['name']:p for p in products}
   ids={p['sku']:byname[p['nombre']]['id'] for p in CATALOG['productos']}
   raw=next(p for p in products if p['category']=='Materia prima')
   # El catálogo, recetas y pantallas deben cargar.
   self.assertEqual(len(call('GET','/enterprise/boms')),5)
   for path in ['/','/recetas','/manufactura','/calidad','/compras','/productos','/finanzas','/static/brand/espuma.svg','/static/js/recetas.js']:
    self.assertEqual(api.get(path).status_code,200,path)
   # No se vende un insumo ni se modifica stock sin lote.
   call('POST','/orders/',{'client_id':1,'items':[{'product_id':raw['id'],'quantity':1}]},400)
   call('PUT',f"/products/{raw['id']}/stock?quantity=9",status=409)
   call('POST','/enterprise/production-orders',{'product_id':ids['JABONERA'],'planned_quantity':1},409)
   call('POST','/enterprise/production-orders',{'product_id':ids['JAB-LAV'],'planned_quantity':-1},409)
   produced=[]
   for sku in ['JAB-LAV','JAB-CIT','JAB-AV','SAL-250','KIT']:
    po=call('POST','/enterprise/production-orders',{'product_id':ids[sku],'planned_quantity':10 if sku!='KIT' else 2})
    path=f"/enterprise/production-orders/{po['id']}/status"
    call('PATCH',path,{'status':'completed'},409)
    for state in ['planned','materials_reserved','in_production','quality_control']:
     call('PATCH',path,{'status':state})
    call('PATCH',path,{'status':'completed'},409)
    call('POST','/enterprise/quality/inspections',{'product_id':ids[sku],'production_order_id':po['id'],'result':'failed','measured_value':'Empaque incompleto'})
    call('PATCH',path,{'status':'completed'},409)
    call('POST','/enterprise/quality/inspections',{'product_id':ids[sku],'production_order_id':po['id'],'result':'passed','measured_value':'Pesos nominales verificados; apariencia y empaques conformes'})
    po=call('PATCH',path,{'status':'completed'});produced.append(po)
    call('PATCH',path,{'status':'completed'},409)
    call('PATCH',path,{'status':'closed'})
   # Escala BOM: 10 lavandas = 990 g base + 10 g fragancia, no 10 veces esa receta.
   with SessionLocal() as db:
    first=db.get(ProductionOrder,produced[0]['id'])
    self.assertEqual(sum(c.consumed_quantity for c in first.consumptions if c.component_product_id==raw['id']),990)
    self.assertEqual(db.get(Product,ids['KIT']).stock,2)
   order=call('POST','/orders/',{'client_id':1,'items':[{'product_id':ids['KIT'],'quantity':1}]})
   self.assertEqual(order['total_amount'],285)
   detail=call('GET',f"/orders/{order['id']}");self.assertTrue(detail['items'][0]['lot_id'])
   trace=call('GET',f"/enterprise/lot-traceability/{detail['items'][0]['lot_id']}")
   self.assertEqual(trace['sales_distribution'][0]['order_id'],order['id'])
   for state in ['preparado','en_ruta','entregado']:call('PATCH',f"/orders/{order['id']}/status",{'status':state})
   call('POST','/finance/payments',{'order_id':order['id'],'amount':'285.00','method':'efectivo','request_id':str(uuid4())},201)
   # Compra con recepción parcial, saldo, rechazo de exceso y expiración.
   supplier=call('GET','/enterprise/suppliers')[0]['id'];wh=call('GET','/enterprise/warehouses')[0]['id']
   po=call('POST','/enterprise/purchase-orders',{'supplier_id':supplier,'items':[{'product_id':raw['id'],'quantity':1000,'unit_price':0.22}]})
   def receive(qty,status=200,**extra):return call('POST','/enterprise/material-receptions',{'purchase_order_id':po['id'],'warehouse_id':wh,'items':[{'product_id':raw['id'],'quantity_received':qty,**extra}]},status)
   receive(1001,409);receive(1,409,expiry_date='2000-01-01');receive(1.5,409)
   receive(600);receive(401,409);receive(400);receive(1,409)
   # Toda existencia agregada debe coincidir con lotes y ubicaciones.
   with SessionLocal() as db:
    for p in db.query(Product).all():
     total=sum(l.current_quantity for l in db.query(Lot).filter_by(product_id=p.id))
     located=sum(s.quantity for s in db.query(StockLocation).filter_by(product_id=p.id))
     self.assertEqual(p.stock,total,p.name);self.assertEqual(p.stock,located,p.name)
   call('POST','/enterprise/workflow/execute-demo-flow',status=409)
   # Una segunda configuración no pisa el catálogo.
   with self.assertRaises(ValueError):configure(demo=True)
   for path in ['/enterprise/inventory-summary','/enterprise/analytics','/enterprise/data-health','/finance/overview']:
    call('GET',path)

if __name__=='__main__': unittest.main()
