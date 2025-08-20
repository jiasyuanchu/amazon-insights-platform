#!/usr/bin/env python3
"""
Debug Firecrawl API Errors
"""
import httpx
import asyncio
import json
import sys
sys.path.append('src')

from src.app.core.config import settings


async def debug_firecrawl_request():
    """Debug why Firecrawl is returning 400 errors"""
    
    print("🔍 Debugging Firecrawl API Request")
    print("=" * 60)
    
    # Test with an Amazon product URL
    test_url = "https://www.amazon.com/dp/B0D1XD1ZV3"
    
    headers = {
        "Authorization": f"Bearer {settings.FIRECRAWL_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Try different payload configurations
    payloads = [
        {
            "name": "Basic scrape",
            "payload": {
                "url": test_url
            }
        },
        {
            "name": "With formats",
            "payload": {
                "url": test_url,
                "formats": ["markdown"]
            }
        },
        {
            "name": "With pageOptions",
            "payload": {
                "url": test_url,
                "pageOptions": {
                    "onlyMainContent": True
                }
            }
        },
        {
            "name": "Minimal with wait",
            "payload": {
                "url": test_url,
                "pageOptions": {
                    "waitFor": 2000
                }
            }
        }
    ]
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        for config in payloads:
            print(f"\n📡 Testing: {config['name']}")
            print(f"   Payload: {json.dumps(config['payload'], indent=2)}")
            
            try:
                response = await client.post(
                    f"{settings.FIRECRAWL_API_URL}/v1/scrape",
                    json=config['payload'],
                    headers=headers
                )
                
                print(f"   Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        print("   ✅ Success!")
                        content = data.get('data', {})
                        if content.get('markdown'):
                            print(f"   Content length: {len(content['markdown'])} chars")
                    else:
                        print(f"   ❌ Failed: {data.get('error', 'Unknown')}")
                else:
                    print(f"   ❌ HTTP Error {response.status_code}")
                    # Print full error response for debugging
                    try:
                        error_data = response.json()
                        print(f"   Error details: {json.dumps(error_data, indent=2)}")
                    except:
                        print(f"   Raw response: {response.text[:500]}")
                        
            except Exception as e:
                print(f"   ❌ Exception: {str(e)}")
    
    # Also test with a non-Amazon URL to see if it's Amazon-specific
    print("\n" + "=" * 60)
    print("📡 Testing with non-Amazon URL for comparison")
    
    test_urls = [
        ("Example.com", "https://example.com"),
        ("Google", "https://www.google.com"),
        ("Wikipedia", "https://en.wikipedia.org/wiki/Web_scraping")
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for name, url in test_urls:
            print(f"\n   Testing {name}: {url}")
            
            payload = {
                "url": url,
                "formats": ["markdown"]
            }
            
            try:
                response = await client.post(
                    f"{settings.FIRECRAWL_API_URL}/v1/scrape",
                    json=payload,
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        print(f"   ✅ Success! Content length: {len(data.get('data', {}).get('markdown', ''))} chars")
                    else:
                        print(f"   ❌ Failed: {data.get('error', 'Unknown')}")
                else:
                    print(f"   ❌ HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ Exception: {str(e)}")


async def main():
    """Run debug tests"""
    
    print("🚀 Firecrawl API Debug Tool")
    print("=" * 60)
    
    if not settings.FIRECRAWL_API_KEY:
        print("❌ No Firecrawl API key configured!")
        return False
    
    await debug_firecrawl_request()
    
    return True


if __name__ == "__main__":
    asyncio.run(main())