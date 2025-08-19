from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, 
    Integer, String, Text, JSON, Index
)
from sqlalchemy.orm import relationship
from src.app.models.base import BaseModel


class Product(BaseModel):
    __tablename__ = "products"
    __table_args__ = (
        Index("idx_product_asin", "asin"),
        Index("idx_product_user", "user_id"),
        Index("idx_product_active", "is_active"),
    )

    # Basic Information
    asin = Column(String(20), unique=True, nullable=False)
    title = Column(Text, nullable=False)
    brand = Column(String(255), nullable=True)
    category = Column(String(255), nullable=True)
    subcategory = Column(String(255), nullable=True)
    
    # URLs
    product_url = Column(Text, nullable=False)
    image_url = Column(Text, nullable=True)
    
    # Tracking Status
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_scraped_at = Column(DateTime(timezone=True), nullable=True)
    
    # Current Metrics (Latest snapshot)
    current_price = Column(Float, nullable=True)
    current_bsr = Column(Integer, nullable=True)
    current_rating = Column(Float, nullable=True)
    current_review_count = Column(Integer, nullable=True)
    current_buy_box_price = Column(Float, nullable=True)
    
    # Additional Data
    features = Column(JSON, nullable=True)  # Product features/bullet points
    variations = Column(JSON, nullable=True)  # Color, size variations
    
    # Relationships
    user = relationship("User", back_populates="products")
    metrics = relationship("ProductMetrics", back_populates="product", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Product(id={self.id}, asin={self.asin}, title={self.title[:30]}...)>"


class ProductMetrics(BaseModel):
    __tablename__ = "product_metrics"
    __table_args__ = (
        Index("idx_metrics_product", "product_id"),
        Index("idx_metrics_timestamp", "scraped_at"),
        Index("idx_metrics_product_time", "product_id", "scraped_at"),
    )

    # Foreign Key
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    # Timestamp
    scraped_at = Column(DateTime(timezone=True), nullable=False)
    
    # Price Metrics
    price = Column(Float, nullable=True)
    buy_box_price = Column(Float, nullable=True)
    lowest_price = Column(Float, nullable=True)
    highest_price = Column(Float, nullable=True)
    price_change_percent = Column(Float, nullable=True)  # vs previous scrape
    
    # Performance Metrics
    bsr = Column(Integer, nullable=True)
    bsr_category = Column(String(255), nullable=True)
    bsr_change_percent = Column(Float, nullable=True)  # vs previous scrape
    
    # Review Metrics
    rating = Column(Float, nullable=True)
    review_count = Column(Integer, nullable=True)
    new_reviews_count = Column(Integer, nullable=True)  # Since last scrape
    
    # Inventory
    in_stock = Column(Boolean, default=True, nullable=False)
    stock_level = Column(String(100), nullable=True)  # "In Stock", "Only 5 left", etc.
    
    # Competition
    seller_count = Column(Integer, nullable=True)
    buy_box_seller = Column(String(255), nullable=True)
    
    # Additional Metrics
    questions_count = Column(Integer, nullable=True)
    images_count = Column(Integer, nullable=True)
    
    # Raw Data (for debugging/analysis)
    raw_data = Column(JSON, nullable=True)
    
    # Relationships
    product = relationship("Product", back_populates="metrics")
    
    def __repr__(self) -> str:
        return f"<ProductMetrics(id={self.id}, product_id={self.product_id}, scraped_at={self.scraped_at})>"