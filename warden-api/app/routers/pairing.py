from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_permission
from app.models import User
from app.schemas.pairing import (
    PairRequestBody,
    PairRequestResponse,
    PairStatusResponse,
    PairActivateRequest,
    PairActivateResponse,
)
from app.services import pairing_service

router = APIRouter(prefix="/pair", tags=["pairing"])


@router.post("/request", response_model=PairRequestResponse)
def request_code(payload: PairRequestBody = PairRequestBody(), db: Session = Depends(get_db)):
    """Flutter app calls this to get a pairing code. No auth required."""
    record = pairing_service.request_code(payload.hardware_id, payload.device_model, payload.platform, db)
    return PairRequestResponse(
        code=record.code,
        qr_payload=record.code,
        expires_at=record.expires_at,
    )


@router.get("/status", response_model=PairStatusResponse)
def poll_status(code: str, db: Session = Depends(get_db)):
    """Flutter app polls this until status is approved or expired. No auth required."""
    return pairing_service.get_status(code, db)


@router.post("/activate", response_model=PairActivateResponse)
def activate(
    payload: PairActivateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("devices:write")),
):
    """Admin panel calls this to approve a pairing code. JWT auth required."""
    device = pairing_service.activate(payload.code, payload.device_name, user, db)
    return PairActivateResponse(device_token=device.device_token, device_name=device.device_name)
