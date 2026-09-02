import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, ConfigDict

from app.models.user import UserRole


class UserBase(BaseModel):
    full_name: str
    email: EmailStr
    role: UserRole = UserRole.VIEWER


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    created_at: datetime
