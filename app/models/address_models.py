from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class AddressCreateModel(BaseModel):
    cep: Optional[str] = None
    uf: str
    city: str
    neighborhood: str
    street: str
    number: str = "S/N"
    lat: Optional[float] = None
    lon: Optional[float] = None
    ibge_code: Optional[int] = None

class AddressModel(AddressCreateModel):
    id: int
    created_at: datetime
    updated_at: datetime