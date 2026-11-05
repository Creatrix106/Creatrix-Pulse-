from typing import Optional, Literal
from pydantic import BaseModel, Field, EmailStr

UserRole = Literal["admin", "analyst", "viewer"]

class UserBase(BaseModel):
    name: str
    email: str
    role: UserRole = "admin"

class RegisterPayload(BaseModel):
    name: str
    email: str
    password: str
    role: Optional[UserRole] = "admin"

class LoginPayload(BaseModel):
    email: str
    password: str

class User(UserBase):
    id: str
    created_at: Optional[str] = None
    active_workspace: Optional[str] = "Personal Workspace"

    class Config:
        orm_mode = True
        allow_population_by_field_name = True

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: User
    role: str = "admin"
    id: str
    name: str
    email: str

class RefreshPayload(BaseModel):
    refresh_token: str
