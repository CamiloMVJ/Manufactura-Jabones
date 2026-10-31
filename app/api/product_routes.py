from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.erp_models import Product, SyncLog, User
from app.schemas import ProductCreate, ProductResponse, ProductUpdate # <-- Importar ProductUpdate
from app.core.events import manager
from app.core.security import get_current_sales_person, get_current_active_admin, get_current_user

router = APIRouter(prefix="/products", tags=["Productos"], dependencies=[Depends(get_current_user)])

# 1. Listar
@router.get("/", response_model=List[ProductResponse])
def list_products(db: Session = Depends(get_db)):
    return db.query(Product).order_by(Product.id).all()

# 2. Crear (Solo Vendedores/Admin)
@router.post("/", response_model=ProductResponse)
def create_product(
    product: ProductCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_sales_person)
):
    if product.stock != 0:
        raise HTTPException(409, 'Crea el producto con stock cero e ingresa existencias mediante Compras y recepción')
    existing = db.query(Product).filter(Product.name == product.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un producto con este nombre")

    new_product = Product(**product.model_dump())
    db.add(new_product)
    
    # Log
    log = SyncLog(entity="Product", action="create", details=f"Creado por {current_user.username}")
    db.add(log)
    
    db.commit()
    db.refresh(new_product)
    return new_product

# 3. Actualizar Producto Completo (Precio, Nombre, etc.)
@router.put("/{id}", response_model=ProductResponse)
def update_product(
    id: int,
    product_update: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_sales_person)
):
    product = db.query(Product).filter(Product.id == id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    if product_update.stock is not None and product_update.stock != product.stock:
        raise HTTPException(409, 'Registra entradas con lote desde Compras; no edites el stock agregado')
    # Actualizar solo los campos enviados
    if product_update.name and db.query(Product).filter(Product.name == product_update.name, Product.id != id).first():
        raise HTTPException(409, "Ya existe un producto con este nombre")
    for key, value in product_update.model_dump(exclude_unset=True).items():
        setattr(product, key, value)

    log = SyncLog(entity="Product", action="update", details=f"ID {id} actualizado por {current_user.username}")
    db.add(log)
    db.commit()
    db.refresh(product)
    return product

# 4. Eliminar Producto (Solo Admin)
@router.delete("/{id}")
def delete_product(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin) # Seguridad estricta
):
    product = db.query(Product).filter(Product.id == id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    # Verificar si tiene ventas asociadas (Integridad Referencial)
    if product.order_items:
        raise HTTPException(status_code=400, detail="No se puede eliminar: El producto tiene ventas registradas.")

    db.delete(product)
    log = SyncLog(entity="Product", action="delete", details=f"ID {id} eliminado por {current_user.username}")
    db.add(log)
    db.commit()
    return {"message": "Producto eliminado correctamente"}

# 5. Endpoint Rápido de Stock (Para el botón rápido)
@router.put("/{id}/stock")
async def update_stock(id: int, quantity: int = Query(..., ge=0), db: Session = Depends(get_db), user: User = Depends(get_current_sales_person)):
    raise HTTPException(409, 'El stock se gestiona por recepciones, producción y ventas con lote')
