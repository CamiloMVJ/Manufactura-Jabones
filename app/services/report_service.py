from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, date, timedelta, timezone
from sqlalchemy.orm import joinedload
from app.models.erp_models import Order, OrderItem, Product, Client, SyncLog

class ReportService:
    def __init__(self, db: Session):
        self.db = db

    def get_dashboard_stats(self):
        """Obtiene métricas generales para las tarjetas del dashboard."""
        # Total ventas ($)
        total_sales = self.db.query(func.sum(Order.total_amount)).scalar() or 0.0
        
        # Pedidos de HOY (Conteo)
        today = datetime.now(timezone.utc).date()
        orders_today = self.db.query(Order).filter(func.date(Order.date) == today).count()

        return {
            "total_sales": total_sales,
            "orders_by_status": {status: count for status, count in self.db.query(Order.status, func.count(Order.id)).group_by(Order.status).all()},
            "pending_orders": self.db.query(Order).filter(Order.status != "entregado").count(),
            "inventory_value": self.db.query(func.sum(Product.price * Product.stock)).scalar() or 0.0,
            "orders_today": orders_today, # Nuevo
            "total_clients": self.db.query(Client).count(),
            "total_products": self.db.query(Product).count(),
            "low_stock_alert": self.db.query(Product).filter(Product.stock < 10).count()
        }

    def get_recent_orders(self, limit: int = 5):
        """Obtiene las últimas órdenes creadas."""
        orders = self.db.query(Order).options(joinedload(Order.client)).order_by(desc(Order.date), desc(Order.id)).limit(limit).all()
        # Formateamos para el frontend
        return [
            {
                "id": o.id,
                "client": o.client.name if o.client else "Cliente Desconocido",
                "date": o.date.strftime("%d/%m/%Y"),
                "total": o.total_amount,
                "status": o.status
            }
            for o in orders
        ]

    def get_low_stock(self):
        """Obtiene la lista de productos con stock crítico (menor a 10)."""
        products = self.db.query(Product).filter(Product.stock < 10).all()
        return [
            {
                "id": p.id,
                "name": p.name,
                "stock": p.stock, 
                "price": p.price,
                "category": p.category or "Sin categoría"
            } for p in products
        ]

    def get_top_products(self, limit: int = 5):
        results = self.db.query(
            Product.name, 
            func.sum(OrderItem.quantity).label('sold')
        ).join(OrderItem).group_by(Product.id).order_by(desc('sold')).limit(limit).all()
        return [{"product": r.name, "sold": r.sold} for r in results]

    def get_sales_trend(self):
        today = datetime.now(timezone.utc).date()
        start = today - timedelta(days=6)
        rows = self.db.query(func.date(Order.date).label("day"), func.sum(Order.total_amount).label("total")).filter(Order.date >= datetime.combine(start, datetime.min.time())).group_by(func.date(Order.date)).all()
        values = {str(row.day): float(row.total) for row in rows}
        return [{"date": (start + timedelta(days=i)).isoformat(), "total": values.get((start + timedelta(days=i)).isoformat(), 0)} for i in range(7)]

    def get_activity(self):
        return [{"id": log.id, "entity": log.entity, "action": log.action, "details": log.details, "date": log.timestamp.isoformat() + "Z"} for log in self.db.query(SyncLog).order_by(SyncLog.timestamp.desc(), SyncLog.id.desc()).limit(8)]

    def get_operations(self):
        today = datetime.now(timezone.utc).date()
        clients = self.db.query(Client.name, func.sum(Order.total_amount).label("total"), func.count(Order.id).label("orders")).join(Order, Order.client_id == Client.id).group_by(Client.id, Client.name).order_by(desc("total")).limit(5).all()
        zones = self.db.query(Client.zone, func.count(Order.id).label("orders"), func.sum(Order.total_amount).label("total")).join(Order, Order.client_id == Client.id).group_by(Client.zone).order_by(desc("orders")).all()
        oldest = self.db.query(Order).options(joinedload(Order.client)).filter(Order.status != "entregado").order_by(Order.date).limit(5).all()
        expiring = self.db.query(Product).filter(Product.stock > 0, Product.expiry_date <= today+timedelta(days=30)).order_by(Product.expiry_date).limit(5).all()
        return {"top_products": self.get_top_products(),
                "top_clients": [{"name": r.name, "total": float(r.total), "orders": r.orders} for r in clients],
                "zones": [{"name": r.zone or "Sin zona", "orders": r.orders, "total": float(r.total)} for r in zones],
                "oldest_orders": [{"id": o.id, "client": o.client.name if o.client else "Cliente", "date": o.date.isoformat()+"Z", "status": o.status, "total": o.total_amount} for o in oldest],
                "expiring_products": [{"id": p.id, "name": p.name, "stock": p.stock, "expiry_date": p.expiry_date.isoformat(), "expired": p.expiry_date < today} for p in expiring]}

