from datetime import datetime, timedelta
from typing import List, Dict, Any
from celery import Task
from sqlalchemy import select, and_
from src.app.tasks.celery_app import celery_app
from src.app.core.database import AsyncSessionLocal
from src.app.models.product import Product, ProductMetrics
from src.app.core.redis import redis_client
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


@celery_app.task(base=AsyncTask, name="monitor_price_changes")
class MonitorPriceChangesTask(AsyncTask):
    async def _run(self):
        logger.info("Starting price monitoring task")
        
        async with AsyncSessionLocal() as db:
            # Get all active products
            result = await db.execute(
                select(Product).where(Product.is_active == True)
            )
            products = result.scalars().all()
            
            monitored_count = 0
            alerts_sent = 0
            
            for product in products:
                try:
                    # Get latest metrics
                    latest_metrics = await db.execute(
                        select(ProductMetrics)
                        .where(ProductMetrics.product_id == product.id)
                        .order_by(ProductMetrics.scraped_at.desc())
                        .limit(2)
                    )
                    metrics_list = latest_metrics.scalars().all()
                    
                    if len(metrics_list) >= 2:
                        current = metrics_list[0]
                        previous = metrics_list[1]
                        
                        # Check for significant price changes
                        if current.price and previous.price:
                            price_change_percent = ((current.price - previous.price) / previous.price) * 100
                            
                            if abs(price_change_percent) > 10:
                                # Send alert (would integrate with notification service)
                                alert_data = {
                                    "product_id": product.id,
                                    "asin": product.asin,
                                    "title": product.title,
                                    "previous_price": previous.price,
                                    "current_price": current.price,
                                    "change_percent": price_change_percent,
                                    "timestamp": datetime.utcnow().isoformat()
                                }
                                
                                # Cache alert in Redis
                                await redis_client.set(
                                    f"price_alert:{product.id}",
                                    alert_data,
                                    expire=3600  # 1 hour
                                )
                                
                                logger.info(
                                    "Price alert triggered",
                                    product_id=product.id,
                                    asin=product.asin,
                                    change_percent=price_change_percent
                                )
                                alerts_sent += 1
                    
                    monitored_count += 1
                    
                except Exception as e:
                    logger.error(
                        "Error monitoring product",
                        product_id=product.id,
                        error=str(e)
                    )
        
        logger.info(
            "Price monitoring completed",
            monitored_count=monitored_count,
            alerts_sent=alerts_sent
        )
        
        return {
            "monitored_count": monitored_count,
            "alerts_sent": alerts_sent,
            "timestamp": datetime.utcnow().isoformat()
        }


@celery_app.task(base=AsyncTask, name="cleanup_old_metrics")
class CleanupOldMetricsTask(AsyncTask):
    async def _run(self, days_to_keep: int = 90):
        logger.info("Starting metrics cleanup task", days_to_keep=days_to_keep)
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        async with AsyncSessionLocal() as db:
            # Delete old metrics
            result = await db.execute(
                select(ProductMetrics)
                .where(ProductMetrics.scraped_at < cutoff_date)
            )
            old_metrics = result.scalars().all()
            
            deleted_count = len(old_metrics)
            
            for metric in old_metrics:
                await db.delete(metric)
            
            await db.commit()
            
            logger.info(
                "Metrics cleanup completed",
                deleted_count=deleted_count,
                cutoff_date=cutoff_date.isoformat()
            )
            
            return {
                "deleted_count": deleted_count,
                "cutoff_date": cutoff_date.isoformat(),
                "timestamp": datetime.utcnow().isoformat()
            }


@celery_app.task(name="update_product_cache")
def update_product_cache(product_id: int, data: Dict[str, Any]):
    """Update product data in Redis cache"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def _update():
            await redis_client.set(
                f"product:{product_id}",
                data,
                expire=1800  # 30 minutes
            )
            logger.info("Product cache updated", product_id=product_id)
        
        loop.run_until_complete(_update())
        return {"status": "success", "product_id": product_id}
        
    except Exception as e:
        logger.error("Failed to update product cache", product_id=product_id, error=str(e))
        return {"status": "error", "product_id": product_id, "error": str(e)}