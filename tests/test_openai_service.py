"""Tests for OpenAI service"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from src.app.services.openai_service import OpenAIService


@pytest.fixture
def openai_service():
    """Create OpenAIService instance for testing"""
    with patch('src.app.core.config.settings.OPENAI_API_KEY', 'test-api-key'):
        service = OpenAIService()
        return service


@pytest.fixture
def product_data():
    """Sample product data for testing"""
    return {
        'title': 'Test Product',
        'asin': 'B08TEST123',
        'price': 29.99,
        'bsr': 1234,
        'rating': 4.5,
        'review_count': 100,
        'category': 'Electronics'
    }


@pytest.fixture
def metrics_history():
    """Sample metrics history for testing"""
    return [
        {'date': '2024-01-01', 'price': 25.99, 'bsr': 1500},
        {'date': '2024-01-02', 'price': 27.99, 'bsr': 1400},
        {'date': '2024-01-03', 'price': 29.99, 'bsr': 1234},
    ]


@pytest.fixture
def competitors_data():
    """Sample competitor data for testing"""
    return [
        {
            'title': 'Competitor 1',
            'price': 24.99,
            'bsr': 1000,
            'rating': 4.3,
            'review_count': 150
        },
        {
            'title': 'Competitor 2',
            'price': 34.99,
            'bsr': 2000,
            'rating': 4.7,
            'review_count': 80
        }
    ]


class TestOpenAIService:
    
    @pytest.mark.asyncio
    async def test_generate_product_insights_success(self, openai_service, product_data, metrics_history):
        """Test successful product insights generation"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Product performing well. Consider price optimization."))]
        
        with patch.object(openai_service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            result = await openai_service.generate_product_insights(product_data, metrics_history)
            
            assert "summary" in result
            assert "recommendations" in result
            assert "opportunities" in result
            assert "Product performing well" in result["summary"]
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_product_insights_no_api_key(self):
        """Test insights generation without API key"""
        with patch('src.app.core.config.settings.OPENAI_API_KEY', None):
            service = OpenAIService()
            result = await service.generate_product_insights({}, [])
            
            assert "not available" in result["summary"]
            assert result["recommendations"] == []
            assert result["opportunities"] == []
    
    @pytest.mark.asyncio
    async def test_generate_product_insights_error_handling(self, openai_service, product_data, metrics_history):
        """Test error handling in insights generation"""
        with patch.object(openai_service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = Exception("API Error")
            
            result = await openai_service.generate_product_insights(product_data, metrics_history)
            
            assert "Error generating AI insights" in result["summary"]
            assert result["recommendations"] == []
            assert result["opportunities"] == []
    
    @pytest.mark.asyncio
    async def test_analyze_competitive_landscape(self, openai_service, product_data, competitors_data):
        """Test competitive landscape analysis"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Competitive position: Strong"))]
        
        with patch.object(openai_service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            result = await openai_service.analyze_competitive_landscape(product_data, competitors_data)
            
            assert "analysis" in result
            assert "positioning" in result
            assert "action_items" in result
            assert result["positioning"] == "competitive"  # Based on price comparison logic
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_market_trends(self, openai_service):
        """Test market trend analysis"""
        historical_data = [
            {'date': '2024-01-01', 'avg_price': 25.00, 'avg_bsr': 1500, 'activity_level': 'normal'},
            {'date': '2024-01-02', 'avg_price': 26.00, 'avg_bsr': 1400, 'activity_level': 'high'},
        ]
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Market trending upward. Seasonal patterns detected."))]
        
        with patch.object(openai_service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            result = await openai_service.analyze_market_trends("Electronics", historical_data)
            
            assert "trend_analysis" in result
            assert "key_insights" in result
            assert "predictions" in result
            assert "Market trending upward" in result["trend_analysis"]
    
    def test_determine_positioning(self, openai_service, product_data, competitors_data):
        """Test competitive positioning determination"""
        # Test price leader positioning
        product_data['price'] = 15.00
        positioning = openai_service._determine_positioning(product_data, competitors_data)
        assert positioning == "price_leader"
        
        # Test premium positioning
        product_data['price'] = 50.00
        positioning = openai_service._determine_positioning(product_data, competitors_data)
        assert positioning == "premium"
        
        # Test competitive positioning
        product_data['price'] = 28.00
        positioning = openai_service._determine_positioning(product_data, competitors_data)
        assert positioning == "competitive"
        
        # Test with no competitors
        positioning = openai_service._determine_positioning(product_data, [])
        assert positioning == "no_competition"
    
    def test_extract_recommendations(self, openai_service):
        """Test recommendation extraction from AI response"""
        content = """
        I recommend optimizing your pricing strategy.
        You should consider improving product descriptions.
        Another recommendation is to expand into new markets.
        General advice here.
        Consider updating your inventory levels.
        """
        
        recommendations = openai_service._extract_recommendations(content)
        
        assert len(recommendations) == 3  # Should return top 3
        assert any("recommend" in r.lower() for r in recommendations)
    
    def test_extract_opportunities(self, openai_service):
        """Test opportunity extraction from AI response"""
        content = """
        There's a great opportunity in the mobile segment.
        Potential for growth in international markets.
        You could expand your product line.
        Regular content here.
        Market gap opportunity exists.
        """
        
        opportunities = openai_service._extract_opportunities(content)
        
        assert len(opportunities) == 3  # Should return top 3
        assert any("opportunity" in o.lower() or "potential" in o.lower() for o in opportunities)
    
    def test_extract_action_items(self, openai_service):
        """Test action item extraction"""
        content = """
        - Implement new pricing strategy
        - Update product descriptions
        * Enhance customer service
        Action: Launch marketing campaign
        • Optimize inventory levels
        Regular text here
        """
        
        action_items = openai_service._extract_action_items(content)
        
        assert len(action_items) <= 5
        assert any("-" in item or "•" in item or "*" in item or "action" in item.lower() for item in action_items)
    
    def test_build_insights_prompt(self, openai_service, product_data, metrics_history):
        """Test prompt building for insights"""
        prompt = openai_service._build_insights_prompt(product_data, metrics_history)
        
        assert "Test Product" in prompt
        assert "B08TEST123" in prompt
        assert "$29.99" in prompt
        assert "#1234" in prompt
        assert "4.5" in prompt
        assert "Recent Performance" in prompt
        assert len(metrics_history) > 0
    
    def test_build_competitive_prompt(self, openai_service, product_data, competitors_data):
        """Test prompt building for competitive analysis"""
        prompt = openai_service._build_competitive_prompt(product_data, competitors_data)
        
        assert "Test Product" in prompt
        assert "Main Product" in prompt
        assert "Top Competitors" in prompt
        assert "Competitor 1" in prompt
        assert "Competitor 2" in prompt
        assert "$24.99" in prompt
        assert "$34.99" in prompt
    
    @pytest.mark.asyncio
    async def test_generate_competitive_insights_with_api(self, openai_service):
        """Test competitive insights generation with API"""
        main_product = {'title': 'Main Product', 'price': 30.00}
        competitor_analyses = [
            {
                'price_comparison': {'price_position': 'competitive', 'difference_percent': 5.0},
                'performance_comparison': {'performance_score': 85},
                'market_position': 'strong',
                'competitive_advantages': {
                    'main_product': ['Quality', 'Brand'],
                    'competitor': ['Price', 'Features']
                }
            }
        ]
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(
            content="Market position: Strong. Advantages: Quality and brand recognition. Threats: Price competition."
        ))]
        
        with patch.object(openai_service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            result = await openai_service.generate_competitive_insights(main_product, competitor_analyses)
            
            assert "market_position_analysis" in result
            assert "competitive_advantages" in result
            assert "threat_assessment" in result
            assert "strategic_recommendations" in result
            assert "full_analysis" in result
    
    @pytest.mark.asyncio
    async def test_generate_competitive_insights_without_api(self):
        """Test competitive insights generation without API key"""
        with patch('src.app.core.config.settings.OPENAI_API_KEY', None):
            service = OpenAIService()
            result = await service.generate_competitive_insights({}, [])
            
            assert "requires OpenAI API" in result["market_position_analysis"]
            assert len(result["competitive_advantages"]) > 0
            assert len(result["threat_assessment"]) > 0
            assert len(result["strategic_recommendations"]) > 0