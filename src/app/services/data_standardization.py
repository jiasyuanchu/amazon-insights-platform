"""Data standardization pipeline for competitor analysis"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import re
import structlog

logger = structlog.get_logger()


class DataStandardizer:
    """Standardize and normalize data from various sources"""
    
    @staticmethod
    def standardize_price(price: Any) -> Optional[float]:
        """
        Standardize price data from various formats
        
        Examples:
        - "$49.99" -> 49.99
        - "49,99 €" -> 49.99
        - "1,234.56" -> 1234.56
        """
        if price is None:
            return None
            
        if isinstance(price, (int, float)):
            return float(price)
            
        # Convert to string and clean
        price_str = str(price)
        
        # Remove currency symbols and whitespace
        price_str = re.sub(r'[$€£¥₹]', '', price_str)
        price_str = price_str.strip()
        
        # Handle European format (comma as decimal separator)
        if ',' in price_str and '.' in price_str:
            # If both exist, comma is thousands separator
            price_str = price_str.replace(',', '')
        elif ',' in price_str and price_str.count(',') == 1:
            # Single comma might be decimal separator
            parts = price_str.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                # Likely European format
                price_str = price_str.replace(',', '.')
            else:
                # Likely thousands separator
                price_str = price_str.replace(',', '')
        
        try:
            return float(price_str)
        except (ValueError, TypeError):
            logger.warning("Failed to parse price", price=price)
            return None
    
    @staticmethod
    def standardize_rating(rating: Any) -> Optional[float]:
        """
        Standardize rating data
        
        Examples:
        - "4.5 out of 5 stars" -> 4.5
        - "4,5" -> 4.5
        - 92 (out of 100) -> 4.6
        """
        if rating is None:
            return None
            
        if isinstance(rating, (int, float)):
            # If it's already a number
            if rating <= 5:
                return float(rating)
            elif rating <= 100:
                # Convert percentage to 5-star scale
                return (rating / 100) * 5
            else:
                return None
        
        # Convert to string and extract number
        rating_str = str(rating)
        
        # Replace comma with dot
        rating_str = rating_str.replace(',', '.')
        
        # Extract first number
        match = re.search(r'(\d+\.?\d*)', rating_str)
        if match:
            try:
                value = float(match.group(1))
                if value <= 5:
                    return value
                elif value <= 100:
                    return (value / 100) * 5
            except ValueError:
                pass
        
        logger.warning("Failed to parse rating", rating=rating)
        return None
    
    @staticmethod
    def standardize_bsr(bsr: Any) -> Optional[int]:
        """
        Standardize Best Sellers Rank
        
        Examples:
        - "#1,234 in Electronics" -> 1234
        - "1234" -> 1234
        """
        if bsr is None:
            return None
            
        if isinstance(bsr, int):
            return bsr
            
        # Convert to string and clean
        bsr_str = str(bsr)
        
        # Remove # and commas
        bsr_str = bsr_str.replace('#', '').replace(',', '')
        
        # Extract first number
        match = re.search(r'(\d+)', bsr_str)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass
        
        logger.warning("Failed to parse BSR", bsr=bsr)
        return None
    
    @staticmethod
    def standardize_review_count(count: Any) -> Optional[int]:
        """
        Standardize review count
        
        Examples:
        - "1,234 customer reviews" -> 1234
        - "1.2K" -> 1200
        - "2.5M" -> 2500000
        """
        if count is None:
            return None
            
        if isinstance(count, int):
            return count
            
        # Convert to string and clean
        count_str = str(count).upper()
        
        # Remove commas
        count_str = count_str.replace(',', '')
        
        # Handle K, M suffixes
        multiplier = 1
        if 'K' in count_str:
            multiplier = 1000
            count_str = count_str.replace('K', '')
        elif 'M' in count_str:
            multiplier = 1000000
            count_str = count_str.replace('M', '')
        
        # Extract number
        match = re.search(r'(\d+\.?\d*)', count_str)
        if match:
            try:
                return int(float(match.group(1)) * multiplier)
            except ValueError:
                pass
        
        logger.warning("Failed to parse review count", count=count)
        return None
    
    @staticmethod
    def standardize_product_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Standardize complete product data structure
        
        Args:
            data: Raw product data from scraping
            
        Returns:
            Standardized product data
        """
        standardized = {
            "asin": data.get("asin"),
            "title": DataStandardizer.clean_text(data.get("title")),
            "brand": DataStandardizer.clean_text(data.get("brand")),
            "price": DataStandardizer.standardize_price(data.get("price")),
            "rating": DataStandardizer.standardize_rating(data.get("rating")),
            "review_count": DataStandardizer.standardize_review_count(
                data.get("review_count") or data.get("reviews")
            ),
            "bsr": DataStandardizer.standardize_bsr(data.get("bsr")),
            "category": DataStandardizer.clean_text(data.get("category")),
            "features": DataStandardizer.extract_features(data.get("features")),
            "images": DataStandardizer.clean_urls(data.get("images", [])),
            "availability": DataStandardizer.standardize_availability(
                data.get("availability")
            ),
            "prime_eligible": DataStandardizer.parse_boolean(
                data.get("prime") or data.get("prime_eligible")
            ),
            "scraped_at": datetime.utcnow().isoformat()
        }
        
        # Remove None values
        return {k: v for k, v in standardized.items() if v is not None}
    
    @staticmethod
    def clean_text(text: Any) -> Optional[str]:
        """Clean and normalize text data"""
        if text is None:
            return None
            
        text = str(text).strip()
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep useful ones
        text = re.sub(r'[^\w\s\-.,!?()&/]', '', text)
        
        return text if text else None
    
    @staticmethod
    def extract_features(features: Any) -> List[str]:
        """Extract and clean product features"""
        if not features:
            return []
            
        if isinstance(features, str):
            # Split by common delimiters
            features = re.split(r'[;|\n]', features)
        elif not isinstance(features, list):
            return []
        
        cleaned = []
        for feature in features:
            if feature:
                clean = DataStandardizer.clean_text(feature)
                if clean and len(clean) > 5:  # Filter out too short features
                    cleaned.append(clean)
        
        return cleaned[:10]  # Limit to 10 features
    
    @staticmethod
    def clean_urls(urls: Any) -> List[str]:
        """Clean and validate URLs"""
        if not urls:
            return []
            
        if isinstance(urls, str):
            urls = [urls]
        elif not isinstance(urls, list):
            return []
        
        cleaned = []
        for url in urls:
            if url and isinstance(url, str):
                url = url.strip()
                if url.startswith(('http://', 'https://', '//')):
                    cleaned.append(url)
        
        return cleaned
    
    @staticmethod
    def standardize_availability(availability: Any) -> Optional[str]:
        """Standardize availability status"""
        if not availability:
            return None
            
        avail_str = str(availability).lower()
        
        if 'in stock' in avail_str or 'available' in avail_str:
            return 'in_stock'
        elif 'out of stock' in avail_str or 'unavailable' in avail_str:
            return 'out_of_stock'
        elif 'limited' in avail_str or 'low stock' in avail_str:
            return 'limited'
        else:
            # Try to extract quantity
            match = re.search(r'(\d+)\s*(?:left|available|in stock)', avail_str)
            if match:
                qty = int(match.group(1))
                if qty == 0:
                    return 'out_of_stock'
                elif qty < 10:
                    return 'limited'
                else:
                    return 'in_stock'
        
        return None
    
    @staticmethod
    def parse_boolean(value: Any) -> Optional[bool]:
        """Parse various boolean representations"""
        if value is None:
            return None
            
        if isinstance(value, bool):
            return value
            
        str_val = str(value).lower()
        
        if str_val in ('true', 'yes', '1', 'y', 't'):
            return True
        elif str_val in ('false', 'no', '0', 'n', 'f'):
            return False
        
        return None
    
    @staticmethod
    def calculate_similarity_score(
        product1: Dict[str, Any],
        product2: Dict[str, Any]
    ) -> float:
        """
        Calculate similarity score between two products
        
        Returns:
            Score between 0 and 1
        """
        score = 0.0
        weights = {
            'category': 0.3,
            'price_range': 0.2,
            'brand': 0.15,
            'rating_range': 0.1,
            'features': 0.25
        }
        
        # Category match
        if product1.get('category') == product2.get('category'):
            score += weights['category']
        
        # Price similarity (within 20%)
        price1 = product1.get('price', 0)
        price2 = product2.get('price', 0)
        if price1 and price2:
            price_diff = abs(price1 - price2) / max(price1, price2)
            if price_diff < 0.2:
                score += weights['price_range'] * (1 - price_diff / 0.2)
        
        # Brand match
        if product1.get('brand') == product2.get('brand'):
            score += weights['brand']
        
        # Rating similarity
        rating1 = product1.get('rating', 0)
        rating2 = product2.get('rating', 0)
        if rating1 and rating2:
            rating_diff = abs(rating1 - rating2)
            if rating_diff < 1:
                score += weights['rating_range'] * (1 - rating_diff)
        
        # Feature overlap
        features1 = set(product1.get('features', []))
        features2 = set(product2.get('features', []))
        if features1 and features2:
            overlap = len(features1.intersection(features2))
            total = len(features1.union(features2))
            if total > 0:
                score += weights['features'] * (overlap / total)
        
        return min(1.0, score)


class CompetitorDataPipeline:
    """Pipeline for processing competitor data"""
    
    def __init__(self):
        self.standardizer = DataStandardizer()
    
    async def process_scraped_data(
        self,
        raw_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process raw scraped data through standardization pipeline
        
        Args:
            raw_data: Raw data from web scraping
            
        Returns:
            Standardized and enriched data
        """
        # Standardize the data
        standardized = self.standardizer.standardize_product_data(raw_data)
        
        # Add metadata
        standardized['processing_timestamp'] = datetime.utcnow().isoformat()
        standardized['data_quality_score'] = self._calculate_data_quality(standardized)
        
        # Log processing
        logger.info(
            "Data processed",
            asin=standardized.get('asin'),
            quality_score=standardized.get('data_quality_score')
        )
        
        return standardized
    
    def _calculate_data_quality(self, data: Dict[str, Any]) -> float:
        """
        Calculate data quality score
        
        Returns:
            Score between 0 and 1
        """
        required_fields = ['asin', 'title', 'price', 'rating']
        optional_fields = ['brand', 'bsr', 'review_count', 'category', 'features']
        
        score = 0.0
        
        # Check required fields (60% weight)
        for field in required_fields:
            if data.get(field) is not None:
                score += 0.6 / len(required_fields)
        
        # Check optional fields (40% weight)
        for field in optional_fields:
            if data.get(field) is not None:
                score += 0.4 / len(optional_fields)
        
        return round(score, 2)
    
    async def batch_process(
        self,
        raw_data_list: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Process multiple products in batch
        
        Args:
            raw_data_list: List of raw product data
            
        Returns:
            List of standardized products
        """
        processed = []
        
        for raw_data in raw_data_list:
            try:
                standardized = await self.process_scraped_data(raw_data)
                processed.append(standardized)
            except Exception as e:
                logger.error(
                    "Failed to process data",
                    error=str(e),
                    asin=raw_data.get('asin')
                )
        
        return processed
    
    def compare_products(
        self,
        main_product: Dict[str, Any],
        competitor: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare two products and generate insights
        
        Args:
            main_product: Standardized main product data
            competitor: Standardized competitor data
            
        Returns:
            Comparison analysis
        """
        comparison = {
            'similarity_score': self.standardizer.calculate_similarity_score(
                main_product, competitor
            ),
            'price_difference': None,
            'rating_difference': None,
            'review_difference': None,
            'competitive_position': None
        }
        
        # Price comparison
        if main_product.get('price') and competitor.get('price'):
            price_diff = main_product['price'] - competitor['price']
            comparison['price_difference'] = price_diff
            comparison['price_difference_percent'] = (
                price_diff / competitor['price'] * 100
            )
            
            if abs(price_diff) < 5:
                comparison['price_position'] = 'comparable'
            elif price_diff > 0:
                comparison['price_position'] = 'premium'
            else:
                comparison['price_position'] = 'value'
        
        # Rating comparison
        if main_product.get('rating') and competitor.get('rating'):
            comparison['rating_difference'] = (
                main_product['rating'] - competitor['rating']
            )
        
        # Review count comparison
        if main_product.get('review_count') and competitor.get('review_count'):
            comparison['review_difference'] = (
                main_product['review_count'] - competitor['review_count']
            )
        
        # Determine competitive position
        comparison['competitive_position'] = self._determine_position(comparison)
        
        return comparison
    
    def _determine_position(self, comparison: Dict[str, Any]) -> str:
        """Determine competitive position based on comparison"""
        advantages = 0
        disadvantages = 0
        
        # Check price
        if comparison.get('price_position') == 'value':
            advantages += 1
        elif comparison.get('price_position') == 'premium':
            if comparison.get('rating_difference', 0) > 0:
                advantages += 1  # Premium justified by quality
            else:
                disadvantages += 1
        
        # Check rating
        if comparison.get('rating_difference', 0) > 0.2:
            advantages += 1
        elif comparison.get('rating_difference', 0) < -0.2:
            disadvantages += 1
        
        # Check reviews (market presence)
        if comparison.get('review_difference', 0) > 100:
            advantages += 1
        elif comparison.get('review_difference', 0) < -100:
            disadvantages += 1
        
        if advantages > disadvantages:
            return 'leader'
        elif disadvantages > advantages:
            return 'challenger'
        else:
            return 'competitive'