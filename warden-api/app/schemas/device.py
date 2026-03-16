from datetime import datetime
from pydantic import BaseModel, ConfigDict


class DeviceRenameBody(BaseModel):
    device_name: str


class DeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_name: str | None
    device_model: str | None
    hardware_id: str | None
    platform: str | None
    paired_at: datetime
    last_seen_at: datetime | None
    revoked: bool
