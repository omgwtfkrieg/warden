import random
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import AppDevice, Camera, PairingCode, User

# Exclude visually confusing characters (0/O, 1/I)
_SAFE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_CODE_EXPIRY_MINUTES = 5


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _generate_code() -> str:
    part = lambda: "".join(random.choices(_SAFE_CHARS, k=4))
    return f"{part()}-{part()}"


def _aspect_ratio(c: Camera) -> float:
    meta = c.stream_metadata or {}
    if c.use_sub_stream and c.sub_rtsp_url:
        stream = meta.get("sub") or {}
    else:
        stream = meta.get("main") or {}
    w, h = stream.get("width"), stream.get("height")
    if w and h and h > 0:
        return round(w / h, 4)
    return round(16 / 9, 4)


def _camera_list(db: Session) -> list[dict]:
    cameras = db.query(Camera).order_by(Camera.display_order, Camera.id).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "stream_url": f"/streams/{c.id}/webrtc",
            "use_sub_stream": c.use_sub_stream,
            "display_order": c.display_order,
            "aspect_ratio": _aspect_ratio(c),
        }
        for c in cameras
    ]


# ---------------------------------------------------------------------------

def request_code(hardware_id: str | None, device_model: str | None, db: Session) -> PairingCode:
    # Clean up any expired pending codes (housekeeping)
    db.query(PairingCode).filter(
        PairingCode.status == "pending",
        PairingCode.expires_at < _now(),
    ).update({"status": "expired"})
    db.flush()

    code = _generate_code()
    expires_at = _now() + timedelta(minutes=_CODE_EXPIRY_MINUTES)

    record = PairingCode(
        code=code,
        status="pending",
        expires_at=expires_at,
        hardware_id=hardware_id,
        device_model=device_model,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_status(code: str, db: Session) -> dict:
    record = db.query(PairingCode).filter(PairingCode.code == code).first()

    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Code not found")

    # Lazy expiry
    if record.status == "pending" and record.expires_at.replace(tzinfo=timezone.utc) < _now():
        record.status = "expired"
        db.commit()

    if record.status == "expired":
        return {"status": "expired"}

    if record.status == "pending":
        return {"status": "pending"}

    # approved — return device token + camera list
    device = db.query(AppDevice).filter(AppDevice.user_id == record.user_id).order_by(AppDevice.paired_at.desc()).first()
    return {
        "status": "approved",
        "device_token": device.device_token if device else None,
        "cameras": _camera_list(db),
    }


def activate(code: str, device_name: str | None, activating_user: User, db: Session) -> AppDevice:
    record = db.query(PairingCode).filter(PairingCode.code == code).first()

    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Code not found")

    if record.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Code is {record.status}")

    if record.expires_at.replace(tzinfo=timezone.utc) < _now():
        record.status = "expired"
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Code has expired")

    device_token = secrets.token_urlsafe(48)

    # Upsert: if the same physical device has paired before, reuse the row
    existing = None
    if record.hardware_id:
        existing = db.query(AppDevice).filter(
            AppDevice.hardware_id == record.hardware_id,
            AppDevice.user_id == activating_user.id,
        ).first()

    if existing:
        existing.device_token = device_token
        existing.device_name = device_name or existing.device_name
        existing.device_model = record.device_model or existing.device_model
        existing.revoked = False
        existing.paired_at = _now()
        device = existing
    else:
        device = AppDevice(
            user_id=activating_user.id,
            device_name=device_name,
            device_model=record.device_model,
            hardware_id=record.hardware_id,
            device_token=device_token,
            revoked=False,
        )
        db.add(device)

    record.status = "approved"
    record.user_id = activating_user.id

    db.commit()
    db.refresh(device)
    return device


def list_devices(user: User, db: Session) -> list[AppDevice]:
    return db.query(AppDevice).filter(AppDevice.user_id == user.id).all()


def revoke_device(device_id: int, user: User, db: Session) -> None:
    device = db.query(AppDevice).filter(
        AppDevice.id == device_id,
        AppDevice.user_id == user.id,
    ).first()

    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    device.revoked = True
    db.commit()


def rename_device(device_id: int, name: str, user: User, db: Session) -> AppDevice:
    device = db.query(AppDevice).filter(
        AppDevice.id == device_id,
        AppDevice.user_id == user.id,
    ).first()

    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    device.device_name = name.strip() or None
    db.commit()
    db.refresh(device)
    return device


def delete_device(device_id: int, user: User, db: Session) -> None:
    device = db.query(AppDevice).filter(
        AppDevice.id == device_id,
        AppDevice.user_id == user.id,
    ).first()

    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    if not device.revoked:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Device must be revoked before it can be deleted",
        )

    db.delete(device)
    db.commit()
