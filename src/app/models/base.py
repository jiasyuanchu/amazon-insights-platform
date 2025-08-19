from datetime import datetime
from typing import Any
from sqlalchemy import Column, DateTime, Integer, func
from sqlalchemy.ext.declarative import declared_attr
from src.app.core.database import Base


class TimestampMixin:
    @declared_attr
    def created_at(cls) -> Any:
        return Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    @declared_attr
    def updated_at(cls) -> Any:
        return Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False
        )


class BaseModel(Base, TimestampMixin):
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    def dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}