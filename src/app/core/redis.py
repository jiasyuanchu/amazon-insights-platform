from typing import Optional, Any
import json
import redis.asyncio as redis
from src.app.core.config import settings
import structlog

logger = structlog.get_logger()


class RedisClient:
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
    
    async def connect(self) -> None:
        try:
            self.redis_client = redis.from_url(
                str(settings.REDIS_URL),
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                decode_responses=True,
            )
            await self.redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            raise
    
    async def disconnect(self) -> None:
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")
    
    async def get(self, key: str) -> Optional[Any]:
        if not self.redis_client:
            return None
        
        try:
            value = await self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error("Redis get error", key=key, error=str(e))
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        expire: Optional[int] = None
    ) -> bool:
        if not self.redis_client:
            return False
        
        try:
            serialized = json.dumps(value)
            if expire:
                await self.redis_client.setex(key, expire, serialized)
            else:
                await self.redis_client.set(key, serialized)
            return True
        except Exception as e:
            logger.error("Redis set error", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        if not self.redis_client:
            return False
        
        try:
            result = await self.redis_client.delete(key)
            return bool(result)
        except Exception as e:
            logger.error("Redis delete error", key=key, error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        if not self.redis_client:
            return False
        
        try:
            return bool(await self.redis_client.exists(key))
        except Exception as e:
            logger.error("Redis exists error", key=key, error=str(e))
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        if not self.redis_client:
            return None
        
        try:
            return await self.redis_client.incrby(key, amount)
        except Exception as e:
            logger.error("Redis increment error", key=key, error=str(e))
            return None
    
    async def expire(self, key: str, seconds: int) -> bool:
        if not self.redis_client:
            return False
        
        try:
            return bool(await self.redis_client.expire(key, seconds))
        except Exception as e:
            logger.error("Redis expire error", key=key, error=str(e))
            return False


# Global Redis client instance
redis_client = RedisClient()


async def get_redis() -> RedisClient:
    return redis_client