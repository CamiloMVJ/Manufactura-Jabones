from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any

from app.db.database import get_db
from app.services.enterprise_service import EnterpriseService
from app.core.security import get_current_user, check_role
from app.models.erp_models import (
    User, AuditLog, Order, OrderItem, Product, Client, ApprovalItem,
    PurchaseRequest, PurchaseOrder, MaterialReception, ProductionOrder,
    QualityInspection, QualityNonConformity
)

router = APIRouter(prefix="/enterprise", tags=["Enterprise Suite"], dependencies=[Depends(get_current_user)])

# ==========================================
# MASTER DATA
# ==========================================
@router.get("/suppliers")
def get_suppliers(db: Session = Depends(get_db)):
    return [
        {
            "id": s.id,
            "name": s.name,
            "tax_id": s.tax_id,
            "contact_name": s.contact_name,
            "email": s.email,
            "phone": s.phone,
            "address": s.address,
            "category": s.category,
            "payment_terms": s.payment_terms
        }
        for s in EnterpriseService(db).get_suppliers()
    ]

@router.post("/suppliers", dependencies=[Depends(check_role(["administrador"]))])
def create_supplier(data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    s = EnterpriseService(db).create_supplier(data, current_user.username)
    return {
        "id": s.id,
        "name": s.name,
        "tax_id": s.tax_id,
        "contact_name": s.contact_name,
        "category": s.category,
        "payment_terms": s.payment_terms
    }

@router.get("/warehouses")
def get_warehouses(db: Session = Depends(get_db)):
    return [
        {"id": w.id, "code": w.code, "name": w.name, "address": w.address}
        for w in EnterpriseService(db).get_warehouses()
    ]

@router.get("/locations")
def get_locations(warehouse_id: Optional[int] = None, db: Session = Depends(get_db)):
    return [
        {"id": l.id, "warehouse_id": l.warehouse_id, "code": l.code, "name": l.name, "aisle": l.aisle, "rack": l.rack, "shelf": l.shelf}
        for l in EnterpriseService(db).get_locations(warehouse_id)
    ]

@router.get("/work-centers")
def get_work_centers(db: Session = Depends(get_db)):
    return [
        {"id": wc.id, "code": wc.code, "name": wc.name, "capacity_per_hour": wc.capacity_per_hour, "cost_per_hour": wc.cost_per_hour, "status": wc.status}
        for wc in EnterpriseService(db).get_work_centers()
    ]

@router.get("/employees")
def get_employees(db: Session = Depends(get_db)):
    return [
        {"id": e.id, "code": e.code, "name": e.name, "position": e.position, "department": e.department, "email": e.email}
        for e in EnterpriseService(db).get_employees()
    ]

# ==========================================
# PROCUREMENT
# ==========================================
@router.get("/purchase-requests")
def get_purchase_requests(db: Session = Depends(get_db)):
    return EnterpriseService(db).get_purchase_requests()

@router.post("/purchase-requests", dependencies=[Depends(check_role(["administrador"]))])
def create_purchase_request(data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    pr = EnterpriseService(db).create_purchase_request(data, current_user.username)
    return {
        "id": pr.id,
        "code": pr.code,
        "status": pr.status,
        "total_estimated": pr.total_estimated,
        "requested_by": pr.requested_by,
        "department": pr.department
    }

@router.get("/purchase-orders")
def get_purchase_orders(db: Session = Depends(get_db)):
    return EnterpriseService(db).get_purchase_orders()

@router.post("/purchase-orders", dependencies=[Depends(check_role(["administrador"]))])
def create_purchase_order(data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    po = EnterpriseService(db).create_purchase_order(data, current_user.username)
    return {
        "id": po.id,
        "code": po.code,
        "status": po.status,
        "total_amount": po.total_amount,
        "supplier_id": po.supplier_id
    }

@router.post("/material-receptions", dependencies=[Depends(check_role(["administrador"]))])
def receive_material(data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rec = EnterpriseService(db).receive_material(
        purchase_order_id=int(data["purchase_order_id"]),
        warehouse_id=int(data.get("warehouse_id", 1)),
        items_data=data["items"],
        received_by=current_user.username
    )
    return {
        "id": rec.id,
        "code": rec.code,
        "status": rec.status,
        "purchase_order_id": rec.purchase_order_id,
        "warehouse_id": rec.warehouse_id
    }

# ==========================================
# INVENTORY & LOT TRACEABILITY
# ==========================================
@router.get("/inventory-summary")
def get_inventory_summary(db: Session = Depends(get_db)):
    return EnterpriseService(db).get_inventory_summary()

@router.get("/lots")
def get_lots(db: Session = Depends(get_db)):
    return EnterpriseService(db).get_lots()

@router.get("/inventory-movements")
def get_inventory_movements(limit: int = 100, db: Session = Depends(get_db)):
    return EnterpriseService(db).get_inventory_movements(limit)

@router.get("/lot-traceability/{lot_id_or_number}")
def get_lot_traceability(lot_id_or_number: str, db: Session = Depends(get_db)):
    res = EnterpriseService(db).get_lot_traceability(lot_id_or_number)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res

# ==========================================
# MANUFACTURING (BOM, ROUTING, OP)
# ==========================================
@router.get("/boms")
def get_boms(db: Session = Depends(get_db)):
    return EnterpriseService(db).get_boms()

@router.get("/routings")
def get_routings(db: Session = Depends(get_db)):
    return EnterpriseService(db).get_routings()

@router.get("/production-orders")
def get_production_orders(db: Session = Depends(get_db)):
    return EnterpriseService(db).get_production_orders()

@router.post("/production-orders", dependencies=[Depends(check_role(["administrador"]))])
def create_production_order(data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    po = EnterpriseService(db).create_production_order(data, current_user.username)
    return {
        "id": po.id,
        "code": po.code,
        "status": po.status,
        "planned_quantity": po.planned_quantity,
        "product_id": po.product_id
    }

@router.patch("/production-orders/{order_id}/status", dependencies=[Depends(check_role(["administrador"]))])
def advance_production_order(order_id: int, data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    po = EnterpriseService(db).advance_production_order(order_id, data["status"], current_user.username)
    return {
        "id": po.id,
        "code": po.code,
        "status": po.status,
        "produced_quantity": po.produced_quantity,
        "finished_lot_id": po.finished_lot_id
    }

# ==========================================
# QUALITY MANAGEMENT
# ==========================================
@router.get("/quality/dashboard")
def get_quality_dashboard(db: Session = Depends(get_db)):
    return EnterpriseService(db).get_quality_dashboard()

@router.post("/quality/inspections", dependencies=[Depends(check_role(["administrador"]))])
def create_quality_inspection(data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    qc = EnterpriseService(db).create_quality_inspection(data, current_user.username)
    return {
        "id": qc.id,
        "code": qc.code,
        "result": qc.result,
        "status": qc.status,
        "product_id": qc.product_id
    }

@router.patch("/quality/non-conformities/{nc_id}/disposition", dependencies=[Depends(check_role(["administrador"]))])
def update_nc_disposition(nc_id: int, data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    nc = EnterpriseService(db).update_non_conformity_disposition(nc_id, data["disposition"], data.get("notes", ""), current_user.username)
    return {
        "id": nc.id,
        "code": nc.code,
        "disposition": nc.disposition,
        "status": nc.status
    }

# ==========================================
# APPROVALS & GOVERNANCE
# ==========================================
@router.get("/approvals")
def get_approvals(status: str = "pending", db: Session = Depends(get_db)):
    return EnterpriseService(db).get_approvals(status)

@router.post("/approvals/{approval_id}/action", dependencies=[Depends(check_role(["administrador"]))])
def process_approval(approval_id: int, data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    apv = EnterpriseService(db).process_approval(approval_id, data["action"], data.get("notes", ""), current_user.username)
    return {
        "id": apv.id,
        "status": apv.status,
        "document_code": apv.document_code
    }

# ==========================================
# SYSTEM & DATA MONITORS
# ==========================================
@router.get("/system-health")
def get_system_health(db: Session = Depends(get_db)):
    return EnterpriseService(db).get_system_health()

@router.get("/data-health")
def get_data_health(db: Session = Depends(get_db)):
    return EnterpriseService(db).get_data_health()

@router.get("/audit-logs")
def get_audit_logs(limit: int = 50, db: Session = Depends(get_db)):
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": l.id,
            "username": l.username,
            "action": l.action,
            "module": l.module,
            "record_reference": l.record_reference,
            "before_state": l.before_state,
            "after_state": l.after_state,
            "ip_address": l.ip_address,
            "created_at": l.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }
        for l in logs
    ]

@router.get("/users")
def get_users(db: Session = Depends(get_db), current_user: User = Depends(check_role(["administrador", "erp_manager"]))):
    users = db.query(User).order_by(User.id).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "is_active": u.is_active,
            "permissions": u.permissions or "Acceso estándar"
        }
        for u in users
    ]

# ==========================================
# GLOBAL SEARCH & ANALYTICS
# ==========================================
@router.get("/global-search")
def global_search(q: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    return EnterpriseService(db).global_search(q)

@router.get("/analytics")
def get_analytics(db: Session = Depends(get_db)):
    return EnterpriseService(db).get_analytics()

@router.get("/project-logs")
def get_project_logs(db: Session = Depends(get_db)):
    return EnterpriseService(db).get_project_logs()

# ==========================================
# END-TO-END DEMONSTRABLE TRANSACTIONAL FLOW
# ==========================================
@router.post("/workflow/execute-demo-flow", dependencies=[Depends(check_role(["administrador"]))])
def execute_demo_flow(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Executes a complete end-to-end transactional ERP cycle:
    Purchase Request -> Purchase Order -> Reception & Raw Lot ->
    Production Order -> Consumption -> Quality Inspection ->
    Finished Goods Lot -> Sales Order Dispatch -> Full Lot Traceability!
    """
    raise HTTPException(409, 'Usa el flujo manual de jabonería descrito en LEEME_JABONERIA.md; el demo agroindustrial fue retirado.')

@router.get('/soap-catalog')
def soap_catalog():
    import json
    from app.core.config import BASE_DIR
    return json.loads((BASE_DIR / 'data/catalogo.json').read_text(encoding='utf-8'))
