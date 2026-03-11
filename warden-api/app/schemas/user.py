from datetime import datetime
from pydantic import BaseModel, ConfigDict


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    permissions: list[str]


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: RoleResponse
    is_active: bool
    created_at: datetime


class UserCreate(BaseModel):
    email: str
    password: str
    role_id: int


class UserUpdate(BaseModel):
    email: str | None = None
    role_id: int | None = None
    is_active: bool | None = None


class PasswordReset(BaseModel):
    password: str
