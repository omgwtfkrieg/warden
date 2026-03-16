from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_device
from app.models import AppDevice
from app.schemas.command import PendingCommandsResponse
from app.services import command_service

router = APIRouter(prefix="/commands", tags=["commands"])


@router.get("/pending", response_model=PendingCommandsResponse)
def get_pending(
    device: AppDevice = Depends(get_device),
    db: Session = Depends(get_db),
):
    """Flutter app polls this with its device token to receive pending commands."""
    return PendingCommandsResponse(commands=command_service.get_pending(device, db))


@router.post("/{command_id}/ack", status_code=204)
def ack_command(
    command_id: int,
    device: AppDevice = Depends(get_device),
    db: Session = Depends(get_db),
):
    """Flutter app calls this after executing a command."""
    command_service.ack_command(command_id, device, db)
