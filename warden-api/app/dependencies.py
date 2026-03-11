from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, AppDevice
from app.services import auth_service

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    user_id = auth_service.decode_access_token(credentials.credentials)
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_permission(permission: str):
    """Dependency factory. Usage: Depends(require_permission("cameras:write"))"""
    def check(current_user: User = Depends(get_current_user)) -> User:
        if permission not in (current_user.role.permissions or []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission}",
            )
        return current_user

    return check


def get_device(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AppDevice:
    """Validates a Flutter app device token (not a JWT)."""
    device = (
        db.query(AppDevice)
        .filter(AppDevice.device_token == credentials.credentials, AppDevice.revoked == False)
        .first()
    )
    if not device:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid device token")
    return device
