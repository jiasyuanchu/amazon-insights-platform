"""Cache management API endpoints"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from src.app.api.dependencies import get_current_user
from src.app.models import User
from src.app.services.advanced_cache import advanced_cache
from src.app.services.competitive_cache import competitive_cache
import structlog

router = APIRouter()
logger = structlog.get_logger()


@router.get("/stats", response_model=Dict[str, Any])
async def get_cache_statistics(
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive cache statistics"""
    try:
        # Get advanced cache stats
        advanced_stats = await advanced_cache.get_cache_stats()
        
        # Get competitive cache stats  
        competitive_stats = await competitive_cache.get_cache_stats()
        
        return {
            "advanced_cache": advanced_stats,
            "competitive_cache": competitive_stats,
            "timestamp": advanced_stats.get("timestamp", "unknown"),
            "cache_services": ["advanced_cache", "competitive_cache"]
        }
        
    except Exception as e:
        logger.error("Failed to get cache stats", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve cache statistics"
        )


@router.get("/performance", response_model=Dict[str, Any])  
async def get_cache_performance_metrics(
    current_user: User = Depends(get_current_user)
):
    """Get cache performance metrics"""
    try:
        stats = await advanced_cache.get_cache_stats()
        performance = stats.get("performance_metrics", {})
        
        # Calculate additional performance metrics
        total_requests = performance.get("total_requests", 0)
        hits = performance.get("hits", 0)
        misses = performance.get("misses", 0)
        
        if total_requests > 0:
            hit_ratio = hits / total_requests
            miss_ratio = misses / total_requests
        else:
            hit_ratio = miss_ratio = 0
        
        return {
            "hit_rate_percent": performance.get("hit_rate_percent", 0),
            "total_requests": total_requests,
            "cache_hits": hits,
            "cache_misses": misses,
            "hit_miss_ratio": hit_ratio / miss_ratio if miss_ratio > 0 else float('inf'),
            "cache_efficiency": "excellent" if hit_ratio > 0.8 else 
                               "good" if hit_ratio > 0.6 else 
                               "fair" if hit_ratio > 0.4 else "poor",
            "memory_usage": stats.get("memory_usage", {}),
            "recommendations": generate_cache_recommendations(hit_ratio, total_requests)
        }
        
    except Exception as e:
        logger.error("Failed to get cache performance", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve cache performance metrics"
        )


@router.delete("/invalidate/{cache_type}")
async def invalidate_cache_type(
    cache_type: str,
    pattern: Optional[str] = Query(None, description="Pattern to match for invalidation"),
    current_user: User = Depends(get_current_user)
):
    """Invalidate cache entries by type and optional pattern"""
    try:
        if pattern:
            deleted_count = await advanced_cache.invalidate_pattern(cache_type, pattern)
            message = f"Invalidated {deleted_count} cache entries matching pattern '{pattern}'"
        else:
            # Invalidate all entries of this type
            deleted_count = await advanced_cache.invalidate_pattern(cache_type, "*")
            message = f"Invalidated all {deleted_count} cache entries of type '{cache_type}'"
        
        logger.info("Cache invalidation", 
                   cache_type=cache_type, 
                   pattern=pattern,
                   deleted=deleted_count,
                   user_id=current_user.id)
        
        return {
            "message": message,
            "cache_type": cache_type,
            "pattern": pattern,
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        logger.error("Cache invalidation failed", 
                    error=str(e), 
                    cache_type=cache_type)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to invalidate cache type '{cache_type}'"
        )


@router.post("/preload/{cache_type}")
async def preload_cache(
    cache_type: str,
    keys: list,
    current_user: User = Depends(get_current_user)
):
    """Preload cache entries (would need background task implementation)"""
    # This would typically trigger background tasks to preload cache
    # For now, return a placeholder response
    
    logger.info("Cache preload requested",
               cache_type=cache_type,
               key_count=len(keys),
               user_id=current_user.id)
    
    return {
        "message": f"Cache preload initiated for {len(keys)} keys",
        "cache_type": cache_type,
        "status": "queued"
    }


@router.post("/cleanup")
async def cleanup_expired_cache(
    current_user: User = Depends(get_current_user)
):
    """Clean up expired cache entries"""
    try:
        cleaned_count = await advanced_cache.cleanup_expired()
        
        logger.info("Cache cleanup completed",
                   cleaned=cleaned_count,
                   user_id=current_user.id)
        
        return {
            "message": f"Cleaned up {cleaned_count} expired cache entries",
            "cleaned_count": cleaned_count
        }
        
    except Exception as e:
        logger.error("Cache cleanup failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to clean up expired cache entries"
        )


@router.get("/config")
async def get_cache_configuration(
    current_user: User = Depends(get_current_user)
):
    """Get cache configuration details"""
    try:
        stats = await advanced_cache.get_cache_stats()
        config = stats.get("configuration_summary", {})
        
        return {
            "cache_configurations": config,
            "namespace_statistics": stats.get("namespace_statistics", {}),
            "total_cache_types": len(config)
        }
        
    except Exception as e:
        logger.error("Failed to get cache config", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve cache configuration"
        )


def generate_cache_recommendations(hit_ratio: float, total_requests: int) -> list:
    """Generate cache optimization recommendations"""
    recommendations = []
    
    if hit_ratio < 0.6:
        recommendations.append("Consider increasing cache TTL for frequently accessed data")
        recommendations.append("Review cache invalidation patterns")
        
    if hit_ratio < 0.4:
        recommendations.append("Implement cache warming for critical data")
        recommendations.append("Review application caching strategy")
        
    if total_requests < 100:
        recommendations.append("Insufficient data for meaningful analysis - monitor longer")
    elif hit_ratio > 0.9:
        recommendations.append("Excellent cache performance - maintain current strategy")
        
    if not recommendations:
        recommendations.append("Cache performance is good - no immediate action needed")
        
    return recommendations