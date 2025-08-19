"""Competitor analysis API endpoints"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from src.app.core.database import get_db
from src.app.api.dependencies import get_current_user
from src.app.models import User, Product, Competitor, CompetitorAnalysis
from src.app.schemas.competitor import (
    CompetitorResponse,
    CompetitorAnalysisResponse,
    CompetitiveReportResponse,
    CompetitorDiscoveryRequest
)
from src.app.services.competitor_service import CompetitorService
from src.app.services.competitive_cache import competitive_cache
from src.app.tasks.competitor_tasks import analyze_competitors_task
import structlog

router = APIRouter()
logger = structlog.get_logger()


@router.post("/discover", response_model=List[CompetitorResponse])
async def discover_competitors(
    request: CompetitorDiscoveryRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Discover competitors for a product"""
    # Verify product ownership
    product = await db.execute(
        select(Product).where(
            and_(
                Product.id == request.product_id,
                Product.user_id == current_user.id
            )
        )
    )
    product = product.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Discover competitors
    service = CompetitorService(db)
    competitors = await service.discover_competitors(
        request.product_id,
        request.max_competitors
    )
    
    # Trigger background analysis
    background_tasks.add_task(
        analyze_competitors_task.delay,
        product_id=request.product_id
    )
    
    logger.info("competitors_discovered",
                user_id=current_user.id,
                product_id=request.product_id,
                count=len(competitors))
    
    return competitors


@router.get("/product/{product_id}", response_model=List[CompetitorResponse])
async def list_product_competitors(
    product_id: int,
    only_direct: bool = Query(False, description="Only show direct competitors"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all competitors for a product"""
    # Verify product ownership
    product = await db.execute(
        select(Product).where(
            and_(
                Product.id == product_id,
                Product.user_id == current_user.id
            )
        )
    )
    if not product.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get competitors
    query = select(Competitor).where(Competitor.main_product_id == product_id)
    
    if only_direct:
        query = query.where(Competitor.is_direct_competitor == 1)
    
    result = await db.execute(query)
    competitors = result.scalars().all()
    
    return competitors


@router.get("/{competitor_id}", response_model=CompetitorResponse)
async def get_competitor(
    competitor_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed competitor information"""
    # Get competitor with ownership check through main product
    result = await db.execute(
        select(Competitor)
        .join(Product, Competitor.main_product_id == Product.id)
        .where(
            and_(
                Competitor.id == competitor_id,
                Product.user_id == current_user.id
            )
        )
    )
    competitor = result.scalar_one_or_none()
    
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    return competitor


@router.post("/{competitor_id}/analyze", response_model=CompetitorAnalysisResponse)
async def analyze_competitor(
    competitor_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Perform detailed analysis of a specific competitor"""
    # Get competitor with ownership check
    result = await db.execute(
        select(Competitor)
        .join(Product, Competitor.main_product_id == Product.id)
        .where(
            and_(
                Competitor.id == competitor_id,
                Product.user_id == current_user.id
            )
        )
    )
    competitor = result.scalar_one_or_none()
    
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    # Perform analysis
    service = CompetitorService(db)
    analysis = await service.analyze_competitor(
        competitor.main_product_id,
        competitor_id
    )
    
    logger.info("competitor_analyzed",
                user_id=current_user.id,
                competitor_id=competitor_id)
    
    return analysis


@router.get("/{competitor_id}/analysis-history", response_model=List[CompetitorAnalysisResponse])
async def get_competitor_analysis_history(
    competitor_id: int,
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get historical analyses for a competitor"""
    # Verify ownership through main product
    competitor = await db.execute(
        select(Competitor)
        .join(Product, Competitor.main_product_id == Product.id)
        .where(
            and_(
                Competitor.id == competitor_id,
                Product.user_id == current_user.id
            )
        )
    )
    if not competitor.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    # Get analysis history
    result = await db.execute(
        select(CompetitorAnalysis)
        .where(CompetitorAnalysis.competitor_id == competitor_id)
        .order_by(CompetitorAnalysis.analyzed_at.desc())
        .limit(limit)
    )
    
    return result.scalars().all()


@router.post("/product/{product_id}/analyze-all", response_model=CompetitiveReportResponse)
async def analyze_all_competitors(
    product_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Analyze all competitors for a product and generate report"""
    # Verify product ownership
    product = await db.execute(
        select(Product).where(
            and_(
                Product.id == product_id,
                Product.user_id == current_user.id
            )
        )
    )
    if not product.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Generate comprehensive report
    service = CompetitorService(db)
    report = await service.batch_analyze_competitors(product_id)
    
    logger.info("competitive_report_generated",
                user_id=current_user.id,
                product_id=product_id,
                competitors_analyzed=report.get("total_competitors", 0))
    
    return report


@router.delete("/{competitor_id}")
async def remove_competitor(
    competitor_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove a competitor from tracking"""
    # Get competitor with ownership check
    result = await db.execute(
        select(Competitor)
        .join(Product, Competitor.main_product_id == Product.id)
        .where(
            and_(
                Competitor.id == competitor_id,
                Product.user_id == current_user.id
            )
        )
    )
    competitor = result.scalar_one_or_none()
    
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    await db.delete(competitor)
    await db.commit()
    
    return {"message": "Competitor removed successfully"}


@router.get("/insights/market-overview", response_model=dict)
async def get_market_overview(
    category: Optional[str] = Query(None, description="Filter by category"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get market overview across all tracked products and competitors"""
    # Get user's products
    query = select(Product).where(Product.user_id == current_user.id)
    if category:
        query = query.where(Product.category == category)
    
    result = await db.execute(query)
    products = result.scalars().all()
    
    if not products:
        return {"message": "No products tracked yet"}
    
    # Get all competitors for user's products
    product_ids = [p.id for p in products]
    competitors = await db.execute(
        select(Competitor).where(Competitor.main_product_id.in_(product_ids))
    )
    competitors = competitors.scalars().all()
    
    # Calculate market statistics
    total_products = len(products)
    total_competitors = len(competitors)
    
    # Average prices
    avg_product_price = sum(p.current_price or 0 for p in products) / total_products if total_products > 0 else 0
    avg_competitor_price = sum(c.current_price or 0 for c in competitors) / total_competitors if total_competitors > 0 else 0
    
    # Find market leaders (best BSR)
    products_with_bsr = [p for p in products if p.current_bsr]
    market_leader = min(products_with_bsr, key=lambda p: p.current_bsr) if products_with_bsr else None
    
    # Direct vs indirect competitors
    direct_competitors = [c for c in competitors if c.is_direct_competitor == 1]
    indirect_competitors = [c for c in competitors if c.is_direct_competitor == 2]
    
    overview = {
        "total_products_tracked": total_products,
        "total_competitors_tracked": total_competitors,
        "market_statistics": {
            "average_product_price": round(avg_product_price, 2),
            "average_competitor_price": round(avg_competitor_price, 2),
            "price_competitiveness": "competitive" if abs(avg_product_price - avg_competitor_price) < 5 else 
                                    "premium" if avg_product_price > avg_competitor_price else "value",
            "market_leader": {
                "asin": market_leader.asin,
                "title": market_leader.title,
                "bsr": market_leader.current_bsr
            } if market_leader else None
        },
        "competitor_breakdown": {
            "direct_competitors": len(direct_competitors),
            "indirect_competitors": len(indirect_competitors),
            "average_similarity_score": sum(c.similarity_score or 0 for c in competitors) / total_competitors if total_competitors > 0 else 0
        },
        "categories_tracked": list(set(p.category for p in products if p.category))
    }
    
    return overview


@router.post("/product/{product_id}/intelligence-report", response_model=dict)
async def generate_intelligence_report(
    product_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate comprehensive AI-powered competitive intelligence report"""
    # Verify product ownership
    product = await db.execute(
        select(Product).where(
            and_(
                Product.id == product_id,
                Product.user_id == current_user.id
            )
        )
    )
    if not product.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Generate comprehensive intelligence report
    service = CompetitorService(db)
    
    try:
        report = await service.generate_comprehensive_intelligence_report(product_id)
        
        logger.info("intelligence_report_generated",
                    user_id=current_user.id,
                    product_id=product_id,
                    competitors_analyzed=report.get("total_competitors", 0))
        
        return report
        
    except Exception as e:
        logger.error("intelligence_report_error", 
                    error=str(e), product_id=product_id)
        raise HTTPException(
            status_code=500, 
            detail="Failed to generate intelligence report"
        )


@router.get("/product/{product_id}/competitive-summary", response_model=dict)
async def get_competitive_summary(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get quick competitive summary for a product"""
    # Verify product ownership
    product = await db.execute(
        select(Product).where(
            and_(
                Product.id == product_id,
                Product.user_id == current_user.id
            )
        )
    )
    product_obj = product.scalar_one_or_none()
    if not product_obj:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get competitors
    competitors = await db.execute(
        select(Competitor).where(Competitor.main_product_id == product_id)
    )
    competitors = competitors.scalars().all()
    
    if not competitors:
        return {
            "message": "No competitors found. Run competitor discovery first.",
            "has_competitors": False
        }
    
    # Calculate summary metrics
    total_competitors = len(competitors)
    direct_competitors = len([c for c in competitors if c.is_direct_competitor == 1])
    
    # Price analysis
    competitor_prices = [c.current_price for c in competitors if c.current_price]
    avg_competitor_price = sum(competitor_prices) / len(competitor_prices) if competitor_prices else 0
    
    price_position = "unknown"
    if product_obj.current_price and avg_competitor_price:
        if product_obj.current_price < avg_competitor_price * 0.9:
            price_position = "value_leader"
        elif product_obj.current_price > avg_competitor_price * 1.1:
            price_position = "premium"
        else:
            price_position = "competitive"
    
    # Performance analysis
    performance_advantages = 0
    if product_obj.current_rating:
        better_rated_count = len([c for c in competitors 
                                if c.current_rating and c.current_rating < product_obj.current_rating])
        performance_advantages += 1 if better_rated_count > len(competitors) / 2 else 0
    
    if product_obj.current_bsr:
        better_bsr_count = len([c for c in competitors 
                              if c.current_bsr and c.current_bsr > product_obj.current_bsr])
        performance_advantages += 1 if better_bsr_count > len(competitors) / 2 else 0
    
    # Competitive strength
    if performance_advantages >= 2:
        competitive_strength = "strong"
    elif performance_advantages == 1:
        competitive_strength = "moderate"
    else:
        competitive_strength = "weak"
    
    summary = {
        "product_title": product_obj.title,
        "has_competitors": True,
        "total_competitors": total_competitors,
        "direct_competitors": direct_competitors,
        "indirect_competitors": total_competitors - direct_competitors,
        "price_position": price_position,
        "average_competitor_price": round(avg_competitor_price, 2) if avg_competitor_price else None,
        "your_price": product_obj.current_price,
        "competitive_strength": competitive_strength,
        "performance_advantages": performance_advantages,
        "recommendations": [
            "Run full intelligence report for detailed insights",
            "Monitor competitor pricing regularly",
            "Consider competitor discovery to find more competitors"
        ]
    }
    
    return summary


@router.get("/cache/stats", response_model=dict)
async def get_cache_stats(
    current_user: User = Depends(get_current_user)
):
    """Get competitive data cache statistics"""
    stats = await competitive_cache.get_cache_stats()
    return {
        "cache_statistics": stats,
        "cache_service": "competitive_cache",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.delete("/cache/product/{product_id}")
async def invalidate_product_cache(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Invalidate all cache for a specific product"""
    # Verify product ownership
    product = await db.execute(
        select(Product).where(
            and_(
                Product.id == product_id,
                Product.user_id == current_user.id
            )
        )
    )
    if not product.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Product not found")
    
    success = await competitive_cache.invalidate_product_cache(product_id)
    
    if success:
        return {"message": f"Cache invalidated for product {product_id}"}
    else:
        raise HTTPException(status_code=500, detail="Failed to invalidate cache")