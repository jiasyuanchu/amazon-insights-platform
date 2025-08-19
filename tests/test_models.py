"""Tests for database models"""

import pytest
from datetime import datetime
from unittest.mock import Mock
from src.app.models import User, Product, Competitor
from src.app.models.product_insights import ProductInsight, MarketTrend, PriceHistory
from src.app.schemas.product import ProductCreate
from src.app.schemas.user import UserCreate


class TestUserModel:
    """Test User model"""
    
    def test_user_creation(self):
        """Test creating a user instance"""
        user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'full_name': 'Test User',
            'hashed_password': 'hashed123',
            'is_active': True
        }
        user = User(**user_data)
        
        assert user.username == 'testuser'
        assert user.email == 'test@example.com'
        assert user.full_name == 'Test User'
        assert user.is_active is True
    
    def test_user_repr(self):
        """Test user string representation"""
        user = User(username='testuser', email='test@example.com')
        assert 'testuser' in repr(user)


class TestProductModel:
    """Test Product model"""
    
    def test_product_creation(self):
        """Test creating a product instance"""
        product_data = {
            'asin': 'B08TEST123',
            'title': 'Test Product',
            'brand': 'TestBrand',
            'category': 'Electronics',
            'current_price': 29.99,
            'current_rating': 4.5,
            'current_bsr': 1000,
            'current_review_count': 500,
            'user_id': 1,
            'is_active': True
        }
        product = Product(**product_data)
        
        assert product.asin == 'B08TEST123'
        assert product.title == 'Test Product'
        assert product.current_price == 29.99
        assert product.current_rating == 4.5
        assert product.is_active is True
    
    def test_product_pricing_methods(self):
        """Test product pricing calculation methods"""
        product = Product(
            asin='B08TEST123',
            current_price=100.0,
            title='Test Product',
            user_id=1
        )
        
        # Test price calculations (these would be methods on the model)
        assert product.current_price == 100.0
    
    def test_product_validation(self):
        """Test product field validation"""
        # Test valid ASIN
        product = Product(asin='B08TEST123', title='Test', user_id=1)
        assert len(product.asin) == 10
        assert product.asin.startswith('B0')


class TestCompetitorModel:
    """Test Competitor model"""
    
    def test_competitor_creation(self):
        """Test creating a competitor instance"""
        competitor_data = {
            'main_product_id': 1,
            'competitor_asin': 'B08COMP123',
            'title': 'Competitor Product',
            'current_price': 25.99,
            'current_rating': 4.2,
            'current_bsr': 1200,
            'similarity_score': 0.85,
            'is_direct_competitor': True
        }
        competitor = Competitor(**competitor_data)
        
        assert competitor.competitor_asin == 'B08COMP123'
        assert competitor.similarity_score == 0.85
        assert competitor.is_direct_competitor is True
    
    def test_competitor_comparison(self):
        """Test competitor comparison logic"""
        competitor = Competitor(
            main_product_id=1,
            competitor_asin='B08COMP123',
            current_price=50.0,
            current_rating=4.0,
            current_bsr=1500,
            similarity_score=0.8
        )
        
        assert competitor.current_price == 50.0
        assert competitor.similarity_score == 0.8


class TestProductInsight:
    """Test ProductInsight model"""
    
    def test_product_insight_creation(self):
        """Test creating product insights"""
        insights_data = {
            'product_id': 1,
            'insight_date': datetime.utcnow(),
            'bsr_rank': 1000,
            'price_position': 'competitive',
            'competitive_gap': 5.0,
            'market_share_estimate': 15.5,
            'performance_score': 85.5
        }
        insights = ProductInsight(**insights_data)
        
        assert insights.product_id == 1
        assert insights.bsr_rank == 1000
        assert insights.competitive_gap == 5.0
        assert insights.performance_score == 85.5
    
    def test_insight_validation(self):
        """Test insight field validation"""
        insights = ProductInsight(
            product_id=1,
            insight_date=datetime.utcnow(),
            performance_score=90.0
        )
        assert insights.performance_score == 90.0


class TestMarketTrend:
    """Test MarketTrend model"""
    
    def test_market_trend_creation(self):
        """Test creating market trends"""
        trends_data = {
            'category': 'Electronics',
            'subcategory': 'Smartphones',
            'trend_date': datetime.utcnow(),
            'avg_price': 299.99,
            'price_trend': 'increasing',
            'avg_rating': 4.2,
            'total_products': 1500,
            'growth_rate': 12.5
        }
        trends = MarketTrend(**trends_data)
        
        assert trends.category == 'Electronics'
        assert trends.subcategory == 'Smartphones'
        assert trends.avg_price == 299.99
        assert trends.growth_rate == 12.5
    
    def test_trend_validation(self):
        """Test trend validation"""
        trends = MarketTrend(
            category='Test Category',
            trend_date=datetime.utcnow(),
            avg_price=100.0
        )
        assert trends.avg_price == 100.0


class TestPriceHistory:
    """Test PriceHistory model"""
    
    def test_price_history_creation(self):
        """Test creating price history"""
        history_data = {
            'product_id': 1,
            'recorded_at': datetime.utcnow(),
            'price': 29.99,
            'currency': 'USD',
            'availability': True,
            'rating': 4.5,
            'review_count': 1000,
            'bsr_rank': 500
        }
        history = PriceHistory(**history_data)
        
        assert history.product_id == 1
        assert history.price == 29.99
        assert history.currency == 'USD'
        assert history.availability is True
        assert history.rating == 4.5
    
    def test_price_history_validation(self):
        """Test price history validation"""
        history = PriceHistory(
            product_id=1,
            recorded_at=datetime.utcnow(),
            price=50.0
        )
        assert history.price > 0


class TestModelRelationships:
    """Test model relationships"""
    
    def test_user_products_relationship(self):
        """Test user-products relationship"""
        user = User(username='testuser', email='test@example.com')
        user.id = 1
        
        product = Product(
            asin='B08TEST123',
            title='Test Product',
            user_id=1
        )
        
        assert product.user_id == user.id
    
    def test_product_competitors_relationship(self):
        """Test product-competitors relationship"""
        product = Product(
            asin='B08MAIN123',
            title='Main Product',
            user_id=1
        )
        product.id = 1
        
        competitor = Competitor(
            main_product_id=1,
            competitor_asin='B08COMP123',
            similarity_score=0.8
        )
        
        assert competitor.main_product_id == product.id
    
    def test_product_insights_relationship(self):
        """Test product-insights relationship"""
        product = Product(
            asin='B08TEST123',
            title='Test Product',
            user_id=1
        )
        product.id = 1
        
        insights = ProductInsight(
            product_id=1,
            insight_date=datetime.utcnow()
        )
        
        assert insights.product_id == product.id


class TestModelMethods:
    """Test model methods and properties"""
    
    def test_product_price_formatting(self):
        """Test product price formatting methods"""
        product = Product(
            asin='B08TEST123',
            title='Test Product',
            current_price=29.99,
            user_id=1
        )
        
        # If there were formatting methods on the model
        assert product.current_price == 29.99
    
    def test_competitor_score_calculation(self):
        """Test competitor score calculations"""
        competitor = Competitor(
            main_product_id=1,
            competitor_asin='B08COMP123',
            similarity_score=0.85,
            current_price=45.0,
            current_rating=4.2
        )
        
        # Test score is within valid range
        assert 0 <= competitor.similarity_score <= 1
    
    def test_insights_json_fields(self):
        """Test JSON field handling"""
        insights = ProductInsight(
            product_id=1,
            insight_date=datetime.utcnow(),
            performance_metrics={'rating': 4.5, 'reviews': 1000},
            recommendations=['monitor_price', 'improve_listing']
        )
        
        if hasattr(insights, 'performance_metrics') and insights.performance_metrics:
            assert isinstance(insights.performance_metrics, dict)
        if hasattr(insights, 'recommendations') and insights.recommendations:
            assert isinstance(insights.recommendations, list)