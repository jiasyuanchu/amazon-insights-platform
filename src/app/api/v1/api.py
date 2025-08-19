from fastapi import APIRouter
from src.app.api.v1.endpoints import auth, users, products, health, competitors, cache_management, rate_limits

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(competitors.router, prefix="/competitors", tags=["competitors"])
api_router.include_router(cache_management.router, prefix="/cache", tags=["cache"])
api_router.include_router(rate_limits.router, prefix="/rate-limits", tags=["rate-limits"])