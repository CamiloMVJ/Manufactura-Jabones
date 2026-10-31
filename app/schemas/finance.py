from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, Field, StringConstraints

Amount = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2, allow_inf_nan=False)]
Method = Literal["efectivo", "transferencia", "tarjeta"]

class PaymentCreate(BaseModel):
    order_id: Annotated[int, Field(gt=0)]
    amount: Amount
    method: Method
    reference: str | None = Field(default=None, max_length=200)
    request_id: UUID

class ExpenseCreate(BaseModel):
    description: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=200)]
    category: Literal["transporte", "servicios", "compras", "personal", "otros"]
    amount: Amount
    method: Method
    reference: str | None = Field(default=None, max_length=200)
    request_id: UUID

