#!/usr/bin/env python3
"""
Query Performance Analysis Script

This script analyzes common database queries to measure performance
improvements from the new indexes.
"""

import asyncio
import time
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.app.core.database import AsyncSessionLocal
from sqlalchemy import text, select
from src.app.models import Product, Competitor, ProductMetrics, ProductInsight
import structlog

logger = structlog.get_logger()


class QueryPerformanceAnalyzer:
    """Analyze database query performance"""
    
    def __init__(self):
        self.session = None
        self.results = []
    
    async def __aenter__(self):
        self.session = AsyncSessionLocal()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def analyze_query(self, name: str, query: str, description: str = "") -> Dict[str, Any]:
        """Analyze a single query performance"""
        print(f"\n🔍 Analyzing: {name}")
        if description:
            print(f"   Description: {description}")
        
        # Enable query planning for analysis
        await self.session.execute(text("SET enable_seqscan = off"))
        
        try:
            # Get query plan
            explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"
            
            start_time = time.time()
            result = await self.session.execute(text(explain_query))
            plan_data = result.scalar()
            end_time = time.time()
            
            execution_time = end_time - start_time
            query_plan = plan_data[0] if plan_data else {}
            
            # Extract key metrics
            planning_time = query_plan.get("Planning Time", 0)
            execution_time_ms = query_plan.get("Execution Time", 0)
            total_cost = query_plan.get("Plan", {}).get("Total Cost", 0)
            
            analysis = {
                "query_name": name,
                "description": description,
                "planning_time_ms": planning_time,
                "execution_time_ms": execution_time_ms,
                "total_cost": total_cost,
                "python_execution_time": execution_time * 1000,
                "uses_index": self._check_index_usage(query_plan),
                "plan": query_plan
            }
            
            self.results.append(analysis)
            
            print(f"   ⏱️  Execution Time: {execution_time_ms:.2f}ms")
            print(f"   💰 Total Cost: {total_cost:.2f}")
            print(f"   📊 Uses Index: {'✅' if analysis['uses_index'] else '❌'}")
            
            return analysis
            
        except Exception as e:
            logger.error("Query analysis failed", error=str(e), query=query)
            return {
                "query_name": name,
                "error": str(e)
            }
        finally:
            # Reset query planning
            await self.session.execute(text("SET enable_seqscan = on"))
    
    def _check_index_usage(self, plan: Dict[str, Any]) -> bool:
        """Check if the query uses indexes"""
        def check_node(node):
            if isinstance(node, dict):
                node_type = node.get("Node Type", "")
                if "Index" in node_type:
                    return True
                
                # Check child plans
                for child in node.get("Plans", []):
                    if check_node(child):
                        return True
            return False
        
        return check_node(plan.get("Plan", {}))
    
    async def run_performance_tests(self):
        """Run comprehensive performance tests"""
        print("🚀 Starting Database Query Performance Analysis")
        print("=" * 60)
        
        # Test 1: Product queries by user
        await self.analyze_query(
            "products_by_user",
            "SELECT * FROM products WHERE user_id = 3 AND is_active = true",
            "Fetch active products for a specific user"
        )
        
        # Test 2: Products by category
        await self.analyze_query(
            "products_by_category",
            "SELECT * FROM products WHERE category = 'Electronics' AND is_active = true",
            "Fetch products by category"
        )
        
        # Test 3: Competitors for product
        await self.analyze_query(
            "competitors_for_product",
            "SELECT * FROM competitors WHERE main_product_id = 11 ORDER BY similarity_score DESC",
            "Get competitors for a specific product"
        )
        
        # Test 4: Recent product metrics
        await self.analyze_query(
            "recent_product_metrics",
            f"""SELECT * FROM product_metrics 
               WHERE product_id = 11 
               AND scraped_at >= '{(datetime.utcnow() - timedelta(days=7)).isoformat()}'
               ORDER BY scraped_at DESC LIMIT 100""",
            "Get recent metrics for a product (last 7 days)"
        )
        
        # Test 5: Price history analysis
        await self.analyze_query(
            "price_history_analysis",
            f"""SELECT product_id, AVG(sale_price) as avg_price, COUNT(*) as data_points
               FROM price_history 
               WHERE tracked_at >= '{(datetime.utcnow() - timedelta(days=30)).isoformat()}'
               GROUP BY product_id
               ORDER BY avg_price DESC""",
            "Analyze price history for all products (last 30 days)"
        )
        
        # Test 6: Active alerts by user
        await self.analyze_query(
            "active_alerts_by_user",
            "SELECT * FROM alert_configurations WHERE user_id = 3 AND is_active = true",
            "Get active alerts for a user"
        )
        
        # Test 7: Recent alert history
        await self.analyze_query(
            "recent_alert_history", 
            f"""SELECT ah.*, ac.alert_name, p.title as product_title
               FROM alert_history ah
               JOIN alert_configurations ac ON ah.configuration_id = ac.id
               JOIN products p ON ah.product_id = p.id
               WHERE ah.triggered_at >= '{(datetime.utcnow() - timedelta(days=7)).isoformat()}'
               ORDER BY ah.triggered_at DESC LIMIT 50""",
            "Get recent alert history with details"
        )
        
        # Test 8: Market overview query
        await self.analyze_query(
            "market_overview",
            """SELECT 
                 category,
                 COUNT(*) as product_count,
                 AVG(current_price) as avg_price,
                 AVG(current_rating) as avg_rating
               FROM products 
               WHERE is_active = true AND current_price IS NOT NULL
               GROUP BY category
               ORDER BY product_count DESC""",
            "Market overview by category"
        )
        
        # Test 9: Top competitors by similarity
        await self.analyze_query(
            "top_competitors_by_similarity",
            """SELECT c.*, p.title as main_product_title
               FROM competitors c
               JOIN products p ON c.main_product_id = p.id
               WHERE c.similarity_score > 0.8 AND c.is_direct_competitor = 1
               ORDER BY c.similarity_score DESC LIMIT 20""",
            "Find top competitors by similarity score"
        )
        
        # Test 10: Complex analytics query
        await self.analyze_query(
            "complex_product_analytics",
            """SELECT 
                 p.id, p.asin, p.title, p.current_price, p.current_rating,
                 COUNT(c.id) as competitor_count,
                 AVG(c.current_price) as avg_competitor_price,
                 AVG(c.similarity_score) as avg_similarity
               FROM products p
               LEFT JOIN competitors c ON p.id = c.main_product_id
               WHERE p.is_active = true
               GROUP BY p.id, p.asin, p.title, p.current_price, p.current_rating
               HAVING COUNT(c.id) > 0
               ORDER BY competitor_count DESC, avg_similarity DESC""",
            "Complex analytics combining products and competitors"
        )
    
    def generate_performance_report(self):
        """Generate a performance analysis report"""
        print("\n📊 PERFORMANCE ANALYSIS REPORT")
        print("=" * 60)
        
        successful_queries = [r for r in self.results if "error" not in r]
        failed_queries = [r for r in self.results if "error" in r]
        
        if successful_queries:
            avg_execution_time = sum(r["execution_time_ms"] for r in successful_queries) / len(successful_queries)
            avg_total_cost = sum(r["total_cost"] for r in successful_queries) / len(successful_queries)
            index_usage_count = sum(1 for r in successful_queries if r["uses_index"])
            
            print(f"\n✅ Successful Queries: {len(successful_queries)}")
            print(f"📈 Average Execution Time: {avg_execution_time:.2f}ms")
            print(f"💰 Average Query Cost: {avg_total_cost:.2f}")
            print(f"🎯 Index Usage Rate: {(index_usage_count/len(successful_queries)*100):.1f}%")
            
            print(f"\n🏆 Performance Rankings:")
            sorted_results = sorted(successful_queries, key=lambda x: x["execution_time_ms"])
            
            for i, result in enumerate(sorted_results[:5], 1):
                print(f"{i:2d}. {result['query_name']}: {result['execution_time_ms']:.2f}ms")
            
            print(f"\n⚠️  Slowest Queries:")
            for i, result in enumerate(sorted_results[-3:], 1):
                print(f"{i:2d}. {result['query_name']}: {result['execution_time_ms']:.2f}ms")
                if not result['uses_index']:
                    print("     ❌ Not using indexes - consider optimization")
        
        if failed_queries:
            print(f"\n❌ Failed Queries: {len(failed_queries)}")
            for result in failed_queries:
                print(f"   - {result['query_name']}: {result['error']}")
        
        print(f"\n💡 Optimization Recommendations:")
        
        slow_queries = [r for r in successful_queries if r["execution_time_ms"] > 50]
        if slow_queries:
            print(f"   - {len(slow_queries)} queries are slower than 50ms")
            print("   - Consider adding more specific indexes")
        
        no_index_queries = [r for r in successful_queries if not r["uses_index"]]
        if no_index_queries:
            print(f"   - {len(no_index_queries)} queries not using indexes")
            print("   - Review query patterns and add missing indexes")
        
        print("\n🎯 Overall Assessment:")
        if avg_execution_time < 20:
            print("   ✅ Excellent - Query performance is optimal")
        elif avg_execution_time < 50:
            print("   ✅ Good - Query performance is acceptable")
        elif avg_execution_time < 100:
            print("   ⚠️  Fair - Some queries may need optimization")
        else:
            print("   ❌ Poor - Significant optimization needed")
        
        return {
            "summary": {
                "total_queries": len(self.results),
                "successful_queries": len(successful_queries),
                "failed_queries": len(failed_queries),
                "avg_execution_time_ms": avg_execution_time if successful_queries else 0,
                "avg_total_cost": avg_total_cost if successful_queries else 0,
                "index_usage_rate": (index_usage_count/len(successful_queries)*100) if successful_queries else 0
            },
            "details": self.results
        }


async def main():
    """Main function to run performance analysis"""
    async with QueryPerformanceAnalyzer() as analyzer:
        await analyzer.run_performance_tests()
        report = analyzer.generate_performance_report()
        
        # Save detailed report
        import json
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        report_filename = f"query_performance_report_{timestamp}.json"
        
        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n💾 Detailed report saved to: {report_filename}")
        print("🎉 Performance analysis complete!")
        
        return report["summary"]["avg_execution_time_ms"] < 50


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)