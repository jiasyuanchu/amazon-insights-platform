"""
Rate limiting implementation for Amazon Insights Platform
"""
import time
import json
from typing import Dict, Optional, Tuple, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import structlog
import asyncio
import hashlib

from src.app.core.config import settings
from src.app.core.redis import get_redis_client

logger = structlog.get_logger()


@dataclass
class RateLimitRule:
    """Rate limit rule configuration"""
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    burst_limit: Optional[int] = None  # Max requests in burst
    burst_window: Optional[int] = 10   # Burst window in seconds
    

@dataclass  
class RateLimitResult:
    """Rate limit check result"""
    allowed: bool
    remaining: int
    reset_time: int
    retry_after: Optional[int] = None


class RateLimiter:
    """Redis-based rate limiter with sliding window and token bucket algorithms"""
    
    def __init__(self):
        self.redis = None
        self.default_rules = {
            "default": RateLimitRule(
                requests_per_minute=settings.RATE_LIMIT_PER_MINUTE,
                requests_per_hour=settings.RATE_LIMIT_PER_HOUR,
                requests_per_day=1440,  # 24 * 60 requests per day
                burst_limit=10,
                burst_window=10
            ),
            "auth": RateLimitRule(
                requests_per_minute=5,
                requests_per_hour=30,
                requests_per_day=100,
                burst_limit=3,
                burst_window=60
            ),
            "api_heavy": RateLimitRule(
                requests_per_minute=20,
                requests_per_hour=200,
                requests_per_day=1000,
                burst_limit=5,
                burst_window=30
            ),
            "ai_analysis": RateLimitRule(
                requests_per_minute=10,
                requests_per_hour=100,
                requests_per_day=500,
                burst_limit=2,
                burst_window=60
            )
        }
    
    async def get_redis(self):
        """Get Redis client"""
        if not self.redis:
            self.redis = await get_redis_client()
        return self.redis
    
    def _get_client_identifier(self, request: Request) -> str:
        """Get unique identifier for the client"""
        # Try to get user ID from request state (set by auth middleware)
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            return f"user:{user_id}"
        
        # Use IP address as fallback
        client_ip = self._get_client_ip(request)
        return f"ip:{client_ip}"
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request"""
        # Check for forwarded headers (reverse proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"
    
    def _generate_key(
        self, 
        identifier: str, 
        rule_name: str, 
        window: str
    ) -> str:
        """Generate Redis key for rate limiting"""
        return f"ratelimit:{rule_name}:{window}:{identifier}"
    
    async def _check_sliding_window(
        self,
        identifier: str,
        rule: RateLimitRule,
        rule_name: str
    ) -> Tuple[bool, Dict[str, int]]:
        """Check rate limits using sliding window algorithm"""
        redis = await self.get_redis()
        current_time = int(time.time())
        
        # Define time windows
        windows = {
            "minute": (60, rule.requests_per_minute),
            "hour": (3600, rule.requests_per_hour), 
            "day": (86400, rule.requests_per_day)
        }
        
        # Check each window
        remaining = {}
        for window_name, (window_size, limit) in windows.items():
            key = self._generate_key(identifier, rule_name, window_name)
            window_start = current_time - window_size
            
            # Remove old entries
            await redis.zremrangebyscore(key, 0, window_start)
            
            # Count current requests in window
            current_count = await redis.zcard(key)
            
            # Check if limit exceeded
            if current_count >= limit:
                remaining[window_name] = 0
                return False, remaining
            
            remaining[window_name] = limit - current_count
            
            # Add current request with score as timestamp
            await redis.zadd(key, {str(current_time): current_time})
            
            # Set expiry for cleanup
            await redis.expire(key, window_size)
        
        return True, remaining
    
    async def _check_burst_limit(
        self,
        identifier: str,
        rule: RateLimitRule,
        rule_name: str
    ) -> Tuple[bool, Optional[int]]:
        """Check burst limit using token bucket algorithm"""
        if not rule.burst_limit:
            return True, None
        
        redis = await self.get_redis()
        current_time = time.time()
        
        # Token bucket key
        bucket_key = f"burst:{rule_name}:{identifier}"
        
        # Get current bucket state
        bucket_data = await redis.get(bucket_key)
        
        if bucket_data:
            bucket_info = json.loads(bucket_data)
            tokens = bucket_info["tokens"]
            last_update = bucket_info["last_update"]
        else:
            # Initialize bucket
            tokens = rule.burst_limit
            last_update = current_time
        
        # Calculate tokens to add based on time elapsed
        time_elapsed = current_time - last_update
        tokens_to_add = int(time_elapsed / rule.burst_window * rule.burst_limit)
        tokens = min(rule.burst_limit, tokens + tokens_to_add)
        
        # Check if request can be processed
        if tokens <= 0:
            retry_after = int(rule.burst_window - (current_time % rule.burst_window))
            return False, retry_after
        
        # Consume token
        tokens -= 1
        
        # Update bucket state
        bucket_info = {
            "tokens": tokens,
            "last_update": current_time
        }
        await redis.set(
            bucket_key, 
            json.dumps(bucket_info), 
            ex=rule.burst_window * 2
        )
        
        return True, None
    
    async def check_rate_limit(
        self,
        request: Request,
        rule_name: str = "default"
    ) -> RateLimitResult:
        """Check if request is allowed under rate limits"""
        try:
            # Get rule configuration
            rule = self.default_rules.get(rule_name, self.default_rules["default"])
            
            # Get client identifier
            identifier = self._get_client_identifier(request)
            
            # Check sliding window limits
            window_allowed, remaining_counts = await self._check_sliding_window(
                identifier, rule, rule_name
            )
            
            if not window_allowed:
                logger.warning(
                    "Rate limit exceeded - sliding window",
                    identifier=identifier,
                    rule=rule_name,
                    remaining=remaining_counts
                )
                return RateLimitResult(
                    allowed=False,
                    remaining=min(remaining_counts.values()),
                    reset_time=int(time.time()) + 60,  # Reset in 1 minute
                    retry_after=60
                )
            
            # Check burst limits
            burst_allowed, retry_after = await self._check_burst_limit(
                identifier, rule, rule_name
            )
            
            if not burst_allowed:
                logger.warning(
                    "Rate limit exceeded - burst limit",
                    identifier=identifier,
                    rule=rule_name,
                    retry_after=retry_after
                )
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=int(time.time()) + retry_after,
                    retry_after=retry_after
                )
            
            # Request allowed
            return RateLimitResult(
                allowed=True,
                remaining=min(remaining_counts.values()),
                reset_time=int(time.time()) + 60
            )
            
        except Exception as e:
            logger.error(
                "Rate limit check failed",
                error=str(e),
                identifier=self._get_client_identifier(request)
            )
            # Fail open - allow request if rate limiter fails
            return RateLimitResult(
                allowed=True,
                remaining=100,
                reset_time=int(time.time()) + 60
            )
    
    async def get_rate_limit_status(
        self,
        request: Request,
        rule_name: str = "default"
    ) -> Dict[str, Union[int, str]]:
        """Get current rate limit status for client"""
        try:
            redis = await self.get_redis()
            rule = self.default_rules.get(rule_name, self.default_rules["default"])
            identifier = self._get_client_identifier(request)
            current_time = int(time.time())
            
            status = {
                "identifier": identifier,
                "rule": rule_name,
                "current_time": current_time
            }
            
            # Check each window
            for window_name, (window_size, limit) in [
                ("minute", (60, rule.requests_per_minute)),
                ("hour", (3600, rule.requests_per_hour)),
                ("day", (86400, rule.requests_per_day))
            ]:
                key = self._generate_key(identifier, rule_name, window_name)
                window_start = current_time - window_size
                
                # Clean old entries
                await redis.zremrangebyscore(key, 0, window_start)
                
                # Count current requests
                current_count = await redis.zcard(key)
                
                status[f"{window_name}_limit"] = limit
                status[f"{window_name}_used"] = current_count
                status[f"{window_name}_remaining"] = limit - current_count
                status[f"{window_name}_reset"] = current_time + window_size
            
            return status
            
        except Exception as e:
            logger.error("Failed to get rate limit status", error=str(e))
            return {"error": "Unable to get rate limit status"}
    
    async def reset_rate_limit(
        self,
        request: Request,
        rule_name: str = "default"
    ) -> bool:
        """Reset rate limits for a client (admin function)"""
        try:
            redis = await self.get_redis()
            identifier = self._get_client_identifier(request)
            
            # Delete all rate limit keys for this client
            pattern = f"ratelimit:{rule_name}:*:{identifier}"
            keys = await redis.keys(pattern)
            
            if keys:
                await redis.delete(*keys)
            
            # Delete burst limit key
            burst_key = f"burst:{rule_name}:{identifier}"
            await redis.delete(burst_key)
            
            logger.info(
                "Rate limits reset",
                identifier=identifier,
                rule=rule_name
            )
            
            return True
            
        except Exception as e:
            logger.error("Failed to reset rate limits", error=str(e))
            return False


# Global rate limiter instance
rate_limiter = RateLimiter()


async def rate_limit_middleware(request: Request, call_next):
    """FastAPI middleware for rate limiting"""
    
    # Skip rate limiting for health checks and metrics
    if request.url.path in ["/health", "/metrics", "/api/v1/health/"]:
        return await call_next(request)
    
    # Determine rate limit rule based on endpoint
    rule_name = "default"
    path = request.url.path
    
    if "/auth/" in path:
        rule_name = "auth"
    elif any(endpoint in path for endpoint in [
        "/competitors/analyze", 
        "/products/update-metrics",
        "/competitors/discover"
    ]):
        rule_name = "api_heavy"
    elif any(endpoint in path for endpoint in [
        "/intelligence-report",
        "/ai-analysis",
        "/openai"
    ]):
        rule_name = "ai_analysis"
    
    # Check rate limits
    result = await rate_limiter.check_rate_limit(request, rule_name)
    
    if not result.allowed:
        # Rate limit exceeded
        headers = {
            "X-RateLimit-Limit": str(
                rate_limiter.default_rules[rule_name].requests_per_minute
            ),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(result.reset_time),
        }
        
        if result.retry_after:
            headers["Retry-After"] = str(result.retry_after)
        
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": "Rate limit exceeded",
                "error_code": "RATE_LIMIT_EXCEEDED",
                "retry_after": result.retry_after,
                "reset_time": result.reset_time
            },
            headers=headers
        )
    
    # Process request
    response = await call_next(request)
    
    # Add rate limit headers to response
    response.headers["X-RateLimit-Limit"] = str(
        rate_limiter.default_rules[rule_name].requests_per_minute
    )
    response.headers["X-RateLimit-Remaining"] = str(result.remaining)
    response.headers["X-RateLimit-Reset"] = str(result.reset_time)
    
    return response


def create_rate_limit_decorator(rule_name: str = "default"):
    """Create a rate limit decorator for specific endpoints"""
    
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            # Check rate limits
            result = await rate_limiter.check_rate_limit(request, rule_name)
            
            if not result.allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded",
                    headers={
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(result.reset_time),
                        "Retry-After": str(result.retry_after or 60)
                    }
                )
            
            # Add rate limit info to request state
            request.state.rate_limit_remaining = result.remaining
            request.state.rate_limit_reset = result.reset_time
            
            return await func(request, *args, **kwargs)
        
        return wrapper
    return decorator


# Decorator instances for different rules
rate_limit_default = create_rate_limit_decorator("default")
rate_limit_auth = create_rate_limit_decorator("auth")
rate_limit_heavy = create_rate_limit_decorator("api_heavy")
rate_limit_ai = create_rate_limit_decorator("ai_analysis")


__all__ = [
    "RateLimitRule",
    "RateLimitResult", 
    "RateLimiter",
    "rate_limiter",
    "rate_limit_middleware",
    "rate_limit_default",
    "rate_limit_auth", 
    "rate_limit_heavy",
    "rate_limit_ai"
]