import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User, RefreshToken


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7
ALGORITHM = "HS256"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(user_id: int) -> tuple[str, int]:
    """Returns (token, expires_in_seconds)."""
    expire = _now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire, "type": "access"}
    token = jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
    return token, ACCESS_TOKEN_EXPIRE_MINUTES * 60


def _create_refresh_token(user_id: int, db: Session) -> str:
    raw_token = secrets.token_urlsafe(48)
    expires_at = _now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    record = RefreshToken(
        user_id=user_id,
        token=raw_token,
        expires_at=expires_at,
        revoked=False,
    )
    db.add(record)
    db.commit()
    return raw_token


def login(email: str, password: str, db: Session) -> dict:
    user = db.query(User).filter(User.email == email, User.is_active == True).first()
    if not user or not _verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    access_token, expires_in = create_access_token(user.id)
    refresh_token = _create_refresh_token(user.id, db)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": expires_in,
    }


def refresh_access_token(raw_token: str, db: Session) -> dict:
    record = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.token == raw_token,
            RefreshToken.revoked == False,
        )
        .first()
    )

    if not record:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    if record.expires_at.replace(tzinfo=timezone.utc) < _now():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

    access_token, expires_in = create_access_token(record.user_id)
    return {"access_token": access_token, "token_type": "bearer", "expires_in": expires_in}


def logout(raw_token: str, db: Session) -> None:
    record = db.query(RefreshToken).filter(RefreshToken.token == raw_token).first()
    if record:
        record.revoked = True
        db.commit()


def decode_access_token(token: str) -> int:
    """Decode and validate an access token. Returns user_id."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return int(user_id)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
