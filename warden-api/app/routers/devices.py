from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_permission
from app.models import User
from app.schemas.device import DeviceResponse, DeviceRenameBody
from app.services import pairing_service

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("", response_model=list[DeviceResponse])
def list_devices(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("devices:read")),
):
    return pairing_service.list_devices(user, db)


@router.patch("/{device_id}", response_model=DeviceResponse)
def rename_device(
    device_id: int,
    body: DeviceRenameBody,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("devices:write")),
):
    return pairing_service.rename_device(device_id, body.device_name, user, db)


@router.delete("/{device_id}", status_code=204)
def revoke_device(
    device_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("devices:write")),
):
    pairing_service.revoke_device(device_id, user, db)


@router.delete("/{device_id}/permanent", status_code=204)
def delete_device(
    device_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("devices:write")),
):
    pairing_service.delete_device(device_id, user, db)
