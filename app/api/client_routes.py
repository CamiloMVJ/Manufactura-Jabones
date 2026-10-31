from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.erp_models import Client, User, SyncLog
from app.schemas import ClientCreate, ClientResponse
from app.core.security import get_current_sales_person, get_current_user

router = APIRouter(prefix="/clients", tags=["Clientes"], dependencies=[Depends(get_current_user)])

@router.get("/", response_model=List[ClientResponse])
def list_clients(db: Session = Depends(get_db)):
    return db.query(Client).all()

@router.post("/", response_model=ClientResponse)
def create_client(
    client: ClientCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_sales_person)
):
    existing = db.query(Client).filter(Client.email == client.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un cliente con ese email")
    
    new_client = Client(
        name=client.name,
        email=client.email,
        contact=client.contact,
        address=client.address,
        zone=client.zone
    )
    db.add(new_client)
    db.add(SyncLog(entity="Client", action="create", details=f"Cliente {client.name} creado por {current_user.username}"))
    db.commit()
    db.refresh(new_client)
    return new_client

@router.get("/{client_id}", response_model=ClientResponse)
def get_client(client_id: int, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return client

@router.put("/{client_id}", response_model=ClientResponse)
def update_client(client_id: int, data: ClientCreate, db: Session = Depends(get_db), user: User = Depends(get_current_sales_person)):
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(404, "Cliente no encontrado")
    if db.query(Client).filter(Client.email == data.email, Client.id != client_id).first():
        raise HTTPException(409, "Ya existe un cliente con ese email")
    for key, value in data.model_dump().items():
        setattr(client, key, value)
    db.add(SyncLog(entity="Client", action="update", details=f"Cliente #{client_id} actualizado por {user.username}"))
    db.commit()
    db.refresh(client)
    return client

