"""Product scraping Celery tasks"""

from datetime import datetime
from celery import Task
from src.app.tasks.celery_app import celery_app
from src.app.core.database import AsyncSessionLocal
from src.app.services.product_service import ProductService
import structlog
import asyncio

logger = structlog.get_logger()


class AsyncTask(Task):
    """Base class for async tasks"""
    def run(self, *args, **kwargs):
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self._run(*args, **kwargs))
    
    async def _run(self, *args, **kwargs):
        raise NotImplementedError


@celery_app.task(name="scrape_product_task")
def scrape_product_task(product_id: int):
    """Synchronous wrapper for product scraping"""
    async def _scrape():
        async with AsyncSessionLocal() as db:
            service = ProductService(db)
            return await service.scrape_and_update_product(product_id)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_scrape())
    finally:
        loop.close()


@celery_app.task(name="scrape_all_user_products")
def scrape_all_user_products(user_id: int):
    """Scrape all products for a user"""
    from src.app.models import Product
    from sqlalchemy import select
    
    async def _scrape_all():
        async with AsyncSessionLocal() as db:
            # Get all active products for user
            result = await db.execute(
                select(Product).where(
                    Product.user_id == user_id,
                    Product.is_active == True
                )
            )
            products = result.scalars().all()
            
            results = []
            for product in products:
                try:
                    service = ProductService(db)
                    result = await service.scrape_and_update_product(product.id)
                    results.append(result)
                except Exception as e:
                    logger.error(
                        "Failed to scrape product",
                        product_id=product.id,
                        error=str(e)
                    )
                    results.append({
                        "product_id": product.id,
                        "success": False,
                        "error": str(e)
                    })
            
            return {
                "user_id": user_id,
                "total_products": len(products),
                "successful": len([r for r in results if r.get("success")]),
                "failed": len([r for r in results if not r.get("success")]),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_scrape_all())
    finally:
        loop.close()


@celery_app.task(name="daily_product_insights")
def daily_product_insights():
    """Generate daily insights for all active products"""
    from src.app.models import Product
    from sqlalchemy import select
    
    async def _generate_insights():
        async with AsyncSessionLocal() as db:
            # Get all active products
            result = await db.execute(
                select(Product).where(Product.is_active == True)
            )
            products = result.scalars().all()
            
            insights_generated = 0
            errors = 0
            
            for product in products:
                try:
                    # Scrape latest data
                    service = ProductService(db)
                    await service.scrape_and_update_product(product.id)
                    insights_generated += 1
                    
                    logger.info(
                        "Generated insights for product",
                        product_id=product.id,
                        asin=product.asin
                    )
                except Exception as e:
                    logger.error(
                        "Failed to generate insights",
                        product_id=product.id,
                        error=str(e)
                    )
                    errors += 1
            
            return {
                "total_products": len(products),
                "insights_generated": insights_generated,
                "errors": errors,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_generate_insights())
    finally:
        loop.close()