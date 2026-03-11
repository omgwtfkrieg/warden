import bcrypt
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import User, Role
from app.schemas.user import UserCreate, UserUpdate


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def list_users(db: Session) -> list[User]:
    return db.query(User).order_by(User.created_at).all()


def list_roles(db: Session) -> list[Role]:
    return db.query(Role).order_by(Role.id).all()


def get_user(user_id: int, db: Session) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def create_user(data: UserCreate, db: Session) -> User:
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")
    if not db.query(Role).filter(Role.id == data.role_id).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role not found")
    user = User(
        email=data.email,
        hashed_password=_hash_password(data.password),
        role_id=data.role_id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(user_id: int, data: UserUpdate, db: Session) -> User:
    user = get_user(user_id, db)
    if data.email is not None:
        conflict = db.query(User).filter(User.email == data.email, User.id != user_id).first()
        if conflict:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")
        user.email = data.email
    if data.role_id is not None:
        if not db.query(Role).filter(Role.id == data.role_id).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role not found")
        user.role_id = data.role_id
    if data.is_active is not None:
        user.is_active = data.is_active
    db.commit()
    db.refresh(user)
    return user


def reset_password(user_id: int, password: str, db: Session) -> None:
    user = get_user(user_id, db)
    user.hashed_password = _hash_password(password)
    db.commit()


def delete_user(user_id: int, current_user_id: int, db: Session) -> None:
    if user_id == current_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )
    user = get_user(user_id, db)
    db.delete(user)
    db.commit()
