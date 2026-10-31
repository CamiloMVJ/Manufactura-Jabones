from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from app.models.erp_models import Order, Payment, Expense

def cents(value):
    return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def payment_data(payment):
    return {"id": payment.id, "order_id": payment.order_id, "amount": str(payment.amount), "method": payment.method,
            "reference": payment.reference, "date": payment.created_at.isoformat()+"Z"}

class FinanceService:
    def __init__(self, db):
        self.db = db

    def receivables(self):
        paid = self.db.query(Payment.order_id.label("order_id"), func.sum(Payment.amount).label("paid")).group_by(Payment.order_id).subquery()
        rows = self.db.query(Order, func.coalesce(paid.c.paid, 0)).outerjoin(paid, paid.c.order_id == Order.id).options(joinedload(Order.client)).order_by(Order.date.desc(), Order.id.desc()).all()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        return [{"id": order.id, "client": order.client.name if order.client else "Cliente no disponible",
                 "date": order.date.isoformat()+"Z", "status": order.status,
                 "total": str(cents(order.total_amount)), "paid": str(cents(amount)),
                 "balance": str(max(Decimal(0), cents(order.total_amount)-cents(amount))),
                 "age_days": max(0, (now-order.date).days)} for order, amount in rows]

    def overview(self):
        receivables = self.receivables()
        receipts = cents(self.db.query(func.sum(Payment.amount)).scalar())
        expenses = cents(self.db.query(func.sum(Expense.amount)).scalar())
        sales = sum((Decimal(r["total"]) for r in receivables), Decimal(0))
        outstanding = sum((Decimal(r["balance"]) for r in receivables), Decimal(0))
        payments = self.db.query(Payment).options(joinedload(Payment.order).joinedload(Order.client)).order_by(Payment.created_at.desc(), Payment.id.desc()).limit(500).all()
        outgoings = self.db.query(Expense).order_by(Expense.created_at.desc(), Expense.id.desc()).limit(500).all()
        movements = [{**payment_data(p), "kind": "cobro", "description": f"Pedido #{p.order_id} · {p.order.client.name if p.order.client else 'Cliente'}", "category": "ventas"} for p in payments]
        movements += [{"id": e.id, "order_id": None, "kind": "gasto", "description": e.description, "category": e.category,
                       "amount": str(e.amount), "method": e.method, "reference": e.reference, "date": e.created_at.isoformat()+"Z"} for e in outgoings]
        movements.sort(key=lambda r: (r["date"],r["id"]), reverse=True)
        today = datetime.now(timezone.utc).date()
        start = datetime.combine(today-timedelta(days=6), datetime.min.time())
        collected_by_day = {str(day): cents(value) for day, value in self.db.query(func.date(Payment.created_at), func.sum(Payment.amount)).filter(Payment.created_at >= start).group_by(func.date(Payment.created_at)).all()}
        spent_by_day = {str(day): cents(value) for day, value in self.db.query(func.date(Expense.created_at), func.sum(Expense.amount)).filter(Expense.created_at >= start).group_by(func.date(Expense.created_at)).all()}
        trend = [{"date": (today-timedelta(days=6-i)).isoformat(),
                  "collected": str(collected_by_day.get((today-timedelta(days=6-i)).isoformat(), 0)),
                  "expenses": str(spent_by_day.get((today-timedelta(days=6-i)).isoformat(), 0))} for i in range(7)]
        return {"summary": {"sales": str(sales), "collected": str(receipts), "expenses": str(expenses),
                            "net_recorded": str(receipts-expenses), "outstanding": str(outstanding),
                            "unpaid_orders": sum(Decimal(r["balance"]) > 0 for r in receivables)},
                "receivables": receivables, "movements": movements, "trend": trend,
                "movement_limit_per_type": 500}

