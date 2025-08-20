"""Tests for Firecrawl service"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import httpx
from datetime import timedelta

from src.app.services.firecrawl_service import FirecrawlService


@pytest.fixture
def firecrawl_service():
    """Create FirecrawlService instance for testing"""
    return FirecrawlService()


@pytest.fixture
def mock_response():
    """Create mock Firecrawl API response"""
    return {
        "success": True,
        "data": {
            "markdown": """
            # Product Title - Amazing Product
            
            Price: $29.99
            Rating: 4.5 out of 5 stars
            1,234 customer reviews
            In Stock
            
            ## Product Features
            - Feature 1
            - Feature 2
            - Feature 3
            """
        }
    }


class TestFirecrawlService:
    
    @pytest.mark.asyncio
    async def test_scrape_url_success(self, firecrawl_service, mock_response):
        """Test successful URL scraping"""
        with patch.object(firecrawl_service.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value.json.return_value = mock_response
            mock_post.return_value.raise_for_status = Mock()
            
            result = await firecrawl_service.scrape_url("https://example.com", use_cache=False)
            
            assert result["success"] is True
            assert "markdown" in result["data"]
            mock_post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_scrape_amazon_product(self, firecrawl_service, mock_response):
        """Test Amazon product scraping"""
        with patch.object(firecrawl_service, 'scrape_url', new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = mock_response
            
            result = await firecrawl_service.scrape_amazon_product("B08N5WRWNW")
            
            assert result["success"] is True
            assert result["asin"] == "B08N5WRWNW"
            assert result["price"] == "$29.99"
            assert "4.5 stars" in result["rating"]
            assert result["availability"] == "In Stock"
    
    def test_extract_title_from_markdown(self, firecrawl_service):
        """Test title extraction from markdown"""
        markdown = "# Amazing Product Title\nSome content here"
        title = firecrawl_service._extract_title_from_markdown(markdown)
        assert title == "Amazing Product Title"
        
        # Test with no title
        markdown = "No heading here"
        title = firecrawl_service._extract_title_from_markdown(markdown)
        assert title == "Unknown Product"
    
    def test_extract_price_from_markdown(self, firecrawl_service):
        """Test price extraction from markdown"""
        markdown = "Price: $49.99\nOther content"
        price = firecrawl_service._extract_price_from_markdown(markdown)
        assert price == "$49.99"
        
        # Test with comma in price
        markdown = "Price: $1,299.00"
        price = firecrawl_service._extract_price_from_markdown(markdown)
        assert price == "$1,299.00"
        
        # Test with no price
        markdown = "No price information"
        price = firecrawl_service._extract_price_from_markdown(markdown)
        assert price == "N/A"
    
    def test_extract_rating_from_markdown(self, firecrawl_service):
        """Test rating extraction from markdown"""
        markdown = "Rating: 4.5 out of 5 stars"
        rating = firecrawl_service._extract_rating_from_markdown(markdown)
        assert rating == "4.5 stars"
        
        # Test alternate format
        markdown = "4.2 stars from customers"
        rating = firecrawl_service._extract_rating_from_markdown(markdown)
        assert rating == "4.2 stars"
        
        # Test no rating
        markdown = "No rating information"
        rating = firecrawl_service._extract_rating_from_markdown(markdown)
        assert rating == "N/A"
    
    def test_extract_review_count_from_markdown(self, firecrawl_service):
        """Test review count extraction from markdown"""
        markdown = "1,234 customer reviews"
        count = firecrawl_service._extract_review_count_from_markdown(markdown)
        assert count == "1,234"
        
        # Test with ratings word
        markdown = "567 ratings"
        count = firecrawl_service._extract_review_count_from_markdown(markdown)
        assert count == "567"
        
        # Test no reviews
        markdown = "No review information"
        count = firecrawl_service._extract_review_count_from_markdown(markdown)
        assert count == "0"
    
    def test_extract_availability_from_markdown(self, firecrawl_service):
        """Test availability extraction from markdown"""
        markdown = "In stock and ready to ship"
        availability = firecrawl_service._extract_availability_from_markdown(markdown)
        assert availability == "In Stock"
        
        markdown = "Currently out of stock"
        availability = firecrawl_service._extract_availability_from_markdown(markdown)
        assert availability == "Out of Stock"
        
        markdown = "This item is currently unavailable"
        availability = firecrawl_service._extract_availability_from_markdown(markdown)
        assert availability == "Currently Unavailable"
        
        markdown = "Available for purchase"
        availability = firecrawl_service._extract_availability_from_markdown(markdown)
        assert availability == "Available"
        
        markdown = "No availability info"
        availability = firecrawl_service._extract_availability_from_markdown(markdown)
        assert availability == "Unknown"
    
    def test_generate_cache_key(self, firecrawl_service):
        """Test cache key generation"""
        key1 = firecrawl_service._generate_cache_key("https://example.com")
        key2 = firecrawl_service._generate_cache_key("https://example.com")
        assert key1 == key2  # Same URL should generate same key
        
        key3 = firecrawl_service._generate_cache_key("https://different.com")
        assert key1 != key3  # Different URLs should generate different keys
        
        # Test with parameters
        key4 = firecrawl_service._generate_cache_key("https://example.com", {"param": "value"})
        assert key1 != key4  # Same URL with params should be different
    
    @pytest.mark.asyncio
    async def test_batch_scrape(self, firecrawl_service):
        """Test batch scraping functionality"""
        urls = [
            "https://example1.com",
            "https://example2.com",
            "https://example3.com"
        ]
        
        with patch.object(firecrawl_service, 'scrape_url', new_callable=AsyncMock) as mock_scrape:
            mock_scrape.side_effect = [
                {"url": urls[0], "success": True, "data": {"content": "page1"}},
                {"url": urls[1], "success": True, "data": {"content": "page2"}},
                {"url": urls[2], "success": False, "error": "Failed"},
            ]
            
            results = await firecrawl_service.batch_scrape(urls, max_concurrent=2)
            
            assert len(results) == 3
            assert results[0]["success"] is True
            assert results[1]["success"] is True
            assert results[2]["success"] is False
            assert mock_scrape.call_count == 3
    
    @pytest.mark.asyncio
    async def test_scrape_url_with_retry(self, firecrawl_service):
        """Test retry mechanism on failure"""
        with patch.object(firecrawl_service.client, 'post', new_callable=AsyncMock) as mock_post:
            # First two calls fail, third succeeds
            mock_post.side_effect = [
                httpx.HTTPStatusError("Error", request=Mock(), response=Mock(status_code=500)),
                httpx.HTTPStatusError("Error", request=Mock(), response=Mock(status_code=500)),
                AsyncMock(json=AsyncMock(return_value={"success": True, "data": {}}),
                         raise_for_status=Mock())()
            ]
            
            result = await firecrawl_service.scrape_url("https://example.com", use_cache=False)
            
            assert result["success"] is True
            assert mock_post.call_count == 3  # Should retry 3 times
    
    @pytest.mark.asyncio
    async def test_scrape_amazon_product_error_handling(self, firecrawl_service):
        """Test error handling in Amazon product scraping"""
        with patch.object(firecrawl_service, 'scrape_url', new_callable=AsyncMock) as mock_scrape:
            mock_scrape.side_effect = Exception("Network error")
            
            result = await firecrawl_service.scrape_amazon_product("B08N5WRWNW")
            
            assert result["success"] is False
            assert "Network error" in result["error"]
            assert result["asin"] == "B08N5WRWNW"