from typing import Optional
from pydantic import BaseModel, EmailStr

class UserRole(BaseModel):
    cod: str
    description: Optional[str] = None
    
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    phone: str
    role: Optional[str] = None
    cnpj: Optional[str] = None
    
class UserModel(UserCreate):
    id: int
    created_at: str