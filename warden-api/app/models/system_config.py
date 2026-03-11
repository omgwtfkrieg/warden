from sqlalchemy import Column, Integer, String
from app.models.base import Base


class SystemConfig(Base):
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(String(1024), nullable=False)
