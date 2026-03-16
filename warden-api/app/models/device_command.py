from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from app.models.base import Base


class DeviceCommand(Base):
    __tablename__ = "device_commands"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("app_devices.id", ondelete="CASCADE"), nullable=False)
    command = Column(String(32), nullable=False)  # reconnect | reload | refresh
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    acked_at = Column(DateTime(timezone=True), nullable=True)
