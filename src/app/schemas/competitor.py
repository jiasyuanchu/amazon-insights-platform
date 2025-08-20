"""Competitor-related Pydantic schemas"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class CompetitorBase(BaseModel):
    competitor_asin: str = Field(..., min_length=10, max_length=10)
    title: str
    brand: Optional[str] = None
    product_url: str
    image_url: Optional[str] = None
    similarity_score: Optional[float] = Field(None, ge=0, le=1)
    is_direct_competitor: int = Field(1, ge=1, le=2)


class CompetitorCreate(CompetitorBase):
    """Schema for creating a new competitor"""
    main_product_id: int


class CompetitorResponse(CompetitorBase):
    id: int
    main_product_id: int
    current_price: Optional[float] = None
    current_bsr: Optional[int] = None
    current_rating: Optional[float] = None
    current_review_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True


class CompetitorDiscoveryRequest(BaseModel):
    product_id: int
    max_competitors: int = Field(5, ge=1, le=20)


class CompetitorAnalysisResponse(BaseModel):
    id: Optional[int] = None
    competitor_id: Optional[int] = None
    analyzed_at: Optional[datetime] = None
    
    # Comparative Metrics
    price_difference: Optional[float] = None
    price_difference_percent: Optional[float] = None
    bsr_difference: Optional[int] = None
    rating_difference: Optional[float] = None
    review_count_difference: Optional[int] = None
    
    # Analysis Results
    price_comparison: Optional[Dict[str, Any]] = None
    performance_comparison: Optional[Dict[str, Any]] = None
    market_position: Optional[str] = None
    competitive_advantages: Optional[Dict[str, List[str]]] = None
    recommendations: Optional[List[Dict[str, Any]]] = None
    
    # AI Insights
    ai_insights: Optional[Dict[str, Any]] = None
    positioning_analysis: Optional[str] = None
    estimated_market_share: Optional[float] = None
    
    # Feature Comparison
    feature_comparison: Optional[Dict[str, Any]] = None
    unique_features_main: Optional[List[str]] = None
    unique_features_competitor: Optional[List[str]] = None
    
    class Config:
        orm_mode = True


class CompetitiveReportResponse(BaseModel):
    product_id: int
    analyzed_at: str
    total_competitors: int
    analyses: List[Dict[str, Any]]
    market_summary: Dict[str, Any]
    strategic_recommendations: List[Dict[str, Any]]
    
    class Config:
        orm_mode = True


class MarketOverviewResponse(BaseModel):
    total_products_tracked: int
    total_competitors_tracked: int
    market_statistics: Dict[str, Any]
    competitor_breakdown: Dict[str, Any]
    categories_tracked: List[str]
    
    class Config:
        orm_mode = True


class CompetitorUpdate(BaseModel):
    similarity_score: Optional[float] = Field(None, ge=0, le=1)
    is_direct_competitor: Optional[int] = Field(None, ge=1, le=2)


class PriceComparisonResponse(BaseModel):
    main_product: Dict[str, Any]
    competitors: List[Dict[str, Any]]
    price_analysis: Dict[str, Any]
    recommendations: List[str]


class PerformanceComparisonResponse(BaseModel):
    main_product_metrics: Dict[str, Any]
    competitor_metrics: List[Dict[str, Any]]
    performance_gaps: Dict[str, Any]
    improvement_areas: List[str]


class CompetitiveTrendResponse(BaseModel):
    period: str
    trend_data: List[Dict[str, Any]]
    insights: List[str]
    predictions: Optional[List[Dict[str, Any]]] = None