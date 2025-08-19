#!/usr/bin/env python3
"""
Amazon Insights Platform API Usage Examples

This script demonstrates how to use the Amazon Insights Platform API
for various use cases including product tracking, competitor analysis,
and generating intelligence reports.
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class AmazonInsightsClient:
    """Client for Amazon Insights Platform API"""
    
    def __init__(self, base_url: str = "http://localhost:8000/api/v1"):
        self.base_url = base_url
        self.session = None
        self.access_token = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def login(self, username: str, password: str) -> bool:
        """Login and get access token"""
        data = aiohttp.FormData()
        data.add_field('username', username)
        data.add_field('password', password)
        
        async with self.session.post(f"{self.base_url}/auth/token", data=data) as resp:
            if resp.status == 200:
                result = await resp.json()
                self.access_token = result["access_token"]
                self.session.headers.update({
                    "Authorization": f"Bearer {self.access_token}"
                })
                return True
            else:
                error = await resp.text()
                print(f"Login failed: {error}")
                return False
    
    async def register(self, username: str, email: str, password: str) -> bool:
        """Register a new user"""
        data = {
            "username": username,
            "email": email,
            "password": password
        }
        
        async with self.session.post(f"{self.base_url}/auth/register", json=data) as resp:
            if resp.status == 201:
                return True
            else:
                error = await resp.text()
                print(f"Registration failed: {error}")
                return False
    
    async def add_product(self, asin: str, title: str, brand: str = None, 
                         category: str = None, description: str = None) -> Optional[Dict]:
        """Add a product for tracking"""
        data = {
            "asin": asin,
            "title": title,
            "brand": brand,
            "category": category,
            "description": description
        }
        
        async with self.session.post(f"{self.base_url}/products/", json=data) as resp:
            if resp.status in [200, 201]:
                return await resp.json()
            else:
                error = await resp.text()
                print(f"Failed to add product: {error}")
                return None
    
    async def get_products(self) -> List[Dict]:
        """Get all tracked products"""
        async with self.session.get(f"{self.base_url}/products/") as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                return []
    
    async def discover_competitors(self, product_id: int, max_competitors: int = 5) -> List[Dict]:
        """Discover competitors for a product"""
        data = {
            "product_id": product_id,
            "max_competitors": max_competitors
        }
        
        async with self.session.post(f"{self.base_url}/competitors/discover", json=data) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                error = await resp.text()
                print(f"Failed to discover competitors: {error}")
                return []
    
    async def get_competitive_summary(self, product_id: int) -> Optional[Dict]:
        """Get competitive summary for a product"""
        async with self.session.get(f"{self.base_url}/competitors/product/{product_id}/competitive-summary") as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                return None
    
    async def analyze_all_competitors(self, product_id: int) -> Optional[Dict]:
        """Analyze all competitors for a product"""
        async with self.session.post(f"{self.base_url}/competitors/product/{product_id}/analyze-all") as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                error = await resp.text()
                print(f"Failed to analyze competitors: {error}")
                return None
    
    async def generate_intelligence_report(self, product_id: int) -> Optional[Dict]:
        """Generate AI-powered intelligence report"""
        async with self.session.post(f"{self.base_url}/competitors/product/{product_id}/intelligence-report") as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                error = await resp.text()
                print(f"Failed to generate intelligence report: {error}")
                return None
    
    async def get_market_overview(self, category: str = None) -> Optional[Dict]:
        """Get market overview"""
        url = f"{self.base_url}/competitors/insights/market-overview"
        if category:
            url += f"?category={category}"
            
        async with self.session.get(url) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                return None
    
    async def create_alert(self, product_id: int, alert_type: str, 
                          threshold_value: float, threshold_type: str) -> Optional[Dict]:
        """Create an alert configuration"""
        data = {
            "alert_type": alert_type,
            "threshold_value": threshold_value,
            "threshold_type": threshold_type,
            "is_active": True
        }
        
        async with self.session.post(f"{self.base_url}/products/{product_id}/alerts", json=data) as resp:
            if resp.status == 201:
                return await resp.json()
            else:
                error = await resp.text()
                print(f"Failed to create alert: {error}")
                return None


# Example usage scenarios

async def example_1_basic_product_tracking():
    """Example 1: Basic product tracking workflow"""
    print("=== Example 1: Basic Product Tracking ===")
    
    async with AmazonInsightsClient() as client:
        # Login with demo account
        if not await client.login("demo_seller", "demopassword123"):
            print("❌ Login failed")
            return
        
        print("✅ Logged in successfully")
        
        # Add a new product
        product = await client.add_product(
            asin="B08N5TEST1",
            title="Example Product for API Demo",
            brand="DemoTech",
            category="Electronics",
            description="A sample product for API demonstration"
        )
        
        if product:
            print(f"✅ Added product: {product['title']}")
            product_id = product['id']
            
            # Set up price alert
            alert = await client.create_alert(
                product_id=product_id,
                alert_type="price_change",
                threshold_value=15.0,
                threshold_type="percentage"
            )
            
            if alert:
                print("✅ Created price change alert (15% threshold)")
            
            # Get all products
            products = await client.get_products()
            print(f"📦 Total products tracked: {len(products)}")
        else:
            print("❌ Failed to add product")


async def example_2_competitor_analysis():
    """Example 2: Comprehensive competitor analysis"""
    print("\n=== Example 2: Competitor Analysis ===")
    
    async with AmazonInsightsClient() as client:
        if not await client.login("demo_seller", "demopassword123"):
            return
        
        # Get existing products
        products = await client.get_products()
        if not products:
            print("❌ No products found")
            return
        
        product = products[0]  # Use first product
        product_id = product['id']
        
        print(f"📦 Analyzing product: {product['title']}")
        
        # Discover competitors
        competitors = await client.discover_competitors(product_id, max_competitors=3)
        print(f"🔍 Discovered {len(competitors)} competitors")
        
        # Get competitive summary
        summary = await client.get_competitive_summary(product_id)
        if summary:
            print(f"📊 Competitive Summary:")
            print(f"   - Total competitors: {summary['total_competitors']}")
            print(f"   - Price position: {summary['price_position']}")
            print(f"   - Competitive strength: {summary['competitive_strength']}")
        
        # Perform comprehensive analysis
        analysis = await client.analyze_all_competitors(product_id)
        if analysis:
            print(f"🧠 Comprehensive Analysis:")
            print(f"   - Analyzed at: {analysis['analyzed_at']}")
            print(f"   - Competitors analyzed: {analysis['total_competitors']}")
            
            if 'strategic_recommendations' in analysis:
                print("   - Top recommendations:")
                for i, rec in enumerate(analysis['strategic_recommendations'][:3], 1):
                    print(f"     {i}. {rec.get('action', 'N/A')}")


async def example_3_intelligence_reports():
    """Example 3: AI-powered intelligence reports"""
    print("\n=== Example 3: AI Intelligence Reports ===")
    
    async with AmazonInsightsClient() as client:
        if not await client.login("demo_seller", "demopassword123"):
            return
        
        products = await client.get_products()
        if not products:
            return
        
        product = products[0]
        product_id = product['id']
        
        print(f"🤖 Generating AI intelligence report for: {product['title'][:50]}...")
        
        # Generate intelligence report
        report = await client.generate_intelligence_report(product_id)
        if report:
            print("✅ Intelligence Report Generated:")
            
            if 'intelligence_summary' in report:
                summary = report['intelligence_summary']
                print(f"   Market Position: {summary.get('market_position', 'N/A')[:100]}...")
                
                if 'key_advantages' in summary:
                    print("   Key Advantages:")
                    for adv in summary['key_advantages'][:3]:
                        print(f"     • {adv}")
                
                if 'priority_actions' in summary:
                    print("   Priority Actions:")
                    for action in summary['priority_actions'][:3]:
                        print(f"     • {action}")
            
            if 'ai_competitive_intelligence' in report:
                ai_insights = report['ai_competitive_intelligence']
                if 'strategic_recommendations' in ai_insights:
                    print(f"   AI Strategic Insights: {len(ai_insights['strategic_recommendations'])} recommendations")
        else:
            print("❌ Failed to generate intelligence report")


async def example_4_market_overview():
    """Example 4: Market overview and trends"""
    print("\n=== Example 4: Market Overview ===")
    
    async with AmazonInsightsClient() as client:
        if not await client.login("demo_seller", "demopassword123"):
            return
        
        # Get overall market overview
        overview = await client.get_market_overview()
        if overview:
            print("🏪 Market Overview:")
            print(f"   Products tracked: {overview['total_products_tracked']}")
            print(f"   Competitors tracked: {overview['total_competitors_tracked']}")
            
            if 'market_statistics' in overview:
                stats = overview['market_statistics']
                print(f"   Average product price: ${stats.get('average_product_price', 0):.2f}")
                print(f"   Average competitor price: ${stats.get('average_competitor_price', 0):.2f}")
                print(f"   Price competitiveness: {stats.get('price_competitiveness', 'unknown')}")
            
            if 'categories_tracked' in overview:
                categories = overview['categories_tracked']
                print(f"   Categories: {', '.join(categories)}")
        
        # Get category-specific overview
        category_overview = await client.get_market_overview(category="Electronics")
        if category_overview:
            print("\n📱 Electronics Category Overview:")
            print(f"   Products: {category_overview['total_products_tracked']}")
            print(f"   Competitors: {category_overview['total_competitors_tracked']}")


async def example_5_automation_workflow():
    """Example 5: Automated monitoring workflow"""
    print("\n=== Example 5: Automation Workflow ===")
    
    async with AmazonInsightsClient() as client:
        if not await client.login("demo_seller", "demopassword123"):
            return
        
        products = await client.get_products()
        
        print(f"🔄 Setting up automated monitoring for {len(products)} products...")
        
        for product in products[:3]:  # Limit to first 3 products
            product_id = product['id']
            
            print(f"\n📦 Setting up automation for: {product['title'][:40]}...")
            
            # Create multiple alert types
            alerts = [
                ("price_change", 10.0, "percentage", "Price change > 10%"),
                ("bsr_change", 25.0, "percentage", "BSR change > 25%"),
                ("rating_drop", 0.2, "absolute", "Rating drop > 0.2"),
            ]
            
            for alert_type, threshold, threshold_type, description in alerts:
                alert = await client.create_alert(
                    product_id=product_id,
                    alert_type=alert_type,
                    threshold_value=threshold,
                    threshold_type=threshold_type
                )
                
                if alert:
                    print(f"   ✅ {description}")
                else:
                    print(f"   ❌ Failed to create {alert_type} alert")
            
            # Discover and analyze competitors
            competitors = await client.discover_competitors(product_id)
            if competitors:
                print(f"   🔍 Discovered {len(competitors)} competitors")
                
                # Quick competitive analysis
                summary = await client.get_competitive_summary(product_id)
                if summary:
                    position = summary.get('price_position', 'unknown')
                    strength = summary.get('competitive_strength', 'unknown')
                    print(f"   📊 Position: {position}, Strength: {strength}")


async def example_6_bulk_operations():
    """Example 6: Bulk operations and data export"""
    print("\n=== Example 6: Bulk Operations ===")
    
    async with AmazonInsightsClient() as client:
        if not await client.login("demo_seller", "demopassword123"):
            return
        
        # Get all products
        products = await client.get_products()
        print(f"📊 Processing {len(products)} products for bulk export...")
        
        # Collect data for all products
        export_data = []
        
        for product in products:
            product_id = product['id']
            
            # Get competitive summary
            summary = await client.get_competitive_summary(product_id)
            
            product_data = {
                'asin': product['asin'],
                'title': product['title'],
                'current_price': product.get('current_price'),
                'current_bsr': product.get('current_bsr'),
                'current_rating': product.get('current_rating'),
                'total_competitors': summary.get('total_competitors', 0) if summary else 0,
                'price_position': summary.get('price_position', 'unknown') if summary else 'unknown',
                'competitive_strength': summary.get('competitive_strength', 'unknown') if summary else 'unknown',
            }
            
            export_data.append(product_data)
        
        # Save to JSON file
        filename = f"product_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        print(f"✅ Exported data to {filename}")
        
        # Display summary statistics
        total_competitors = sum(p['total_competitors'] for p in export_data)
        avg_rating = sum(p['current_rating'] or 0 for p in export_data) / len(export_data) if export_data else 0
        
        print(f"📈 Summary Statistics:")
        print(f"   Total products: {len(export_data)}")
        print(f"   Total competitors tracked: {total_competitors}")
        print(f"   Average rating: {avg_rating:.2f}")
        
        # Count by competitive strength
        strength_counts = {}
        for product in export_data:
            strength = product['competitive_strength']
            strength_counts[strength] = strength_counts.get(strength, 0) + 1
        
        print(f"   Competitive strength distribution:")
        for strength, count in strength_counts.items():
            print(f"     {strength}: {count}")


async def main():
    """Run all examples"""
    print("🚀 Amazon Insights Platform API Examples")
    print("=" * 50)
    
    examples = [
        example_1_basic_product_tracking,
        example_2_competitor_analysis,
        example_3_intelligence_reports,
        example_4_market_overview,
        example_5_automation_workflow,
        example_6_bulk_operations
    ]
    
    for example in examples:
        try:
            await example()
            await asyncio.sleep(1)  # Brief pause between examples
        except Exception as e:
            print(f"❌ Example failed: {e}")
    
    print("\n✅ All examples completed!")
    print("\nFor more information:")
    print("📖 API Documentation: http://localhost:8000/api/v1/docs")
    print("📊 Flower Monitoring: http://localhost:5555")
    print("📈 Grafana Dashboard: http://localhost:3000")


if __name__ == "__main__":
    asyncio.run(main())