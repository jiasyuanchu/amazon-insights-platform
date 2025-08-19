from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.app.core.database import get_db
from src.app.models.user import User
from src.app.schemas.user import UserResponse, UserUpdate
from src.app.api.v1.endpoints.auth import get_current_active_user

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: User = Depends(get_current_active_user)
):
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_user_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # Update user fields
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
    if user_update.company_name is not None:
        current_user.company_name = user_update.company_name
    if user_update.brand_name is not None:
        current_user.brand_name = user_update.brand_name
    if user_update.firecrawl_api_key is not None:
        current_user.firecrawl_api_key = user_update.firecrawl_api_key
    if user_update.openai_api_key is not None:
        current_user.openai_api_key = user_update.openai_api_key
    
    await db.commit()
    await db.refresh(current_user)
    
    return current_user