from datetime import date, datetime
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Money = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Role = Literal["administrador", "vendedor", "repartidor"]

class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class UserBase(BaseModel):
    username: Name
    email: Name
    role: Role

class UserCreate(UserBase):
    password: Annotated[str, Field(min_length=8, max_length=72)]

    @field_validator("password")
    @classmethod
    def bcrypt_byte_limit(cls, value):
        if len(value.encode("utf-8")) > 72:
            raise ValueError("La contraseña no puede superar 72 bytes UTF-8")
        return value

class UserResponse(UserBase, ORMModel):
    id: int
    is_active: bool

class Token(BaseModel):
    access_token: str
    token_type: str

class ProductBase(BaseModel):
    name: Name
    price: Money
    stock: Annotated[int, Field(ge=0)]
    category: str | None = Field(default=None, max_length=200)
    expiry_date: date | None = None

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Name | None = None
    price: Money | None = None
    stock: Annotated[int, Field(ge=0)] | None = None
    category: str | None = Field(default=None, max_length=200)
    expiry_date: date | None = None

    @field_validator("name", "price", "stock")
    @classmethod
    def required_values_cannot_be_null(cls, value):
        if value is None:
            raise ValueError("Este campo no puede ser nulo")
        return value

class ProductResponse(ProductBase, ORMModel):
    id: int

class OrderItemCreate(BaseModel):
    product_id: Annotated[int, Field(gt=0)]
    quantity: Annotated[int, Field(gt=0, le=1_000_000)]

class OrderCreate(BaseModel):
    client_id: Annotated[int, Field(gt=0)]
    items: Annotated[list[OrderItemCreate], Field(min_length=1, max_length=200)]

class OrderResponse(ORMModel):
    id: int
    total_amount: float
    date: datetime
    status: str

class OrderStatusUpdate(BaseModel):
    status: Literal["pendiente", "preparado", "en_ruta", "entregado"]

class ClientBase(BaseModel):
    name: Name
    email: Name
    contact: str | None = Field(default=None, max_length=200)
    address: str | None = Field(default=None, max_length=500)
    zone: str | None = Field(default=None, max_length=200)

class ClientCreate(ClientBase):
    pass

class ClientResponse(ClientBase, ORMModel):
    id: int

