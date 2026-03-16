from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base


class PairingCode(Base):
    __tablename__ = "pairing_codes"

    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    hardware_id = Column(String(255), nullable=True)
    device_model = Column(String(255), nullable=True)
    platform = Column(String(20), nullable=True)

    user = relationship("User")
