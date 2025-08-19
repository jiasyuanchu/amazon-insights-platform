"""Product service for business logic"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_
from src.app.models import (
    Product, ProductMetrics, ProductInsight, 
    PriceHistory, AlertConfiguration, AlertHistory
)
from src.app.services.firecrawl_service import firecrawl_service
from src.app.services.openai_service import OpenAIService
import structlog
import re

logger = structlog.get_logger()


class ProductService:
    """Service for product-related operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.openai_service = OpenAIService()
    
    async def scrape_and_update_product(self, product_id: int) -> Dict[str, Any]:
        """
        Scrape product data and update database
        
        Args:
            product_id: ID of the product to scrape
            
        Returns:
            Dictionary with scraping results
        """
        # Get product
        result = await self.db.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()
        
        if not product:
            raise ValueError(f"Product {product_id} not found")
        
        try:
            # Scrape product data
            logger.info("scraping_product", product_id=product_id, asin=product.asin)
            scraped_data = await firecrawl_service.scrape_amazon_product(product.asin)
            
            if not scraped_data.get("success"):
                raise Exception(f"Scraping failed: {scraped_data.get('error')}")
            
            # Parse scraped data
            extracted = scraped_data.get("data", {}).get("extract", {})
            
            # Update product basic info
            if extracted.get("title"):
                product.title = extracted["title"]
            if extracted.get("images") and len(extracted["images"]) > 0:
                product.image_url = extracted["images"][0]
            
            # Parse price
            price = self._parse_price(extracted.get("price"))
            if price:
                product.current_price = price
            
            # Parse BSR
            bsr_info = self._parse_bsr(extracted.get("bsr_rank"))
            if bsr_info:
                product.current_bsr = bsr_info["rank"]
            
            # Parse rating
            rating_info = self._parse_rating(extracted.get("rating"))
            if rating_info:
                product.current_rating = rating_info["rating"]
                product.current_review_count = rating_info["count"]
            
            # Update last scraped time
            product.last_scraped_at = datetime.utcnow()
            
            # Create metrics record
            metrics = ProductMetrics(
                product_id=product.id,
                scraped_at=datetime.utcnow(),
                price=price,
                bsr=bsr_info.get("rank") if bsr_info else None,
                bsr_category=bsr_info.get("category") if bsr_info else None,
                rating=rating_info.get("rating") if rating_info else None,
                review_count=rating_info.get("count") if rating_info else None,
                in_stock=extracted.get("availability", "").lower() != "out of stock",
                raw_data=extracted
            )
            self.db.add(metrics)
            
            # Create price history record
            price_history = PriceHistory(
                product_id=product.id,
                tracked_at=datetime.utcnow(),
                sale_price=price,
                in_stock=metrics.in_stock,
                stock_level=extracted.get("availability")
            )
            self.db.add(price_history)
            
            # Generate and save insights
            await self._generate_product_insights(product, metrics)
            
            # Check and trigger alerts
            await self._check_and_trigger_alerts(product, metrics)
            
            await self.db.commit()
            
            logger.info("product_scraped_successfully", 
                       product_id=product_id,
                       price=price,
                       bsr=bsr_info)
            
            return {
                "success": True,
                "product_id": product_id,
                "asin": product.asin,
                "price": price,
                "bsr": bsr_info,
                "rating": rating_info
            }
            
        except Exception as e:
            logger.error("product_scraping_error", 
                        product_id=product_id,
                        error=str(e))
            raise
    
    def _parse_price(self, price_str: Optional[str]) -> Optional[float]:
        """Parse price from string"""
        if not price_str:
            return None
        
        # Remove currency symbols and extract number
        price_match = re.search(r'[\d,]+\.?\d*', price_str)
        if price_match:
            price = price_match.group().replace(',', '')
            return float(price)
        return None
    
    def _parse_bsr(self, bsr_str: Optional[str]) -> Optional[Dict[str, Any]]:
        """Parse BSR from string"""
        if not bsr_str:
            return None
        
        # Extract rank number
        rank_match = re.search(r'#?([\d,]+)', bsr_str)
        if rank_match:
            rank = int(rank_match.group(1).replace(',', ''))
            
            # Extract category
            category_match = re.search(r'in\s+(.+?)(?:\s*\(|$)', bsr_str)
            category = category_match.group(1) if category_match else None
            
            return {
                "rank": rank,
                "category": category
            }
        return None
    
    def _parse_rating(self, rating_str: Optional[str]) -> Optional[Dict[str, Any]]:
        """Parse rating from string"""
        if not rating_str:
            return None
        
        # Extract rating value
        rating_match = re.search(r'([\d.]+)\s*out of\s*5', rating_str)
        if rating_match:
            rating = float(rating_match.group(1))
            
            # Extract review count
            count_match = re.search(r'([\d,]+)\s*(?:global\s+)?(?:ratings?|reviews?)', rating_str)
            count = int(count_match.group(1).replace(',', '')) if count_match else None
            
            return {
                "rating": rating,
                "count": count
            }
        return None
    
    async def _generate_product_insights(self, product: Product, metrics: ProductMetrics):
        """Generate AI-powered insights for product"""
        # Get previous metrics for comparison
        prev_metrics = await self.db.execute(
            select(ProductMetrics)
            .where(
                and_(
                    ProductMetrics.product_id == product.id,
                    ProductMetrics.scraped_at < metrics.scraped_at
                )
            )
            .order_by(ProductMetrics.scraped_at.desc())
            .limit(1)
        )
        prev_metrics = prev_metrics.scalar_one_or_none()
        
        # Calculate changes
        price_change_percent = None
        bsr_change_percent = None
        
        if prev_metrics:
            if prev_metrics.price and metrics.price:
                price_change_percent = ((metrics.price - prev_metrics.price) / prev_metrics.price) * 100
            if prev_metrics.bsr and metrics.bsr:
                bsr_change_percent = ((metrics.bsr - prev_metrics.bsr) / prev_metrics.bsr) * 100
        
        # Generate AI summary (placeholder - would call OpenAI)
        ai_summary = f"Product shows {'improving' if bsr_change_percent and bsr_change_percent < 0 else 'stable'} performance. "
        if price_change_percent and abs(price_change_percent) > 10:
            ai_summary += f"Significant price {'increase' if price_change_percent > 0 else 'decrease'} detected. "
        
        # Calculate opportunity score (simple heuristic for now)
        opportunity_score = 50.0
        if bsr_change_percent and bsr_change_percent < -10:
            opportunity_score += 20
        if price_change_percent and price_change_percent < -5:
            opportunity_score += 15
        if metrics.rating and metrics.rating >= 4.0:
            opportunity_score += 15
        
        # Create insight record
        insight = ProductInsight(
            product_id=product.id,
            insight_date=datetime.utcnow(),
            bsr_rank=metrics.bsr,
            bsr_category=metrics.bsr_category,
            bsr_change_percent=bsr_change_percent,
            current_price=metrics.price,
            price_change_percent=price_change_percent,
            total_reviews=metrics.review_count,
            avg_rating=metrics.rating,
            ai_summary=ai_summary,
            opportunity_score=min(opportunity_score, 100)
        )
        self.db.add(insight)
    
    async def _check_and_trigger_alerts(self, product: Product, metrics: ProductMetrics):
        """Check alert conditions and trigger if met"""
        # Get active alert configurations for this product
        alerts = await self.db.execute(
            select(AlertConfiguration).where(
                and_(
                    AlertConfiguration.product_id == product.id,
                    AlertConfiguration.is_active == True
                )
            )
        )
        
        for alert_config in alerts.scalars():
            triggered = False
            alert_type = None
            alert_message = None
            trigger_value = None
            threshold_value = None
            
            # Check price drop threshold
            if alert_config.price_drop_threshold and metrics.price:
                prev_metrics = await self._get_previous_metrics(product.id)
                if prev_metrics and prev_metrics.price:
                    price_drop_percent = ((prev_metrics.price - metrics.price) / prev_metrics.price) * 100
                    if price_drop_percent >= alert_config.price_drop_threshold:
                        triggered = True
                        alert_type = "price_drop"
                        alert_message = f"Price dropped by {price_drop_percent:.1f}% (from ${prev_metrics.price:.2f} to ${metrics.price:.2f})"
                        trigger_value = price_drop_percent
                        threshold_value = alert_config.price_drop_threshold
            
            # Check BSR improvement
            if not triggered and alert_config.bsr_improvement_threshold and metrics.bsr:
                prev_metrics = await self._get_previous_metrics(product.id)
                if prev_metrics and prev_metrics.bsr:
                    bsr_improvement = prev_metrics.bsr - metrics.bsr
                    if bsr_improvement >= alert_config.bsr_improvement_threshold:
                        triggered = True
                        alert_type = "bsr_improvement"
                        alert_message = f"BSR improved by {bsr_improvement} ranks (from #{prev_metrics.bsr} to #{metrics.bsr})"
                        trigger_value = bsr_improvement
                        threshold_value = alert_config.bsr_improvement_threshold
            
            # Create alert history if triggered
            if triggered:
                alert_history = AlertHistory(
                    configuration_id=alert_config.id,
                    product_id=product.id,
                    alert_type=alert_type,
                    alert_message=alert_message,
                    severity="info",
                    trigger_value=trigger_value,
                    threshold_value=threshold_value
                )
                self.db.add(alert_history)
                
                # TODO: Send notifications (email, webhook, etc.)
                logger.info("alert_triggered",
                           product_id=product.id,
                           alert_type=alert_type,
                           message=alert_message)
    
    async def _get_previous_metrics(self, product_id: int) -> Optional[ProductMetrics]:
        """Get the most recent previous metrics for a product"""
        result = await self.db.execute(
            select(ProductMetrics)
            .where(ProductMetrics.product_id == product_id)
            .order_by(ProductMetrics.scraped_at.desc())
            .offset(1)
            .limit(1)
        )
        return result.scalar_one_or_none()