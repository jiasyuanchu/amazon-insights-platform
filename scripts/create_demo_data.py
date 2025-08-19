#!/usr/bin/env python3
"""
Create demo data for Amazon Insights Platform

This script creates sample users, products, and competitors
for demonstration and testing purposes.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
import random

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.app.core.database import AsyncSessionLocal, init_db
from src.app.models import User, Product, Competitor, ProductMetrics, AlertConfiguration
from src.app.api.v1.endpoints.auth import get_password_hash
from sqlalchemy import select
import structlog

logger = structlog.get_logger()


class DemoDataCreator:
    def __init__(self):
        self.session = None
        
    async def __aenter__(self):
        await init_db()
        self.session = AsyncSessionLocal()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def create_demo_users(self):
        """Create demo users"""
        demo_users = [
            {
                "username": "demo_seller",
                "email": "demo@amazon-insights.com",
                "password": "demopassword123",
                "full_name": "Demo Amazon Seller",
                "company_name": "Demo Electronics Co.",
                "brand_name": "DemoTech"
            },
            {
                "username": "test_seller", 
                "email": "test@amazon-insights.com",
                "password": "testpassword123",
                "full_name": "Test Seller",
                "company_name": "Test Products LLC",
                "brand_name": "TestBrand"
            }
        ]
        
        created_users = []
        
        for user_data in demo_users:
            # Check if user exists
            result = await self.session.execute(
                select(User).where(User.username == user_data["username"])
            )
            existing_user = result.scalar_one_or_none()
            
            if not existing_user:
                user = User(
                    username=user_data["username"],
                    email=user_data["email"],
                    hashed_password=get_password_hash(user_data["password"]),
                    full_name=user_data["full_name"],
                    company_name=user_data["company_name"],
                    brand_name=user_data["brand_name"],
                    is_active=True
                )
                self.session.add(user)
                await self.session.commit()
                await self.session.refresh(user)
                created_users.append(user)
                logger.info("Created demo user", username=user.username)
            else:
                created_users.append(existing_user)
                logger.info("Demo user already exists", username=existing_user.username)
        
        return created_users
    
    async def create_demo_products(self, users):
        """Create demo products for users"""
        demo_products = [
            # Electronics
            {
                "asin": "B08N5WRWNW",
                "title": "Echo Dot (4th Gen) | Smart speaker with Alexa | Charcoal",
                "brand": "Amazon",
                "category": "Electronics",
                "subcategory": "Smart Home",
                "current_price": 49.99,
                "current_bsr": 1250,
                "current_rating": 4.7,
                "current_review_count": 287653,
                "features": [
                    "Improved speaker quality",
                    "Voice control for smart home",
                    "Compact design",
                    "Multiple colors available"
                ]
            },
            {
                "asin": "B09B8V1LZ3", 
                "title": "Fire TV Stick 4K Max streaming device",
                "brand": "Amazon",
                "category": "Electronics",
                "subcategory": "Streaming Devices",
                "current_price": 54.99,
                "current_bsr": 890,
                "current_rating": 4.5,
                "current_review_count": 156432,
                "features": [
                    "4K Ultra HD streaming",
                    "Alexa Voice Remote",
                    "WiFi 6 support",
                    "Dolby Vision support"
                ]
            },
            # Home & Kitchen
            {
                "asin": "B087QZLZNH",
                "title": "Instant Vortex Plus 4 Quart Air Fryer",
                "brand": "Instant",
                "category": "Home & Kitchen",
                "subcategory": "Kitchen Appliances",
                "current_price": 79.99,
                "current_bsr": 45,
                "current_rating": 4.6,
                "current_review_count": 89234,
                "features": [
                    "4 cooking programs",
                    "Easy cleanup",
                    "Compact design",
                    "Quick cooking"
                ]
            },
            # Books
            {
                "asin": "B08HYPDDW1",
                "title": "The Complete Amazon Seller Guide 2024",
                "brand": "Self-Published",
                "category": "Books",
                "subcategory": "Business",
                "current_price": 19.99,
                "current_bsr": 2340,
                "current_rating": 4.8,
                "current_review_count": 1245,
                "features": [
                    "Latest strategies",
                    "Step-by-step guide",
                    "Case studies included",
                    "Kindle edition available"
                ]
            },
            # Sports & Outdoors
            {
                "asin": "B09SXLZPQ4",
                "title": "Adjustable Resistance Bands Set with Handles",
                "brand": "FitLife",
                "category": "Sports & Outdoors",
                "subcategory": "Exercise Equipment",
                "current_price": 29.99,
                "current_bsr": 156,
                "current_rating": 4.4,
                "current_review_count": 23456,
                "features": [
                    "Multiple resistance levels",
                    "Door anchor included",
                    "Portable design",
                    "Exercise guide included"
                ]
            }
        ]
        
        created_products = []
        
        for i, product_data in enumerate(demo_products):
            user = users[i % len(users)]  # Distribute products among users
            
            # Check if product exists
            result = await self.session.execute(
                select(Product).where(Product.asin == product_data["asin"])
            )
            existing_product = result.scalar_one_or_none()
            
            if not existing_product:
                product = Product(
                    asin=product_data["asin"],
                    title=product_data["title"],
                    brand=product_data["brand"],
                    category=product_data["category"],
                    subcategory=product_data["subcategory"],
                    product_url=f"https://www.amazon.com/dp/{product_data['asin']}",
                    user_id=user.id,
                    current_price=product_data["current_price"],
                    current_bsr=product_data["current_bsr"],
                    current_rating=product_data["current_rating"],
                    current_review_count=product_data["current_review_count"],
                    features=product_data["features"],
                    is_active=True
                )
                self.session.add(product)
                await self.session.commit()
                await self.session.refresh(product)
                created_products.append(product)
                logger.info("Created demo product", asin=product.asin, title=product.title[:50])
            else:
                created_products.append(existing_product)
                logger.info("Demo product already exists", asin=existing_product.asin)
        
        return created_products
    
    async def create_demo_competitors(self, products):
        """Create demo competitors for products"""
        competitors_data = {
            "B08N5WRWNW": [  # Echo Dot competitors
                {
                    "asin": "B09B93ZDG4",
                    "title": "Google Nest Mini (2nd Generation)",
                    "price": 49.99,
                    "rating": 4.5,
                    "review_count": 156789,
                    "similarity_score": 0.92
                },
                {
                    "asin": "B08H75RTZ8", 
                    "title": "Apple HomePod mini",
                    "price": 99.99,
                    "rating": 4.3,
                    "review_count": 45623,
                    "similarity_score": 0.78
                }
            ],
            "B09B8V1LZ3": [  # Fire TV Stick competitors
                {
                    "asin": "B08GDV7W73",
                    "title": "Roku Streaming Stick 4K+",
                    "price": 49.99,
                    "rating": 4.6,
                    "review_count": 89456,
                    "similarity_score": 0.89
                },
                {
                    "asin": "B08T6W83BR",
                    "title": "NVIDIA SHIELD TV",
                    "price": 149.99,
                    "rating": 4.4,
                    "review_count": 34567,
                    "similarity_score": 0.73
                }
            ],
            "B087QZLZNH": [  # Air Fryer competitors
                {
                    "asin": "B07GJBBGHG",
                    "title": "COSORI Air Fryer Max XL",
                    "price": 89.99,
                    "rating": 4.5,
                    "review_count": 67890,
                    "similarity_score": 0.88
                },
                {
                    "asin": "B08R3QVFH2",
                    "title": "Ninja Air Fryer AF101",
                    "price": 79.99,
                    "rating": 4.7,
                    "review_count": 98765,
                    "similarity_score": 0.85
                }
            ]
        }
        
        created_competitors = []
        
        for product in products:
            if product.asin in competitors_data:
                for comp_data in competitors_data[product.asin]:
                    # Check if competitor exists
                    result = await self.session.execute(
                        select(Competitor).where(
                            (Competitor.main_product_id == product.id) &
                            (Competitor.competitor_asin == comp_data["asin"])
                        )
                    )
                    existing_competitor = result.scalar_one_or_none()
                    
                    if not existing_competitor:
                        competitor = Competitor(
                            main_product_id=product.id,
                            competitor_asin=comp_data["asin"],
                            title=comp_data["title"],
                            product_url=f"https://www.amazon.com/dp/{comp_data['asin']}",
                            current_price=comp_data["price"],
                            current_rating=comp_data["rating"],
                            current_review_count=comp_data["review_count"],
                            similarity_score=comp_data["similarity_score"],
                            is_direct_competitor=1 if comp_data["similarity_score"] > 0.8 else 2
                        )
                        self.session.add(competitor)
                        created_competitors.append(competitor)
                        logger.info("Created competitor", 
                                  main_asin=product.asin, 
                                  competitor_asin=comp_data["asin"])
        
        if created_competitors:
            await self.session.commit()
        
        return created_competitors
    
    async def create_demo_metrics(self, products):
        """Create historical metrics for products"""
        created_metrics = []
        
        for product in products:
            # Generate 30 days of historical data
            base_date = datetime.utcnow() - timedelta(days=30)
            
            for days_ago in range(30, 0, -1):
                metric_date = base_date + timedelta(days=30-days_ago)
                
                # Add some variation to the metrics
                price_variation = random.uniform(0.9, 1.1)
                bsr_variation = random.uniform(0.8, 1.2)
                rating_variation = random.uniform(0.98, 1.02)
                
                metrics = ProductMetrics(
                    product_id=product.id,
                    scraped_at=metric_date,
                    price=round(product.current_price * price_variation, 2) if product.current_price else None,
                    bsr=int(product.current_bsr * bsr_variation) if product.current_bsr else None,
                    rating=min(5.0, product.current_rating * rating_variation) if product.current_rating else None,
                    review_count=product.current_review_count + random.randint(-100, 500) if product.current_review_count else None,
                    buy_box_price=round(product.current_price * price_variation * 1.05, 2) if product.current_price else None
                )
                self.session.add(metrics)
                created_metrics.append(metrics)
        
        if created_metrics:
            await self.session.commit()
            logger.info("Created historical metrics", count=len(created_metrics))
        
        return created_metrics
    
    async def create_demo_alerts(self, products, users):
        """Create demo alert configurations"""
        created_alerts = []
        
        for i, product in enumerate(products[:3]):  # Only create alerts for first 3 products
            user = users[i % len(users)]  # Distribute among users
            
            # Create different types of alerts
            alerts_config = [
                {
                    "alert_name": "Price Drop Alert",
                    "price_drop_threshold": 10.0,
                    "email_enabled": True,
                },
                {
                    "alert_name": "BSR Improvement",
                    "bsr_improvement_threshold": 1000,
                    "email_enabled": True,
                },
                {
                    "alert_name": "Rating Drop Warning",
                    "rating_drop_threshold": 0.2,
                    "email_enabled": True,
                },
                {
                    "alert_name": "New Competitor Alert",
                    "new_competitor_alert": True,
                    "email_enabled": True,
                }
            ]
            
            for config in alerts_config:
                alert = AlertConfiguration(
                    user_id=user.id,
                    product_id=product.id,
                    **config
                )
                self.session.add(alert)
                created_alerts.append(alert)
        
        if created_alerts:
            await self.session.commit()
            logger.info("Created demo alerts", count=len(created_alerts))
        
        return created_alerts


async def main():
    """Main function to create all demo data"""
    print("🚀 Creating demo data for Amazon Insights Platform...")
    
    async with DemoDataCreator() as creator:
        try:
            # Create demo users
            print("👥 Creating demo users...")
            users = await creator.create_demo_users()
            print(f"✅ Created {len(users)} demo users")
            
            # Create demo products
            print("📦 Creating demo products...")
            products = await creator.create_demo_products(users)
            print(f"✅ Created {len(products)} demo products")
            
            # Create demo competitors
            print("🔍 Creating demo competitors...")
            competitors = await creator.create_demo_competitors(products)
            print(f"✅ Created {len(competitors)} demo competitors")
            
            # Create historical metrics
            print("📊 Creating historical metrics...")
            metrics = await creator.create_demo_metrics(products)
            print(f"✅ Created {len(metrics)} historical data points")
            
            # Create demo alerts
            print("🔔 Creating demo alerts...")
            alerts = await creator.create_demo_alerts(products, users)
            print(f"✅ Created {len(alerts)} alert configurations")
            
            print("\n🎉 Demo data creation complete!")
            print("\n📋 Demo Account Details:")
            print("Username: demo_seller")
            print("Password: demopassword123")
            print("Email: demo@amazon-insights.com")
            print("\n🔑 Test Account Details:")
            print("Username: test_seller") 
            print("Password: testpassword123")
            print("Email: test@amazon-insights.com")
            print("\n🌐 Access the API at: http://localhost:8000/api/v1/docs")
            
        except Exception as e:
            logger.error("Failed to create demo data", error=str(e))
            print(f"❌ Error creating demo data: {e}")
            return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)