"""Product tracking and insights API endpoints"""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from src.app.core.database import get_db
from src.app.api.dependencies import get_current_user
from src.app.models import User, Product, ProductMetrics, ProductInsight, PriceHistory
from src.app.schemas.product import (
    ProductCreate,
    ProductResponse,
    ProductUpdate,
    ProductInsightResponse,
    PriceHistoryResponse,
    BatchProductImport
)
from src.app.services.product_service import ProductService
from src.app.tasks.scraping_tasks import scrape_product_task
import structlog

router = APIRouter()
logger = structlog.get_logger()


@router.post("/", response_model=ProductResponse)
async def create_product(
    product_data: ProductCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a new product to track"""
    # Check if product already exists for this user
    existing = await db.execute(
        select(Product).where(
            and_(
                Product.asin == product_data.asin,
                Product.user_id == current_user.id
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Product already being tracked")
    
    # Create product with auto-generated fields
    product_dict = product_data.dict()
    product_dict['product_url'] = f"https://www.amazon.com/dp/{product_data.asin}"
    if not product_dict.get('title'):
        product_dict['title'] = f"Product {product_data.asin}"
    
    product = Product(
        **product_dict,
        user_id=current_user.id
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    
    # Trigger initial scraping in background
    background_tasks.add_task(
        scrape_product_task.delay,
        product_id=product.id
    )
    
    logger.info("product_created", 
                user_id=current_user.id, 
                product_id=product.id,
                asin=product.asin)
    
    return product


@router.get("/", response_model=List[ProductResponse])
async def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    is_active: Optional[bool] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all tracked products for current user"""
    query = select(Product).where(Product.user_id == current_user.id)
    
    if is_active is not None:
        query = query.where(Product.is_active == is_active)
    if category:
        query = query.where(Product.category == category)
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    products = result.scalars().all()
    
    return products


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific product"""
    product = await db.execute(
        select(Product).where(
            and_(
                Product.id == product_id,
                Product.user_id == current_user.id
            )
        )
    )
    product = product.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return product


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_update: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update product tracking settings"""
    result = await db.execute(
        select(Product).where(
            and_(
                Product.id == product_id,
                Product.user_id == current_user.id
            )
        )
    )
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    for field, value in product_update.dict(exclude_unset=True).items():
        setattr(product, field, value)
    
    await db.commit()
    await db.refresh(product)
    
    return product


@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Stop tracking a product"""
    result = await db.execute(
        select(Product).where(
            and_(
                Product.id == product_id,
                Product.user_id == current_user.id
            )
        )
    )
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    await db.delete(product)
    await db.commit()
    
    return {"message": "Product deleted successfully"}


@router.get("/{product_id}/insights", response_model=List[ProductInsightResponse])
async def get_product_insights(
    product_id: int,
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get product insights for the last N days"""
    # Verify product ownership
    product = await db.execute(
        select(Product).where(
            and_(
                Product.id == product_id,
                Product.user_id == current_user.id
            )
        )
    )
    if not product.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get insights
    start_date = datetime.utcnow() - timedelta(days=days)
    insights = await db.execute(
        select(ProductInsight).where(
            and_(
                ProductInsight.product_id == product_id,
                ProductInsight.insight_date >= start_date
            )
        ).order_by(ProductInsight.insight_date.desc())
    )
    
    return insights.scalars().all()


@router.get("/{product_id}/price-history", response_model=List[PriceHistoryResponse])
async def get_price_history(
    product_id: int,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get price history for a product"""
    # Verify product ownership
    product = await db.execute(
        select(Product).where(
            and_(
                Product.id == product_id,
                Product.user_id == current_user.id
            )
        )
    )
    if not product.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get price history
    start_date = datetime.utcnow() - timedelta(days=days)
    price_history = await db.execute(
        select(PriceHistory).where(
            and_(
                PriceHistory.product_id == product_id,
                PriceHistory.tracked_at >= start_date
            )
        ).order_by(PriceHistory.tracked_at.desc())
    )
    
    return price_history.scalars().all()


@router.post("/{product_id}/refresh")
async def refresh_product_data(
    product_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Manually trigger a product data refresh"""
    # Verify product ownership
    product = await db.execute(
        select(Product).where(
            and_(
                Product.id == product_id,
                Product.user_id == current_user.id
            )
        )
    )
    product = product.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if recently scraped (prevent abuse)
    if product.last_scraped_at:
        time_since_last = datetime.utcnow() - product.last_scraped_at.replace(tzinfo=None)
        if time_since_last < timedelta(minutes=5):
            raise HTTPException(
                status_code=429, 
                detail="Product was recently refreshed. Please wait 5 minutes."
            )
    
    # Trigger scraping
    background_tasks.add_task(
        scrape_product_task.delay,
        product_id=product.id
    )
    
    return {"message": "Product refresh initiated", "product_id": product_id}


@router.post("/batch-import", response_model=dict)
async def batch_import_products(
    import_data: BatchProductImport,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Import multiple products at once"""
    if len(import_data.asins) > 50:
        raise HTTPException(
            status_code=400,
            detail="Maximum 50 products can be imported at once"
        )
    
    imported = []
    skipped = []
    
    for asin in import_data.asins:
        # Check if already exists
        existing = await db.execute(
            select(Product).where(
                and_(
                    Product.asin == asin,
                    Product.user_id == current_user.id
                )
            )
        )
        
        if existing.scalar_one_or_none():
            skipped.append(asin)
            continue
        
        # Create product with minimal info
        product = Product(
            asin=asin,
            title=f"Product {asin} (pending scrape)",
            product_url=f"https://www.amazon.com/dp/{asin}",
            user_id=current_user.id,
            category=import_data.default_category
        )
        db.add(product)
        imported.append(asin)
    
    await db.commit()
    
    # Trigger scraping for all imported products
    if imported:
        products = await db.execute(
            select(Product).where(
                and_(
                    Product.asin.in_(imported),
                    Product.user_id == current_user.id
                )
            )
        )
        for product in products.scalars():
            background_tasks.add_task(
                scrape_product_task.delay,
                product_id=product.id
            )
    
    return {
        "imported": imported,
        "skipped": skipped,
        "total_imported": len(imported),
        "total_skipped": len(skipped)
    }


@router.get("/insights/opportunities", response_model=List[ProductInsightResponse])
async def get_opportunity_products(
    min_score: float = Query(70, ge=0, le=100),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get products with highest opportunity scores"""
    # Get user's products
    user_products = await db.execute(
        select(Product.id).where(Product.user_id == current_user.id)
    )
    product_ids = [p for p in user_products.scalars()]
    
    if not product_ids:
        return []
    
    # Get latest insights with high opportunity scores
    subquery = (
        select(
            ProductInsight.product_id,
            func.max(ProductInsight.insight_date).label("latest_date")
        )
        .where(ProductInsight.product_id.in_(product_ids))
        .group_by(ProductInsight.product_id)
        .subquery()
    )
    
    insights = await db.execute(
        select(ProductInsight)
        .join(
            subquery,
            and_(
                ProductInsight.product_id == subquery.c.product_id,
                ProductInsight.insight_date == subquery.c.latest_date
            )
        )
        .where(ProductInsight.opportunity_score >= min_score)
        .order_by(ProductInsight.opportunity_score.desc())
        .limit(limit)
    )
    
    return insights.scalars().all()