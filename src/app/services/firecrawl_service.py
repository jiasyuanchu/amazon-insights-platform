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
        
        # Build request payload
        payload = {
            "url": url,
            "formats": ["markdown", "html", "extract"],
            "onlyMainContent": True,
            "removeBase64Images": True,
        }
        
        if wait_for_selector:
            payload["waitFor"] = wait_for_selector
        
        if extract_schema:
            payload["extract"] = extract_schema
        
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
                await redis_client.setex(
                    cache_key,
                    int(self.cache_ttl.total_seconds()),
                    json.dumps(data)
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
        
        # Define extraction schema for Amazon products
        extract_schema = {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "selector": "h1#title span"
                },
                "price": {
                    "type": "string", 
                    "selector": "span.a-price-whole"
                },
                "rating": {
                    "type": "string",
                    "selector": "span.a-icon-alt"
                },
                "availability": {
                    "type": "string",
                    "selector": "div#availability span"
                },
                "bsr_rank": {
                    "type": "string",
                    "selector": "#SalesRank"
                },
                "feature_bullets": {
                    "type": "array",
                    "selector": "div#feature-bullets ul.a-unordered-list li span.a-list-item"
                },
                "images": {
                    "type": "array",
                    "selector": "div#altImages ul.a-unordered-list img"
                }
            }
        }
        
        return await self.scrape_url(
            url=url,
            wait_for_selector="h1#title",
            extract_schema=extract_schema
        )
    
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