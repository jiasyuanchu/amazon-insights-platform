from contextlib import asynccontextmanager
from fastapi import FastAPI
from prometheus_client import make_asgi_app
import structlog
from src.app.core.config import settings
from src.app.core.database import init_db, close_db
from src.app.core.redis import redis_client
from src.app.core.middleware import setup_security_middleware
from src.app.api.v1.api import api_router

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer() if settings.LOG_FORMAT == "json" else structlog.dev.ConsoleRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up", app_name=settings.APP_NAME, version=settings.APP_VERSION)
    await init_db()
    await redis_client.connect()
    
    yield
    
    # Shutdown
    logger.info("Shutting down")
    await redis_client.disconnect()
    await close_db()


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description="""
        # Amazon Business Intelligence Platform API
        
        A comprehensive API for Amazon sellers to track products, analyze competitors, and gain market insights.
        
        ## Features
        
        ### 🎯 Product Management
        - **Product Tracking**: Monitor product performance metrics (BSR, price, ratings)
        - **Price History**: Track pricing changes over time
        - **Alert System**: Get notified of significant changes
        
        ### 🔍 Competitive Intelligence
        - **Competitor Discovery**: Automatically find similar products
        - **Competitive Analysis**: Compare performance metrics with competitors
        - **Market Positioning**: Understand your position in the market
        - **AI-Powered Insights**: Get strategic recommendations from advanced AI analysis
        
        ### 📊 Analytics & Reports
        - **Performance Dashboards**: Visualize product metrics
        - **Market Trends**: Track category and market trends
        - **Intelligence Reports**: Comprehensive competitive intelligence reports
        
        ### ⚡ Advanced Features
        - **Real-time Updates**: Background tasks keep data fresh
        - **Smart Caching**: Optimized performance with intelligent caching
        - **Rate Limiting**: Built-in API protection
        - **Structured Logging**: Complete audit trail
        
        ## Authentication
        
        This API uses JWT Bearer token authentication. 
        
        1. Register a new user account with `POST /auth/register`
        2. Login to get an access token with `POST /auth/token`  
        3. Include the token in requests: `Authorization: Bearer <token>`
        
        ## Rate Limits
        
        - **Authentication endpoints**: 5 requests per minute
        - **General API endpoints**: 100 requests per minute
        - **Data-intensive endpoints**: 20 requests per minute
        
        ## Getting Started
        
        1. 📝 **Register**: Create your account
        2. 🔑 **Authenticate**: Get your access token
        3. 📦 **Add Products**: Start tracking your products
        4. 🔍 **Discover Competitors**: Find competing products
        5. 📊 **Analyze**: Generate insights and reports
        """,
        version=settings.APP_VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url=f"{settings.API_V1_STR}/docs",
        redoc_url=f"{settings.API_V1_STR}/redoc",
        lifespan=lifespan,
        contact={
            "name": "Amazon Insights Platform",
            "url": "https://github.com/your-repo/amazon-insights-platform",
            "email": "support@amazon-insights.com",
        },
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT",
        },
        openapi_tags=[
            {
                "name": "Authentication",
                "description": "User authentication and authorization endpoints",
            },
            {
                "name": "Users", 
                "description": "User management operations",
            },
            {
                "name": "Products",
                "description": "Product tracking and management operations",
            },
            {
                "name": "Competitors",
                "description": "Competitive intelligence and analysis operations",
            },
            {
                "name": "Health",
                "description": "System health and monitoring endpoints",
            },
        ],
    )

    # Set up security middleware (includes CORS, rate limiting, security headers, etc.)
    setup_security_middleware(app)

    # Add Prometheus metrics endpoint
    if settings.PROMETHEUS_ENABLED:
        metrics_app = make_asgi_app()
        app.mount("/metrics", metrics_app)

    # Include API router
    app.include_router(api_router, prefix=settings.API_V1_STR)

    @app.get("/")
    async def root():
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "docs": f"{settings.API_V1_STR}/docs",
        }

    return app


app = create_application()