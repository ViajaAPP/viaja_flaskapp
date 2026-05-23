from typing import Optional
from pydantic import BaseModel, EmailStr
from .enums import UserRole
    
class UserCreateModel(BaseModel):
    username: str
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    phone: str
    role: UserRole
    photo: str
    cnpj: Optional[str] = None
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
class UserModel(UserCreateModel):
    id: int
    created_at: str