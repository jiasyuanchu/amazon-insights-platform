"""Competitor analysis and discovery service"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_
from src.app.models import (
    Product, Competitor, CompetitorAnalysis,
    ProductMetrics, ProductInsight
)
from src.app.services.firecrawl_service import firecrawl_service
from src.app.services.openai_service import OpenAIService
from src.app.core.redis import redis_client
from src.app.services.competitive_cache import competitive_cache
from src.app.services.advanced_cache import advanced_cache, cache_result
import structlog
import json
import re

logger = structlog.get_logger()


class CompetitorService:
    """Service for competitor discovery and analysis"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.openai_service = OpenAIService()
    
    async def discover_competitors(
        self, 
        product_id: int, 
        max_competitors: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Discover competitors for a product
        
        Args:
            product_id: ID of the main product
            max_competitors: Maximum number of competitors to find
            
        Returns:
            List of discovered competitor ASINs with basic info
        """
        # Get main product
        result = await self.db.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()
        
        if not product:
            raise ValueError(f"Product {product_id} not found")
        
        # Check cache first
        cached_competitors = await competitive_cache.get_competitor_list(product_id)
        if cached_competitors:
            logger.info("competitors_cache_hit", product_id=product_id)
            return cached_competitors
        
        logger.info("discovering_competitors", 
                   product_id=product_id, 
                   asin=product.asin)
        
        # Scrape Amazon search results for similar products
        competitors = await self._search_similar_products(
            product.title,
            product.category,
            product.asin,
            max_competitors
        )
        
        # Save discovered competitors and get the saved objects
        saved_competitors = []
        for comp_data in competitors:
            saved_comp = await self._save_competitor(product_id, comp_data)
            if saved_comp:
                saved_competitors.append(saved_comp)
        
        # Cache results
        await competitive_cache.cache_competitor_list(product_id, saved_competitors)
        
        return saved_competitors
    
    async def _search_similar_products(
        self,
        title: str,
        category: Optional[str],
        exclude_asin: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Search for similar products on Amazon
        
        This is a simplified version. In production, you would:
        1. Use Amazon Product Advertising API
        2. Or scrape search results page
        3. Apply ML to find truly similar products
        """
        # Extract key terms from title for search
        search_terms = self._extract_search_terms(title)
        
        # Build search query
        search_query = " ".join(search_terms[:3])  # Use top 3 terms
        if category:
            search_query = f"{category} {search_query}"
        
        # For demo purposes, return mock competitors
        # In production, this would call Firecrawl or Amazon API
        mock_competitors = [
            {
                "asin": "B09B8V1LZ3",
                "title": "Competitor Echo Dot (5th Gen)",
                "price": 49.99,
                "rating": 4.6,
                "review_count": 15234,
                "similarity_score": 0.92
            },
            {
                "asin": "B09B93ZDG4", 
                "title": "Google Nest Mini",
                "price": 45.99,
                "rating": 4.5,
                "review_count": 23456,
                "similarity_score": 0.85
            },
            {
                "asin": "B08H75RTZ8",
                "title": "HomePod Mini",
                "price": 89.99,
                "rating": 4.3,
                "review_count": 8765,
                "similarity_score": 0.78
            }
        ]
        
        # Filter out the main product
        competitors = [c for c in mock_competitors if c["asin"] != exclude_asin]
        
        return competitors[:limit]
    
    def _extract_search_terms(self, title: str) -> List[str]:
        """Extract important search terms from product title"""
        # Remove common words and keep important terms
        stop_words = {'the', 'and', 'or', 'with', 'for', 'of', 'in', 'on', 'at'}
        
        # Extract words
        words = re.findall(r'\b\w+\b', title.lower())
        
        # Filter and prioritize
        important_words = [w for w in words if w not in stop_words and len(w) > 2]
        
        return important_words
    
    async def _save_competitor(
        self, 
        main_product_id: int, 
        competitor_data: Dict[str, Any]
    ) -> Optional[Competitor]:
        """Save or update competitor in database and return the competitor object"""
        # Check if competitor already exists
        result = await self.db.execute(
            select(Competitor).where(
                and_(
                    Competitor.main_product_id == main_product_id,
                    Competitor.competitor_asin == competitor_data["asin"]
                )
            )
        )
        existing = result.scalar_one_or_none()
        
        if not existing:
            # Create new competitor
            competitor = Competitor(
                main_product_id=main_product_id,
                competitor_asin=competitor_data["asin"],
                title=competitor_data["title"],
                product_url=f"https://www.amazon.com/dp/{competitor_data['asin']}",
                current_price=competitor_data.get("price"),
                current_rating=competitor_data.get("rating"),
                current_review_count=competitor_data.get("review_count"),
                similarity_score=competitor_data.get("similarity_score", 0.5),
                is_direct_competitor=1 if competitor_data.get("similarity_score", 0) > 0.8 else 2
            )
            self.db.add(competitor)
            await self.db.commit()
            await self.db.refresh(competitor)
            return competitor
        else:
            # Update existing competitor
            existing.current_price = competitor_data.get("price")
            existing.current_rating = competitor_data.get("rating")
            existing.current_review_count = competitor_data.get("review_count")
            await self.db.commit()
            await self.db.refresh(existing)
            return existing
    
    async def analyze_competitor(
        self,
        product_id: int,
        competitor_id: int
    ) -> Dict[str, Any]:
        """
        Perform detailed analysis of a competitor
        
        Args:
            product_id: Main product ID
            competitor_id: Competitor ID
            
        Returns:
            Detailed competitive analysis
        """
        # Get main product and competitor
        main_product = await self.db.execute(
            select(Product).where(Product.id == product_id)
        )
        main_product = main_product.scalar_one_or_none()
        
        competitor = await self.db.execute(
            select(Competitor).where(Competitor.id == competitor_id)
        )
        competitor = competitor.scalar_one_or_none()
        
        if not main_product or not competitor:
            raise ValueError("Product or competitor not found")
        
        # Check cache for analysis
        cached_analysis = await competitive_cache.get_analysis_report(product_id, competitor_id)
        if cached_analysis:
            logger.info("analysis_cache_hit", product_id=product_id, competitor_id=competitor_id)
            return cached_analysis
        
        # Perform analysis
        analysis = {
            "price_comparison": self._analyze_pricing(main_product, competitor),
            "performance_comparison": self._analyze_performance(main_product, competitor),
            "market_position": self._determine_market_position(main_product, competitor),
            "competitive_advantages": await self._identify_advantages(main_product, competitor),
            "recommendations": await self._generate_recommendations(main_product, competitor),
            "ai_insights": await self._generate_ai_insights(main_product, competitor)
        }
        
        # Cache the analysis
        await competitive_cache.cache_analysis_report(product_id, competitor_id, analysis)
        
        # Save analysis to database (only create new if needed)
        try:
            db_analysis = CompetitorAnalysis(
                competitor_id=competitor_id,
                analyzed_at=datetime.utcnow(),
                price_difference=analysis["price_comparison"]["difference"],
                price_difference_percent=analysis["price_comparison"]["difference_percent"],
                bsr_difference=analysis["performance_comparison"].get("bsr_difference"),
                rating_difference=analysis["performance_comparison"].get("rating_difference"),
                main_advantages=analysis["competitive_advantages"]["main_product"],
                competitor_advantages=analysis["competitive_advantages"]["competitor"],
                positioning_analysis=analysis["market_position"],
                recommended_actions=analysis["recommendations"]
            )
            self.db.add(db_analysis)
            await self.db.commit()
        except Exception as e:
            logger.warning("Failed to save analysis to database", error=str(e))
            # Don't fail the whole analysis if DB save fails
            await self.db.rollback()
        
        return analysis
    
    def _analyze_pricing(
        self,
        main_product: Product,
        competitor: Competitor
    ) -> Dict[str, Any]:
        """Analyze pricing differences"""
        main_price = main_product.current_price or 0
        comp_price = competitor.current_price or 0
        
        difference = main_price - comp_price
        difference_percent = (difference / comp_price * 100) if comp_price > 0 else 0
        
        return {
            "main_price": main_price,
            "competitor_price": comp_price,
            "difference": difference,
            "difference_percent": round(difference_percent, 2),
            "price_position": "premium" if difference > 0 else "competitive" if difference == 0 else "value"
        }
    
    def _analyze_performance(
        self,
        main_product: Product,
        competitor: Competitor
    ) -> Dict[str, Any]:
        """Analyze performance metrics"""
        return {
            "bsr_difference": (main_product.current_bsr or 0) - (competitor.current_bsr or 0),
            "rating_difference": (main_product.current_rating or 0) - (competitor.current_rating or 0),
            "review_difference": (main_product.current_review_count or 0) - (competitor.current_review_count or 0),
            "performance_score": self._calculate_performance_score(main_product, competitor)
        }
    
    def _calculate_performance_score(
        self,
        main_product: Product,
        competitor: Competitor
    ) -> float:
        """Calculate overall performance score (0-100)"""
        score = 50.0  # Base score
        
        # BSR comparison (lower is better)
        if main_product.current_bsr and competitor.current_bsr:
            if main_product.current_bsr < competitor.current_bsr:
                score += 15
            else:
                score -= 15
        
        # Rating comparison
        if main_product.current_rating and competitor.current_rating:
            rating_diff = main_product.current_rating - competitor.current_rating
            score += rating_diff * 10
        
        # Review count comparison (more reviews = more established)
        if main_product.current_review_count and competitor.current_review_count:
            if main_product.current_review_count > competitor.current_review_count:
                score += 10
            else:
                score -= 10
        
        # Price competitiveness
        if main_product.current_price and competitor.current_price:
            if main_product.current_price < competitor.current_price:
                score += 15  # Price advantage
        
        return max(0, min(100, score))
    
    def _determine_market_position(
        self,
        main_product: Product,
        competitor: Competitor
    ) -> str:
        """Determine market positioning"""
        price_ratio = (main_product.current_price or 0) / (competitor.current_price or 1)
        
        if price_ratio > 1.2:
            if (main_product.current_rating or 0) > (competitor.current_rating or 0):
                return "premium_leader"
            else:
                return "overpriced"
        elif price_ratio < 0.8:
            return "value_leader"
        else:
            if (main_product.current_bsr or float('inf')) < (competitor.current_bsr or float('inf')):
                return "market_leader"
            else:
                return "follower"
    
    async def _identify_advantages(
        self,
        main_product: Product,
        competitor: Competitor
    ) -> Dict[str, List[str]]:
        """Identify competitive advantages using AI"""
        main_advantages = []
        competitor_advantages = []
        
        # Price advantage
        if main_product.current_price and competitor.current_price:
            if main_product.current_price < competitor.current_price:
                main_advantages.append("Lower price point")
            else:
                competitor_advantages.append("More competitive pricing")
        
        # Rating advantage
        if main_product.current_rating and competitor.current_rating:
            if main_product.current_rating > competitor.current_rating:
                main_advantages.append("Higher customer satisfaction")
            else:
                competitor_advantages.append("Better customer ratings")
        
        # Market position advantage
        if main_product.current_bsr and competitor.current_bsr:
            if main_product.current_bsr < competitor.current_bsr:
                main_advantages.append("Better sales rank")
            else:
                competitor_advantages.append("Stronger market position")
        
        return {
            "main_product": main_advantages,
            "competitor": competitor_advantages
        }
    
    async def _generate_recommendations(
        self,
        main_product: Product,
        competitor: Competitor
    ) -> List[Dict[str, Any]]:
        """Generate strategic recommendations"""
        recommendations = []
        
        # Price recommendations
        if main_product.current_price and competitor.current_price:
            price_diff_percent = ((main_product.current_price - competitor.current_price) / competitor.current_price) * 100
            
            if price_diff_percent > 15:
                recommendations.append({
                    "type": "pricing",
                    "priority": "high",
                    "action": "Consider price reduction",
                    "reason": f"Your price is {price_diff_percent:.1f}% higher than competitor",
                    "expected_impact": "Increase conversion rate and sales volume"
                })
            elif price_diff_percent < -15:
                recommendations.append({
                    "type": "pricing",
                    "priority": "medium",
                    "action": "Opportunity for price increase",
                    "reason": f"You're priced {abs(price_diff_percent):.1f}% below competitor",
                    "expected_impact": "Improve profit margins without losing competitiveness"
                })
        
        # Performance recommendations
        if main_product.current_rating and competitor.current_rating:
            if main_product.current_rating < competitor.current_rating - 0.3:
                recommendations.append({
                    "type": "quality",
                    "priority": "high",
                    "action": "Focus on product quality improvements",
                    "reason": f"Competitor has {competitor.current_rating:.1f} rating vs your {main_product.current_rating:.1f}",
                    "expected_impact": "Improve customer satisfaction and reduce returns"
                })
        
        # Marketing recommendations
        if main_product.current_review_count and competitor.current_review_count:
            if main_product.current_review_count < competitor.current_review_count / 2:
                recommendations.append({
                    "type": "marketing",
                    "priority": "medium",
                    "action": "Implement review generation campaign",
                    "reason": f"Competitor has {competitor.current_review_count} reviews vs your {main_product.current_review_count}",
                    "expected_impact": "Build social proof and trust"
                })
        
        return recommendations
    
    async def batch_analyze_competitors(
        self,
        product_id: int
    ) -> Dict[str, Any]:
        """
        Analyze all competitors for a product
        
        Args:
            product_id: Main product ID
            
        Returns:
            Comprehensive competitive analysis report
        """
        # Get all competitors
        result = await self.db.execute(
            select(Competitor).where(Competitor.main_product_id == product_id)
        )
        competitors = result.scalars().all()
        
        if not competitors:
            # Discover competitors first
            await self.discover_competitors(product_id)
            result = await self.db.execute(
                select(Competitor).where(Competitor.main_product_id == product_id)
            )
            competitors = result.scalars().all()
        
        # Analyze each competitor in parallel
        tasks = [
            self.analyze_competitor(product_id, comp.id)
            for comp in competitors
        ]
        analyses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out any errors
        successful_analyses = [
            a for a in analyses
            if not isinstance(a, Exception)
        ]
        
        # Generate summary report
        report = {
            "product_id": product_id,
            "analyzed_at": datetime.utcnow().isoformat(),
            "total_competitors": len(competitors),
            "analyses": successful_analyses,
            "market_summary": self._generate_market_summary(successful_analyses),
            "strategic_recommendations": self._consolidate_recommendations(successful_analyses)
        }
        
        # Cache report
        await competitive_cache.cache_intelligence_report(product_id, report)
        
        return report
    
    def _generate_market_summary(
        self,
        analyses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate market summary from analyses"""
        if not analyses:
            return {}
        
        avg_competitor_price = sum(
            a["price_comparison"]["competitor_price"] 
            for a in analyses if "price_comparison" in a
        ) / len(analyses)
        
        market_positions = [
            a.get("market_position", "unknown")
            for a in analyses
        ]
        
        return {
            "average_competitor_price": round(avg_competitor_price, 2),
            "dominant_position": max(set(market_positions), key=market_positions.count),
            "competitive_intensity": "high" if len(analyses) > 3 else "medium" if len(analyses) > 1 else "low",
            "total_threats": sum(
                len(a.get("competitive_advantages", {}).get("competitor", []))
                for a in analyses
            ),
            "total_advantages": sum(
                len(a.get("competitive_advantages", {}).get("main_product", []))
                for a in analyses
            )
        }
    
    def _consolidate_recommendations(
        self,
        analyses: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Consolidate and prioritize recommendations"""
        all_recommendations = []
        
        for analysis in analyses:
            if "recommendations" in analysis:
                all_recommendations.extend(analysis["recommendations"])
        
        # Remove duplicates and prioritize
        seen = set()
        unique_recommendations = []
        
        for rec in all_recommendations:
            rec_key = rec.get("action", "")
            if rec_key not in seen:
                seen.add(rec_key)
                unique_recommendations.append(rec)
        
        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        unique_recommendations.sort(
            key=lambda x: priority_order.get(x.get("priority", "low"), 3)
        )
        
        return unique_recommendations[:5]  # Return top 5 recommendations
    
    async def _generate_ai_insights(
        self,
        main_product: Product,
        competitor: Competitor
    ) -> Dict[str, Any]:
        """Generate AI-powered competitive insights"""
        try:
            # Convert to dict format for OpenAI service
            main_data = {
                "asin": main_product.asin,
                "title": main_product.title,
                "price": main_product.current_price,
                "bsr": main_product.current_bsr,
                "rating": main_product.current_rating,
                "review_count": main_product.current_review_count,
                "category": main_product.category
            }
            
            comp_data = {
                "asin": competitor.competitor_asin,
                "title": competitor.title,
                "price": competitor.current_price,
                "bsr": competitor.current_bsr,
                "rating": competitor.current_rating,
                "review_count": competitor.current_review_count
            }
            
            # Get AI insights
            insights = await self.openai_service.analyze_competitive_landscape(
                main_data, [comp_data]
            )
            
            return insights
            
        except Exception as e:
            logger.error("ai_insights_error", error=str(e))
            return {
                "analysis": "AI insights temporarily unavailable",
                "positioning": "unknown",
                "action_items": []
            }
    
    async def generate_comprehensive_intelligence_report(
        self,
        product_id: int
    ) -> Dict[str, Any]:
        """
        Generate comprehensive competitive intelligence report with AI insights
        """
        # Get main product
        result = await self.db.execute(
            select(Product).where(Product.id == product_id)
        )
        main_product = result.scalar_one_or_none()
        
        if not main_product:
            raise ValueError(f"Product {product_id} not found")
        
        # Check for cached intelligence report
        cached_report = await competitive_cache.get_intelligence_report(product_id)
        if cached_report:
            logger.info("intelligence_report_cache_hit", product_id=product_id)
            return cached_report
        
        # Get all competitor analyses
        report = await self.batch_analyze_competitors(product_id)
        
        if not report.get("analyses"):
            return report
        
        # Generate comprehensive AI insights
        main_data = {
            "asin": main_product.asin,
            "title": main_product.title,
            "price": main_product.current_price,
            "bsr": main_product.current_bsr,
            "rating": main_product.current_rating,
            "review_count": main_product.current_review_count,
            "category": main_product.category
        }
        
        try:
            comprehensive_insights = await self.openai_service.generate_competitive_insights(
                main_data, report["analyses"]
            )
            
            # Enhance report with AI insights
            report.update({
                "ai_competitive_intelligence": comprehensive_insights,
                "intelligence_summary": {
                    "market_position": comprehensive_insights.get("market_position_analysis", ""),
                    "key_advantages": comprehensive_insights.get("competitive_advantages", [])[:3],
                    "primary_threats": comprehensive_insights.get("threat_assessment", [])[:3],
                    "priority_actions": comprehensive_insights.get("strategic_recommendations", [])[:3]
                }
            })
            
            # Add trend analysis if we have historical data
            if main_product.category:
                trend_analysis = await self._analyze_category_trends(main_product.category)
                report["market_trends"] = trend_analysis
            
        except Exception as e:
            logger.error("comprehensive_intelligence_error", error=str(e))
            report["ai_competitive_intelligence"] = {
                "error": "AI intelligence analysis temporarily unavailable"
            }
        
        return report
    
    async def _analyze_category_trends(self, category: str) -> Dict[str, Any]:
        """Analyze market trends for a category"""
        try:
            # Get historical data for trend analysis
            # In production, this would query actual historical data
            mock_historical_data = [
                {"date": "2024-01", "avg_price": 45.99, "avg_bsr": 15000, "activity_level": "high"},
                {"date": "2024-02", "avg_price": 47.50, "avg_bsr": 14500, "activity_level": "normal"},
                {"date": "2024-03", "avg_price": 49.99, "avg_bsr": 16000, "activity_level": "normal"}
            ]
            
            return await self.openai_service.analyze_market_trends(
                category, mock_historical_data
            )
            
        except Exception as e:
            logger.error("trend_analysis_error", error=str(e))
            return {
                "trend_analysis": "Trend analysis temporarily unavailable",
                "key_insights": [],
                "predictions": []
            }