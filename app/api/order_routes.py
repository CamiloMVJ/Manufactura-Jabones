from app.services.soap_operations import consume, SELLABLE
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import update
from sqlalchemy.orm import Session, joinedload, selectinload
from app.core.events import manager
from app.core.security import get_current_user, get_current_sales_person
from app.db.database import get_db
from app.models.erp_models import Client, Order, OrderItem, Product, SyncLog, User, OrderStatusEvent
from app.schemas import OrderCreate, OrderResponse
from app.schemas.schemas import OrderStatusUpdate

router = APIRouter(prefix="/orders", tags=["Órdenes"], dependencies=[Depends(get_current_user)])

def serialize_order(order):
    return {
        "id": order.id, "client_id": order.client_id,
        "client": order.client.name if order.client else "Cliente no disponible",
        "zone": order.client.zone if order.client else None,
        "date": order.date.isoformat() + "Z", "status": order.status,
        "total_amount": order.total_amount,
        "items": [{"product_id": item.product_id,
                   "name": item.product.name if item.product else "Producto no disponible",
                   "lot_id": item.lot_id, "quantity": item.quantity, "subtotal": item.subtotal}
                  for item in order.items],
    }

@router.get("/")
def list_orders(db: Session = Depends(get_db), limit: int = Query(500, ge=1, le=1000)):
    orders = db.query(Order).options(joinedload(Order.client), selectinload(Order.items).joinedload(OrderItem.product)).order_by(Order.date.desc(), Order.id.desc()).limit(limit).all()
    return [serialize_order(order) for order in orders]

@router.get("/{order_id}")
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Pedido no encontrado")
    result = serialize_order(order)
    events = db.query(OrderStatusEvent).filter(OrderStatusEvent.order_id == order_id).order_by(OrderStatusEvent.created_at, OrderStatusEvent.id).all()
    result["timeline"] = [{"status": e.status, "previous_status": e.previous_status, "username": e.username, "date": e.created_at.isoformat()+"Z"} for e in events]
    return result

@router.post("/", response_model=OrderResponse)
async def create_order(order_data: OrderCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_sales_person)):
    quantities = Counter()
    for item in order_data.items:
        quantities[item.product_id] += item.quantity
    try:
        if not db.get(Client, order_data.client_id):
            raise HTTPException(404, "Cliente no encontrado")
        order = Order(client_id=order_data.client_id, total_amount=0)
        db.add(order)
        db.flush()
        db.add(OrderStatusEvent(order_id=order.id, status="pendiente", username=current_user.username))
        total = Decimal("0.00")
        details = []
        # Descuento condicionado: dos ventas no pueden gastar el mismo stock.
        for product_id, quantity in sorted(quantities.items()):
            product = db.query(Product).filter(Product.id == product_id).with_for_update().first()
            if not product:
                raise HTTPException(404, f"Producto {product_id} no encontrado")
            if product.category not in SELLABLE:
                raise HTTPException(400, 'Solo pueden venderse productos terminados y accesorios')
            try:
                allocations = consume(db, product_id, quantity, f'PED-{order.id}')
            except ValueError as error:
                raise HTTPException(409, str(error)) from error
            subtotal = (Decimal(str(product.price)) * quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            total += subtotal
            for lot_id, allocated in allocations:
                part = (Decimal(str(product.price)) * int(allocated)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                db.add(OrderItem(order_id=order.id, product_id=product_id, lot_id=lot_id, quantity=int(allocated), subtotal=float(part)))
            details.append(f"{product.name} (x{quantity})")
        order.total_amount = float(total)
        db.add(SyncLog(entity="Order", action="create", details=f"Pedido #{order.id} por {current_user.username}. Total: {total}"))
        db.commit()
        db.refresh(order)
    except Exception:
        db.rollback()
        raise
    await manager.broadcast_event("NEW_ORDER", {"order_id": order.id, "total": float(total), "items": details, "created_by": current_user.username})
    return order

@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_status(order_id: int, data: OrderStatusUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role not in ("administrador", "vendedor", "repartidor"):
        raise HTTPException(403, "No tienes permiso para actualizar pedidos")
    order = db.query(Order).filter(Order.id == order_id).with_for_update().first()
    if not order:
        raise HTTPException(404, "Pedido no encontrado")
    transitions = {"pendiente": "preparado", "preparado": "en_ruta", "en_ruta": "entregado"}
    if transitions.get(order.status) != data.status:
        raise HTTPException(409, "El pedido debe avanzar al siguiente estado")
    if user.role == "repartidor" and data.status == "preparado":
        raise HTTPException(403, "La preparación corresponde al equipo de ventas")
    previous_status = order.status
    changed = db.execute(update(Order).where(Order.id == order_id, Order.status == previous_status).values(status=data.status).execution_options(synchronize_session=False))
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "El pedido cambió. Actualiza el tablero antes de continuar")
    db.add(OrderStatusEvent(order_id=order_id, previous_status=previous_status, status=data.status, username=user.username))
    db.add(SyncLog(entity="Order", action="status", details=f"Pedido #{order.id}: {data.status} por {user.username}"))
    db.commit()
    db.refresh(order)
    await manager.broadcast_event("ORDER_UPDATE", {"order_id": order.id, "status": order.status})
    return order

