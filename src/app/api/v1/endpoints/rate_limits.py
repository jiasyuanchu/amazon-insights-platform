"""
Rate limiting management endpoints
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
import structlog

from src.app.core.rate_limiter import rate_limiter
from src.app.core.security import get_current_active_user, require_permissions
from src.app.models.user import User

logger = structlog.get_logger()
router = APIRouter()


class RateLimitStatus(BaseModel):
    """Rate limit status response model"""
    identifier: str
    rule: str
    current_time: int
    minute_limit: int
    minute_used: int
    minute_remaining: int
    minute_reset: int
    hour_limit: int
    hour_used: int
    hour_remaining: int
    hour_reset: int
    day_limit: int
    day_used: int
    day_remaining: int
    day_reset: int


class RateLimitResetRequest(BaseModel):
    """Rate limit reset request model"""
    rule_name: str = "default"
    reason: str


@router.get(
    "/status", 
    response_model=Dict[str, Any],
    summary="Get rate limit status",
    description="Get current rate limit status for the requesting client"
)
async def get_rate_limit_status(
    request: Request,
    rule_name: str = "default",
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current rate limit status for the authenticated user.
    
    Shows remaining requests for different time windows (minute, hour, day).
    """
    try:
        # Store user ID in request state for rate limiter
        request.state.user_id = current_user.id
        
        status = await rate_limiter.get_rate_limit_status(request, rule_name)
        
        logger.info(
            "Rate limit status requested",
            user_id=current_user.id,
            rule=rule_name,
            status=status
        )
        
        return {
            "status": "success",
            "data": status,
            "user_id": current_user.id,
            "rule_applied": rule_name
        }
        
    except Exception as e:
        logger.error(
            "Failed to get rate limit status",
            user_id=current_user.id,
            rule=rule_name,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve rate limit status"
        )


@router.get(
    "/rules",
    response_model=Dict[str, Any],
    summary="Get rate limit rules",
    description="Get all available rate limit rules and their configurations"
)
async def get_rate_limit_rules(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all rate limit rules and their configurations.
    
    This endpoint helps clients understand the rate limits they're subject to.
    """
    try:
        rules_info = {}
        
        for rule_name, rule in rate_limiter.default_rules.items():
            rules_info[rule_name] = {
                "requests_per_minute": rule.requests_per_minute,
                "requests_per_hour": rule.requests_per_hour,
                "requests_per_day": rule.requests_per_day,
                "burst_limit": rule.burst_limit,
                "burst_window": rule.burst_window,
                "description": _get_rule_description(rule_name)
            }
        
        logger.info(
            "Rate limit rules requested",
            user_id=current_user.id
        )
        
        return {
            "status": "success",
            "rules": rules_info,
            "user_id": current_user.id
        }
        
    except Exception as e:
        logger.error(
            "Failed to get rate limit rules",
            user_id=current_user.id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve rate limit rules"
        )


@router.post(
    "/reset",
    response_model=Dict[str, Any],
    summary="Reset rate limits",
    description="Reset rate limits for the current user (requires admin permissions)"
)
async def reset_rate_limits(
    request: Request,
    reset_request: RateLimitResetRequest,
    current_user: User = Depends(require_permissions(["admin"]))
):
    """
    Reset rate limits for the current user.
    
    This is an administrative function that requires special permissions.
    Should be used sparingly and only for legitimate reasons.
    """
    try:
        # Store user ID in request state
        request.state.user_id = current_user.id
        
        # Reset rate limits
        success = await rate_limiter.reset_rate_limit(
            request, 
            reset_request.rule_name
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reset rate limits"
            )
        
        logger.info(
            "Rate limits reset",
            user_id=current_user.id,
            rule=reset_request.rule_name,
            reason=reset_request.reason,
            admin_user=current_user.username
        )
        
        return {
            "status": "success",
            "message": "Rate limits have been reset",
            "rule": reset_request.rule_name,
            "reset_by": current_user.username,
            "reason": reset_request.reason
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to reset rate limits",
            user_id=current_user.id,
            rule=reset_request.rule_name,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to reset rate limits"
        )


@router.get(
    "/health",
    response_model=Dict[str, Any],
    summary="Rate limiter health check",
    description="Check if the rate limiter is working properly"
)
async def rate_limiter_health_check(
    current_user: User = Depends(get_current_active_user)
):
    """
    Health check for the rate limiting system.
    
    Verifies that Redis connection is working and rate limiter is functional.
    """
    try:
        # Test Redis connection
        redis_client = await rate_limiter.get_redis()
        await redis_client.ping()
        
        # Test basic rate limit functionality
        test_key = f"health_check:{current_user.id}"
        await redis_client.set(test_key, "test", ex=10)
        test_value = await redis_client.get(test_key)
        await redis_client.delete(test_key)
        
        if test_value != "test":
            raise Exception("Redis test operation failed")
        
        logger.info(
            "Rate limiter health check passed",
            user_id=current_user.id
        )
        
        return {
            "status": "healthy",
            "message": "Rate limiter is functioning properly",
            "redis_connected": True,
            "timestamp": rate_limiter.redis is not None
        }
        
    except Exception as e:
        logger.error(
            "Rate limiter health check failed",
            user_id=current_user.id,
            error=str(e)
        )
        
        return {
            "status": "unhealthy",
            "message": "Rate limiter is not functioning properly",
            "redis_connected": False,
            "error": str(e)
        }


@router.get(
    "/analytics",
    response_model=Dict[str, Any],
    summary="Rate limit analytics",
    description="Get rate limiting analytics and statistics (admin only)"
)
async def get_rate_limit_analytics(
    current_user: User = Depends(require_permissions(["admin"]))
):
    """
    Get rate limiting analytics and statistics.
    
    Provides insights into rate limiting patterns, top consumers, etc.
    Only available to administrators.
    """
    try:
        redis_client = await rate_limiter.get_redis()
        
        # Get basic statistics
        total_keys = len(await redis_client.keys("ratelimit:*"))
        burst_keys = len(await redis_client.keys("burst:*"))
        
        # Get memory usage (approximate)
        memory_info = await redis_client.info('memory')
        used_memory = memory_info.get('used_memory_human', 'unknown')
        
        # Get sample of active rate limits
        sample_keys = await redis_client.keys("ratelimit:*:minute:*")
        active_limits = len(sample_keys)
        
        analytics = {
            "total_rate_limit_keys": total_keys,
            "burst_limit_keys": burst_keys,
            "active_minute_limits": active_limits,
            "redis_memory_usage": used_memory,
            "available_rules": list(rate_limiter.default_rules.keys()),
            "rule_configurations": {
                name: {
                    "per_minute": rule.requests_per_minute,
                    "per_hour": rule.requests_per_hour,
                    "per_day": rule.requests_per_day
                }
                for name, rule in rate_limiter.default_rules.items()
            }
        }
        
        logger.info(
            "Rate limit analytics requested",
            admin_user=current_user.username,
            analytics_summary=analytics
        )
        
        return {
            "status": "success",
            "analytics": analytics,
            "generated_by": current_user.username
        }
        
    except Exception as e:
        logger.error(
            "Failed to get rate limit analytics",
            admin_user=current_user.username,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve rate limit analytics"
        )


def _get_rule_description(rule_name: str) -> str:
    """Get human-readable description for rate limit rule"""
    descriptions = {
        "default": "General API endpoints with standard rate limits",
        "auth": "Authentication endpoints with strict limits to prevent brute force",
        "api_heavy": "Resource-intensive endpoints like competitor analysis",
        "ai_analysis": "AI-powered analysis endpoints with conservative limits"
    }
    
    return descriptions.get(rule_name, "Custom rate limit rule")