"""Product insights and tracking models"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, 
    ForeignKey, JSON, Text, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.app.models.base import BaseModel


class ProductInsight(BaseModel):
    """Daily product performance insights"""
    __tablename__ = "product_insights"
    
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    insight_date = Column(DateTime(timezone=True), nullable=False)
    
    # Performance Metrics
    bsr_rank = Column(Integer)
    bsr_category = Column(String(255))
    bsr_change_percent = Column(Float)  # Daily BSR change %
    
    # Price Insights
    current_price = Column(Float)
    price_change_amount = Column(Float)
    price_change_percent = Column(Float)
    competitor_avg_price = Column(Float)
    price_position = Column(String(50))  # "below_market", "at_market", "above_market"
    
    # Review Insights  
    total_reviews = Column(Integer)
    new_reviews_today = Column(Integer)
    avg_rating = Column(Float)
    rating_trend = Column(String(20))  # "improving", "stable", "declining"
    
    # Competitive Insights
    market_share_estimate = Column(Float)
    competitive_intensity = Column(String(20))  # "low", "medium", "high", "very_high"
    total_competitors = Column(Integer)
    
    # AI-Generated Insights
    ai_summary = Column(Text)
    ai_recommendations = Column(JSON)
    opportunity_score = Column(Float)  # 0-100 score
    risk_indicators = Column(JSON)
    
    # Relationships
    product = relationship("Product", back_populates="insights")
    
    __table_args__ = (
        UniqueConstraint("product_id", "insight_date"),
        Index("idx_product_insights_date", "product_id", "insight_date"),
        Index("idx_insights_opportunity", "opportunity_score"),
    )


class PriceHistory(BaseModel):
    """Detailed price tracking history"""
    __tablename__ = "price_history"
    
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    tracked_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # Price Data
    list_price = Column(Float)
    sale_price = Column(Float)
    discount_percent = Column(Float)
    currency = Column(String(3), default="USD")
    
    # Availability
    in_stock = Column(Boolean, default=True)
    stock_level = Column(String(100))  # "In Stock", "Only 5 left", etc.
    seller_name = Column(String(255))
    fulfillment = Column(String(50))  # "FBA", "FBM", "Amazon"
    
    # Promotions
    has_coupon = Column(Boolean, default=False)
    coupon_discount = Column(Float)
    promotion_text = Column(Text)
    
    # Relationships
    product = relationship("Product", back_populates="price_history")
    
    __table_args__ = (
        Index("idx_price_history_product_time", "product_id", "tracked_at"),
    )


class AlertConfiguration(BaseModel):
    """User-defined alert rules for products"""
    __tablename__ = "alert_configurations"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    # Alert Settings
    alert_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Price Alerts
    price_drop_threshold = Column(Float)  # Alert if price drops by X%
    price_increase_threshold = Column(Float)  # Alert if price increases by X%
    target_price = Column(Float)  # Alert when price reaches this value
    
    # BSR Alerts
    bsr_improvement_threshold = Column(Integer)  # Alert if BSR improves by X ranks
    bsr_decline_threshold = Column(Integer)  # Alert if BSR declines by X ranks
    target_bsr = Column(Integer)  # Alert when BSR reaches this rank
    
    # Review Alerts
    negative_review_threshold = Column(Integer)  # Alert on X negative reviews
    rating_drop_threshold = Column(Float)  # Alert if rating drops by X points
    
    # Competition Alerts
    new_competitor_alert = Column(Boolean, default=False)
    competitor_price_undercut = Column(Boolean, default=True)
    
    # Notification Settings
    email_enabled = Column(Boolean, default=True)
    push_enabled = Column(Boolean, default=False)
    webhook_url = Column(String(500))
    
    # Relationships
    user = relationship("User", back_populates="alert_configurations")
    product = relationship("Product", back_populates="alert_configurations")
    alerts_triggered = relationship("AlertHistory", back_populates="configuration")
    
    __table_args__ = (
        UniqueConstraint("user_id", "product_id", "alert_name"),
        Index("idx_alert_config_active", "is_active", "user_id"),
    )


class AlertHistory(BaseModel):
    """History of triggered alerts"""
    __tablename__ = "alert_history"
    
    configuration_id = Column(Integer, ForeignKey("alert_configurations.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    # Alert Details
    alert_type = Column(String(50), nullable=False)  # "price_drop", "bsr_change", etc.
    alert_message = Column(Text, nullable=False)
    severity = Column(String(20))  # "info", "warning", "critical"
    
    # Trigger Data
    triggered_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    trigger_value = Column(Float)  # The value that triggered the alert
    threshold_value = Column(Float)  # The threshold that was exceeded
    
    # Notification Status
    email_sent = Column(Boolean, default=False)
    push_sent = Column(Boolean, default=False)
    webhook_sent = Column(Boolean, default=False)
    acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime(timezone=True))
    
    # Relationships
    configuration = relationship("AlertConfiguration", back_populates="alerts_triggered")
    product = relationship("Product", back_populates="alert_history")
    
    __table_args__ = (
        Index("idx_alert_history_time", "triggered_at"),
        Index("idx_alert_history_product", "product_id", "triggered_at"),
    )


class MarketTrend(BaseModel):
    """Market and category trend analysis"""
    __tablename__ = "market_trends"
    
    category = Column(String(255), nullable=False)
    trend_date = Column(DateTime(timezone=True), nullable=False)
    
    # Market Metrics
    total_products = Column(Integer)
    avg_price = Column(Float)
    avg_rating = Column(Float)
    avg_reviews = Column(Integer)
    
    # Trend Indicators
    price_trend = Column(String(20))  # "increasing", "stable", "decreasing"
    demand_trend = Column(String(20))
    competition_level = Column(String(20))
    
    # Top Performers
    top_products = Column(JSON)  # List of top ASINs
    rising_products = Column(JSON)  # Products gaining traction
    declining_products = Column(JSON)  # Products losing ground
    
    # AI Analysis
    market_summary = Column(Text)
    opportunities = Column(JSON)
    threats = Column(JSON)
    
    __table_args__ = (
        UniqueConstraint("category", "trend_date"),
        Index("idx_market_trends", "category", "trend_date"),
    )