from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from src.app.core.database import get_db
from src.app.models.user import User
from src.app.models.product import Product, ProductMetrics
from src.app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from src.app.api.v1.endpoints.auth import get_current_active_user
import structlog

router = APIRouter()
logger = structlog.get_logger()


@router.post("/", response_model=ProductResponse)
async def create_product(
    product_in: ProductCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # Check if product already exists for this user
    result = await db.execute(
        select(Product).where(
            and_(
                Product.asin == product_in.asin,
                Product.user_id == current_user.id
            )
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Product already being tracked")
    
    # Create new product
    product = Product(
        **product_in.dict(),
        user_id=current_user.id
    )
    
    db.add(product)
    await db.commit()
    await db.refresh(product)
    
    logger.info("Product added for tracking", product_id=product.id, asin=product.asin, user_id=current_user.id)
    
    return product


@router.get("/", response_model=List[ProductResponse])
async def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Product).where(Product.user_id == current_user.id)
    
    if is_active is not None:
        query = query.where(Product.is_active == is_active)
    
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    products = result.scalars().all()
    
    return products


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
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
    
    return product


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_update: ProductUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
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
    
    # Update product fields
    for field, value in product_update.dict(exclude_unset=True).items():
        setattr(product, field, value)
    
    await db.commit()
    await db.refresh(product)
    
    return product


@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
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
    
    logger.info("Product deleted", product_id=product_id, user_id=current_user.id)
    
    return {"message": "Product deleted successfully"}