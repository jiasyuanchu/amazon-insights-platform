"""Competitor analysis Celery tasks"""

from datetime import datetime
from celery import Task
from src.app.tasks.celery_app import celery_app
from src.app.core.database import AsyncSessionLocal
from src.app.services.competitor_service import CompetitorService
from src.app.models import Product, Competitor
from sqlalchemy import select
import structlog
import asyncio

logger = structlog.get_logger()


@celery_app.task(name="analyze_competitors_task")
def analyze_competitors_task(product_id: int):
    """Analyze all competitors for a product"""
    async def _analyze():
        async with AsyncSessionLocal() as db:
            service = CompetitorService(db)
            
            # First discover competitors if none exist
            result = await db.execute(
                select(Competitor).where(Competitor.main_product_id == product_id)
            )
            existing_competitors = result.scalars().all()
            
            if not existing_competitors:
                logger.info("Discovering competitors", product_id=product_id)
                await service.discover_competitors(product_id)
            
            # Now analyze all competitors
            logger.info("Analyzing competitors", product_id=product_id)
            report = await service.batch_analyze_competitors(product_id)
            
            return {
                "product_id": product_id,
                "competitors_analyzed": report.get("total_competitors", 0),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_analyze())
    finally:
        loop.close()


@celery_app.task(name="discover_new_competitors")
def discover_new_competitors():
    """Periodically discover new competitors for all products"""
    async def _discover():
        async with AsyncSessionLocal() as db:
            # Get all active products
            result = await db.execute(
                select(Product).where(Product.is_active == True)
            )
            products = result.scalars().all()
            
            service = CompetitorService(db)
            discovered_total = 0
            
            for product in products:
                try:
                    competitors = await service.discover_competitors(
                        product.id,
                        max_competitors=5
                    )
                    discovered_total += len(competitors)
                    
                    logger.info(
                        "Discovered competitors for product",
                        product_id=product.id,
                        count=len(competitors)
                    )
                except Exception as e:
                    logger.error(
                        "Failed to discover competitors",
                        product_id=product.id,
                        error=str(e)
                    )
            
            return {
                "products_processed": len(products),
                "competitors_discovered": discovered_total,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_discover())
    finally:
        loop.close()


@celery_app.task(name="update_competitor_metrics")
def update_competitor_metrics():
    """Update metrics for all tracked competitors"""
    async def _update():
        async with AsyncSessionLocal() as db:
            # Get all competitors
            result = await db.execute(select(Competitor))
            competitors = result.scalars().all()
            
            updated_count = 0
            
            for competitor in competitors:
                try:
                    # In production, this would scrape actual data
                    # For now, we'll simulate updates
                    import random
                    
                    # Simulate price changes
                    if competitor.current_price:
                        price_change = random.uniform(-5, 5)
                        competitor.current_price = max(
                            1, 
                            competitor.current_price + price_change
                        )
                    
                    # Simulate BSR changes
                    if competitor.current_bsr:
                        bsr_change = random.randint(-100, 100)
                        competitor.current_bsr = max(
                            1,
                            competitor.current_bsr + bsr_change
                        )
                    
                    # Simulate rating changes
                    if competitor.current_rating:
                        rating_change = random.uniform(-0.1, 0.1)
                        competitor.current_rating = max(
                            1.0,
                            min(5.0, competitor.current_rating + rating_change)
                        )
                    
                    updated_count += 1
                    
                except Exception as e:
                    logger.error(
                        "Failed to update competitor metrics",
                        competitor_id=competitor.id,
                        error=str(e)
                    )
            
            await db.commit()
            
            return {
                "competitors_updated": updated_count,
                "total_competitors": len(competitors),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_update())
    finally:
        loop.close()


@celery_app.task(name="generate_competitive_reports")
def generate_competitive_reports():
    """Generate competitive intelligence reports for all products"""
    async def _generate():
        async with AsyncSessionLocal() as db:
            # Get all active products
            result = await db.execute(
                select(Product).where(Product.is_active == True)
            )
            products = result.scalars().all()
            
            service = CompetitorService(db)
            reports_generated = 0
            
            for product in products:
                try:
                    # Check if product has competitors
                    comp_result = await db.execute(
                        select(Competitor).where(
                            Competitor.main_product_id == product.id
                        )
                    )
                    
                    if comp_result.scalars().first():
                        # Generate report
                        report = await service.batch_analyze_competitors(product.id)
                        reports_generated += 1
                        
                        logger.info(
                            "Generated competitive report",
                            product_id=product.id,
                            competitors=report.get("total_competitors", 0)
                        )
                except Exception as e:
                    logger.error(
                        "Failed to generate report",
                        product_id=product.id,
                        error=str(e)
                    )
            
            return {
                "reports_generated": reports_generated,
                "products_processed": len(products),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_generate())
    finally:
        loop.close()