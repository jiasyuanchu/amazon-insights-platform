"""Firecrawl API service wrapper for web scraping"""

from typing import Dict, Any, Optional, List
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog
from src.app.core.config import settings
from src.app.core.redis import redis_client
import json
import hashlib
from datetime import timedelta

logger = structlog.get_logger()


class FirecrawlService:
    """Service for interacting with Firecrawl API"""
    
    def __init__(self):
        self.api_key = settings.FIRECRAWL_API_KEY
        self.base_url = settings.FIRECRAWL_API_URL
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
        self.cache_ttl = timedelta(hours=24)  # 24 hour cache
    
    def _generate_cache_key(self, url: str, params: Optional[Dict] = None) -> str:
        """Generate cache key for URL and parameters"""
        cache_data = f"{url}:{json.dumps(params or {}, sort_keys=True)}"
        return f"firecrawl:{hashlib.md5(cache_data.encode()).hexdigest()}"
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def scrape_url(
        self, 
        url: str, 
        wait_for_selector: Optional[str] = None,
        extract_schema: Optional[Dict] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Scrape a URL using Firecrawl API
        
        Args:
            url: The URL to scrape
            wait_for_selector: CSS selector to wait for before scraping
            extract_schema: Schema for structured data extraction
            use_cache: Whether to use cached results
        
        Returns:
            Scraped data from Firecrawl
        """
        # Check cache first
        if use_cache:
            cache_key = self._generate_cache_key(url, {"selector": wait_for_selector})
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                logger.info("firecrawl_cache_hit", url=url)
                return json.loads(cached_data)
        
        # Build request payload for Firecrawl v1 API
        payload = {
            "url": url,
            "formats": ["markdown"]  # v1 API uses simplified formats
        }
        
        # v1 API doesn't support these old parameters
        # Instead, we'll rely on markdown parsing
        
        try:
            logger.info("firecrawl_scraping", url=url)
            response = await self.client.post(
                f"{self.base_url}/v1/scrape",
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Cache successful response
            if use_cache and data.get("success"):
                await redis_client.set(
                    cache_key,
                    json.dumps(data),
                    expire=int(self.cache_ttl.total_seconds())
                )
            
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error("firecrawl_error", 
                        url=url, 
                        status_code=e.response.status_code,
                        error=str(e))
            raise
        except Exception as e:
            logger.error("firecrawl_unexpected_error", url=url, error=str(e))
            raise
    
    async def scrape_amazon_product(self, asin: str) -> Dict[str, Any]:
        """
        Specialized method to scrape Amazon product page
        
        Args:
            asin: Amazon Standard Identification Number
        
        Returns:
            Structured product data
        """
        url = f"https://www.amazon.com/dp/{asin}"
        
        try:
            # Scrape without complex schema first
            result = await self.scrape_url(
                url=url,
                wait_for_selector=None,  # Don't wait for specific selector
                extract_schema=None,  # Don't use schema extraction for now
                use_cache=True
            )
            
            if result and result.get("success"):
                data = result.get("data", {})
                markdown_content = data.get("markdown", "")
                
                # Parse basic info from markdown
                parsed_data = {
                    "asin": asin,
                    "url": url,
                    "title": self._extract_title_from_markdown(markdown_content),
                    "price": self._extract_price_from_markdown(markdown_content),
                    "rating": self._extract_rating_from_markdown(markdown_content),
                    "review_count": self._extract_review_count_from_markdown(markdown_content),
                    "availability": self._extract_availability_from_markdown(markdown_content),
                    "raw_markdown": markdown_content[:1000],  # Store first 1000 chars for reference
                    "success": True
                }
                
                return parsed_data
            else:
                logger.warning("firecrawl_scrape_failed", asin=asin, url=url)
                return {
                    "asin": asin,
                    "url": url,
                    "success": False,
                    "error": result.get("error", "Unknown error")
                }
                
        except Exception as e:
            logger.error("scrape_amazon_product_error", asin=asin, error=str(e))
            return {
                "asin": asin,
                "url": url,
                "success": False,
                "error": str(e)
            }
    
    def _extract_title_from_markdown(self, markdown: str) -> str:
        """Extract product title from markdown content"""
        import re
        # Look for common title patterns
        patterns = [
            r'#\s+([^\n]+)',  # H1 heading
            r'##\s+([^\n]+)',  # H2 heading
            r'\*\*([^*]+)\*\*',  # Bold text (often titles)
        ]
        
        for pattern in patterns:
            match = re.search(pattern, markdown[:500])  # Search in first 500 chars
            if match:
                title = match.group(1).strip()
                if len(title) > 10 and len(title) < 200:  # Reasonable title length
                    return title
        
        return "Unknown Product"
    
    def _extract_price_from_markdown(self, markdown: str) -> str:
        """Extract price from markdown content"""
        import re
        # Look for price patterns
        patterns = [
            r'\$([0-9,]+\.?[0-9]*)',  # $123.45 or $1,234
            r'USD\s*([0-9,]+\.?[0-9]*)',  # USD 123.45
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, markdown)
            if matches:
                # Return the first reasonable price found
                for price in matches:
                    price_float = float(price.replace(',', ''))
                    if 0.01 <= price_float <= 100000:  # Reasonable price range
                        return f"${price}"
        
        return "N/A"
    
    def _extract_rating_from_markdown(self, markdown: str) -> str:
        """Extract rating from markdown content"""
        import re
        # Look for rating patterns
        patterns = [
            r'([0-9]\.?[0-9]?)\s*out of\s*5',  # 4.5 out of 5
            r'([0-9]\.?[0-9]?)\s*stars?',  # 4.5 stars
            r'Rating:\s*([0-9]\.?[0-9]?)',  # Rating: 4.5
        ]
        
        for pattern in patterns:
            match = re.search(pattern, markdown, re.IGNORECASE)
            if match:
                rating = match.group(1)
                try:
                    rating_float = float(rating)
                    if 0 <= rating_float <= 5:
                        return f"{rating} stars"
                except:
                    pass
        
        return "N/A"
    
    def _extract_review_count_from_markdown(self, markdown: str) -> str:
        """Extract review count from markdown content"""
        import re
        # Look for review count patterns
        patterns = [
            r'([0-9,]+)\s*(?:customer\s*)?reviews?',  # 1,234 reviews or 1,234 customer reviews
            r'([0-9,]+)\s*ratings?',  # 1,234 ratings
        ]
        
        for pattern in patterns:
            match = re.search(pattern, markdown, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return "0"
    
    def _extract_availability_from_markdown(self, markdown: str) -> str:
        """Extract availability from markdown content"""
        if "in stock" in markdown.lower():
            return "In Stock"
        elif "out of stock" in markdown.lower():
            return "Out of Stock"
        elif "currently unavailable" in markdown.lower():
            return "Currently Unavailable"
        elif "available" in markdown.lower():
            return "Available"
        
        return "Unknown"
    
    async def batch_scrape(
        self, 
        urls: List[str], 
        max_concurrent: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Scrape multiple URLs concurrently
        
        Args:
            urls: List of URLs to scrape
            max_concurrent: Maximum concurrent requests
        
        Returns:
            List of scraped data
        """
        import asyncio
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def scrape_with_semaphore(url: str):
            async with semaphore:
                try:
                    return await self.scrape_url(url)
                except Exception as e:
                    logger.error("batch_scrape_error", url=url, error=str(e))
                    return {"url": url, "error": str(e), "success": False}
        
        tasks = [scrape_with_semaphore(url) for url in urls]
        return await asyncio.gather(*tasks)
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Singleton instance
firecrawl_service = FirecrawlService()