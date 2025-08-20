"""OpenAI API service wrapper"""

from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI
from src.app.core.config import settings
import structlog

logger = structlog.get_logger()


class OpenAIService:
    """Service for interacting with OpenAI API"""
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL
        if self.api_key:
            self.client = AsyncOpenAI(api_key=self.api_key)
        else:
            self.client = None
    
    async def generate_product_insights(
        self,
        product_data: Dict[str, Any],
        metrics_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate AI-powered insights for a product
        
        Args:
            product_data: Current product information
            metrics_history: Historical metrics data
            
        Returns:
            Generated insights and recommendations
        """
        if not self.api_key:
            logger.warning("openai_api_key_not_configured")
            return {
                "summary": "AI insights not available (API key not configured)",
                "recommendations": [],
                "opportunities": []
            }
        
        try:
            # Prepare prompt
            prompt = self._build_insights_prompt(product_data, metrics_history)
            
            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert Amazon seller consultant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            
            # Parse response (would need more sophisticated parsing in production)
            return {
                "summary": content,
                "recommendations": self._extract_recommendations(content),
                "opportunities": self._extract_opportunities(content)
            }
            
        except Exception as e:
            logger.error("openai_api_error", error=str(e))
            return {
                "summary": "Error generating AI insights",
                "recommendations": [],
                "opportunities": []
            }
    
    async def analyze_competitive_landscape(
        self,
        product: Dict[str, Any],
        competitors: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze competitive positioning
        
        Args:
            product: Main product data
            competitors: List of competitor products
            
        Returns:
            Competitive analysis insights
        """
        if not self.api_key:
            return {
                "positioning": "unknown",
                "strengths": [],
                "weaknesses": [],
                "recommendations": []
            }
        
        try:
            prompt = self._build_competitive_prompt(product, competitors)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert in competitive analysis for e-commerce."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=600
            )
            
            content = response.choices[0].message.content
            
            return {
                "analysis": content,
                "positioning": self._determine_positioning(product, competitors),
                "action_items": self._extract_action_items(content)
            }
            
        except Exception as e:
            logger.error("openai_competitive_analysis_error", error=str(e))
            return {
                "positioning": "error",
                "analysis": "Error analyzing competition",
                "action_items": []
            }
    
    async def generate_competitive_insights(
        self,
        main_product: Dict[str, Any],
        competitor_analyses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive competitive intelligence insights
        
        Args:
            main_product: Main product data
            competitor_analyses: List of competitor analysis results
            
        Returns:
            AI-powered competitive insights
        """
        if not self.api_key:
            return self._mock_competitive_insights()
        
        try:
            prompt = self._build_competitive_intelligence_prompt(
                main_product, competitor_analyses
            )
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert Amazon marketplace strategist specializing in competitive intelligence."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.6,
                max_tokens=800
            )
            
            content = response.choices[0].message.content
            
            return {
                "market_position_analysis": self._extract_market_position(content),
                "competitive_advantages": self._extract_advantages(content),
                "threat_assessment": self._extract_threats(content),
                "strategic_recommendations": self._extract_strategic_recommendations(content),
                "pricing_strategy": self._extract_pricing_insights(content),
                "market_opportunities": self._extract_opportunities_detailed(content),
                "risk_factors": self._extract_risks(content),
                "full_analysis": content
            }
            
        except Exception as e:
            logger.error("competitive_intelligence_error", error=str(e))
            return self._mock_competitive_insights()
    
    async def analyze_market_trends(
        self,
        category: str,
        historical_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze market trends and predict future movements
        """
        if not self.api_key:
            return {
                "trend_analysis": "Market trend analysis not available",
                "predictions": [],
                "seasonal_patterns": []
            }
        
        try:
            prompt = self._build_trend_analysis_prompt(category, historical_data)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a market analyst specializing in Amazon marketplace trends."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=600
            )
            
            content = response.choices[0].message.content
            
            return {
                "trend_analysis": content,
                "key_insights": self._extract_trend_insights(content),
                "predictions": self._extract_predictions(content),
                "action_recommendations": self._extract_trend_actions(content)
            }
            
        except Exception as e:
            logger.error("trend_analysis_error", error=str(e))
            return {
                "trend_analysis": "Error analyzing market trends",
                "key_insights": [],
                "predictions": [],
                "action_recommendations": []
            }
    
    def _build_insights_prompt(
        self,
        product_data: Dict[str, Any],
        metrics_history: List[Dict[str, Any]]
    ) -> str:
        """Build prompt for insights generation"""
        prompt = f"""
        Analyze the following Amazon product data and provide insights:
        
        Product: {product_data.get('title', 'Unknown')}
        ASIN: {product_data.get('asin', 'Unknown')}
        Current Price: ${product_data.get('price', 0):.2f}
        BSR: #{product_data.get('bsr', 'N/A')}
        Rating: {product_data.get('rating', 'N/A')} stars
        Reviews: {product_data.get('review_count', 0)}
        
        Recent Performance:
        """
        
        for metric in metrics_history[:5]:
            prompt += f"\n- {metric.get('date')}: Price ${metric.get('price', 0):.2f}, BSR #{metric.get('bsr', 'N/A')}"
        
        prompt += """
        
        Please provide:
        1. A brief summary of the product's current performance
        2. Key opportunities for improvement
        3. Specific action recommendations
        4. Risk factors to monitor
        """
        
        return prompt
    
    def _build_competitive_prompt(
        self,
        product: Dict[str, Any],
        competitors: List[Dict[str, Any]]
    ) -> str:
        """Build prompt for competitive analysis"""
        prompt = f"""
        Analyze the competitive positioning of this product:
        
        Main Product:
        - Title: {product.get('title')}
        - Price: ${product.get('price', 0):.2f}
        - BSR: #{product.get('bsr', 'N/A')}
        - Rating: {product.get('rating', 'N/A')}
        - Reviews: {product.get('review_count', 0)}
        
        Top Competitors:
        """
        
        for i, comp in enumerate(competitors[:5], 1):
            prompt += f"""
        {i}. {comp.get('title', 'Unknown')}
           - Price: ${comp.get('price', 0):.2f}
           - BSR: #{comp.get('bsr', 'N/A')}
           - Rating: {comp.get('rating', 'N/A')}
        """
        
        prompt += """
        
        Provide:
        1. Competitive positioning assessment
        2. Key differentiators
        3. Pricing strategy recommendations
        4. Areas for improvement
        """
        
        return prompt
    
    def _extract_recommendations(self, content: str) -> List[str]:
        """Extract recommendations from AI response"""
        # Simple extraction - would be more sophisticated in production
        recommendations = []
        lines = content.split('\n')
        for line in lines:
            if any(keyword in line.lower() for keyword in ['recommend', 'should', 'consider']):
                recommendations.append(line.strip())
        return recommendations[:3]  # Return top 3
    
    def _extract_opportunities(self, content: str) -> List[str]:
        """Extract opportunities from AI response"""
        opportunities = []
        lines = content.split('\n')
        for line in lines:
            if any(keyword in line.lower() for keyword in ['opportunity', 'potential', 'could']):
                opportunities.append(line.strip())
        return opportunities[:3]
    
    def _extract_action_items(self, content: str) -> List[str]:
        """Extract action items from competitive analysis"""
        action_items = []
        lines = content.split('\n')
        for line in lines:
            if line.strip().startswith(('-', '•', '*')) or any(keyword in line.lower() for keyword in ['action', 'implement', 'adjust']):
                action_items.append(line.strip())
        return action_items[:5]
    
    def _determine_positioning(
        self,
        product: Dict[str, Any],
        competitors: List[Dict[str, Any]]
    ) -> str:
        """Determine competitive positioning"""
        if not competitors:
            return "no_competition"
        
        product_price = product.get('price', 0)
        competitor_prices = [c.get('price', 0) for c in competitors if c.get('price')]
        
        if not competitor_prices:
            return "unknown"
        
        avg_competitor_price = sum(competitor_prices) / len(competitor_prices)
        
        if product_price < avg_competitor_price * 0.8:
            return "price_leader"
        elif product_price > avg_competitor_price * 1.2:
            return "premium"
        else:
            return "competitive"
    
    def _build_competitive_intelligence_prompt(
        self,
        main_product: Dict[str, Any],
        competitor_analyses: List[Dict[str, Any]]
    ) -> str:
        """Build comprehensive competitive intelligence prompt"""
        prompt = f"""
        Conduct a comprehensive competitive intelligence analysis for:
        
        MAIN PRODUCT:
        - Title: {main_product.get('title', 'Unknown')}
        - ASIN: {main_product.get('asin', 'Unknown')}
        - Price: ${main_product.get('price', 0):.2f}
        - BSR: #{main_product.get('bsr', 'N/A')}
        - Rating: {main_product.get('rating', 'N/A')} stars
        - Reviews: {main_product.get('review_count', 0)}
        - Category: {main_product.get('category', 'Unknown')}
        
        COMPETITIVE LANDSCAPE ANALYSIS:
        """
        
        for i, analysis in enumerate(competitor_analyses[:5], 1):
            prompt += f"""
        Competitor {i}:
        - Price Position: {analysis.get('price_comparison', {}).get('price_position', 'unknown')}
        - Price Difference: {analysis.get('price_comparison', {}).get('difference_percent', 0):.1f}%
        - Performance Score: {analysis.get('performance_comparison', {}).get('performance_score', 'N/A')}
        - Market Position: {analysis.get('market_position', 'unknown')}
        - Main Advantages: {', '.join(analysis.get('competitive_advantages', {}).get('main_product', []))}
        - Competitor Advantages: {', '.join(analysis.get('competitive_advantages', {}).get('competitor', []))}
        """
        
        prompt += """
        
        Please provide a comprehensive analysis including:
        
        1. MARKET POSITION ANALYSIS: Where does this product stand in the competitive landscape?
        
        2. COMPETITIVE ADVANTAGES: What are the product's key strengths vs competitors?
        
        3. THREAT ASSESSMENT: What are the biggest competitive threats and vulnerabilities?
        
        4. STRATEGIC RECOMMENDATIONS: What specific actions should be taken to improve competitive position?
        
        5. PRICING STRATEGY: How should pricing be adjusted based on competitive analysis?
        
        6. MARKET OPPORTUNITIES: What gaps in the market could be exploited?
        
        7. RISK FACTORS: What competitive risks should be monitored?
        
        Provide actionable, specific insights based on the data.
        """
        
        return prompt
    
    def _build_trend_analysis_prompt(
        self,
        category: str,
        historical_data: List[Dict[str, Any]]
    ) -> str:
        """Build market trend analysis prompt"""
        prompt = f"""
        Analyze market trends for the {category} category based on historical data:
        
        HISTORICAL PERFORMANCE:
        """
        
        for data_point in historical_data[-10:]:  # Last 10 data points
            prompt += f"""
        - {data_point.get('date')}: Avg Price ${data_point.get('avg_price', 0):.2f}, 
          Avg BSR {data_point.get('avg_bsr', 'N/A')}, Market Activity: {data_point.get('activity_level', 'normal')}
        """
        
        prompt += """
        
        Please analyze:
        1. Overall market trends and trajectory
        2. Seasonal patterns and cyclical behavior
        3. Pricing trends and competitive pressure
        4. Market growth or decline indicators
        5. Predictions for next 3-6 months
        6. Recommended actions based on trends
        """
        
        return prompt
    
    def _mock_competitive_insights(self) -> Dict[str, Any]:
        """Return mock competitive insights when OpenAI is not available"""
        return {
            "market_position_analysis": "Market position analysis requires OpenAI API configuration",
            "competitive_advantages": ["Price competitiveness", "Product quality"],
            "threat_assessment": ["Competitor pricing pressure", "New market entrants"],
            "strategic_recommendations": [
                "Monitor competitor pricing closely",
                "Focus on product differentiation",
                "Improve customer service quality"
            ],
            "pricing_strategy": "Maintain competitive pricing while focusing on value proposition",
            "market_opportunities": ["Underserved customer segments", "Product feature gaps"],
            "risk_factors": ["Price wars", "Market saturation"],
            "full_analysis": "Detailed competitive intelligence analysis requires OpenAI API key configuration."
        }
    
    def _extract_market_position(self, content: str) -> str:
        """Extract market position analysis from AI response"""
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'market position' in line.lower():
                # Try to get the next few lines
                position_text = ' '.join(lines[i:i+3])
                return position_text.strip()
        return "Market position analysis not clearly identified"
    
    def _extract_advantages(self, content: str) -> List[str]:
        """Extract competitive advantages"""
        advantages = []
        lines = content.split('\n')
        
        in_advantages_section = False
        for line in lines:
            line = line.strip()
            if 'competitive advantage' in line.lower() or 'strength' in line.lower():
                in_advantages_section = True
                continue
            elif in_advantages_section and line.startswith(('-', '•', '*')):
                advantages.append(line[1:].strip())
            elif in_advantages_section and line and not line.startswith(('-', '•', '*')):
                in_advantages_section = False
        
        return advantages[:5]
    
    def _extract_threats(self, content: str) -> List[str]:
        """Extract threat assessment"""
        threats = []
        lines = content.split('\n')
        
        in_threats_section = False
        for line in lines:
            line = line.strip()
            if 'threat' in line.lower() or 'risk' in line.lower() or 'vulnerability' in line.lower():
                in_threats_section = True
                continue
            elif in_threats_section and line.startswith(('-', '•', '*')):
                threats.append(line[1:].strip())
            elif in_threats_section and line and not line.startswith(('-', '•', '*')):
                in_threats_section = False
        
        return threats[:5]
    
    def _extract_strategic_recommendations(self, content: str) -> List[str]:
        """Extract strategic recommendations"""
        recommendations = []
        lines = content.split('\n')
        
        in_recommendations_section = False
        for line in lines:
            line = line.strip()
            if 'strategic' in line.lower() and 'recommend' in line.lower():
                in_recommendations_section = True
                continue
            elif in_recommendations_section and line.startswith(('-', '•', '*')):
                recommendations.append(line[1:].strip())
            elif in_recommendations_section and line and not line.startswith(('-', '•', '*')):
                in_recommendations_section = False
        
        return recommendations[:6]
    
    def _extract_pricing_insights(self, content: str) -> str:
        """Extract pricing strategy insights"""
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'pricing' in line.lower() and ('strategy' in line.lower() or 'recommend' in line.lower()):
                # Get the next 2-3 lines
                pricing_text = ' '.join(lines[i:i+3])
                return pricing_text.strip()
        return "No specific pricing insights identified"
    
    def _extract_opportunities_detailed(self, content: str) -> List[str]:
        """Extract market opportunities"""
        opportunities = []
        lines = content.split('\n')
        
        in_opportunities_section = False
        for line in lines:
            line = line.strip()
            if 'opportunit' in line.lower() or 'gap' in line.lower():
                in_opportunities_section = True
                continue
            elif in_opportunities_section and line.startswith(('-', '•', '*')):
                opportunities.append(line[1:].strip())
            elif in_opportunities_section and line and not line.startswith(('-', '•', '*')):
                in_opportunities_section = False
        
        return opportunities[:4]
    
    def _extract_risks(self, content: str) -> List[str]:
        """Extract risk factors"""
        risks = []
        lines = content.split('\n')
        
        in_risks_section = False
        for line in lines:
            line = line.strip()
            if 'risk factor' in line.lower() or 'monitor' in line.lower():
                in_risks_section = True
                continue
            elif in_risks_section and line.startswith(('-', '•', '*')):
                risks.append(line[1:].strip())
            elif in_risks_section and line and not line.startswith(('-', '•', '*')):
                in_risks_section = False
        
        return risks[:4]
    
    def _extract_trend_insights(self, content: str) -> List[str]:
        """Extract trend insights"""
        insights = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if any(keyword in line.lower() for keyword in ['trend', 'pattern', 'indicates', 'shows']):
                if line.startswith(('-', '•', '*')):
                    insights.append(line[1:].strip())
                else:
                    insights.append(line)
        
        return insights[:5]
    
    def _extract_predictions(self, content: str) -> List[str]:
        """Extract market predictions"""
        predictions = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if any(keyword in line.lower() for keyword in ['predict', 'expect', 'forecast', 'likely']):
                if line.startswith(('-', '•', '*')):
                    predictions.append(line[1:].strip())
                else:
                    predictions.append(line)
        
        return predictions[:4]
    
    def _extract_trend_actions(self, content: str) -> List[str]:
        """Extract trend-based action recommendations"""
        actions = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if any(keyword in line.lower() for keyword in ['should', 'recommend', 'action', 'consider']):
                if line.startswith(('-', '•', '*')):
                    actions.append(line[1:].strip())
                else:
                    actions.append(line)
        
        return actions[:5]