from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Boolean, Date, Numeric, CheckConstraint, Text
from sqlalchemy.orm import relationship
from app.db.database import Base
from datetime import datetime
import enum

# --- Enums del Negocio ---
class SyncStatus(str, enum.Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"

class OrderStatus(str, enum.Enum): # RF-11
    PENDIENTE = "pendiente"
    PREPARADO = "preparado"
    EN_RUTA = "en_ruta"
    ENTREGADO = "entregado"

class UserRole(str, enum.Enum): # RF-19
    ADMIN = "administrador"
    VENDEDOR = "vendedor"
    REPARTIDOR = "repartidor"
    ERP_MANAGER = "erp_manager"
    PROD_MANAGER = "produccion"
    QUALITY_INSPECTOR = "calidad"
    WAREHOUSE_MANAGER = "almacen"

# --- Tabla de Usuarios (RF-19 & RNF-04) ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String) # RNF-04: Encriptado
    role = Column(String, default=UserRole.VENDEDOR) # admin, vendedor, repartidor, etc.
    is_active = Column(Boolean, default=True)
    permissions = Column(String(500), nullable=True) # JSON o lista separada por comas

# --- Tablas del Negocio (Existentes) ---
class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    contact = Column(String, nullable=True) # RF-01
    address = Column(String, nullable=True) # RF-01
    zone = Column(String, nullable=True)    # RF-02: Zona de entrega (Rivas, Tola, etc.)
    email = Column(String)
    orders = relationship("Order", back_populates="client")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    category = Column(String, nullable=True) # RF-04
    stock = Column(Integer)
    price = Column(Float)
    expiry_date = Column(Date, nullable=True) # RF-04: Fecha caducidad
    order_items = relationship("OrderItem", back_populates="product")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, default=datetime.utcnow)
    total_amount = Column(Float, default=0.0)
    status = Column(String, default=OrderStatus.PENDIENTE) # RF-11
    client_id = Column(Integer, ForeignKey("clients.id"))
    
    client = relationship("Client", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    lot_id = Column(Integer, ForeignKey("lots.id"), nullable=True)
    quantity = Column(Integer)
    subtotal = Column(Float)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")
    lot = relationship("Lot", foreign_keys=[lot_id])

class SyncLog(Base):
    __tablename__ = "sync_logs"
    id = Column(Integer, primary_key=True, index=True)
    entity = Column(String, index=True)
    action = Column(String)
    details = Column(String, nullable=True)
    status = Column(String, default=SyncStatus.SUCCESS)
    timestamp = Column(DateTime, default=datetime.utcnow)

class Payment(Base):
    """Cobros registrados: no se infieren a partir del estado de entrega."""
    __tablename__ = "payments"
    __table_args__ = (CheckConstraint("amount > 0", name="ck_payment_positive"),)
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    amount = Column(Numeric(14, 2), nullable=False)
    method = Column(String(30), nullable=False)
    reference = Column(String(200), nullable=True)
    request_id = Column(String(36), unique=True, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    order = relationship("Order")

class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (CheckConstraint("amount > 0", name="ck_expense_positive"),)
    id = Column(Integer, primary_key=True)
    description = Column(String(200), nullable=False)
    category = Column(String(50), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    method = Column(String(30), nullable=False)
    reference = Column(String(200), nullable=True)
    request_id = Column(String(36), unique=True, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class OrderStatusEvent(Base):
    __tablename__ = "order_status_events"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    previous_status = Column(String(30), nullable=True)
    status = Column(String(30), nullable=False)
    username = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# ==========================================
# MASTER DATA SUITE
# ==========================================

class Supplier(Base):
    __tablename__ = "suppliers"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    tax_id = Column(String(50), nullable=True) # RUC / Identificación
    contact_name = Column(String(200), nullable=True)
    email = Column(String(200), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(String(500), nullable=True)
    category = Column(String(100), nullable=True)
    payment_terms = Column(String(100), default="30 días")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Warehouse(Base):
    __tablename__ = "warehouses"
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    address = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)

class Location(Base):
    __tablename__ = "locations"
    id = Column(Integer, primary_key=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    code = Column(String(50), nullable=False)
    name = Column(String(200), nullable=False)
    aisle = Column(String(50), nullable=True)
    rack = Column(String(50), nullable=True)
    shelf = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    warehouse = relationship("Warehouse", backref="locations")

class WorkCenter(Base):
    __tablename__ = "work_centers"
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    capacity_per_hour = Column(Float, default=100.0)
    cost_per_hour = Column(Float, default=25.0)
    status = Column(String(50), default="operativo")
    is_active = Column(Boolean, default=True)

class Employee(Base):
    __tablename__ = "employees"
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    position = Column(String(100), nullable=False)
    department = Column(String(100), nullable=False)
    email = Column(String(200), nullable=True)
    phone = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)


# ==========================================
# INVENTORY, LOTS & TRACEABILITY
# ==========================================

class Lot(Base):
    __tablename__ = "lots"
    id = Column(Integer, primary_key=True)
    lot_number = Column(String(100), unique=True, nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    initial_quantity = Column(Float, default=0.0)
    current_quantity = Column(Float, default=0.0)
    manufacture_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    status = Column(String(50), default="released") # quarantine, released, consumed, rejected, expired
    notes = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product")
    supplier = relationship("Supplier")

class StockLocation(Base):
    __tablename__ = "stock_locations"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    lot_id = Column(Integer, ForeignKey("lots.id"), nullable=True)
    quantity = Column(Float, default=0.0)
    reserved_quantity = Column(Float, default=0.0)

    product = relationship("Product")
    warehouse = relationship("Warehouse")
    location = relationship("Location")
    lot = relationship("Lot")

class InventoryMovement(Base):
    __tablename__ = "inventory_movements"
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    lot_id = Column(Integer, ForeignKey("lots.id"), nullable=True)
    movement_type = Column(String(50), nullable=False) # purchase_receipt, production_consumption, production_output, sales_dispatch, transfer, adjustment
    source_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)
    source_location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    dest_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)
    dest_location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    quantity = Column(Float, nullable=False)
    reference_doc_type = Column(String(50), nullable=True) # purchase_order, production_order, sales_order, quality_scrap, adjustment
    reference_doc_id = Column(String(50), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product")
    lot = relationship("Lot")
    user = relationship("User")
    source_warehouse = relationship("Warehouse", foreign_keys=[source_warehouse_id])
    dest_warehouse = relationship("Warehouse", foreign_keys=[dest_warehouse_id])


# ==========================================
# PROCUREMENT SUITE
# ==========================================

class PurchaseRequest(Base):
    __tablename__ = "purchase_requests"
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    requested_by = Column(String(100), nullable=False)
    department = Column(String(100), default="Operaciones")
    date = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="pending_approval") # draft, pending_approval, approved, rejected, ordered
    total_estimated = Column(Float, default=0.0)
    notes = Column(String(500), nullable=True)
    items = relationship("PurchaseRequestItem", back_populates="request", cascade="all, delete-orphan")

class PurchaseRequestItem(Base):
    __tablename__ = "purchase_request_items"
    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey("purchase_requests.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    estimated_unit_price = Column(Float, default=0.0)
    request = relationship("PurchaseRequest", back_populates="items")
    product = relationship("Product")

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    request_id = Column(Integer, ForeignKey("purchase_requests.id"), nullable=True)
    order_date = Column(DateTime, default=datetime.utcnow)
    expected_delivery_date = Column(Date, nullable=True)
    status = Column(String(50), default="approved") # draft, pending_approval, approved, ordered, received, cancelled
    total_amount = Column(Float, default=0.0)
    notes = Column(String(500), nullable=True)
    supplier = relationship("Supplier")
    items = relationship("PurchaseOrderItem", back_populates="purchase_order", cascade="all, delete-orphan")

class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"
    id = Column(Integer, primary_key=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)
    received_quantity = Column(Float, default=0.0)
    purchase_order = relationship("PurchaseOrder", back_populates="items")
    product = relationship("Product")

class MaterialReception(Base):
    __tablename__ = "material_receptions"
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    reception_date = Column(DateTime, default=datetime.utcnow)
    received_by = Column(String(100), default="Almacenero Central")
    status = Column(String(50), default="completed") # pending, completed
    notes = Column(String(500), nullable=True)
    purchase_order = relationship("PurchaseOrder")
    warehouse = relationship("Warehouse")
    items = relationship("MaterialReceptionItem", back_populates="reception", cascade="all, delete-orphan")

class MaterialReceptionItem(Base):
    __tablename__ = "material_reception_items"
    id = Column(Integer, primary_key=True)
    reception_id = Column(Integer, ForeignKey("material_receptions.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity_received = Column(Float, nullable=False)
    lot_number = Column(String(100), nullable=True)
    reception = relationship("MaterialReception", back_populates="items")
    product = relationship("Product")


# ==========================================
# MANUFACTURING SUITE (BOM, ROUTING, OP)
# ==========================================

class BillOfMaterial(Base):
    __tablename__ = "bills_of_material"
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)
    finished_product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    version = Column(String(20), default="1.0")
    quantity = Column(Float, default=1.0)
    is_active = Column(Boolean, default=True)
    notes = Column(String(500), nullable=True)
    finished_product = relationship("Product")
    items = relationship("BOMItem", back_populates="bom", cascade="all, delete-orphan")

class BOMItem(Base):
    __tablename__ = "bom_items"
    id = Column(Integer, primary_key=True)
    bom_id = Column(Integer, ForeignKey("bills_of_material.id"), nullable=False)
    component_product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    scrap_percentage = Column(Float, default=0.0)
    bom = relationship("BillOfMaterial", back_populates="items")
    component_product = relationship("Product")

class Routing(Base):
    __tablename__ = "routings"
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    finished_product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    description = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    finished_product = relationship("Product")
    operations = relationship("RoutingOperation", back_populates="routing", cascade="all, delete-orphan")

class RoutingOperation(Base):
    __tablename__ = "routing_operations"
    id = Column(Integer, primary_key=True)
    routing_id = Column(Integer, ForeignKey("routings.id"), nullable=False)
    sequence = Column(Integer, default=10)
    work_center_id = Column(Integer, ForeignKey("work_centers.id"), nullable=False)
    operation_name = Column(String(200), nullable=False)
    standard_duration_minutes = Column(Float, default=15.0)
    routing = relationship("Routing", back_populates="operations")
    work_center = relationship("WorkCenter")

class ProductionOrder(Base):
    __tablename__ = "production_orders"
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    bom_id = Column(Integer, ForeignKey("bills_of_material.id"), nullable=True)
    routing_id = Column(Integer, ForeignKey("routings.id"), nullable=True)
    raw_material_lot_id = Column(Integer, ForeignKey("lots.id"), nullable=True)
    finished_lot_id = Column(Integer, ForeignKey("lots.id"), nullable=True)
    planned_quantity = Column(Float, nullable=False)
    produced_quantity = Column(Float, default=0.0)
    status = Column(String(50), default="draft") # draft, planned, materials_reserved, in_production, quality_control, completed, closed
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    created_by = Column(String(100), default="Jefe de Producción")
    notes = Column(String(500), nullable=True)

    product = relationship("Product")
    bom = relationship("BillOfMaterial")
    routing = relationship("Routing")
    raw_lot = relationship("Lot", foreign_keys=[raw_material_lot_id])
    finished_lot = relationship("Lot", foreign_keys=[finished_lot_id])
    work_orders = relationship("ProductionWorkOrder", back_populates="production_order", cascade="all, delete-orphan")
    consumptions = relationship("ProductionMaterialConsumption", back_populates="production_order", cascade="all, delete-orphan")

class ProductionMaterialConsumption(Base):
    __tablename__ = "production_consumptions"
    id = Column(Integer, primary_key=True)
    production_order_id = Column(Integer, ForeignKey("production_orders.id"), nullable=False)
    component_product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    lot_id = Column(Integer, ForeignKey("lots.id"), nullable=True)
    planned_quantity = Column(Float, nullable=False)
    consumed_quantity = Column(Float, default=0.0)
    status = Column(String(50), default="consumed")
    production_order = relationship("ProductionOrder", back_populates="consumptions")
    component_product = relationship("Product")
    lot = relationship("Lot")

class ProductionWorkOrder(Base):
    __tablename__ = "production_work_orders"
    id = Column(Integer, primary_key=True)
    production_order_id = Column(Integer, ForeignKey("production_orders.id"), nullable=False)
    operation_sequence = Column(Integer, default=10)
    work_center_id = Column(Integer, ForeignKey("work_centers.id"), nullable=False)
    operation_name = Column(String(200), nullable=False)
    status = Column(String(50), default="completed") # pending, in_progress, completed, paused
    operator_name = Column(String(100), nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_minutes = Column(Float, default=0.0)
    production_order = relationship("ProductionOrder", back_populates="work_orders")
    work_center = relationship("WorkCenter")


# ==========================================
# QUALITY MANAGEMENT SUITE
# ==========================================

class QualityInspection(Base):
    __tablename__ = "quality_inspections"
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    lot_id = Column(Integer, ForeignKey("lots.id"), nullable=True)
    production_order_id = Column(Integer, ForeignKey("production_orders.id"), nullable=True)
    reception_id = Column(Integer, ForeignKey("material_receptions.id"), nullable=True)
    inspection_type = Column(String(50), default="finished_goods") # incoming_raw_material, in_process, finished_goods
    expected_value = Column(String(200), nullable=True)
    measured_value = Column(String(200), nullable=True)
    result = Column(String(50), default="passed") # passed, failed, conditional
    inspector_name = Column(String(100), default="Inspector Calidad")
    inspection_date = Column(DateTime, default=datetime.utcnow)
    observations = Column(String(500), nullable=True)
    status = Column(String(50), default="completed")

    product = relationship("Product")
    lot = relationship("Lot")
    production_order = relationship("ProductionOrder")

class QualityNonConformity(Base):
    __tablename__ = "quality_non_conformities"
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    inspection_id = Column(Integer, ForeignKey("quality_inspections.id"), nullable=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    lot_id = Column(Integer, ForeignKey("lots.id"), nullable=True)
    severity = Column(String(50), default="minor") # minor, major, critical
    description = Column(String(500), nullable=False)
    cause = Column(String(500), nullable=True)
    disposition = Column(String(50), default="rework") # scrap, rework, release
    disposition_notes = Column(String(500), nullable=True)
    status = Column(String(50), default="resolved") # open, investigating, resolved, accepted
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product")
    lot = relationship("Lot")
    inspection = relationship("QualityInspection")


# ==========================================
# GOVERNANCE, APPROVALS, AUDIT & LOGS
# ==========================================

class ApprovalItem(Base):
    __tablename__ = "approval_items"
    id = Column(Integer, primary_key=True)
    document_type = Column(String(50), nullable=False) # purchase_request, purchase_order, inventory_adjustment, quality_release, expense
    document_id = Column(Integer, nullable=False)
    document_code = Column(String(50), nullable=False)
    requested_by = Column(String(100), nullable=False)
    amount = Column(Float, default=0.0)
    reason = Column(String(500), nullable=False)
    status = Column(String(50), default="pending") # pending, approved, rejected
    approver_name = Column(String(100), nullable=True)
    approval_notes = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    username = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)
    module = Column(String(100), nullable=False)
    record_id = Column(String(50), nullable=True)
    record_reference = Column(String(200), nullable=True)
    ip_address = Column(String(50), default="127.0.0.1")
    before_state = Column(Text, nullable=True)
    after_state = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class SystemIssueLog(Base):
    __tablename__ = "system_issue_logs"
    id = Column(Integer, primary_key=True)
    issue = Column(String(200), nullable=False)
    module = Column(String(100), nullable=False)
    detected_date = Column(Date, default=datetime.utcnow)
    impact = Column(String(50), default="medium") # low, medium, high, critical
    cause = Column(String(500), nullable=True)
    solution = Column(String(500), nullable=True)
    status = Column(String(50), default="resolved") # open, investigating, resolved, accepted
    responsible = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class ContributionLog(Base):
    __tablename__ = "contribution_logs"
    id = Column(Integer, primary_key=True)
    contributor = Column(String(100), nullable=False)
    task = Column(String(200), nullable=False)
    module = Column(String(100), nullable=False)
    description = Column(String(500), nullable=False)
    commit_ref = Column(String(50), default="HEAD")
    status = Column(String(50), default="completado")
    created_at = Column(DateTime, default=datetime.utcnow)

