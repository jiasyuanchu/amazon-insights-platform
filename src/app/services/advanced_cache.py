"""Advanced caching service with intelligent cache management"""

import json
import hashlib
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from src.app.core.redis import redis_client
import structlog

logger = structlog.get_logger()


@dataclass
class CacheConfig:
    """Cache configuration settings"""
    ttl: int  # Time to live in seconds
    namespace: str
    compression: bool = False
    serialize_json: bool = True
    auto_refresh: bool = False
    refresh_threshold: float = 0.8  # Refresh when 80% of TTL is reached


class AdvancedCacheService:
    """Advanced caching service with intelligent management"""
    
    def __init__(self):
        self.redis = redis_client
        self.cache_configs = self._initialize_cache_configs()
        self.metrics = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "refreshes": 0
        }
    
    def _initialize_cache_configs(self) -> Dict[str, CacheConfig]:
        """Initialize cache configurations for different data types"""
        return {
            # API Response Caching
            "api_response": CacheConfig(
                ttl=300,  # 5 minutes
                namespace="api:response",
                compression=True,
                auto_refresh=False
            ),
            
            # Product Data Caching
            "product_data": CacheConfig(
                ttl=1800,  # 30 minutes
                namespace="product:data",
                compression=False,
                auto_refresh=True,
                refresh_threshold=0.7
            ),
            
            # Competitor Analysis
            "competitor_analysis": CacheConfig(
                ttl=3600,  # 1 hour
                namespace="competitor:analysis",
                compression=True,
                auto_refresh=True,
                refresh_threshold=0.8
            ),
            
            # Market Intelligence
            "market_intelligence": CacheConfig(
                ttl=7200,  # 2 hours
                namespace="market:intelligence",
                compression=True,
                auto_refresh=False
            ),
            
            # User Session Data
            "user_session": CacheConfig(
                ttl=86400,  # 24 hours
                namespace="user:session",
                compression=False,
                auto_refresh=False
            ),
            
            # Expensive Computations
            "computation": CacheConfig(
                ttl=21600,  # 6 hours
                namespace="compute:result",
                compression=True,
                auto_refresh=True,
                refresh_threshold=0.9
            ),
            
            # Search Results
            "search_results": CacheConfig(
                ttl=900,  # 15 minutes
                namespace="search:results",
                compression=True,
                auto_refresh=False
            ),
            
            # Rate Limiting
            "rate_limit": CacheConfig(
                ttl=3600,  # 1 hour
                namespace="rate:limit",
                compression=False,
                serialize_json=False,
                auto_refresh=False
            )
        }
    
    def _generate_cache_key(self, config: CacheConfig, key: str) -> str:
        """Generate standardized cache key"""
        key_hash = hashlib.md5(key.encode()).hexdigest()[:12]
        return f"{config.namespace}:{key_hash}"
    
    def _serialize_value(self, value: Any, config: CacheConfig) -> str:
        """Serialize value for caching"""
        if not config.serialize_json:
            return str(value)
        
        try:
            return json.dumps(value, default=str)
        except (TypeError, ValueError) as e:
            logger.warning("Failed to serialize cache value", error=str(e))
            return str(value)
    
    def _deserialize_value(self, value: str, config: CacheConfig) -> Any:
        """Deserialize cached value"""
        if not config.serialize_json:
            return value
        
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    
    async def get(
        self, 
        cache_type: str, 
        key: str, 
        default: Any = None
    ) -> Any:
        """Get value from cache with intelligent management"""
        config = self.cache_configs.get(cache_type)
        if not config:
            logger.warning("Unknown cache type", cache_type=cache_type)
            return default
        
        cache_key = self._generate_cache_key(config, key)
        
        try:
            # Get value and TTL
            pipe = self.redis.pipeline()
            pipe.get(cache_key)
            pipe.ttl(cache_key)
            results = await pipe.execute()
            
            cached_value, ttl = results[0], results[1]
            
            if cached_value is None:
                self.metrics["misses"] += 1
                logger.debug("Cache miss", cache_key=cache_key)
                return default
            
            self.metrics["hits"] += 1
            
            # Check if auto-refresh is needed
            if config.auto_refresh and ttl > 0:
                refresh_time = config.ttl * (1 - config.refresh_threshold)
                if ttl < refresh_time:
                    # Schedule background refresh (would need task queue)
                    logger.debug("Cache refresh needed", 
                               cache_key=cache_key, 
                               ttl=ttl, 
                               refresh_time=refresh_time)
            
            return self._deserialize_value(cached_value.decode(), config)
            
        except Exception as e:
            logger.error("Cache get error", error=str(e), cache_key=cache_key)
            return default
    
    async def set(
        self, 
        cache_type: str, 
        key: str, 
        value: Any,
        ttl_override: Optional[int] = None
    ) -> bool:
        """Set value in cache with configuration"""
        config = self.cache_configs.get(cache_type)
        if not config:
            logger.warning("Unknown cache type", cache_type=cache_type)
            return False
        
        cache_key = self._generate_cache_key(config, key)
        ttl = ttl_override or config.ttl
        
        try:
            serialized_value = self._serialize_value(value, config)
            
            # Add metadata for advanced features
            cache_data = {
                "value": serialized_value,
                "cached_at": datetime.utcnow().isoformat(),
                "cache_type": cache_type,
                "original_ttl": ttl
            }
            
            if config.serialize_json:
                cache_data_str = json.dumps(cache_data)
            else:
                cache_data_str = serialized_value
            
            await self.redis.setex(cache_key, ttl, cache_data_str)
            self.metrics["sets"] += 1
            
            logger.debug("Cache set", cache_key=cache_key, ttl=ttl)
            return True
            
        except Exception as e:
            logger.error("Cache set error", error=str(e), cache_key=cache_key)
            return False
    
    async def delete(self, cache_type: str, key: str) -> bool:
        """Delete specific cache entry"""
        config = self.cache_configs.get(cache_type)
        if not config:
            return False
        
        cache_key = self._generate_cache_key(config, key)
        
        try:
            result = await self.redis.delete(cache_key)
            if result > 0:
                self.metrics["deletes"] += 1
                logger.debug("Cache delete", cache_key=cache_key)
            return result > 0
            
        except Exception as e:
            logger.error("Cache delete error", error=str(e), cache_key=cache_key)
            return False
    
    async def invalidate_pattern(self, cache_type: str, pattern: str) -> int:
        """Invalidate multiple cache entries by pattern"""
        config = self.cache_configs.get(cache_type)
        if not config:
            return 0
        
        search_pattern = f"{config.namespace}:*{pattern}*"
        
        try:
            keys = []
            cursor = 0
            
            while True:
                cursor, batch_keys = await self.redis.scan(
                    cursor=cursor, 
                    match=search_pattern, 
                    count=100
                )
                keys.extend(batch_keys)
                if cursor == 0:
                    break
            
            if keys:
                deleted_count = await self.redis.delete(*keys)
                self.metrics["deletes"] += deleted_count
                logger.info("Pattern invalidation", 
                           pattern=pattern, 
                           deleted=deleted_count)
                return deleted_count
            
            return 0
            
        except Exception as e:
            logger.error("Pattern invalidation error", 
                        error=str(e), 
                        pattern=pattern)
            return 0
    
    async def get_with_lock(
        self,
        cache_type: str,
        key: str,
        computation_func: Callable,
        lock_timeout: int = 30,
        **kwargs
    ) -> Any:
        """Get cache value with distributed lock to prevent cache stampede"""
        # First try to get from cache
        cached_value = await self.get(cache_type, key)
        if cached_value is not None:
            return cached_value
        
        # Try to acquire lock
        config = self.cache_configs.get(cache_type)
        if not config:
            return await computation_func(**kwargs)
        
        lock_key = f"lock:{self._generate_cache_key(config, key)}"
        
        try:
            # Try to acquire lock
            lock_acquired = await self.redis.set(
                lock_key, 
                "locked", 
                ex=lock_timeout, 
                nx=True
            )
            
            if lock_acquired:
                # We got the lock, compute the value
                try:
                    computed_value = await computation_func(**kwargs)
                    await self.set(cache_type, key, computed_value)
                    return computed_value
                finally:
                    # Release lock
                    await self.redis.delete(lock_key)
            else:
                # Someone else is computing, wait a bit and try cache again
                import asyncio
                await asyncio.sleep(0.1)  # Wait 100ms
                cached_value = await self.get(cache_type, key)
                if cached_value is not None:
                    return cached_value
                
                # If still no cache, compute without lock (fallback)
                return await computation_func(**kwargs)
                
        except Exception as e:
            logger.error("Cache lock error", error=str(e), key=key)
            # Fallback to direct computation
            return await computation_func(**kwargs)
    
    async def bulk_get(
        self, 
        cache_type: str, 
        keys: List[str]
    ) -> Dict[str, Any]:
        """Get multiple cache values efficiently"""
        config = self.cache_configs.get(cache_type)
        if not config:
            return {}
        
        cache_keys = [self._generate_cache_key(config, key) for key in keys]
        
        try:
            values = await self.redis.mget(cache_keys)
            result = {}
            
            for i, (original_key, cached_value) in enumerate(zip(keys, values)):
                if cached_value is not None:
                    result[original_key] = self._deserialize_value(
                        cached_value.decode(), config
                    )
                    self.metrics["hits"] += 1
                else:
                    self.metrics["misses"] += 1
            
            return result
            
        except Exception as e:
            logger.error("Bulk get error", error=str(e))
            return {}
    
    async def bulk_set(
        self, 
        cache_type: str, 
        data: Dict[str, Any],
        ttl_override: Optional[int] = None
    ) -> bool:
        """Set multiple cache values efficiently"""
        config = self.cache_configs.get(cache_type)
        if not config:
            return False
        
        ttl = ttl_override or config.ttl
        
        try:
            pipe = self.redis.pipeline()
            
            for key, value in data.items():
                cache_key = self._generate_cache_key(config, key)
                serialized_value = self._serialize_value(value, config)
                pipe.setex(cache_key, ttl, serialized_value)
            
            results = await pipe.execute()
            self.metrics["sets"] += len(data)
            
            return all(results)
            
        except Exception as e:
            logger.error("Bulk set error", error=str(e))
            return False
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        try:
            # Get Redis info
            redis_info = await self.redis.info("memory")
            
            # Get key counts by namespace
            namespace_stats = {}
            for cache_type, config in self.cache_configs.items():
                pattern = f"{config.namespace}:*"
                keys = []
                cursor = 0
                
                while True:
                    cursor, batch_keys = await self.redis.scan(
                        cursor=cursor, 
                        match=pattern, 
                        count=100
                    )
                    keys.extend(batch_keys)
                    if cursor == 0:
                        break
                
                namespace_stats[cache_type] = {
                    "key_count": len(keys),
                    "ttl": config.ttl,
                    "namespace": config.namespace
                }
            
            # Calculate hit rate
            total_requests = self.metrics["hits"] + self.metrics["misses"]
            hit_rate = (self.metrics["hits"] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                "performance_metrics": {
                    **self.metrics,
                    "hit_rate_percent": round(hit_rate, 2),
                    "total_requests": total_requests
                },
                "memory_usage": {
                    "used_memory": redis_info.get("used_memory_human", "0B"),
                    "used_memory_peak": redis_info.get("used_memory_peak_human", "0B"),
                    "memory_fragmentation_ratio": redis_info.get("mem_fragmentation_ratio", 0)
                },
                "namespace_statistics": namespace_stats,
                "configuration_summary": {
                    cache_type: {
                        "ttl": config.ttl,
                        "auto_refresh": config.auto_refresh,
                        "compression": config.compression
                    }
                    for cache_type, config in self.cache_configs.items()
                }
            }
            
        except Exception as e:
            logger.error("Failed to get cache stats", error=str(e))
            return {
                "error": "Failed to retrieve cache statistics",
                "performance_metrics": self.metrics
            }
    
    async def cleanup_expired(self) -> int:
        """Clean up expired cache entries (Redis handles this automatically, but useful for stats)"""
        try:
            cleaned = 0
            for cache_type, config in self.cache_configs.items():
                pattern = f"{config.namespace}:*"
                keys = []
                cursor = 0
                
                while True:
                    cursor, batch_keys = await self.redis.scan(
                        cursor=cursor,
                        match=pattern,
                        count=100
                    )
                    
                    # Check TTL for each key
                    for key in batch_keys:
                        ttl = await self.redis.ttl(key)
                        if ttl == -2:  # Key doesn't exist
                            cleaned += 1
                    
                    if cursor == 0:
                        break
            
            logger.info("Cache cleanup completed", cleaned_keys=cleaned)
            return cleaned
            
        except Exception as e:
            logger.error("Cache cleanup error", error=str(e))
            return 0


# Global advanced cache instance
advanced_cache = AdvancedCacheService()

# Convenient decorator for caching function results
def cache_result(cache_type: str, key_prefix: str = "", ttl: Optional[int] = None):
    """Decorator to cache function results"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_parts = [key_prefix or func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(key_parts)
            
            # Try to get from cache first
            cached_result = await advanced_cache.get(cache_type, cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await advanced_cache.set(cache_type, cache_key, result, ttl_override=ttl)
            return result
        
        def sync_wrapper(*args, **kwargs):
            # For synchronous functions, would need sync Redis client
            return func(*args, **kwargs)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator