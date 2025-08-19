from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession as AsyncSessionType
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool
from src.app.core.config import settings
import os

# Create async engine only if not testing
engine: Optional[object] = None
AsyncSessionLocal: Optional[object] = None

if not settings.is_testing:
    # Create async engine
    if settings.is_development:
        # Use NullPool for development (no connection pooling)
        engine = create_async_engine(
            str(settings.DATABASE_URL),
            echo=settings.DEBUG,
            future=True,
            poolclass=NullPool,
        )
    else:
        # Use connection pooling for production
        engine = create_async_engine(
            str(settings.DATABASE_URL),
            echo=settings.DEBUG,
            future=True,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
        )

    # Create async session factory
    AsyncSessionLocal = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

# Create declarative base
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    if settings.is_testing or AsyncSessionLocal is None:
        # Return mock session for testing
        from unittest.mock import AsyncMock
        mock_session = AsyncMock(spec=AsyncSession)
        yield mock_session
        return
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    if settings.is_testing or engine is None:
        return
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    if settings.is_testing or engine is None:
        return
    await engine.dispose()