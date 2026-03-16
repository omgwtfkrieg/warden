from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class CommandCreate(BaseModel):
    command: Literal['reconnect', 'reload', 'refresh']


class CommandResponse(BaseModel):
    id: int
    command: str
    created_at: datetime

    model_config = {'from_attributes': True}


class PendingCommandsResponse(BaseModel):
    commands: list[CommandResponse]
