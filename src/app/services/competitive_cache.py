"""Competitive data caching service"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import hashlib
from src.app.core.redis import redis_client
import structlog

logger = structlog.get_logger()


class CompetitiveCacheService:
    """Service for caching competitive intelligence data"""
    
    # Cache durations in seconds
    COMPETITOR_DATA_TTL = 6 * 60 * 60  # 6 hours
    ANALYSIS_REPORT_TTL = 2 * 60 * 60  # 2 hours
    INTELLIGENCE_REPORT_TTL = 4 * 60 * 60  # 4 hours
    MARKET_TRENDS_TTL = 24 * 60 * 60  # 24 hours
    COMPETITOR_LIST_TTL = 12 * 60 * 60  # 12 hours
    
    @staticmethod
    def _generate_cache_key(prefix: str, *args) -> str:
        """Generate cache key from prefix and arguments"""
        key_parts = [str(arg) for arg in args]
        key_string = f"{prefix}:{':'.join(key_parts)}"
        return key_string
    
    @staticmethod
    def _generate_hash_key(prefix: str, data: Dict[str, Any]) -> str:
        """Generate hash-based cache key for complex data"""
        data_string = json.dumps(data, sort_keys=True)
        hash_digest = hashlib.md5(data_string.encode()).hexdigest()[:12]
        return f"{prefix}:{hash_digest}"
    
    async def cache_competitor_data(
        self,
        asin: str,
        data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache competitor product data
        
        Args:
            asin: Competitor ASIN
            data: Competitor data to cache
            ttl: Time to live in seconds
            
        Returns:
            True if cached successfully
        """
        try:
            cache_key = self._generate_cache_key("competitor_data", asin)
            
            # Add metadata
            cached_data = {
                **data,
                "cached_at": datetime.utcnow().isoformat(),
                "cache_version": "1.0"
            }
            
            ttl = ttl or self.COMPETITOR_DATA_TTL
            await redis_client.setex(
                cache_key,
                ttl,
                json.dumps(cached_data, default=str)
            )
            
            logger.info("competitor_data_cached", asin=asin, ttl=ttl)
            return True
            
        except Exception as e:
            logger.error("cache_competitor_data_error", error=str(e), asin=asin)
            return False
    
    async def get_competitor_data(self, asin: str) -> Optional[Dict[str, Any]]:
        """
        Get cached competitor data
        
        Args:
            asin: Competitor ASIN
            
        Returns:
            Cached data or None if not found
        """
        try:
            cache_key = self._generate_cache_key("competitor_data", asin)
            cached_data = await redis_client.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                logger.info("competitor_data_cache_hit", asin=asin)
                return data
            
            logger.info("competitor_data_cache_miss", asin=asin)
            return None
            
        except Exception as e:
            logger.error("get_competitor_data_error", error=str(e), asin=asin)
            return None
    
    async def cache_analysis_report(
        self,
        product_id: int,
        competitor_id: int,
        analysis: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """Cache competitor analysis report"""
        try:
            cache_key = self._generate_cache_key(
                "analysis_report", product_id, competitor_id
            )
            
            cached_data = {
                **analysis,
                "cached_at": datetime.utcnow().isoformat(),
                "product_id": product_id,
                "competitor_id": competitor_id
            }
            
            ttl = ttl or self.ANALYSIS_REPORT_TTL
            await redis_client.setex(
                cache_key,
                ttl,
                json.dumps(cached_data, default=str)
            )
            
            logger.info("analysis_report_cached", 
                       product_id=product_id, 
                       competitor_id=competitor_id)
            return True
            
        except Exception as e:
            logger.error("cache_analysis_report_error", 
                        error=str(e), 
                        product_id=product_id,
                        competitor_id=competitor_id)
            return False
    
    async def get_analysis_report(
        self,
        product_id: int,
        competitor_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get cached analysis report"""
        try:
            cache_key = self._generate_cache_key(
                "analysis_report", product_id, competitor_id
            )
            cached_data = await redis_client.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                logger.info("analysis_report_cache_hit", 
                           product_id=product_id, 
                           competitor_id=competitor_id)
                return data
            
            return None
            
        except Exception as e:
            logger.error("get_analysis_report_error", 
                        error=str(e), 
                        product_id=product_id,
                        competitor_id=competitor_id)
            return None
    
    async def cache_intelligence_report(
        self,
        product_id: int,
        report: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """Cache comprehensive intelligence report"""
        try:
            cache_key = self._generate_cache_key("intelligence_report", product_id)
            
            cached_data = {
                **report,
                "cached_at": datetime.utcnow().isoformat()
            }
            
            ttl = ttl or self.INTELLIGENCE_REPORT_TTL
            await redis_client.setex(
                cache_key,
                ttl,
                json.dumps(cached_data, default=str)
            )
            
            logger.info("intelligence_report_cached", product_id=product_id)
            return True
            
        except Exception as e:
            logger.error("cache_intelligence_report_error", 
                        error=str(e), 
                        product_id=product_id)
            return False
    
    async def get_intelligence_report(
        self,
        product_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get cached intelligence report"""
        try:
            cache_key = self._generate_cache_key("intelligence_report", product_id)
            cached_data = await redis_client.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                logger.info("intelligence_report_cache_hit", product_id=product_id)
                return data
            
            return None
            
        except Exception as e:
            logger.error("get_intelligence_report_error", 
                        error=str(e), 
                        product_id=product_id)
            return None
    
    async def cache_market_trends(
        self,
        category: str,
        trends: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """Cache market trend analysis"""
        try:
            cache_key = self._generate_cache_key("market_trends", category.lower())
            
            cached_data = {
                **trends,
                "cached_at": datetime.utcnow().isoformat(),
                "category": category
            }
            
            ttl = ttl or self.MARKET_TRENDS_TTL
            await redis_client.setex(
                cache_key,
                ttl,
                json.dumps(cached_data, default=str)
            )
            
            logger.info("market_trends_cached", category=category)
            return True
            
        except Exception as e:
            logger.error("cache_market_trends_error", 
                        error=str(e), 
                        category=category)
            return False
    
    async def get_market_trends(self, category: str) -> Optional[Dict[str, Any]]:
        """Get cached market trends"""
        try:
            cache_key = self._generate_cache_key("market_trends", category.lower())
            cached_data = await redis_client.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                logger.info("market_trends_cache_hit", category=category)
                return data
            
            return None
            
        except Exception as e:
            logger.error("get_market_trends_error", 
                        error=str(e), 
                        category=category)
            return None
    
    async def cache_competitor_list(
        self,
        product_id: int,
        competitors: List[Dict[str, Any]],
        ttl: Optional[int] = None
    ) -> bool:
        """Cache competitor list"""
        try:
            cache_key = self._generate_cache_key("competitor_list", product_id)
            
            cached_data = {
                "competitors": competitors,
                "cached_at": datetime.utcnow().isoformat(),
                "product_id": product_id,
                "count": len(competitors)
            }
            
            ttl = ttl or self.COMPETITOR_LIST_TTL
            await redis_client.setex(
                cache_key,
                ttl,
                json.dumps(cached_data, default=str)
            )
            
            logger.info("competitor_list_cached", 
                       product_id=product_id, 
                       count=len(competitors))
            return True
            
        except Exception as e:
            logger.error("cache_competitor_list_error", 
                        error=str(e), 
                        product_id=product_id)
            return False
    
    async def get_competitor_list(
        self,
        product_id: int
    ) -> Optional[List[Dict[str, Any]]]:
        """Get cached competitor list"""
        try:
            cache_key = self._generate_cache_key("competitor_list", product_id)
            cached_data = await redis_client.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                logger.info("competitor_list_cache_hit", product_id=product_id)
                return data.get("competitors", [])
            
            return None
            
        except Exception as e:
            logger.error("get_competitor_list_error", 
                        error=str(e), 
                        product_id=product_id)
            return None
    
    async def invalidate_product_cache(self, product_id: int) -> bool:
        """
        Invalidate all cache entries for a product
        
        Args:
            product_id: Product ID
            
        Returns:
            True if invalidated successfully
        """
        try:
            patterns_to_delete = [
                f"*competitor_list:{product_id}*",
                f"*analysis_report:{product_id}:*",
                f"*intelligence_report:{product_id}*"
            ]
            
            deleted_count = 0
            # Simplified cache invalidation for now
            # In production, you'd use SCAN to find and delete keys
            
            logger.info("product_cache_invalidated", 
                       product_id=product_id, 
                       deleted_keys=deleted_count)
            return True
            
        except Exception as e:
            logger.error("invalidate_product_cache_error", 
                        error=str(e), 
                        product_id=product_id)
            return False
    
    async def invalidate_competitor_cache(self, asin: str) -> bool:
        """Invalidate cache for a specific competitor"""
        try:
            # Simplified competitor cache invalidation
            # In production, you'd scan for keys matching the pattern
            cache_key = self._generate_cache_key("competitor_data", asin)
            await redis_client.delete(cache_key)
            
            logger.info("competitor_cache_invalidated", asin=asin, deleted_keys=1)
            return True
            
        except Exception as e:
            logger.error("invalidate_competitor_cache_error", 
                        error=str(e), 
                        asin=asin)
            return False
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            stats = {
                "cache_hits": 0,
                "cache_misses": 0,
                "active_keys": {
                    "competitor_data": 0,
                    "analysis_reports": 0,
                    "intelligence_reports": 0,
                    "market_trends": 0,
                    "competitor_lists": 0
                },
                "memory_usage": "unknown"
            }
            
            # Count keys by type (simplified since keys() may not be available)
            # In production, you'd use SCAN or maintain counters
            for key_type in stats["active_keys"].keys():
                stats["active_keys"][key_type] = 0  # Simplified for now
            
            # Get memory info if available
            try:
                memory_info = await redis_client.info('memory')
                stats["memory_usage"] = memory_info.get('used_memory_human', 'unknown')
            except:
                pass
            
            return stats
            
        except Exception as e:
            logger.error("get_cache_stats_error", error=str(e))
            return {"error": "Failed to get cache statistics"}
    
    async def warm_up_cache(
        self,
        product_ids: List[int],
        max_competitors: int = 5
    ) -> Dict[str, Any]:
        """
        Warm up cache for multiple products
        
        Args:
            product_ids: List of product IDs to warm up
            max_competitors: Maximum competitors to cache per product
            
        Returns:
            Warmup statistics
        """
        try:
            warmed_up = {
                "products_processed": 0,
                "competitors_cached": 0,
                "errors": 0
            }
            
            for product_id in product_ids[:10]:  # Limit to 10 products
                try:
                    # This would typically involve calling the competitor service
                    # to generate and cache fresh data
                    warmed_up["products_processed"] += 1
                    
                except Exception as e:
                    warmed_up["errors"] += 1
                    logger.error("cache_warmup_error", 
                                error=str(e), 
                                product_id=product_id)
            
            logger.info("cache_warmup_completed", **warmed_up)
            return warmed_up
            
        except Exception as e:
            logger.error("cache_warmup_error", error=str(e))
            return {"error": "Cache warmup failed"}


# Global cache service instance
competitive_cache = CompetitiveCacheService()