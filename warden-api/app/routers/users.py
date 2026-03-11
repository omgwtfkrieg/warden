from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models import User
from app.schemas.user import (
    UserCreate, UserUpdate, UserResponse,
    RoleResponse, PasswordReset,
)
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    _=Depends(require_permission("users:read")),
):
    return user_service.list_users(db)


@router.get("/roles", response_model=list[RoleResponse])
def list_roles(
    db: Session = Depends(get_db),
    _=Depends(require_permission("users:read")),
):
    return user_service.list_roles(db)


@router.post("", response_model=UserResponse, status_code=201)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _=Depends(require_permission("users:write")),
):
    return user_service.create_user(payload, db)


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_permission("users:write")),
):
    return user_service.update_user(user_id, payload, db)


@router.post("/{user_id}/reset-password", status_code=204)
def reset_password(
    user_id: int,
    payload: PasswordReset,
    db: Session = Depends(get_db),
    _=Depends(require_permission("users:write")),
):
    user_service.reset_password(user_id, payload.password, db)


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_permission("users:write")),
):
    user_service.delete_user(user_id, current_user.id, db)
