from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl


class ProductBase(BaseModel):
    asin: str = Field(..., min_length=10, max_length=20)
    title: str
    brand: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    product_url: str
    image_url: Optional[str] = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    is_active: Optional[bool] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None


class ProductResponse(ProductBase):
    id: int
    user_id: int
    is_active: bool
    last_scraped_at: Optional[datetime] = None
    current_price: Optional[float] = None
    current_bsr: Optional[int] = None
    current_rating: Optional[float] = None
    current_review_count: Optional[int] = None
    current_buy_box_price: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProductMetricsBase(BaseModel):
    price: Optional[float] = None
    buy_box_price: Optional[float] = None
    lowest_price: Optional[float] = None
    highest_price: Optional[float] = None
    bsr: Optional[int] = None
    bsr_category: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    in_stock: bool = True
    stock_level: Optional[str] = None
    seller_count: Optional[int] = None
    buy_box_seller: Optional[str] = None


class ProductMetricsResponse(ProductMetricsBase):
    id: int
    product_id: int
    scraped_at: datetime
    price_change_percent: Optional[float] = None
    bsr_change_percent: Optional[float] = None
    new_reviews_count: Optional[int] = None
    
    class Config:
        from_attributes = True