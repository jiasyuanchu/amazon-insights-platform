from datetime import datetime
from typing import Dict, Any, List
from celery import Task
from sqlalchemy import select
from src.app.tasks.celery_app import celery_app
from src.app.core.database import AsyncSessionLocal
from src.app.models.product import Product, ProductMetrics
import structlog
import asyncio
import httpx

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


@celery_app.task(base=AsyncTask, name="scrape_all_products")
class ScrapeAllProductsTask(AsyncTask):
    async def _run(self):
        logger.info("Starting daily product scraping")
        
        async with AsyncSessionLocal() as db:
            # Get all active products
            result = await db.execute(
                select(Product).where(Product.is_active == True)
            )
            products = result.scalars().all()
            
            scraped_count = 0
            failed_count = 0
            
            for product in products:
                try:
                    # Trigger individual scraping task
                    scrape_single_product.delay(product.id)
                    scraped_count += 1
                except Exception as e:
                    logger.error(
                        "Failed to queue scraping task",
                        product_id=product.id,
                        error=str(e)
                    )
                    failed_count += 1
            
            logger.info(
                "Product scraping tasks queued",
                scraped_count=scraped_count,
                failed_count=failed_count
            )
            
            return {
                "total_products": len(products),
                "queued": scraped_count,
                "failed": failed_count,
                "timestamp": datetime.utcnow().isoformat()
            }


@celery_app.task(base=AsyncTask, name="scrape_single_product")
class ScrapeSingleProductTask(AsyncTask):
    async def _run(self, product_id: int):
        logger.info("Scraping product", product_id=product_id)
        
        async with AsyncSessionLocal() as db:
            # Get product
            result = await db.execute(
                select(Product).where(Product.id == product_id)
            )
            product = result.scalar_one_or_none()
            
            if not product:
                logger.error("Product not found", product_id=product_id)
                return {"status": "error", "message": "Product not found"}
            
            try:
                # Here we would call Firecrawl API
                # For now, using mock data
                scraped_data = await self._mock_scrape_product(product.asin)
                
                # Create new metrics entry
                metrics = ProductMetrics(
                    product_id=product.id,
                    scraped_at=datetime.utcnow(),
                    price=scraped_data.get("price"),
                    buy_box_price=scraped_data.get("buy_box_price"),
                    bsr=scraped_data.get("bsr"),
                    bsr_category=scraped_data.get("bsr_category"),
                    rating=scraped_data.get("rating"),
                    review_count=scraped_data.get("review_count"),
                    in_stock=scraped_data.get("in_stock", True),
                    stock_level=scraped_data.get("stock_level"),
                    seller_count=scraped_data.get("seller_count"),
                    buy_box_seller=scraped_data.get("buy_box_seller"),
                    raw_data=scraped_data
                )
                
                # Calculate changes from previous metrics
                prev_metrics = await db.execute(
                    select(ProductMetrics)
                    .where(ProductMetrics.product_id == product.id)
                    .order_by(ProductMetrics.scraped_at.desc())
                    .limit(1)
                )
                previous = prev_metrics.scalar_one_or_none()
                
                if previous:
                    if metrics.price and previous.price:
                        metrics.price_change_percent = ((metrics.price - previous.price) / previous.price) * 100
                    if metrics.bsr and previous.bsr:
                        metrics.bsr_change_percent = ((metrics.bsr - previous.bsr) / previous.bsr) * 100
                    if metrics.review_count and previous.review_count:
                        metrics.new_reviews_count = metrics.review_count - previous.review_count
                
                # Update product current metrics
                product.current_price = metrics.price
                product.current_bsr = metrics.bsr
                product.current_rating = metrics.rating
                product.current_review_count = metrics.review_count
                product.current_buy_box_price = metrics.buy_box_price
                product.last_scraped_at = datetime.utcnow()
                
                db.add(metrics)
                await db.commit()
                
                logger.info(
                    "Product scraped successfully",
                    product_id=product_id,
                    asin=product.asin
                )
                
                return {
                    "status": "success",
                    "product_id": product_id,
                    "asin": product.asin,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                logger.error(
                    "Failed to scrape product",
                    product_id=product_id,
                    error=str(e)
                )
                return {
                    "status": "error",
                    "product_id": product_id,
                    "error": str(e)
                }
    
    async def _mock_scrape_product(self, asin: str) -> Dict[str, Any]:
        """Mock scraping function - would be replaced with Firecrawl API call"""
        import random
        
        return {
            "asin": asin,
            "price": round(random.uniform(10, 500), 2),
            "buy_box_price": round(random.uniform(10, 500), 2),
            "bsr": random.randint(100, 100000),
            "bsr_category": "Home & Kitchen",
            "rating": round(random.uniform(3.0, 5.0), 1),
            "review_count": random.randint(10, 5000),
            "in_stock": random.choice([True, True, True, False]),
            "stock_level": random.choice(["In Stock", "Only 5 left", "Low stock"]),
            "seller_count": random.randint(1, 20),
            "buy_box_seller": "Amazon.com",
            "scraped_at": datetime.utcnow().isoformat()
        }


# Create task instances
scrape_all_products = ScrapeAllProductsTask()
scrape_single_product = ScrapeSingleProductTask()