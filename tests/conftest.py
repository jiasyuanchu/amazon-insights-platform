"""Test configuration and fixtures"""

import pytest
import os
import asyncio
from unittest.mock import AsyncMock, Mock
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Set test environment variables before importing app
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/test"  # Mock postgres URL
os.environ["REDIS_URL"] = "redis://localhost:6379/15"  # Test database
os.environ["CELERY_BROKER_URL"] = "redis://localhost:6379/15"
os.environ["CELERY_RESULT_BACKEND"] = "redis://localhost:6379/15"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["TESTING"] = "true"


# Remove custom event_loop fixture to avoid deprecation warnings
# pytest-asyncio handles this automatically with asyncio_mode = "auto"


@pytest.fixture
def mock_db():
    """Mock database session"""
    session = AsyncMock(spec=AsyncSession)
    
    # Mock common database operations
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock() 
    session.close = AsyncMock()
    session.add = Mock()
    session.refresh = AsyncMock()
    
    return session


@pytest.fixture  
def mock_redis():
    """Mock Redis client"""
    redis_client = AsyncMock()
    
    # Mock common Redis operations
    redis_client.get = AsyncMock()
    redis_client.set = AsyncMock()
    redis_client.setex = AsyncMock()
    redis_client.delete = AsyncMock()
    redis_client.scan = AsyncMock()
    redis_client.mget = AsyncMock()
    redis_client.pipeline = Mock()
    redis_client.pipeline.return_value = AsyncMock()
    redis_client.info = AsyncMock()
    
    return redis_client


@pytest.fixture
def mock_user():
    """Mock user object"""
    user = Mock()
    user.id = 1
    user.username = "testuser"
    user.email = "test@example.com"
    user.is_active = True
    user.full_name = "Test User"
    return user


@pytest.fixture
def mock_product():
    """Mock product object"""
    product = Mock()
    product.id = 1
    product.asin = "B08TEST123"
    product.title = "Test Product"
    product.brand = "TestBrand"
    product.category = "Electronics"
    product.current_price = 29.99
    product.current_rating = 4.5
    product.current_bsr = 1000
    product.current_review_count = 500
    product.user_id = 1
    product.is_active = True
    return product


@pytest.fixture
def mock_competitor():
    """Mock competitor object"""
    competitor = Mock()
    competitor.id = 2
    competitor.main_product_id = 1
    competitor.competitor_asin = "B08COMP123"
    competitor.title = "Competitor Product"
    competitor.current_price = 25.99
    competitor.current_rating = 4.2
    competitor.current_bsr = 1200
    competitor.similarity_score = 0.85
    competitor.is_direct_competitor = 1
    return competitor


@pytest.fixture
def test_client():
    """Test client for API endpoints"""
    from src.app.main import app
    with TestClient(app) as client:
        yield client


@pytest.fixture
async def async_client():
    """Async test client for API endpoints"""
    from src.app.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


# Mock external dependencies
@pytest.fixture(autouse=True)
def mock_external_dependencies(monkeypatch):
    """Auto-mock external dependencies"""
    
    # Mock database engine creation
    mock_engine = AsyncMock()
    monkeypatch.setattr("src.app.core.database.create_async_engine", lambda *args, **kwargs: mock_engine)
    
    # Mock Redis client creation
    mock_redis = AsyncMock()
    monkeypatch.setattr("src.app.core.redis.redis.from_url", lambda *args, **kwargs: mock_redis)
    
    # Mock Redis pool
    monkeypatch.setattr("src.app.core.redis.redis_client", mock_redis)
    
    # Mock database session factory
    mock_session_factory = AsyncMock()
    monkeypatch.setattr("src.app.core.database.AsyncSessionLocal", mock_session_factory)
    
    # Mock Celery
    monkeypatch.setattr("src.app.tasks.celery_app.celery_app", AsyncMock())
    
    # Mock OpenAI client
    monkeypatch.setenv("OPENAI_API_KEY", "")
    
    # Mock Firecrawl client
    monkeypatch.setenv("FIRECRAWL_API_KEY", "")


@pytest.fixture
def sample_api_response():
    """Sample API response data"""
    return {
        "success": True,
        "data": {
            "id": 1,
            "name": "Test Item",
            "value": 42
        },
        "timestamp": "2025-01-01T00:00:00Z"
    }


@pytest.fixture
def sample_cache_data():
    """Sample cache data for testing"""
    return {
        "key1": {"value": "data1", "timestamp": "2025-01-01T00:00:00Z"},
        "key2": {"value": "data2", "timestamp": "2025-01-01T01:00:00Z"},
        "key3": {"value": "data3", "timestamp": "2025-01-01T02:00:00Z"}
    }


@pytest.fixture
def sample_competitor_data():
    """Sample competitor analysis data"""
    return {
        "main_product": {
            "asin": "B08MAIN123",
            "title": "Main Product",
            "price": 50.0,
            "rating": 4.5,
            "bsr": 1000
        },
        "competitors": [
            {
                "asin": "B08COMP1",
                "title": "Competitor 1", 
                "price": 45.0,
                "rating": 4.2,
                "bsr": 1200,
                "similarity_score": 0.85
            },
            {
                "asin": "B08COMP2",
                "title": "Competitor 2",
                "price": 55.0,
                "rating": 4.7,
                "bsr": 800,
                "similarity_score": 0.78
            }
        ],
        "analysis": {
            "price_position": "competitive",
            "market_position": "strong",
            "advantages": ["higher_rating", "better_reviews"],
            "recommendations": ["monitor_pricing", "improve_features"]
        }
    }


# Pytest configuration
pytest_plugins = ["pytest_asyncio"]


@pytest.fixture
def anyio_backend():
    """Set anyio backend for async tests"""
    return "asyncio"