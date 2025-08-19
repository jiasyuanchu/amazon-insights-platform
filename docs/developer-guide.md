# Developer Guide - Amazon Insights Platform

A comprehensive guide for developers contributing to the Amazon Insights Platform.

## 📋 Table of Contents

- [Development Setup](#development-setup)
- [Architecture Overview](#architecture-overview)
- [Code Organization](#code-organization)
- [Development Workflow](#development-workflow)
- [Testing Guide](#testing-guide)
- [API Development](#api-development)
- [Database Operations](#database-operations)
- [Background Tasks](#background-tasks)
- [Performance Optimization](#performance-optimization)
- [Security Guidelines](#security-guidelines)
- [Deployment & CI/CD](#deployment--cicd)
- [Troubleshooting](#troubleshooting)

## 🚀 Development Setup

### Prerequisites

```bash
# System requirements
- Python 3.11+
- Docker & Docker Compose
- Git
- Pre-commit hooks

# Recommended tools
- PyCharm or VS Code
- Postman or Insomnia (API testing)
- pgAdmin (PostgreSQL management)
- Redis Insight (Redis management)
```

### Local Environment Setup

```bash
# 1. Clone repository
git clone https://github.com/your-username/amazon-insights-platform.git
cd amazon-insights-platform

# 2. Create virtual environment (optional)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate     # Windows

# 3. Install development dependencies
pip install -r requirements-dev.txt

# 4. Setup pre-commit hooks
pre-commit install

# 5. Copy environment template
cp .env.example .env

# 6. Start development services
docker-compose up -d

# 7. Run database migrations
docker exec amazon_insights_api alembic upgrade head

# 8. Create demo data (optional)
docker exec -it amazon_insights_api python scripts/create_demo_data.py

# 9. Verify setup
curl http://localhost:8000/api/v1/health/
```

### IDE Configuration

#### VS Code Settings (.vscode/settings.json)
```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "python.formatting.provider": "black",
  "python.sortImports.args": ["--profile", "black"],
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests/"],
  "files.exclude": {
    "**/__pycache__": true,
    "**/.pytest_cache": true,
    "**/htmlcov": true,
    "**/.coverage": true
  }
}
```

#### PyCharm Configuration
1. Set Python interpreter: File → Settings → Project → Python Interpreter
2. Enable Black formatter: Settings → Tools → External Tools
3. Configure pytest: Settings → Tools → Python Integrated Tools
4. Setup code inspections: Settings → Editor → Inspections

## 🏗️ Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Layer                          │
│  Frontend (Future) │ API Clients │ Third-party Integrations │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────┐
│                    API Gateway                             │
│              FastAPI + Pydantic                           │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────┐
│                 Business Logic                             │
├─────────────┬─────────────┬─────────────┬─────────────────────┤
│ Auth        │ Products    │ Competitors │ Analytics           │
│ Service     │ Service     │ Service     │ Service             │
└─────────────┴─────────────┴─────────────┴─────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────┐
│              Background Processing                         │
├─────────────┬─────────────┬─────────────┬─────────────────────┤
│ Celery      │ Redis       │ Scheduled   │ Event-driven        │
│ Workers     │ Queue       │ Tasks       │ Tasks               │
└─────────────┴─────────────┴─────────────┴─────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────┐
│                   Data Layer                               │
├─────────────┬─────────────┬─────────────┬─────────────────────┤
│ PostgreSQL  │ Redis       │ External    │ File System         │
│ Database    │ Cache       │ APIs        │ Storage             │
└─────────────┴─────────────┴─────────────┴─────────────────────┘
```

### Core Technologies

- **FastAPI**: Modern, fast web framework for building APIs
- **SQLAlchemy**: Python SQL toolkit and ORM
- **Alembic**: Database migration tool
- **Celery**: Distributed task queue
- **Redis**: In-memory data structure store (caching & queues)
- **Pydantic**: Data validation using Python type annotations
- **Pytest**: Testing framework
- **Docker**: Containerization platform

## 📁 Code Organization

### Directory Structure

```
src/app/
├── api/                    # API layer
│   ├── dependencies.py     # FastAPI dependencies
│   └── v1/
│       ├── api.py         # API router aggregation
│       └── endpoints/     # API endpoints
│           ├── auth.py
│           ├── products.py
│           └── competitors.py
├── core/                  # Core utilities
│   ├── config.py         # Configuration management
│   ├── database.py       # Database connection
│   └── redis.py          # Redis connection
├── models/               # SQLAlchemy models
│   ├── base.py          # Base model class
│   ├── user.py
│   ├── product.py
│   └── competitor.py
├── schemas/             # Pydantic schemas
│   ├── auth.py
│   ├── product.py
│   └── competitor.py
├── services/           # Business logic
│   ├── product_service.py
│   ├── competitor_service.py
│   └── openai_service.py
├── tasks/             # Celery background tasks
│   ├── celery_app.py
│   ├── product_tasks.py
│   └── competitor_tasks.py
└── main.py           # FastAPI application factory
```

### Naming Conventions

#### Files and Directories
```python
# Snake case for files and directories
user_service.py
competitor_analysis.py
product_models/

# Kebab case for API endpoints
/api/v1/competitive-analysis
/api/v1/price-history
```

#### Python Code
```python
# Classes: PascalCase
class ProductService:
    pass

class CompetitorAnalysis:
    pass

# Functions and variables: snake_case
def get_product_metrics():
    pass

def analyze_competitor_data():
    pass

user_id = 1
competitor_data = {}

# Constants: UPPER_SNAKE_CASE
DEFAULT_CACHE_TTL = 3600
MAX_COMPETITORS = 10
```

#### Database
```sql
-- Tables: snake_case
users
products
competitor_analysis

-- Columns: snake_case
user_id
created_at
competitor_asin
```

## 🔄 Development Workflow

### Git Workflow

#### Branch Naming
```bash
# Feature branches
feature/add-competitor-analysis
feature/improve-caching-system

# Bug fixes
fix/product-update-issue
fix/authentication-bug

# Hot fixes
hotfix/critical-security-patch

# Release branches
release/v1.0.0
```

#### Commit Message Format
```
type(scope): description

body (optional)

footer (optional)

Examples:
feat(api): add competitor discovery endpoint
fix(db): resolve connection pool timeout
docs(readme): update installation instructions
test(services): add unit tests for product service
refactor(auth): simplify JWT token validation
perf(cache): optimize Redis cache performance
```

### Development Process

1. **Create Feature Branch**
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/your-feature-name
   ```

2. **Development**
   ```bash
   # Make changes
   # Run tests frequently
   pytest tests/ -v
   
   # Run linting
   flake8 src/
   black src/
   isort src/
   ```

3. **Testing**
   ```bash
   # Unit tests
   pytest tests/unit/ -v
   
   # Integration tests
   pytest tests/integration/ -v
   
   # Coverage report
   pytest tests/ --cov=src --cov-report=html
   ```

4. **Pre-commit Checks**
   ```bash
   # Automatic via pre-commit hooks
   # Or manually:
   pre-commit run --all-files
   ```

5. **Create Pull Request**
   - Write descriptive title and description
   - Include testing instructions
   - Link related issues
   - Add screenshots for UI changes

### Code Review Guidelines

#### For Authors
- Keep PRs focused and reasonably sized
- Write clear commit messages
- Include comprehensive tests
- Update documentation
- Self-review before requesting review

#### For Reviewers
- Focus on correctness, maintainability, and performance
- Provide constructive feedback
- Test the changes locally when necessary
- Approve when satisfied with quality

## 🧪 Testing Guide

### Testing Philosophy

We follow the testing pyramid approach:
- **Unit Tests (70%)**: Fast, isolated tests for individual functions
- **Integration Tests (20%)**: Test component interactions
- **End-to-End Tests (10%)**: Full application workflow tests

### Test Structure

```
tests/
├── conftest.py              # Pytest configuration and fixtures
├── unit/                    # Unit tests
│   ├── test_services.py
│   ├── test_models.py
│   └── test_schemas.py
├── integration/             # Integration tests
│   ├── test_api_endpoints.py
│   ├── test_database.py
│   └── test_cache.py
└── e2e/                    # End-to-end tests
    ├── test_user_workflows.py
    └── test_competitor_analysis.py
```

### Writing Tests

#### Unit Test Example
```python
# tests/unit/test_product_service.py
import pytest
from unittest.mock import Mock, AsyncMock
from src.app.services.product_service import ProductService

class TestProductService:
    def setup_method(self):
        self.mock_db = AsyncMock()
        self.service = ProductService(self.mock_db)
    
    @pytest.mark.asyncio
    async def test_get_product_by_id(self):
        # Arrange
        product_id = 1
        expected_product = Mock()
        expected_product.id = product_id
        self.mock_db.get.return_value = expected_product
        
        # Act
        result = await self.service.get_product_by_id(product_id)
        
        # Assert
        assert result.id == product_id
        self.mock_db.get.assert_called_once_with(product_id)
```

#### Integration Test Example
```python
# tests/integration/test_api_endpoints.py
import pytest
from httpx import AsyncClient
from src.app.main import app

@pytest.mark.asyncio
async def test_create_product_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/products/",
            json={
                "asin": "B08TEST123",
                "title": "Test Product",
                "category": "Electronics"
            },
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 201
        assert response.json()["asin"] == "B08TEST123"
```

### Test Configuration

#### pytest.ini
```ini
[tool:pytest]
minversion = 8.0
testpaths = tests
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*
addopts = 
    --verbose
    --tb=short
    --strict-markers
    --strict-config
    --cov=src
    --cov-report=term-missing
    --cov-report=html:htmlcov
    --cov-fail-under=70
asyncio_mode = auto
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow running tests
```

### Running Tests

```bash
# All tests
pytest

# Specific test categories
pytest -m unit
pytest -m integration
pytest -m e2e

# Specific test file
pytest tests/unit/test_product_service.py

# Specific test method
pytest tests/unit/test_product_service.py::TestProductService::test_get_product_by_id

# With coverage
pytest --cov=src --cov-report=html

# Parallel execution
pytest -n auto

# Watch mode (requires pytest-watch)
ptw tests/ src/
```

## 🛠️ API Development

### FastAPI Best Practices

#### Endpoint Structure
```python
# src/app/api/v1/endpoints/products.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from src.app.api.dependencies import get_db, get_current_user
from src.app.schemas.product import ProductCreate, ProductResponse
from src.app.services.product_service import ProductService

router = APIRouter()

@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Create a new product for tracking.
    
    Args:
        product: Product creation data
        db: Database session
        current_user: Authenticated user
    
    Returns:
        Created product data
    
    Raises:
        HTTPException: If product creation fails
    """
    service = ProductService(db)
    
    try:
        return await service.create_product(product, current_user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Product creation failed", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
```

#### Schema Definition
```python
# src/app/schemas/product.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime

class ProductBase(BaseModel):
    asin: str = Field(..., min_length=10, max_length=10, description="Amazon ASIN")
    title: str = Field(..., max_length=500, description="Product title")
    brand: Optional[str] = Field(None, max_length=100, description="Product brand")
    category: Optional[str] = Field(None, max_length=100, description="Product category")
    
    @field_validator('asin')
    def validate_asin(cls, v):
        if not v.startswith('B0'):
            raise ValueError('ASIN must start with B0')
        if not v[2:].isalnum():
            raise ValueError('ASIN must be alphanumeric after B0')
        return v.upper()

class ProductCreate(ProductBase):
    description: Optional[str] = Field(None, max_length=2000)

class ProductResponse(ProductBase):
    id: int
    current_price: Optional[float]
    current_rating: Optional[float]
    current_bsr: Optional[int]
    current_review_count: Optional[int]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}
```

### Error Handling

#### Custom Exception Classes
```python
# src/app/core/exceptions.py
class AmazonInsightsException(Exception):
    """Base exception for Amazon Insights Platform"""
    pass

class ProductNotFoundError(AmazonInsightsException):
    """Raised when product is not found"""
    pass

class CompetitorAnalysisError(AmazonInsightsException):
    """Raised when competitor analysis fails"""
    pass

class RateLimitExceededError(AmazonInsightsException):
    """Raised when rate limit is exceeded"""
    pass
```

#### Error Handler
```python
# src/app/core/error_handlers.py
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

async def amazon_insights_exception_handler(request: Request, exc: AmazonInsightsException):
    logger.error(f"Amazon Insights error: {str(exc)}", extra={"request": request.url})
    return JSONResponse(
        status_code=400,
        content={
            "detail": str(exc),
            "error_code": exc.__class__.__name__,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
```

### Authentication & Authorization

#### JWT Implementation
```python
# src/app/core/security.py
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
```

## 🗄️ Database Operations

### SQLAlchemy Models

#### Base Model
```python
# src/app/models/base.py
from sqlalchemy import Column, Integer, DateTime, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class BaseModel(Base):
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
```

#### Model Definition
```python
# src/app/models/product.py
from sqlalchemy import Column, String, Float, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .base import BaseModel

class Product(BaseModel):
    __tablename__ = "products"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    asin = Column(String(10), unique=True, index=True, nullable=False)
    title = Column(String(500), nullable=False)
    brand = Column(String(100), index=True)
    category = Column(String(100), index=True)
    
    current_price = Column(Float)
    current_rating = Column(Float)
    current_bsr = Column(Integer)
    current_review_count = Column(Integer)
    
    is_active = Column(Boolean, default=True, index=True)
    
    # Relationships
    user = relationship("User", back_populates="products")
    competitors = relationship("Competitor", back_populates="main_product")
    price_history = relationship("PriceHistory", back_populates="product")
```

### Database Migrations

#### Creating Migrations
```bash
# Auto-generate migration
docker exec -it amazon_insights_api alembic revision --autogenerate -m "Add product insights table"

# Create empty migration
docker exec -it amazon_insights_api alembic revision -m "Custom migration"

# Apply migrations
docker exec -it amazon_insights_api alembic upgrade head

# Check current version
docker exec -it amazon_insights_api alembic current

# Migration history
docker exec -it amazon_insights_api alembic history
```

#### Migration Best Practices
```python
# migrations/versions/add_indexes.py
"""Add database indexes for performance

Revision ID: abc123
Revises: def456
Create Date: 2024-01-15 10:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add indexes
    op.create_index('idx_products_user_active', 'products', ['user_id', 'is_active'])
    op.create_index('idx_competitors_similarity', 'competitors', ['similarity_score'])
    
    # Add constraints
    op.create_check_constraint(
        'ck_products_price_positive',
        'products',
        'current_price > 0'
    )

def downgrade():
    # Remove in reverse order
    op.drop_constraint('ck_products_price_positive', 'products')
    op.drop_index('idx_competitors_similarity', 'products')
    op.drop_index('idx_products_user_active', 'products')
```

### Query Optimization

#### Efficient Queries
```python
# src/app/services/product_service.py
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload, joinedload

class ProductService:
    async def get_user_products_with_stats(self, user_id: int):
        """Get user products with competitor statistics"""
        query = (
            select(Product)
            .options(
                selectinload(Product.competitors),  # Avoid N+1 queries
                joinedload(Product.user)
            )
            .where(
                and_(
                    Product.user_id == user_id,
                    Product.is_active == True
                )
            )
            .order_by(Product.created_at.desc())
        )
        
        result = await self.db.execute(query)
        return result.unique().scalars().all()
    
    async def get_product_performance_stats(self, product_id: int):
        """Get aggregated performance statistics"""
        query = (
            select(
                func.avg(PriceHistory.list_price).label('avg_price'),
                func.min(PriceHistory.list_price).label('min_price'),
                func.max(PriceHistory.list_price).label('max_price'),
                func.count(PriceHistory.id).label('data_points')
            )
            .where(PriceHistory.product_id == product_id)
        )
        
        result = await self.db.execute(query)
        return result.first()
```

## 🔄 Background Tasks

### Celery Configuration

#### Task Definition
```python
# src/app/tasks/product_tasks.py
from celery import shared_task
from sqlalchemy.orm import Session
from src.app.core.database import get_db
from src.app.services.product_service import ProductService
import structlog

logger = structlog.get_logger()

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 60},
    name="update_product_metrics"
)
def update_product_metrics(self, product_id: int):
    """Update product metrics from external APIs"""
    try:
        with get_db() as db:
            service = ProductService(db)
            result = service.update_product_metrics(product_id)
            
            logger.info(
                "Product metrics updated",
                product_id=product_id,
                task_id=self.request.id,
                result=result
            )
            
            return {"status": "success", "product_id": product_id}
            
    except Exception as exc:
        logger.error(
            "Product metrics update failed",
            product_id=product_id,
            task_id=self.request.id,
            error=str(exc)
        )
        raise self.retry(exc=exc)

@shared_task(name="discover_competitors")
def discover_competitors(product_id: int, max_competitors: int = 5):
    """Background task to discover product competitors"""
    with get_db() as db:
        service = CompetitorService(db)
        competitors = service.discover_competitors(product_id, max_competitors)
        
        return {
            "product_id": product_id,
            "competitors_found": len(competitors),
            "competitors": [c.id for c in competitors]
        }
```

#### Scheduled Tasks
```python
# src/app/tasks/celery_app.py
from celery import Celery
from celery.schedules import crontab

celery_app = Celery("amazon_insights")

# Scheduled tasks
celery_app.conf.beat_schedule = {
    'update-all-products': {
        'task': 'update_all_products',
        'schedule': crontab(minute=0, hour='*/6'),  # Every 6 hours
    },
    'competitor-discovery': {
        'task': 'discover_new_competitors',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    'cleanup-old-data': {
        'task': 'cleanup_old_price_history',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),  # Weekly
    },
}
```

### Task Monitoring

#### Custom Task Base Class
```python
# src/app/tasks/base.py
from celery import Task
import structlog

logger = structlog.get_logger()

class BaseTask(Task):
    def on_success(self, retval, task_id, args, kwargs):
        logger.info(
            "Task succeeded",
            task_id=task_id,
            task_name=self.name,
            result=retval
        )
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(
            "Task failed",
            task_id=task_id,
            task_name=self.name,
            error=str(exc),
            traceback=einfo.traceback
        )
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        logger.warning(
            "Task retry",
            task_id=task_id,
            task_name=self.name,
            error=str(exc),
            retry_count=self.request.retries
        )
```

## ⚡ Performance Optimization

### Caching Strategies

#### Redis Caching
```python
# src/app/services/cache_service.py
import json
import hashlib
from typing import Any, Optional
from redis import Redis
import structlog

logger = structlog.get_logger()

class CacheService:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.default_ttl = 3600
    
    def _generate_key(self, prefix: str, *args) -> str:
        """Generate cache key from prefix and arguments"""
        key_parts = [str(arg) for arg in args]
        key_string = f"{prefix}:{':'.join(key_parts)}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache"""
        try:
            cached_value = await self.redis.get(key)
            if cached_value:
                return json.loads(cached_value)
            return default
        except Exception as e:
            logger.error("Cache get error", key=key, error=str(e))
            return default
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        try:
            ttl = ttl or self.default_ttl
            serialized_value = json.dumps(value, default=str)
            await self.redis.setex(key, ttl, serialized_value)
            return True
        except Exception as e:
            logger.error("Cache set error", key=key, error=str(e))
            return False

    def cache_result(self, prefix: str, ttl: int = None):
        """Decorator to cache function results"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                cache_key = self._generate_key(prefix, *args, **kwargs)
                
                # Try to get from cache
                cached_result = await self.get(cache_key)
                if cached_result is not None:
                    return cached_result
                
                # Execute function and cache result
                result = await func(*args, **kwargs)
                await self.set(cache_key, result, ttl)
                return result
            return wrapper
        return decorator
```

### Database Performance

#### Connection Pooling
```python
# src/app/core/database.py
from sqlalchemy.pool import QueuePool
from sqlalchemy.ext.asyncio import create_async_engine

def create_database_engine():
    return create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_size=20,  # Number of connections to maintain
        max_overflow=40,  # Additional connections that can be created
        pool_timeout=30,  # Timeout to get connection from pool
        pool_recycle=1800,  # Recycle connections after 30 minutes
        pool_pre_ping=True,  # Validate connections before use
        poolclass=QueuePool
    )
```

#### Query Optimization
```python
# Efficient bulk operations
async def bulk_update_products(self, updates: List[Dict]):
    """Bulk update products efficiently"""
    stmt = (
        update(Product)
        .where(Product.id == bindparam('product_id'))
        .values(
            current_price=bindparam('price'),
            current_bsr=bindparam('bsr'),
            updated_at=func.now()
        )
    )
    
    await self.db.execute(stmt, updates)
    await self.db.commit()

# Use indexes effectively
async def get_products_by_category_with_index(self, category: str, user_id: int):
    """Query uses composite index on (user_id, category, is_active)"""
    return await self.db.execute(
        select(Product)
        .where(
            and_(
                Product.user_id == user_id,
                Product.category == category,
                Product.is_active == True
            )
        )
        .order_by(Product.created_at.desc())
    )
```

## 🔒 Security Guidelines

### Input Validation

#### Pydantic Models
```python
from pydantic import BaseModel, validator, Field
from typing import Optional
import re

class ProductCreate(BaseModel):
    asin: str = Field(..., min_length=10, max_length=10)
    title: str = Field(..., min_length=1, max_length=500)
    category: Optional[str] = Field(None, max_length=100)
    
    @validator('asin')
    def validate_asin(cls, v):
        if not re.match(r'^B0[A-Z0-9]{8}$', v):
            raise ValueError('Invalid ASIN format')
        return v.upper()
    
    @validator('title')
    def validate_title(cls, v):
        # Remove potential XSS
        cleaned = re.sub(r'<[^>]*>', '', v)
        if not cleaned.strip():
            raise ValueError('Title cannot be empty after cleaning')
        return cleaned.strip()
```

### Authentication Security

#### Rate Limiting
```python
# src/app/core/rate_limiter.py
from fastapi import HTTPException, status
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Apply to endpoints
@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, user_credentials: UserLogin):
    # Login logic
    pass

@router.get("/products/")
@limiter.limit("100/minute")
async def get_products(request: Request):
    # Get products logic
    pass
```

### SQL Injection Prevention

```python
# GOOD: Use SQLAlchemy ORM
async def get_product_by_asin(self, asin: str):
    return await self.db.execute(
        select(Product).where(Product.asin == asin)
    )

# GOOD: Use parameterized queries
async def search_products(self, search_term: str):
    return await self.db.execute(
        text("SELECT * FROM products WHERE title ILIKE :search"),
        {"search": f"%{search_term}%"}
    )

# BAD: String concatenation (vulnerable to SQL injection)
# async def search_products_bad(self, search_term: str):
#     return await self.db.execute(
#         text(f"SELECT * FROM products WHERE title LIKE '%{search_term}%'")
#     )
```

## 🚀 Deployment & CI/CD

### Docker Best Practices

#### Multi-stage Dockerfile
```dockerfile
# Dockerfile.prod
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim as production

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Set environment variables
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/v1/health/ || exit 1

EXPOSE 8000

CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### CI/CD Pipeline

#### GitHub Actions
```yaml
# .github/workflows/ci.yml
name: CI Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements-dev.txt
    
    - name: Run tests
      run: |
        pytest tests/ --cov=src --cov-report=xml
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
        REDIS_URL: redis://localhost:6379/0
        SECRET_KEY: test-secret-key
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
    
    - name: Run linting
      run: |
        flake8 src/
        black --check src/
        isort --check-only src/
    
    - name: Run security checks
      run: |
        bandit -r src/
        safety check
```

## 🔧 Troubleshooting

### Common Issues

#### Database Connection Issues
```bash
# Check database connectivity
docker exec amazon_insights_postgres pg_isready -U postgres

# View database logs
docker-compose logs postgres

# Test connection from API container
docker exec -it amazon_insights_api python -c "
from src.app.core.database import engine
from sqlalchemy import text
async def test():
    async with engine.begin() as conn:
        result = await conn.execute(text('SELECT version()'))
        print(result.fetchone())
import asyncio
asyncio.run(test())
"
```

#### Redis Connection Issues
```bash
# Check Redis connectivity
docker exec amazon_insights_redis redis-cli ping

# Monitor Redis
docker exec amazon_insights_redis redis-cli monitor

# Check Redis memory usage
docker exec amazon_insights_redis redis-cli info memory
```

#### Performance Issues
```bash
# Check API container resources
docker stats amazon_insights_api

# Monitor slow queries (add to PostgreSQL config)
log_min_duration_statement = 1000  # Log queries > 1 second

# Profile Python code
pip install py-spy
py-spy record -o profile.svg -d 30 -p $(pgrep -f "uvicorn")
```

### Debugging Tools

#### Logging Configuration
```python
# src/app/core/logging.py
import structlog
import logging.config

def configure_logging():
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
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

# Use in code
logger = structlog.get_logger()
logger.info("Product created", product_id=123, user_id=456)
```

#### Database Query Debugging
```python
# Enable SQLAlchemy query logging
engine = create_async_engine(DATABASE_URL, echo=True)

# Log slow queries
@event.listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.time()

@event.listens_for(Engine, "after_cursor_execute")  
def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - context._query_start_time
    if total > 0.5:  # Log queries > 500ms
        logger.warning("Slow query", duration=total, query=statement[:100])
```

---

## 📞 Support

### Development Support
- **Internal Documentation**: Check `/docs` directory for detailed guides
- **Code Review**: Use GitHub pull request reviews
- **Architecture Discussions**: Use GitHub Discussions
- **Bug Reports**: Create GitHub Issues with reproduction steps

### Useful Resources
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [Pydantic Documentation](https://pydantic-docs.helpmanual.io/)

**Happy Coding! 🚀**