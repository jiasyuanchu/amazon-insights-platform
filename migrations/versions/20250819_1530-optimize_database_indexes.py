"""Optimize database indexes for better query performance

Revision ID: optimize_database_indexes
Revises: 11809d3e71e5
Create Date: 2025-08-19 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'optimize_database_indexes'
down_revision = '11809d3e71e5'
branch_labels = None
depends_on = None


def upgrade():
    """Add optimized database indexes for better query performance"""
    
    # Add composite indexes for common query patterns
    
    # Products table optimizations
    op.create_index(
        'idx_products_user_active', 
        'products', 
        ['user_id', 'is_active'],
        if_not_exists=True
    )
    
    op.create_index(
        'idx_products_category_active', 
        'products', 
        ['category', 'is_active'],
        if_not_exists=True
    )
    
    op.create_index(
        'idx_products_brand_category', 
        'products', 
        ['brand', 'category'],
        if_not_exists=True
    )
    
    # Add partial index for active products only
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_products_active_only 
        ON products (id, asin, current_price, current_bsr, current_rating) 
        WHERE is_active = true
    """)
    
    # Product metrics optimizations for time-series queries
    op.create_index(
        'idx_metrics_product_price_time', 
        'product_metrics', 
        ['product_id', 'price', 'scraped_at'],
        if_not_exists=True
    )
    
    op.create_index(
        'idx_metrics_recent_data', 
        'product_metrics', 
        ['scraped_at', 'product_id'],
        if_not_exists=True
    )
    
    # Competitors table optimizations
    op.create_index(
        'idx_competitors_product_similarity', 
        'competitors', 
        ['main_product_id', 'similarity_score', 'is_direct_competitor'],
        if_not_exists=True
    )
    
    op.create_index(
        'idx_competitors_direct_only', 
        'competitors', 
        ['main_product_id', 'current_price', 'current_rating'],
        if_not_exists=True
    )
    
    # Product insights optimizations
    op.create_index(
        'idx_insights_product_date', 
        'product_insights', 
        ['product_id', 'insight_date'],
        if_not_exists=True
    )
    
    op.create_index(
        'idx_insights_opportunity_score', 
        'product_insights', 
        ['opportunity_score', 'insight_date'],
        if_not_exists=True
    )
    
    # Price history optimizations
    op.create_index(
        'idx_price_history_recent', 
        'price_history', 
        ['product_id', 'tracked_at', 'sale_price'],
        if_not_exists=True
    )
    
    # Alert configurations optimizations
    op.create_index(
        'idx_alerts_active_user', 
        'alert_configurations', 
        ['user_id', 'is_active'],
        if_not_exists=True
    )
    
    op.create_index(
        'idx_alerts_product_active', 
        'alert_configurations', 
        ['product_id', 'is_active'],
        if_not_exists=True
    )
    
    # Alert history optimizations for monitoring
    op.create_index(
        'idx_alert_history_recent', 
        'alert_history', 
        ['triggered_at', 'product_id', 'acknowledged'],
        if_not_exists=True
    )
    
    # Competitor analyses optimizations
    op.create_index(
        'idx_competitor_analyses_recent', 
        'competitor_analyses', 
        ['competitor_id', 'analyzed_at'],
        if_not_exists=True
    )
    
    # Users table optimization for authentication
    op.create_index(
        'idx_users_active_login', 
        'users', 
        ['username', 'is_active'],
        if_not_exists=True
    )
    
    op.create_index(
        'idx_users_email_active', 
        'users', 
        ['email', 'is_active'],
        if_not_exists=True
    )


def downgrade():
    """Remove optimized indexes"""
    
    # Remove composite indexes
    indexes_to_drop = [
        'idx_products_user_active',
        'idx_products_category_active', 
        'idx_products_brand_category',
        'idx_products_active_only',
        'idx_metrics_product_price_time',
        'idx_metrics_recent_data',
        'idx_competitors_product_similarity',
        'idx_competitors_direct_only',
        'idx_insights_product_date',
        'idx_insights_opportunity_score',
        'idx_price_history_recent',
        'idx_alerts_active_user',
        'idx_alerts_product_active',
        'idx_alert_history_recent',
        'idx_competitor_analyses_recent',
        'idx_users_active_login',
        'idx_users_email_active'
    ]
    
    for index_name in indexes_to_drop:
        op.execute(f"DROP INDEX IF EXISTS {index_name}")