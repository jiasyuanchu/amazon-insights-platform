"""Tests for Pydantic schemas and validation"""

import pytest
from datetime import datetime
from pydantic import ValidationError
from src.app.schemas.user import UserCreate, UserResponse, UserUpdate
from src.app.schemas.product import (
    ProductCreate, ProductResponse, ProductUpdate,
    ProductInsightResponse, ProductMetricsResponse
)
from src.app.schemas.competitor import (
    CompetitorBase, CompetitorCreate, CompetitorResponse,
    CompetitorDiscoveryRequest, CompetitorAnalysisResponse
)
from src.app.schemas.auth import Token, TokenData


class TestUserSchemas:
    """Test user-related schemas"""
    
    def test_user_create_valid(self):
        """Test valid user creation schema"""
        user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'validpassword123',
            'full_name': 'Test User'
        }
        user = UserCreate(**user_data)
        
        assert user.username == 'testuser'
        assert user.email == 'test@example.com'
        assert user.password == 'validpassword123'
    
    def test_user_create_invalid_email(self):
        """Test invalid email validation"""
        with pytest.raises(ValidationError):
            UserCreate(
                username='testuser',
                email='invalid-email',
                password='password123'
            )
    
    def test_user_response_schema(self):
        """Test user response schema"""
        user_data = {
            'id': 1,
            'username': 'testuser',
            'email': 'test@example.com',
            'full_name': 'Test User',
            'is_active': True,
            'created_at': datetime.utcnow()
        }
        user = UserResponse(**user_data)
        
        assert user.id == 1
        assert user.is_active is True
        assert hasattr(user, 'created_at')
    
    def test_user_update_partial(self):
        """Test partial user update schema"""
        update_data = {
            'full_name': 'Updated Name'
        }
        user_update = UserUpdate(**update_data)
        
        assert user_update.full_name == 'Updated Name'
        assert user_update.username is None  # Optional field


class TestProductSchemas:
    """Test product-related schemas"""
    
    def test_product_create_valid(self):
        """Test valid product creation"""
        product_data = {
            'asin': 'B08TEST123',
            'title': 'Test Product',
            'brand': 'TestBrand',
            'category': 'Electronics'
        }
        product = ProductCreate(**product_data)
        
        assert product.asin == 'B08TEST123'
        assert product.title == 'Test Product'
        assert len(product.asin) == 10
    
    def test_product_create_invalid_asin(self):
        """Test invalid ASIN validation"""
        with pytest.raises(ValidationError):
            ProductCreate(
                asin='INVALID',  # Too short
                title='Test Product'
            )
    
    def test_product_response_schema(self):
        """Test product response schema"""
        product_data = {
            'id': 1,
            'asin': 'B08TEST123',
            'title': 'Test Product',
            'current_price': 29.99,
            'current_rating': 4.5,
            'current_bsr': 1000,
            'is_active': True,
            'created_at': datetime.utcnow(),
            'user_id': 1
        }
        product = ProductResponse(**product_data)
        
        assert product.id == 1
        assert product.current_price == 29.99
        assert product.current_rating == 4.5
    
    def test_product_insight_response_schema(self):
        """Test product insight response schema"""
        insight_data = {
            'id': 1,
            'product_id': 1,
            'insight_date': datetime.utcnow(),
            'bsr_rank': 1000,
            'price_position': 'competitive',
            'competitive_gap': 5.0,
            'performance_score': 85.5,
            'created_at': datetime.utcnow()
        }
        insight = ProductInsightResponse(**insight_data)
        
        assert insight.id == 1
        assert insight.bsr_rank == 1000
        assert insight.performance_score == 85.5
    
    def test_product_metrics_response_schema(self):
        """Test product metrics response schema"""
        metrics_data = {
            'product_id': 1,
            'current_price': 29.99,
            'current_rating': 4.5,
            'current_bsr': 1000,
            'current_review_count': 500,
            'last_updated': datetime.utcnow()
        }
        metrics = ProductMetricsResponse(**metrics_data)
        
        assert metrics.current_price == 29.99
        assert metrics.current_rating == 4.5
        assert metrics.current_bsr == 1000


class TestCompetitorSchemas:
    """Test competitor-related schemas"""
    
    def test_competitor_base_schema(self):
        """Test competitor base schema"""
        competitor_data = {
            'competitor_asin': 'B08COMP123',
            'title': 'Competitor Product',
            'brand': 'CompetitorBrand',
            'category': 'Electronics'
        }
        competitor = CompetitorBase(**competitor_data)
        
        assert competitor.competitor_asin == 'B08COMP123'
        assert competitor.title == 'Competitor Product'
        assert competitor.brand == 'CompetitorBrand'
    
    def test_competitor_create_schema(self):
        """Test competitor create schema"""
        create_data = {
            'main_product_id': 1,
            'competitor_asin': 'B08COMP123',
            'title': 'Competitor Product',
            'similarity_score': 0.85
        }
        competitor = CompetitorCreate(**create_data)
        
        assert competitor.main_product_id == 1
        assert competitor.similarity_score == 0.85
    
    def test_competitor_response_schema(self):
        """Test competitor response schema"""
        competitor_data = {
            'id': 1,
            'main_product_id': 1,
            'competitor_asin': 'B08COMP123',
            'title': 'Competitor Product',
            'current_price': 25.99,
            'current_rating': 4.2,
            'similarity_score': 0.85,
            'is_direct_competitor': True,
            'discovered_at': datetime.utcnow(),
            'created_at': datetime.utcnow()
        }
        competitor = CompetitorResponse(**competitor_data)
        
        assert competitor.competitor_asin == 'B08COMP123'
        assert competitor.similarity_score == 0.85
        assert competitor.is_direct_competitor is True
    
    def test_competitor_discovery_request_schema(self):
        """Test competitor discovery request schema"""
        request_data = {
            'product_id': 1,
            'max_competitors': 10
        }
        request = CompetitorDiscoveryRequest(**request_data)
        
        assert request.product_id == 1
        assert request.max_competitors == 10
    
    def test_competitor_analysis_response_schema(self):
        """Test competitor analysis response schema"""
        analysis_data = {
            'id': 1,
            'product_id': 1,
            'competitor_id': 2,
            'analysis_type': 'pricing_comparison',
            'main_product_advantages': ['Better rating', 'More reviews'],
            'competitor_advantages': ['Lower price'],
            'market_position': 'competitive',
            'recommendations': ['Monitor pricing'],
            'generated_at': datetime.utcnow(),
            'created_at': datetime.utcnow()
        }
        analysis = CompetitorAnalysisResponse(**analysis_data)
        
        assert analysis.product_id == 1
        assert analysis.competitor_id == 2
        assert len(analysis.main_product_advantages) == 2
        assert analysis.market_position == 'competitive'


class TestAuthSchemas:
    """Test authentication schemas"""
    
    def test_token_schema(self):
        """Test token schema"""
        token_data = {
            'access_token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9',
            'token_type': 'bearer',
            'expires_in': 3600,
            'refresh_token': 'refresh_token_value'
        }
        token = Token(**token_data)
        
        assert token.token_type == 'bearer'
        assert token.expires_in == 3600
    
    def test_token_data_schema(self):
        """Test token data schema"""
        token_data = {
            'sub': 'testuser',
            'exp': 1234567890,
            'user_id': 1
        }
        token_data_obj = TokenData(**token_data)
        
        assert token_data_obj.sub == 'testuser'
        assert token_data_obj.user_id == 1


class TestSchemaValidation:
    """Test schema validation rules"""
    
    def test_asin_validation(self):
        """Test ASIN validation across schemas"""
        valid_asins = ['B08TEST123', 'B07VALID12', 'B09EXAMPLE']
        invalid_asins = ['INVALID', '12345', '', 'B08TOOLONG123']
        
        for asin in valid_asins:
            product = ProductCreate(asin=asin, title='Test')
            assert product.asin == asin
        
        for asin in invalid_asins:
            with pytest.raises(ValidationError):
                ProductCreate(asin=asin, title='Test')
    
    def test_price_validation(self):
        """Test price validation in product response"""
        # Valid prices
        valid_price = 29.99
        product = ProductResponse(
            id=1,
            asin='B08TEST123',
            title='Test Product',
            current_price=valid_price,
            user_id=1,
            is_active=True,
            created_at=datetime.utcnow()
        )
        assert product.current_price == valid_price
    
    def test_rating_validation(self):
        """Test rating validation in product response"""
        # Valid rating
        valid_rating = 4.5
        product = ProductResponse(
            id=1,
            asin='B08TEST123',
            title='Test Product',
            current_rating=valid_rating,
            user_id=1,
            is_active=True,
            created_at=datetime.utcnow()
        )
        assert product.current_rating == valid_rating
    
    def test_email_validation(self):
        """Test email validation"""
        valid_emails = [
            'test@example.com',
            'user.name@domain.co.uk',
            'user+tag@example.org'
        ]
        invalid_emails = [
            'invalid-email',
            '@domain.com',
            'user@',
            'user space@domain.com'
        ]
        
        for email in valid_emails:
            user = UserCreate(
                username='test',
                email=email,
                password='password123'
            )
            assert user.email == email
        
        for email in invalid_emails:
            with pytest.raises(ValidationError):
                UserCreate(
                    username='test',
                    email=email,
                    password='password123'
                )


class TestSchemaDefaults:
    """Test schema default values"""
    
    def test_product_create_defaults(self):
        """Test product creation defaults"""
        product = ProductCreate(asin='B08TEST123', title='Test Product')
        
        # Check that optional fields have appropriate defaults
        assert hasattr(product, 'description')  # Should be optional
    
    def test_user_create_defaults(self):
        """Test user creation defaults"""
        user = UserCreate(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
        
        assert hasattr(user, 'full_name')  # Should be optional


class TestSchemaConversions:
    """Test schema type conversions and serialization"""
    
    def test_datetime_serialization(self):
        """Test datetime field handling"""
        now = datetime.utcnow()
        
        user = UserResponse(
            id=1,
            username='test',
            email='test@example.com',
            is_active=True,
            created_at=now
        )
        
        # Test that datetime is properly handled
        assert user.created_at == now
    
    def test_json_serialization(self):
        """Test JSON serialization of schemas"""
        product = ProductResponse(
            id=1,
            asin='B08TEST123',
            title='Test Product',
            user_id=1,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        # Test that schema can be serialized
        json_data = product.model_dump()
        assert isinstance(json_data, dict)
        assert json_data['asin'] == 'B08TEST123'