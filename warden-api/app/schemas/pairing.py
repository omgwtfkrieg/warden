from datetime import datetime
from pydantic import BaseModel


class PairRequestBody(BaseModel):
    hardware_id: str | None = None
    device_model: str | None = None
    platform: str | None = None


class PairRequestResponse(BaseModel):
    code: str
    qr_payload: str
    expires_at: datetime


class PairStatusResponse(BaseModel):
    status: str  # pending | approved | expired
    device_token: str | None = None
    cameras: list[dict] | None = None


class PairActivateRequest(BaseModel):
    code: str
    device_name: str | None = None


class PairActivateResponse(BaseModel):
    device_token: str
    device_name: str | None
