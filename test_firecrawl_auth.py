#!/usr/bin/env python3
"""
Test Firecrawl API Authentication
"""
import httpx
import asyncio
import json
import sys
sys.path.append('src')

from src.app.core.config import settings


async def test_firecrawl_auth():
    """Test if Firecrawl API key is valid"""
    
    print("🔑 Testing Firecrawl API Authentication")
    print("=" * 60)
    print(f"API Key: {settings.FIRECRAWL_API_KEY[:10]}...{settings.FIRECRAWL_API_KEY[-4:]}")
    print(f"API URL: {settings.FIRECRAWL_API_URL}")
    
    # Test with a simple URL first
    test_url = "https://example.com"
    
    headers = {
        "Authorization": f"Bearer {settings.FIRECRAWL_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "url": test_url,
        "formats": ["markdown"],
        "onlyMainContent": True
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print(f"\n📡 Testing scrape endpoint with: {test_url}")
            response = await client.post(
                f"{settings.FIRECRAWL_API_URL}/v1/scrape",
                json=payload,
                headers=headers
            )
            
            print(f"📊 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ Authentication successful!")
                data = response.json()
                if data.get("success"):
                    print("✅ Scraping successful!")
                    print(f"   Content length: {len(data.get('data', {}).get('markdown', ''))} chars")
                else:
                    print("❌ Scraping failed but auth is OK")
            elif response.status_code == 401:
                print("❌ Authentication failed - Invalid API key")
            elif response.status_code == 400:
                print("❌ Bad Request - Check API format")
                print(f"   Response: {response.text[:200]}")
            elif response.status_code == 429:
                print("⚠️ Rate limit exceeded")
            else:
                print(f"❌ Unexpected status: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False
    
    return True


async def test_firecrawl_amazon():
    """Test Firecrawl with actual Amazon URL"""
    
    print("\n🛒 Testing Amazon Scraping")
    print("=" * 60)
    
    # Test with a simpler Amazon page (Amazon homepage)
    test_url = "https://www.amazon.com"
    
    headers = {
        "Authorization": f"Bearer {settings.FIRECRAWL_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "url": test_url,
        "formats": ["markdown"],
        "onlyMainContent": False,  # Don't filter for Amazon homepage
        "waitFor": 2000  # Wait 2 seconds for page to load
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            print(f"📡 Testing with Amazon homepage: {test_url}")
            response = await client.post(
                f"{settings.FIRECRAWL_API_URL}/v1/scrape",
                json=payload,
                headers=headers
            )
            
            print(f"📊 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    print("✅ Amazon scraping successful!")
                    content = data.get('data', {}).get('markdown', '')
                    print(f"   Content length: {len(content)} chars")
                    if "Amazon" in content:
                        print("   ✅ Amazon content detected")
                else:
                    print("❌ Scraping failed")
                    print(f"   Error: {data.get('error', 'Unknown')}")
            else:
                print(f"❌ Failed with status: {response.status_code}")
                print(f"   Response: {response.text[:300]}")
                
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False
    
    return True


async def main():
    """Run all tests"""
    
    print("🚀 Firecrawl API Testing")
    print("=" * 60)
    
    if not settings.FIRECRAWL_API_KEY:
        print("❌ No Firecrawl API key configured!")
        return False
    
    # Test 1: Basic auth test
    auth_success = await test_firecrawl_auth()
    
    if auth_success:
        # Test 2: Amazon scraping
        await test_firecrawl_amazon()
    
    return auth_success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)