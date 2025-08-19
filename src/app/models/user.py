from sqlalchemy import Boolean, Column, String, Text, DateTime
from sqlalchemy.orm import relationship
from src.app.models.base import BaseModel


class User(BaseModel):
    __tablename__ = "users"

    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Brand/Company information
    company_name = Column(String(255), nullable=True)
    brand_name = Column(String(255), nullable=True)
    
    # API Keys (encrypted in production)
    firecrawl_api_key = Column(Text, nullable=True)
    openai_api_key = Column(Text, nullable=True)
    
    # Relationships
    products = relationship("Product", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"