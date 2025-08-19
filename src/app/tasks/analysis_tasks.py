from datetime import datetime
from typing import Dict, Any, List
from celery import Task
from sqlalchemy import select, and_
from src.app.tasks.celery_app import celery_app
from src.app.core.database import AsyncSessionLocal
from src.app.models.product import Product, ProductMetrics
from src.app.models.competitor import Competitor, CompetitorAnalysis
import structlog
import asyncio

logger = structlog.get_logger()


class AsyncTask(Task):
    def run(self, *args, **kwargs):
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self._run(*args, **kwargs))
    
    async def _run(self, *args, **kwargs):
        raise NotImplementedError


@celery_app.task(base=AsyncTask, name="run_competitive_analysis")
class RunCompetitiveAnalysisTask(AsyncTask):
    async def _run(self):
        logger.info("Starting daily competitive analysis")
        
        async with AsyncSessionLocal() as db:
            # Get all active products with competitors
            result = await db.execute(
                select(Product).where(Product.is_active == True)
            )
            products = result.scalars().all()
            
            analyzed_count = 0
            
            for product in products:
                # Get competitors for this product
                competitors_result = await db.execute(
                    select(Competitor).where(Competitor.main_product_id == product.id)
                )
                competitors = competitors_result.scalars().all()
                
                if competitors:
                    # Trigger analysis for each competitor
                    for competitor in competitors:
                        analyze_competitor.delay(competitor.id)
                        analyzed_count += 1
            
            logger.info(
                "Competitive analysis tasks queued",
                analyzed_count=analyzed_count
            )
            
            return {
                "products_checked": len(products),
                "analyses_queued": analyzed_count,
                "timestamp": datetime.utcnow().isoformat()
            }


@celery_app.task(base=AsyncTask, name="analyze_competitor")
class AnalyzeCompetitorTask(AsyncTask):
    async def _run(self, competitor_id: int):
        logger.info("Analyzing competitor", competitor_id=competitor_id)
        
        async with AsyncSessionLocal() as db:
            # Get competitor and main product
            competitor_result = await db.execute(
                select(Competitor).where(Competitor.id == competitor_id)
            )
            competitor = competitor_result.scalar_one_or_none()
            
            if not competitor:
                logger.error("Competitor not found", competitor_id=competitor_id)
                return {"status": "error", "message": "Competitor not found"}
            
            # Get main product
            product_result = await db.execute(
                select(Product).where(Product.id == competitor.main_product_id)
            )
            main_product = product_result.scalar_one_or_none()
            
            if not main_product:
                logger.error("Main product not found", product_id=competitor.main_product_id)
                return {"status": "error", "message": "Main product not found"}
            
            try:
                # Perform competitive analysis
                analysis_data = await self._perform_analysis(main_product, competitor)
                
                # Create analysis record
                analysis = CompetitorAnalysis(
                    competitor_id=competitor.id,
                    analyzed_at=datetime.utcnow(),
                    price_difference=analysis_data.get("price_difference"),
                    price_difference_percent=analysis_data.get("price_difference_percent"),
                    bsr_difference=analysis_data.get("bsr_difference"),
                    rating_difference=analysis_data.get("rating_difference"),
                    review_count_difference=analysis_data.get("review_count_difference"),
                    main_advantages=analysis_data.get("main_advantages"),
                    competitor_advantages=analysis_data.get("competitor_advantages"),
                    ai_insights=analysis_data.get("ai_insights"),
                    positioning_analysis=analysis_data.get("positioning_analysis"),
                    recommended_actions=analysis_data.get("recommended_actions"),
                    estimated_market_share=analysis_data.get("estimated_market_share"),
                    feature_comparison=analysis_data.get("feature_comparison")
                )
                
                db.add(analysis)
                await db.commit()
                
                logger.info(
                    "Competitor analysis completed",
                    competitor_id=competitor_id,
                    main_product_id=main_product.id
                )
                
                return {
                    "status": "success",
                    "competitor_id": competitor_id,
                    "analysis_id": analysis.id,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                logger.error(
                    "Failed to analyze competitor",
                    competitor_id=competitor_id,
                    error=str(e)
                )
                return {
                    "status": "error",
                    "competitor_id": competitor_id,
                    "error": str(e)
                }
    
    async def _perform_analysis(self, main_product: Product, competitor: Competitor) -> Dict[str, Any]:
        """Perform competitive analysis - would integrate with AI service"""
        
        # Calculate basic metrics differences
        price_diff = None
        price_diff_percent = None
        if main_product.current_price and competitor.current_price:
            price_diff = main_product.current_price - competitor.current_price
            price_diff_percent = (price_diff / competitor.current_price) * 100
        
        bsr_diff = None
        if main_product.current_bsr and competitor.current_bsr:
            bsr_diff = main_product.current_bsr - competitor.current_bsr
        
        rating_diff = None
        if main_product.current_rating and competitor.current_rating:
            rating_diff = main_product.current_rating - competitor.current_rating
        
        review_diff = None
        if main_product.current_review_count and competitor.current_review_count:
            review_diff = main_product.current_review_count - competitor.current_review_count
        
        # Mock AI analysis (would call OpenAI API)
        analysis = {
            "price_difference": price_diff,
            "price_difference_percent": price_diff_percent,
            "bsr_difference": bsr_diff,
            "rating_difference": rating_diff,
            "review_count_difference": review_diff,
            "main_advantages": [
                "Better customer rating",
                "More reviews indicating trust",
                "Prime eligibility"
            ] if rating_diff and rating_diff > 0 else [],
            "competitor_advantages": [
                "Lower price point",
                "Better BSR ranking",
                "More color options"
            ] if price_diff and price_diff > 0 else [],
            "ai_insights": {
                "market_position": "Strong competitor in mid-range segment",
                "customer_sentiment": "Positive overall with concerns about durability",
                "opportunity_areas": ["Improve product descriptions", "Add video content"]
            },
            "positioning_analysis": "Main product positioned as premium option with better quality",
            "recommended_actions": [
                "Consider price adjustment to be more competitive",
                "Highlight unique features in listing",
                "Improve product images"
            ],
            "estimated_market_share": 15.5,
            "feature_comparison": {
                "common_features": ["Waterproof", "1-year warranty"],
                "unique_main": ["Extra accessories included"],
                "unique_competitor": ["Lighter weight"]
            }
        }
        
        return analysis


# Create task instances
run_competitive_analysis = RunCompetitiveAnalysisTask()
analyze_competitor = AnalyzeCompetitorTask()