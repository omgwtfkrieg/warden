from sqlalchemy import Boolean, Column, Integer, JSON, String, DateTime
from sqlalchemy.sql import func
from app.models.base import Base


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    ip_address = Column(String(45), nullable=True)
    rtsp_url = Column(String(512), nullable=False)
    use_ffmpeg = Column(Boolean, nullable=False, default=False)
    use_sub_stream = Column(Boolean, nullable=False, default=True)
    always_on = Column(Boolean, nullable=False, default=False)
    stream_path = Column(String(255), nullable=True)
    sub_rtsp_url = Column(String(512), nullable=True)
    stream_metadata = Column(JSON, nullable=True)
    display_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
