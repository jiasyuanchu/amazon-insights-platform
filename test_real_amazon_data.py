#!/usr/bin/env python3
"""
Test Real Amazon Data Scraping with Firecrawl API
"""
import asyncio
import json
import sys
sys.path.append('src')

from src.app.core.config import settings
from src.app.services.firecrawl_service import FirecrawlService
from src.app.services.product_service import ProductService
from src.app.services.competitor_service import CompetitorService
from src.app.services.openai_service import OpenAIService
from src.app.core.database import get_db
import httpx


async def test_firecrawl_scraping():
    """Test Firecrawl API with real Amazon product URLs"""
    
    print("🔥 Testing Firecrawl API for Real Amazon Data Scraping")
    print("=" * 60)
    
    # Test products (popular categories)
    test_products = [
        {
            "name": "Wireless Earbuds",
            "url": "https://www.amazon.com/dp/B0D1XD1ZV3",  # Apple AirPods Pro
            "category": "Electronics"
        },
        {
            "name": "Yoga Mat", 
            "url": "https://www.amazon.com/dp/B01LP0VBDI",  # Gaiam Yoga Mat
            "category": "Sports & Outdoors"
        },
        {
            "name": "Kitchen Knife Set",
            "url": "https://www.amazon.com/dp/B01NBCPN1P",  # McCook Knife Set
            "category": "Kitchen"
        }
    ]
    
    firecrawl_service = FirecrawlService()
    openai_service = OpenAIService()
    
    successful_scrapes = []
    failed_scrapes = []
    
    for product in test_products:
        print(f"\n📦 Testing: {product['name']}")
        print(f"   URL: {product['url']}")
        print(f"   Category: {product['category']}")
        
        try:
            # Scrape product data
            print("   ⏳ Scraping product data...")
            # Extract ASIN from URL
            asin = product['url'].split('/dp/')[-1].split('/')[0].split('?')[0]
            scraped_data = await firecrawl_service.scrape_amazon_product(asin)
            
            if scraped_data:
                print("   ✅ Successfully scraped!")
                
                # Extract key information
                title = scraped_data.get('title', 'N/A')
                price = scraped_data.get('price', 'N/A')
                rating = scraped_data.get('rating', 'N/A')
                reviews = scraped_data.get('review_count', 'N/A')
                availability = scraped_data.get('availability', 'N/A')
                
                print(f"   📊 Product Details:")
                print(f"      Title: {title[:60]}...")
                print(f"      Price: {price}")
                print(f"      Rating: {rating}")
                print(f"      Reviews: {reviews}")
                print(f"      Availability: {availability}")
                
                # Store successful scrape
                successful_scrapes.append({
                    "name": product['name'],
                    "url": product['url'],
                    "data": scraped_data
                })
                
                # Test AI insights generation
                if scraped_data.get('asin'):
                    print("   🤖 Generating AI insights...")
                    insights = await openai_service.generate_product_insights(
                        scraped_data, 
                        []  # Empty history for new product
                    )
                    if insights and insights.get('summary'):
                        print(f"      AI Summary: {insights['summary'][:100]}...")
                
            else:
                print("   ❌ Failed to scrape product data")
                failed_scrapes.append(product)
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            failed_scrapes.append(product)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Scraping Summary:")
    print(f"   ✅ Successful: {len(successful_scrapes)}/{len(test_products)}")
    print(f"   ❌ Failed: {len(failed_scrapes)}/{len(test_products)}")
    
    if successful_scrapes:
        print("\n🎯 Successfully Scraped Products:")
        for item in successful_scrapes:
            print(f"   - {item['name']}: {item['data'].get('title', 'N/A')[:50]}...")
    
    if failed_scrapes:
        print("\n❌ Failed Products:")
        for item in failed_scrapes:
            print(f"   - {item['name']}: {item['url']}")
    
    return len(successful_scrapes) > 0


async def test_competitor_discovery():
    """Test competitor discovery with real data"""
    
    print("\n🔍 Testing Competitor Discovery")
    print("=" * 60)
    
    # Use a main product URL
    main_product_url = "https://www.amazon.com/dp/B0D1XD1ZV3"  # AirPods Pro
    
    firecrawl_service = FirecrawlService()
    
    print("📦 Main Product: Apple AirPods Pro")
    print(f"   URL: {main_product_url}")
    
    try:
        # Scrape main product
        print("   ⏳ Scraping main product...")
        # Extract ASIN from URL
        asin = main_product_url.split('/dp/')[-1].split('/')[0].split('?')[0]
        main_product_data = await firecrawl_service.scrape_amazon_product(asin)
        
        if main_product_data:
            print("   ✅ Main product scraped successfully")
            
            # Search for competitors
            print("\n🔍 Searching for competitors...")
            search_query = "wireless earbuds noise cancelling"
            
            # In a real scenario, we would search Amazon for similar products
            # For now, we'll use predefined competitor URLs
            competitor_urls = [
                "https://www.amazon.com/dp/B0B2RJPJ2F",  # Sony WF-1000XM4
                "https://www.amazon.com/dp/B08G1Y1V26",  # Bose QuietComfort
                "https://www.amazon.com/dp/B085VQFHKP",  # Samsung Galaxy Buds
            ]
            
            competitors = []
            for url in competitor_urls:
                print(f"   ⏳ Scraping competitor: {url}")
                try:
                    # Extract ASIN from URL
                    comp_asin = url.split('/dp/')[-1].split('/')[0].split('?')[0]
                    comp_data = await firecrawl_service.scrape_amazon_product(comp_asin)
                    if comp_data:
                        competitors.append(comp_data)
                        print(f"      ✅ Scraped: {comp_data.get('title', 'Unknown')[:40]}...")
                except Exception as e:
                    print(f"      ❌ Failed: {str(e)}")
            
            print(f"\n📊 Found {len(competitors)} competitors")
            
            # Competitive analysis
            if competitors:
                print("\n📈 Competitive Analysis:")
                
                # Safe price parsing
                def parse_price(price_str):
                    if not price_str or price_str == 'N/A':
                        return 0.0
                    try:
                        return float(str(price_str).replace('$', '').replace(',', ''))
                    except:
                        return 0.0
                
                main_price = parse_price(main_product_data.get('price', '0'))
                
                for comp in competitors:
                    comp_price = parse_price(comp.get('price', '0'))
                    price_diff = main_price - comp_price if main_price and comp_price else 0
                    
                    print(f"\n   📦 {comp.get('title', 'Unknown')[:40]}...")
                    print(f"      Price: ${comp_price:.2f}")
                    print(f"      Price Difference: ${price_diff:.2f}")
                    print(f"      Rating: {comp.get('rating', 'N/A')}")
                    print(f"      Reviews: {comp.get('review_count', 'N/A')}")
            
            return True
        else:
            print("   ❌ Failed to scrape main product")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False


async def main():
    """Run all tests"""
    
    print("🚀 Starting Real Amazon Data Testing Suite")
    print("=" * 60)
    
    # Check API keys
    print("🔑 Checking API Keys...")
    print(f"   Firecrawl API: {'✅ Configured' if settings.FIRECRAWL_API_KEY else '❌ Missing'}")
    print(f"   OpenAI API: {'✅ Configured' if settings.OPENAI_API_KEY else '❌ Missing'}")
    
    if not settings.FIRECRAWL_API_KEY:
        print("\n❌ Firecrawl API key is not configured!")
        print("   Please set FIRECRAWL_API_KEY in your .env file")
        return False
    
    # Test 1: Basic scraping
    scraping_success = await test_firecrawl_scraping()
    
    # Test 2: Competitor discovery
    competitor_success = await test_competitor_discovery()
    
    # Summary
    print("\n" + "=" * 60)
    print("🎯 Test Results Summary:")
    print(f"   Product Scraping: {'✅ Passed' if scraping_success else '❌ Failed'}")
    print(f"   Competitor Discovery: {'✅ Passed' if competitor_success else '❌ Failed'}")
    
    if scraping_success and competitor_success:
        print("\n🎉 All tests passed! Real Amazon data scraping is working!")
        return True
    else:
        print("\n⚠️ Some tests failed. Please check the errors above.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)