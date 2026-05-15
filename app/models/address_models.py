from pydantic import BaseModel
from datetime import datetime

class AddressCreateModel(BaseModel):
    cep: str
    uf: str
    city: str
    neighborhood: str
    street: str
    number: str
    
class AddressModel(AddressCreateModel):
    id: int
    created_at: datetime
    updated_at: datetime