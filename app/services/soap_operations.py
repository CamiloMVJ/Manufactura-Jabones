"""Operaciones de jabonería; cantidades enteras en gramos o unidades del catálogo."""
from datetime import datetime, date
from math import isfinite
from uuid import uuid4
from sqlalchemy import update, or_
from app.models.erp_models import (
 Product, Lot, StockLocation, InventoryMovement, BillOfMaterial, Routing,
 ProductionOrder, ProductionMaterialConsumption, ProductionWorkOrder,
 QualityInspection, Warehouse, PurchaseOrder, PurchaseOrderItem,
 MaterialReception, MaterialReceptionItem, AuditLog, Supplier, PurchaseRequest)

SELLABLE = ('Jabones', 'Sales de baño', 'Accesorios', 'Kits')

def code(prefix):
 return f'{prefix}-{datetime.now():%Y%m%d}-{uuid4().hex[:10]}'

def whole(value):
 n = float(value)
 if not isfinite(n) or n <= 0 or not n.is_integer():
  raise ValueError('Usa una cantidad positiva entera: gramos para insumos y unidades para empaques y productos.')
 return int(n)

def audit(db, username, action, reference):
 db.add(AuditLog(username=username, action=action, module='jabonería', record_reference=reference))

def add_stock(db, product_id, lot_id, warehouse_id, quantity):
 stock = db.query(StockLocation).filter_by(product_id=product_id, lot_id=lot_id, warehouse_id=warehouse_id).first()
 if stock: stock.quantity += quantity
 else: db.add(StockLocation(product_id=product_id, lot_id=lot_id, warehouse_id=warehouse_id, quantity=quantity))

def consume(db, product_id, quantity, reference, preferred_lot=None):
 """FEFO de lotes liberados; todas las escrituras pertenecen a la transacción llamadora."""
 quantity = whole(quantity)
 product = db.get(Product, product_id)
 if not product: raise ValueError('Producto no encontrado')
 changed = db.execute(update(Product).where(Product.id == product_id, Product.stock >= quantity).values(stock=Product.stock-quantity).execution_options(synchronize_session=False))
 if changed.rowcount != 1: raise ValueError(f'Stock insuficiente: {product.name}')
 db.expire(product, ['stock'])
 lots = db.query(Lot).filter(Lot.product_id == product_id, Lot.status == 'released', Lot.current_quantity > 0, or_(Lot.expiry_date.is_(None), Lot.expiry_date >= date.today())).order_by(Lot.expiry_date.is_(None), Lot.expiry_date, Lot.id).with_for_update().all()
 if preferred_lot:
  preferred = next((lot for lot in lots if lot.id == preferred_lot), None)
  if not preferred: raise ValueError('El lote elegido no corresponde al insumo o no está liberado/vigente')
  lots = [preferred] + [lot for lot in lots if lot.id != preferred_lot]
 remaining = quantity
 allocations = []
 for lot in lots:
  take = min(remaining, lot.current_quantity)
  if take <= 0: continue
  changed = db.execute(update(Lot).where(Lot.id == lot.id, Lot.current_quantity >= take).values(current_quantity=Lot.current_quantity-take).execution_options(synchronize_session=False))
  if changed.rowcount != 1: raise ValueError('El lote cambió; vuelve a intentar')
  db.expire(lot, ['current_quantity'])
  if lot.current_quantity == 0: lot.status = 'consumed'
  stocks = db.query(StockLocation).filter_by(lot_id=lot.id).order_by(StockLocation.id).all()
  left = take
  for stock in stocks:
   used = min(left, stock.quantity)
   stock.quantity -= used
   left -= used
  if left > 0: raise ValueError(f'Existencias por ubicación inconsistentes: {product.name}')
  db.add(InventoryMovement(code=code('MOV'), product_id=product_id, lot_id=lot.id,
    movement_type='sales_dispatch' if reference.startswith('PED-') else 'production_consumption',
    quantity=take, reference_doc_type='sales_order' if reference.startswith('PED-') else 'production_order', reference_doc_id=reference))
  allocations.append((lot.id, take))
  remaining -= take
  if remaining == 0: break
 if remaining > 0: raise ValueError(f'Lotes liberados insuficientes: {product.name}. Registra la recepción con su lote.')
 return allocations

class SoapOperations:
 def create_production_order(self, data, username='admin'):
  try:
   product_id = int(data['product_id']); qty = whole(data['planned_quantity'])
   bom = self.db.query(BillOfMaterial).filter_by(finished_product_id=product_id, is_active=True).first()
   if data.get('bom_id'): bom = self.db.get(BillOfMaterial, int(data['bom_id']))
   if not bom or not bom.is_active or bom.finished_product_id != product_id or not bom.items or bom.quantity <= 0:
    raise ValueError('El producto debe tener una receta activa y válida')
   routing = self.db.query(Routing).filter_by(finished_product_id=product_id, is_active=True).first()
   if data.get('routing_id'): routing = self.db.get(Routing, int(data['routing_id']))
   if not routing or routing.finished_product_id != product_id or not routing.is_active:
    raise ValueError('El producto debe tener una ruta activa y válida')
   po = ProductionOrder(code=code('OP'), product_id=product_id, bom_id=bom.id, routing_id=routing.id,
    planned_quantity=qty, status='draft', created_by=username, notes=data.get('notes',''), raw_material_lot_id=data.get('raw_material_lot_id') or None)
   self.db.add(po); self.db.flush()
   for item in bom.items:
    needed = item.quantity * qty / bom.quantity * (1 + item.scrap_percentage/100)
    needed = whole(round(needed, 8))
    self.db.add(ProductionMaterialConsumption(production_order_id=po.id, component_product_id=item.component_product_id,
     planned_quantity=needed, consumed_quantity=0, status='planned'))
   for op in routing.operations:
    self.db.add(ProductionWorkOrder(production_order_id=po.id, operation_sequence=op.sequence, work_center_id=op.work_center_id,
     operation_name=op.operation_name, status='pending', duration_minutes=op.standard_duration_minutes))
   audit(self.db, username, 'CREATE', po.code); self.db.commit(); return po
  except Exception:
   self.db.rollback(); raise

 def advance_production_order(self, order_id, target_status, username='admin'):
  try:
   po = self.db.query(ProductionOrder).filter_by(id=order_id).with_for_update().first()
   if not po: raise ValueError('Orden de producción no encontrada')
   transitions = {'draft':'planned','planned':'materials_reserved','materials_reserved':'in_production','in_production':'quality_control','quality_control':'completed','completed':'closed'}
   if transitions.get(po.status) != target_status: raise ValueError('La orden debe avanzar una sola etapa y no puede repetirse')
   # El estado previo es una precondición también en SQLite, que no usa FOR UPDATE.
   previous = po.status
   changed = self.db.execute(update(ProductionOrder).where(ProductionOrder.id == order_id, ProductionOrder.status == previous).values(status=target_status).execution_options(synchronize_session=False))
   if changed.rowcount != 1: raise ValueError('La orden cambió; actualiza la pantalla')
   self.db.expire(po, ['status'])
   if target_status == 'materials_reserved':
    # No promete reservas físicas: la disponibilidad se verifica y consume al iniciar.
    for c in po.consumptions:
     p = self.db.get(Product,c.component_product_id)
     if not p or p.stock < c.planned_quantity: raise ValueError('Insumos insuficientes para planificar')
   elif target_status == 'in_production':
    po.start_date = datetime.utcnow()
    original = list(po.consumptions)
    for index,c in enumerate(original):
     allocations = consume(self.db,c.component_product_id,c.planned_quantity,po.code,po.raw_material_lot_id if index == 0 else None)
     first_qty = allocations[0][1]
     c.planned_quantity = first_qty; c.consumed_quantity = first_qty; c.lot_id = allocations[0][0]; c.status='consumed'
     for lot_id,qty in allocations[1:]:
      self.db.add(ProductionMaterialConsumption(production_order_id=po.id,component_product_id=c.component_product_id,
       lot_id=lot_id,planned_quantity=qty,consumed_quantity=qty,status='consumed'))
    for wo in po.work_orders: wo.status='in_progress'
   elif target_status == 'quality_control':
    for wo in po.work_orders: wo.status='completed'; wo.completed_at=datetime.utcnow()
   elif target_status == 'completed':
    qc = self.db.query(QualityInspection).filter_by(production_order_id=po.id,product_id=po.product_id).order_by(QualityInspection.id.desc()).first()
    if not qc or qc.result != 'passed' or not qc.measured_value:
     raise ValueError('Registra una inspección aprobada con mediciones y el ID de esta orden en Calidad')
    if po.finished_lot_id: raise ValueError('Esta orden ya generó un lote')
    po.produced_quantity = po.planned_quantity; po.end_date=datetime.utcnow()
    lot = Lot(lot_number=code('PT'),product_id=po.product_id,initial_quantity=po.produced_quantity,
     current_quantity=po.produced_quantity,manufacture_date=date.today(),status='released',notes=f'Orden {po.code}; caducidad pendiente de validación técnica')
    self.db.add(lot); self.db.flush(); po.finished_lot_id=lot.id; qc.lot_id=lot.id
    self.db.execute(update(Product).where(Product.id==po.product_id).values(stock=Product.stock+int(po.produced_quantity)).execution_options(synchronize_session=False))
    warehouse=self.db.query(Warehouse).filter_by(code='PT').first()
    if not warehouse: raise ValueError('Falta el almacén PT; ejecuta la configuración de jabonería')
    add_stock(self.db,po.product_id,lot.id,warehouse.id,po.produced_quantity)
    self.db.add(InventoryMovement(code=code('MOV'),product_id=po.product_id,lot_id=lot.id,movement_type='production_output',
     dest_warehouse_id=warehouse.id,quantity=po.produced_quantity,reference_doc_type='production_order',reference_doc_id=po.code))
   audit(self.db,username,'STATUS_CHANGE',f'{po.code}: {previous} -> {target_status}'); self.db.commit(); return po
  except Exception:
   self.db.rollback(); raise

 def create_purchase_order(self, data, username='admin'):
  try:
   if not self.db.get(Supplier, int(data['supplier_id'])): raise ValueError('Proveedor no encontrado')
   if not data.get('items'): raise ValueError('La compra necesita al menos un insumo')
   if data.get('request_id'):
    request=self.db.get(PurchaseRequest,int(data['request_id']))
    if not request or request.status!='approved': raise ValueError('La solicitud debe estar aprobada')
   validated=[];seen=set()
   for item in data['items']:
    pid=int(item['product_id']);qty=whole(item['quantity']);price=float(item['unit_price'])
    if pid in seen: raise ValueError('Agrupa el insumo en una sola línea')
    seen.add(pid)
    product=self.db.get(Product,pid)
    if not product or product.category not in ('Materia prima','Empaques','Accesorios'): raise ValueError('Solo se compran materias primas, empaques y accesorios de reventa')
    if not isfinite(price) or price<0: raise ValueError('Precio de compra inválido')
    validated.append((pid,qty,price))
   po=PurchaseOrder(code=code('OC'),supplier_id=int(data['supplier_id']),request_id=data.get('request_id'),
    expected_delivery_date=date.fromisoformat(data['expected_delivery_date']) if data.get('expected_delivery_date') else None,
    total_amount=round(sum(q*p for _,q,p in validated),2),notes=data.get('notes',''),status='approved')
   self.db.add(po);self.db.flush()
   for pid,qty,price in validated:
    self.db.add(PurchaseOrderItem(purchase_order_id=po.id,product_id=pid,quantity=qty,unit_price=price,subtotal=round(qty*price,2),received_quantity=0))
   if data.get('request_id'): request.status='ordered'
   audit(self.db,username,'CREATE',po.code);self.db.commit();return po
  except Exception:
   self.db.rollback();raise

 def receive_material(self,purchase_order_id,warehouse_id,items_data,received_by='admin'):
  try:
   po=self.db.query(PurchaseOrder).filter_by(id=purchase_order_id).with_for_update().first()
   if not po or po.status not in ('approved','ordered','partial'): raise ValueError('La compra no admite recepciones')
   if not self.db.get(Warehouse,warehouse_id) or not items_data: raise ValueError('Almacén o detalle inválido')
   reception=MaterialReception(code=code('REC'),purchase_order_id=po.id,warehouse_id=warehouse_id,received_by=received_by,status='completed')
   self.db.add(reception);self.db.flush()
   for item in items_data:
    qty=whole(item['quantity_received']); pid=int(item['product_id'])
    poi=self.db.query(PurchaseOrderItem).filter_by(purchase_order_id=po.id,product_id=pid).first()
    if not poi or qty > poi.quantity-poi.received_quantity: raise ValueError('Recepción superior al saldo de la compra o producto ajeno')
    number=item.get('lot_number') or code('MP')
    if self.db.query(Lot).filter_by(lot_number=number).first(): raise ValueError('Usa un código de lote nuevo para esta recepción')
    expiry=date.fromisoformat(item['expiry_date']) if item.get('expiry_date') else None
    if expiry and expiry < date.today(): raise ValueError('No se puede recibir un lote vencido como liberado')
    lot=Lot(lot_number=number,product_id=pid,supplier_id=po.supplier_id,initial_quantity=qty,current_quantity=qty,status='released',expiry_date=expiry,notes=f'Recepción {reception.code}; verificar ficha del proveedor')
    self.db.add(lot);self.db.flush()
    self.db.add(MaterialReceptionItem(reception_id=reception.id,product_id=pid,quantity_received=qty,lot_number=number))
    product=self.db.get(Product,pid);product.stock+=qty;poi.received_quantity+=qty
    add_stock(self.db,pid,lot.id,warehouse_id,qty)
    self.db.add(InventoryMovement(code=code('MOV'),product_id=pid,lot_id=lot.id,movement_type='purchase_receipt',dest_warehouse_id=warehouse_id,
     quantity=qty,reference_doc_type='material_reception',reference_doc_id=reception.code))
   self.db.flush()
   po.status='received' if all(i.received_quantity>=i.quantity for i in po.items) else 'partial'
   audit(self.db,received_by,'RECEIVE',reception.code);self.db.commit();return reception
  except Exception:
   self.db.rollback();raise
