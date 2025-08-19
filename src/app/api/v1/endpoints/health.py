from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis
from src.app.core.database import get_db
from src.app.core.config import settings
import structlog

router = APIRouter()
logger = structlog.get_logger()


@router.get("/")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    checks = {
        "database": False,
        "redis": False,
    }
    
    # Check database connection
    try:
        result = await db.execute(text("SELECT 1"))
        checks["database"] = result.scalar() == 1
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
    
    # Check Redis connection
    try:
        redis_client = redis.from_url(str(settings.REDIS_URL))
        await redis_client.ping()
        checks["redis"] = True
        await redis_client.close()
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
    
    all_healthy = all(checks.values())
    
    return {
        "status": "ready" if all_healthy else "not ready",
        "checks": checks,
    }


@router.get("/live")
async def liveness_check():
    return {"status": "alive"}