from sqlalchemy import (
    Column, DateTime, Float, ForeignKey, 
    Integer, String, Text, JSON, Index
)
from sqlalchemy.orm import relationship
from src.app.models.base import BaseModel


class Competitor(BaseModel):
    __tablename__ = "competitors"
    __table_args__ = (
        Index("idx_competitor_product", "main_product_id"),
        Index("idx_competitor_asin", "competitor_asin"),
    )

    # Main Product Reference
    main_product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    # Competitor Product Information
    competitor_asin = Column(String(20), nullable=False)
    title = Column(Text, nullable=False)
    brand = Column(String(255), nullable=True)
    product_url = Column(Text, nullable=False)
    image_url = Column(Text, nullable=True)
    
    # Current Metrics
    current_price = Column(Float, nullable=True)
    current_bsr = Column(Integer, nullable=True)
    current_rating = Column(Float, nullable=True)
    current_review_count = Column(Integer, nullable=True)
    
    # Competitive Position
    similarity_score = Column(Float, nullable=True)  # 0-1 score
    is_direct_competitor = Column(Integer, default=1, nullable=False)  # 1=direct, 2=indirect
    
    # Relationships
    main_product = relationship("Product", back_populates="competitors")
    analyses = relationship("CompetitorAnalysis", back_populates="competitor", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Competitor(id={self.id}, main={self.main_product_id}, asin={self.competitor_asin})>"


class CompetitorAnalysis(BaseModel):
    __tablename__ = "competitor_analyses"
    __table_args__ = (
        Index("idx_analysis_competitor", "competitor_id"),
        Index("idx_analysis_timestamp", "analyzed_at"),
    )

    # Foreign Key
    competitor_id = Column(Integer, ForeignKey("competitors.id"), nullable=False)
    
    # Timestamp
    analyzed_at = Column(DateTime(timezone=True), nullable=False)
    
    # Comparative Metrics
    price_difference = Column(Float, nullable=True)  # Main - Competitor
    price_difference_percent = Column(Float, nullable=True)
    bsr_difference = Column(Integer, nullable=True)
    rating_difference = Column(Float, nullable=True)
    review_count_difference = Column(Integer, nullable=True)
    
    # Competitive Advantages
    main_advantages = Column(JSON, nullable=True)  # List of advantages
    competitor_advantages = Column(JSON, nullable=True)
    
    # AI Analysis
    ai_insights = Column(JSON, nullable=True)
    positioning_analysis = Column(Text, nullable=True)
    recommended_actions = Column(JSON, nullable=True)
    
    # Market Share Estimation
    estimated_market_share = Column(Float, nullable=True)  # Percentage
    
    # Feature Comparison
    feature_comparison = Column(JSON, nullable=True)
    unique_features_main = Column(JSON, nullable=True)
    unique_features_competitor = Column(JSON, nullable=True)
    
    # Relationships
    competitor = relationship("Competitor", back_populates="analyses")
    
    def __repr__(self) -> str:
        return f"<CompetitorAnalysis(id={self.id}, competitor_id={self.competitor_id}, analyzed_at={self.analyzed_at})>"