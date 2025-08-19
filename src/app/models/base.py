from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, func
from src.app.core.database import Base


class BaseModel(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    def dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}