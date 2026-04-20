from typing import Optional
from pydantic import BaseModel, EmailStr
from .enums import UserRole
    
class UserCreateModel(BaseModel):
    username: str
    email: EmailStr
    password: str
    phone: str
    role: UserRole
    cnpj: Optional[str] = None
    
class UserModel(UserCreateModel):
    id: int
    created_at: str