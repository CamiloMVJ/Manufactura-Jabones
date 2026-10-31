from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.events import manager
from app.core.security import get_current_sales_person, get_current_active_admin
from app.db.database import get_db
from app.models.erp_models import Order, Payment, Expense, SyncLog, User
from app.schemas.finance import PaymentCreate, ExpenseCreate
from app.services.finance_service import FinanceService, cents, payment_data

router = APIRouter(prefix="/finance", tags=["Finanzas"], dependencies=[Depends(get_current_sales_person)])

@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    return FinanceService(db).overview()

@router.post("/payments", status_code=201)
async def record_payment(data: PaymentCreate, db: Session = Depends(get_db), user: User = Depends(get_current_sales_person)):
    try:
        # Bloqueo de escritura también en SQLite; serializa cobros sobre el mismo pedido.
        changed = db.execute(update(Order).where(Order.id == data.order_id).values(total_amount=Order.total_amount))
        if changed.rowcount != 1:
            raise HTTPException(404, "Pedido no encontrado")
        previous = db.query(Payment).filter(Payment.request_id == str(data.request_id)).first()
        if previous:
            if previous.order_id != data.order_id or previous.amount != data.amount or previous.method != data.method or previous.reference != data.reference:
                raise HTTPException(409, "La solicitud ya se usó con otros datos")
            db.rollback()
            return payment_data(previous)
        order = db.get(Order, data.order_id)
        from sqlalchemy import func
        paid = cents(db.query(func.sum(Payment.amount)).filter(Payment.order_id == order.id).scalar())
        if data.amount > cents(order.total_amount)-paid:
            raise HTTPException(409, "El cobro supera el saldo pendiente del pedido")
        payment = Payment(**data.model_dump(exclude={"request_id"}), request_id=str(data.request_id), created_by=user.id)
        db.add(payment)
        db.add(SyncLog(entity="Payment", action="create", details=f"Cobro de C$ {data.amount} al pedido #{order.id} por {user.username}"))
        db.commit()
        db.refresh(payment)
    except IntegrityError:
        db.rollback()
        previous = db.query(Payment).filter(Payment.request_id == str(data.request_id)).first()
        if not previous or previous.order_id != data.order_id or previous.amount != data.amount or previous.method != data.method or previous.reference != data.reference:
            raise HTTPException(409, "La solicitud ya se usó con otros datos")
        return payment_data(previous)
    except Exception:
        db.rollback()
        raise
    await manager.broadcast_event("FINANCE_UPDATE", {"order_id": data.order_id})
    return payment_data(payment)

@router.post("/expenses", status_code=201)
async def record_expense(data: ExpenseCreate, db: Session = Depends(get_db), user: User = Depends(get_current_active_admin)):
    # El idempotency key evita duplicar un gasto al reenviar después de un corte de red.
    from sqlalchemy.exc import IntegrityError
    payload = data.model_dump(exclude={"request_id"})
    try:
        expense = Expense(**payload, request_id=str(data.request_id), created_by=user.id)
        db.add(expense)
        db.flush()
        db.add(SyncLog(entity="Expense", action="create", details=f"Gasto de C$ {data.amount}: {data.description} por {user.username}"))
        db.commit()
        db.refresh(expense)
    except IntegrityError:
        db.rollback()
        expense = db.query(Expense).filter(Expense.request_id == str(data.request_id)).first()
        if not expense or any(getattr(expense,key) != value for key,value in payload.items()):
            raise HTTPException(409, "La solicitud ya se usó con otros datos")
    except Exception:
        db.rollback()
        raise
    await manager.broadcast_event("FINANCE_UPDATE", {})
    return {"id": expense.id, "amount": str(expense.amount), "description": expense.description}

