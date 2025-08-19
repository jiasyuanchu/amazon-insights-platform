"""Product-related Pydantic schemas"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator


class ProductBase(BaseModel):
    asin: str = Field(..., min_length=10, max_length=10)
    title: str
    brand: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    product_url: str
    image_url: Optional[str] = None
    is_active: bool = True


class ProductCreate(BaseModel):
    asin: str = Field(..., min_length=10, max_length=10)
    title: Optional[str] = None
    category: Optional[str] = None
    
    @validator('asin')
    def validate_asin(cls, v):
        return v.upper()


class ProductUpdate(BaseModel):
    is_active: Optional[bool] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None


class ProductResponse(ProductBase):
    id: int
    user_id: int
    last_scraped_at: Optional[datetime] = None
    current_price: Optional[float] = None
    current_bsr: Optional[int] = None
    current_rating: Optional[float] = None
    current_review_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True


class ProductMetricsResponse(BaseModel):
    id: int
    product_id: int
    scraped_at: datetime
    price: Optional[float] = None
    bsr: Optional[int] = None
    bsr_category: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    in_stock: bool
    seller_count: Optional[int] = None
    
    class Config:
        orm_mode = True


class ProductInsightResponse(BaseModel):
    id: int
    product_id: int
    insight_date: datetime
    
    # Performance Metrics
    bsr_rank: Optional[int] = None
    bsr_category: Optional[str] = None
    bsr_change_percent: Optional[float] = None
    
    # Price Insights
    current_price: Optional[float] = None
    price_change_percent: Optional[float] = None
    competitor_avg_price: Optional[float] = None
    price_position: Optional[str] = None
    
    # Review Insights
    total_reviews: Optional[int] = None
    new_reviews_today: Optional[int] = None
    avg_rating: Optional[float] = None
    rating_trend: Optional[str] = None
    
    # Competitive Insights
    market_share_estimate: Optional[float] = None
    competitive_intensity: Optional[str] = None
    total_competitors: Optional[int] = None
    
    # AI-Generated Insights
    ai_summary: Optional[str] = None
    ai_recommendations: Optional[List[Dict[str, Any]]] = None
    opportunity_score: Optional[float] = None
    risk_indicators: Optional[List[Dict[str, Any]]] = None
    
    created_at: datetime
    
    class Config:
        orm_mode = True


class PriceHistoryResponse(BaseModel):
    id: int
    product_id: int
    tracked_at: datetime
    list_price: Optional[float] = None
    sale_price: Optional[float] = None
    discount_percent: Optional[float] = None
    in_stock: bool
    stock_level: Optional[str] = None
    seller_name: Optional[str] = None
    fulfillment: Optional[str] = None
    has_coupon: bool
    coupon_discount: Optional[float] = None
    
    class Config:
        orm_mode = True


class BatchProductImport(BaseModel):
    asins: List[str] = Field(..., min_items=1, max_items=50)
    default_category: Optional[str] = None
    
    @validator('asins')
    def validate_asins(cls, v):
        # Remove duplicates and validate format
        unique_asins = list(set(asin.upper() for asin in v))
        for asin in unique_asins:
            if len(asin) != 10:
                raise ValueError(f"Invalid ASIN format: {asin}")
        return unique_asins


class AlertConfigurationCreate(BaseModel):
    product_id: int
    alert_name: str
    is_active: bool = True
    
    # Price Alerts
    price_drop_threshold: Optional[float] = None
    price_increase_threshold: Optional[float] = None
    target_price: Optional[float] = None
    
    # BSR Alerts
    bsr_improvement_threshold: Optional[int] = None
    bsr_decline_threshold: Optional[int] = None
    target_bsr: Optional[int] = None
    
    # Review Alerts
    negative_review_threshold: Optional[int] = None
    rating_drop_threshold: Optional[float] = None
    
    # Competition Alerts
    new_competitor_alert: bool = False
    competitor_price_undercut: bool = True
    
    # Notification Settings
    email_enabled: bool = True
    push_enabled: bool = False
    webhook_url: Optional[str] = None


class AlertConfigurationResponse(AlertConfigurationCreate):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True


class AlertHistoryResponse(BaseModel):
    id: int
    configuration_id: int
    product_id: int
    alert_type: str
    alert_message: str
    severity: Optional[str] = None
    triggered_at: datetime
    trigger_value: Optional[float] = None
    threshold_value: Optional[float] = None
    acknowledged: bool
    acknowledged_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True


class MarketTrendResponse(BaseModel):
    id: int
    category: str
    trend_date: datetime
    total_products: Optional[int] = None
    avg_price: Optional[float] = None
    avg_rating: Optional[float] = None
    avg_reviews: Optional[int] = None
    price_trend: Optional[str] = None
    demand_trend: Optional[str] = None
    competition_level: Optional[str] = None
    market_summary: Optional[str] = None
    opportunities: Optional[List[Dict[str, Any]]] = None
    threats: Optional[List[Dict[str, Any]]] = None
    
    class Config:
        orm_mode = True