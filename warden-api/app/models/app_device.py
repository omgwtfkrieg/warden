from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base


class AppDevice(Base):
    __tablename__ = "app_devices"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    device_name = Column(String(255), nullable=True)
    device_model = Column(String(255), nullable=True)
    hardware_id = Column(String(255), nullable=True, index=True)
    platform = Column(String(20), nullable=True)
    device_token = Column(String(255), unique=True, nullable=False, index=True)
    paired_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    revoked = Column(Boolean, nullable=False, default=False)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="devices")
