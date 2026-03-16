from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import AppDevice, DeviceCommand, User


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_command(device_id: int, command: str, requesting_user: User, db: Session) -> DeviceCommand:
    device = db.query(AppDevice).filter(
        AppDevice.id == device_id,
        AppDevice.user_id == requesting_user.id,
        AppDevice.revoked == False,
    ).first()

    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    cmd = DeviceCommand(device_id=device_id, command=command, created_at=_now())
    db.add(cmd)
    db.commit()
    db.refresh(cmd)
    return cmd


def get_pending(device: AppDevice, db: Session) -> list[DeviceCommand]:
    # Heartbeat — update last_seen_at on every poll
    device.last_seen_at = _now()
    db.commit()

    return (
        db.query(DeviceCommand)
        .filter(DeviceCommand.device_id == device.id, DeviceCommand.acked_at == None)
        .order_by(DeviceCommand.created_at)
        .all()
    )


def ack_command(command_id: int, device: AppDevice, db: Session) -> None:
    cmd = db.query(DeviceCommand).filter(
        DeviceCommand.id == command_id,
        DeviceCommand.device_id == device.id,
    ).first()

    if not cmd:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Command not found")

    cmd.acked_at = _now()
    db.commit()
