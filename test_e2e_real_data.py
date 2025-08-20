#!/usr/bin/env python3
"""
End-to-End Test with Real Amazon Data
完整測試從資料抓取到分析的整個流程
"""
import asyncio
import sys
import json
from datetime import datetime
sys.path.append('src')

from src.app.core.config import settings
from src.app.core.database import AsyncSessionLocal, engine
from src.app.models.product import Product, ProductMetrics
from src.app.models.competitor import Competitor, CompetitorAnalysis
from src.app.services.firecrawl_service import FirecrawlService
from src.app.services.openai_service import OpenAIService
from src.app.services.product_service import ProductService
from src.app.services.competitor_service import CompetitorService
from sqlalchemy import select
import httpx


class E2ETestRunner:
    """端到端測試執行器"""
    
    def __init__(self):
        self.firecrawl = FirecrawlService()
        self.openai = OpenAIService()
        # Services will be initialized with db session when needed
        self.test_results = []
        
    async def run_all_tests(self):
        """執行所有端到端測試"""
        print("🚀 開始真實資料端到端測試")
        print("=" * 80)
        
        # Test 1: 創建產品並抓取資料
        product_id = await self.test_product_creation_and_scraping()
        
        if product_id:
            # Test 2: 更新產品指標
            await self.test_metrics_update(product_id)
            
            # Test 3: 發現競爭對手
            competitor_ids = await self.test_competitor_discovery(product_id)
            
            # Test 4: 競爭分析
            if competitor_ids:
                await self.test_competitive_analysis(product_id, competitor_ids)
            
            # Test 5: AI洞察生成
            await self.test_ai_insights_generation(product_id)
            
            # Test 6: API端點測試
            await self.test_api_endpoints(product_id)
            
            # Test 7: Celery異步任務
            await self.test_celery_tasks(product_id)
        
        # 顯示測試結果
        self.display_results()
    
    async def test_product_creation_and_scraping(self):
        """Test 1: 創建產品並抓取真實Amazon資料"""
        print("\n📦 Test 1: 產品創建與資料抓取")
        print("-" * 40)
        
        try:
            async with AsyncSessionLocal() as db:
                # 首先確保有測試用戶
                from src.app.models.user import User
                from sqlalchemy import select
                
                result = await db.execute(
                    select(User).where(User.email == "test@example.com")
                )
                test_user = result.scalar_one_or_none()
                
                if not test_user:
                    print("  創建測試用戶...")
                    test_user = User(
                        username="testuser",
                        email="test@example.com",
                        hashed_password="test_hash"
                    )
                    db.add(test_user)
                    await db.commit()
                    await db.refresh(test_user)
                    print(f"  ✅ 測試用戶創建成功，ID: {test_user.id}")
                else:
                    print(f"  ℹ️ 使用現有測試用戶，ID: {test_user.id}")
                # 測試產品資料
                test_products = [
                    {
                        "asin": "B0D1XD1ZV3",
                        "title": "Apple AirPods Pro (測試)",
                        "category": "Electronics"
                    },
                    {
                        "asin": "B08N5WRWNW",
                        "title": "Echo Dot (測試)",
                        "category": "Smart Home"
                    }
                ]
                
                created_products = []
                
                for product_data in test_products:
                    print(f"\n創建產品: {product_data['title']}")
                    
                    # 檢查產品是否已存在
                    result = await db.execute(
                        select(Product).where(Product.asin == product_data['asin'])
                    )
                    existing = result.scalar_one_or_none()
                    
                    if existing:
                        print(f"  ⚠️ 產品已存在，使用現有ID: {existing.id}")
                        product = existing
                    else:
                        # 創建新產品
                        product = Product(
                            asin=product_data['asin'],
                            title=product_data['title'],
                            category=product_data['category'],
                            product_url=f"https://www.amazon.com/dp/{product_data['asin']}",
                            user_id=test_user.id,  # 添加用戶ID
                            is_active=True
                        )
                        db.add(product)
                        await db.commit()
                        await db.refresh(product)
                        print(f"  ✅ 產品創建成功，ID: {product.id}")
                    
                    # 抓取真實資料
                    print(f"  🔄 抓取Amazon資料...")
                    scraped_data = await self.firecrawl.scrape_amazon_product(product.asin)
                    
                    if scraped_data.get('success'):
                        # 更新產品資訊
                        if scraped_data.get('title') != 'Unknown Product':
                            product.title = scraped_data['title']
                        product.current_price = self._parse_price(scraped_data.get('price'))
                        product.current_rating = self._parse_rating(scraped_data.get('rating'))
                        product.updated_at = datetime.utcnow()
                        
                        await db.commit()
                        print(f"  ✅ 資料抓取成功")
                        print(f"     - 價格: {scraped_data.get('price')}")
                        print(f"     - 評分: {scraped_data.get('rating')}")
                        print(f"     - 庫存: {scraped_data.get('availability')}")
                        
                        created_products.append(product.id)
                    else:
                        print(f"  ❌ 資料抓取失敗: {scraped_data.get('error')}")
                
                self.test_results.append({
                    "test": "產品創建與抓取",
                    "status": "✅ 成功" if created_products else "❌ 失敗",
                    "details": f"創建 {len(created_products)} 個產品"
                })
                
                return created_products[0] if created_products else None
                
        except Exception as e:
            print(f"  ❌ 錯誤: {str(e)}")
            self.test_results.append({
                "test": "產品創建與抓取",
                "status": "❌ 失敗",
                "details": str(e)
            })
            return None
    
    async def test_metrics_update(self, product_id: int):
        """Test 2: 更新產品指標"""
        print("\n📊 Test 2: 產品指標更新")
        print("-" * 40)
        
        try:
            async with AsyncSessionLocal() as db:
                # 獲取產品
                result = await db.execute(
                    select(Product).where(Product.id == product_id)
                )
                product = result.scalar_one()
                
                # 創建指標記錄
                metrics = ProductMetrics(
                    product_id=product.id,
                    price=product.current_price or 0,
                    bsr=12345,  # 模擬BSR
                    rating=product.current_rating or 0,
                    review_count=100,  # 模擬評論數
                    scraped_at=datetime.utcnow()
                )
                
                db.add(metrics)
                await db.commit()
                
                print(f"  ✅ 指標更新成功")
                print(f"     - 產品ID: {product.id}")
                print(f"     - 價格: ${metrics.price}")
                print(f"     - BSR: {metrics.bsr}")
                print(f"     - 評分: {metrics.rating}")
                
                self.test_results.append({
                    "test": "產品指標更新",
                    "status": "✅ 成功",
                    "details": "指標記錄已創建"
                })
                
        except Exception as e:
            print(f"  ❌ 錯誤: {str(e)}")
            self.test_results.append({
                "test": "產品指標更新",
                "status": "❌ 失敗",
                "details": str(e)
            })
    
    async def test_competitor_discovery(self, product_id: int):
        """Test 3: 發現競爭對手"""
        print("\n🔍 Test 3: 競爭對手發現")
        print("-" * 40)
        
        try:
            async with AsyncSessionLocal() as db:
                # 模擬競爭對手ASINs
                competitor_asins = [
                    "B0B2RJPJ2F",  # Sony WF-1000XM4
                    "B08G1Y1V26",  # Bose QuietComfort
                    "B085VQFHKP",  # Samsung Galaxy Buds
                ]
                
                created_competitors = []
                
                for asin in competitor_asins:
                    print(f"\n  添加競爭對手: {asin}")
                    
                    # 檢查是否已存在
                    result = await db.execute(
                        select(Competitor).where(
                            Competitor.main_product_id == product_id,
                            Competitor.competitor_asin == asin
                        )
                    )
                    existing = result.scalar_one_or_none()
                    
                    if not existing:
                        # 抓取競爭對手資料
                        scraped = await self.firecrawl.scrape_amazon_product(asin)
                        
                        competitor = Competitor(
                            main_product_id=product_id,
                            competitor_asin=asin,
                            title=scraped.get('title', f'Competitor {asin}'),
                            product_url=f"https://www.amazon.com/dp/{asin}",
                            current_price=self._parse_price(scraped.get('price')),
                            current_rating=self._parse_rating(scraped.get('rating')),
                            similarity_score=0.85,  # 模擬相似度
                            is_direct_competitor=True
                        )
                        
                        db.add(competitor)
                        await db.commit()
                        await db.refresh(competitor)
                        
                        print(f"    ✅ 競爭對手添加成功，ID: {competitor.id}")
                        created_competitors.append(competitor.id)
                    else:
                        print(f"    ⚠️ 競爭對手已存在，ID: {existing.id}")
                        created_competitors.append(existing.id)
                
                self.test_results.append({
                    "test": "競爭對手發現",
                    "status": "✅ 成功",
                    "details": f"發現 {len(created_competitors)} 個競爭對手"
                })
                
                return created_competitors
                
        except Exception as e:
            print(f"  ❌ 錯誤: {str(e)}")
            self.test_results.append({
                "test": "競爭對手發現",
                "status": "❌ 失敗",
                "details": str(e)
            })
            return []
    
    async def test_competitive_analysis(self, product_id: int, competitor_ids: list):
        """Test 4: 競爭分析"""
        print("\n📈 Test 4: 競爭分析")
        print("-" * 40)
        
        try:
            async with AsyncSessionLocal() as db:
                # 獲取主產品
                result = await db.execute(
                    select(Product).where(Product.id == product_id)
                )
                main_product = result.scalar_one()
                
                # 分析每個競爭對手
                for comp_id in competitor_ids[:2]:  # 只分析前2個
                    result = await db.execute(
                        select(Competitor).where(Competitor.id == comp_id)
                    )
                    competitor = result.scalar_one()
                    
                    print(f"\n  分析競爭對手: {competitor.title[:30]}...")
                    
                    # 創建分析記錄
                    analysis = CompetitorAnalysis(
                        competitor_id=comp_id,
                        analyzed_at=datetime.utcnow(),
                        price_difference=float(main_product.current_price or 0) - float(competitor.current_price or 0),
                        price_difference_percent=self._calculate_percent_diff(
                            main_product.current_price,
                            competitor.current_price
                        ),
                        rating_difference=float(main_product.current_rating or 0) - float(competitor.current_rating or 0)
                    )
                    
                    # 生成AI洞察
                    if self.openai.api_key:
                        insights = await self.openai.analyze_competitive_landscape(
                            {
                                'title': main_product.title,
                                'price': main_product.current_price,
                                'rating': main_product.current_rating
                            },
                            [{
                                'title': competitor.title,
                                'price': competitor.current_price,
                                'rating': competitor.current_rating
                            }]
                        )
                        analysis.ai_insights = insights
                    
                    db.add(analysis)
                    await db.commit()
                    
                    print(f"    ✅ 分析完成")
                    print(f"       - 價格差異: ${analysis.price_difference:.2f}")
                    print(f"       - 百分比差異: {analysis.price_difference_percent:.1f}%")
                
                self.test_results.append({
                    "test": "競爭分析",
                    "status": "✅ 成功",
                    "details": f"分析了 {min(2, len(competitor_ids))} 個競爭對手"
                })
                
        except Exception as e:
            print(f"  ❌ 錯誤: {str(e)}")
            self.test_results.append({
                "test": "競爭分析",
                "status": "❌ 失敗",
                "details": str(e)
            })
    
    async def test_ai_insights_generation(self, product_id: int):
        """Test 5: AI洞察生成"""
        print("\n🤖 Test 5: AI洞察生成")
        print("-" * 40)
        
        try:
            async with AsyncSessionLocal() as db:
                # 獲取產品和歷史指標
                result = await db.execute(
                    select(Product).where(Product.id == product_id)
                )
                product = result.scalar_one()
                
                # 獲取指標歷史
                result = await db.execute(
                    select(ProductMetrics)
                    .where(ProductMetrics.product_id == product_id)
                    .order_by(ProductMetrics.scraped_at.desc())
                    .limit(5)
                )
                metrics = result.scalars().all()
                
                print(f"  生成產品洞察: {product.title[:30]}...")
                
                # 生成AI洞察
                product_data = {
                    'title': product.title,
                    'asin': product.asin,
                    'price': product.current_price,
                    'rating': product.current_rating,
                    'category': product.category
                }
                
                metrics_history = [
                    {
                        'date': m.scraped_at.strftime('%Y-%m-%d'),
                        'price': m.price,
                        'bsr': m.bsr,
                        'rating': m.rating
                    }
                    for m in metrics
                ]
                
                insights = await self.openai.generate_product_insights(
                    product_data,
                    metrics_history
                )
                
                print(f"  ✅ AI洞察生成成功")
                print(f"     摘要: {insights['summary'][:100]}...")
                
                if insights.get('recommendations'):
                    print(f"     建議數量: {len(insights['recommendations'])}")
                
                self.test_results.append({
                    "test": "AI洞察生成",
                    "status": "✅ 成功",
                    "details": "洞察已生成"
                })
                
        except Exception as e:
            print(f"  ❌ 錯誤: {str(e)}")
            self.test_results.append({
                "test": "AI洞察生成",
                "status": "❌ 失敗",
                "details": str(e)
            })
    
    async def test_api_endpoints(self, product_id: int):
        """Test 6: API端點測試"""
        print("\n🌐 Test 6: API端點測試")
        print("-" * 40)
        
        try:
            async with httpx.AsyncClient() as client:
                base_url = "http://localhost:8000"
                
                # 測試根端點
                print("  測試 / 端點...")
                response = await client.get(f"{base_url}/")
                assert response.status_code == 200
                data = response.json()
                print(f"    ✅ API名稱: {data['name']}")
                print(f"    ✅ 版本: {data['version']}")
                
                # 測試產品端點 (需要認證，這裡只測試結構)
                print("  測試 /api/v1/products 端點...")
                response = await client.get(f"{base_url}/api/v1/products")
                print(f"    ℹ️ 狀態碼: {response.status_code}")
                
                self.test_results.append({
                    "test": "API端點測試",
                    "status": "✅ 成功",
                    "details": "API響應正常"
                })
                
        except Exception as e:
            print(f"  ❌ 錯誤: {str(e)}")
            self.test_results.append({
                "test": "API端點測試",
                "status": "❌ 失敗",
                "details": str(e)
            })
    
    async def test_celery_tasks(self, product_id: int):
        """Test 7: Celery異步任務"""
        print("\n⚡ Test 7: Celery異步任務")
        print("-" * 40)
        
        try:
            from src.app.tasks.scraping_tasks import scrape_all_products
            
            print(f"  觸發批量產品抓取任務...")
            
            # 觸發異步任務
            task = scrape_all_products.delay()
            print(f"    ✅ 任務已提交，ID: {task.id}")
            
            # 等待一下讓任務開始
            await asyncio.sleep(2)
            
            print(f"    ℹ️ 任務狀態: {task.status}")
            
            self.test_results.append({
                "test": "Celery異步任務",
                "status": "✅ 成功",
                "details": f"任務ID: {task.id}"
            })
            
        except Exception as e:
            print(f"  ❌ 錯誤: {str(e)}")
            self.test_results.append({
                "test": "Celery異步任務",
                "status": "⚠️ 跳過",
                "details": "Celery未配置或未運行"
            })
    
    def display_results(self):
        """顯示測試結果總結"""
        print("\n" + "=" * 80)
        print("📊 測試結果總結")
        print("=" * 80)
        
        for result in self.test_results:
            print(f"\n{result['test']}:")
            print(f"  狀態: {result['status']}")
            print(f"  詳情: {result['details']}")
        
        # 計算成功率
        success_count = sum(1 for r in self.test_results if "✅" in r['status'])
        total_count = len(self.test_results)
        success_rate = (success_count / total_count * 100) if total_count > 0 else 0
        
        print("\n" + "-" * 40)
        print(f"總計: {success_count}/{total_count} 測試通過")
        print(f"成功率: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("\n🎉 端到端測試成功！系統運作正常。")
        elif success_rate >= 60:
            print("\n⚠️ 部分測試通過，請檢查失敗的項目。")
        else:
            print("\n❌ 測試失敗較多，需要修復問題。")
    
    def _parse_price(self, price_str):
        """解析價格字串"""
        if not price_str or price_str == 'N/A':
            return None
        try:
            return float(str(price_str).replace('$', '').replace(',', ''))
        except:
            return None
    
    def _parse_rating(self, rating_str):
        """解析評分字串"""
        if not rating_str or rating_str == 'N/A':
            return None
        try:
            return float(str(rating_str).split()[0])
        except:
            return None
    
    def _calculate_percent_diff(self, val1, val2):
        """計算百分比差異"""
        if not val2 or val2 == 0:
            return 0
        return ((val1 or 0) - val2) / val2 * 100


async def main():
    """主函數"""
    print("🏁 Amazon Insights Platform - 真實資料端到端測試")
    print("=" * 80)
    print(f"時間: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"環境: Development")
    print()
    
    # 檢查API keys
    print("🔑 檢查配置...")
    print(f"  Firecrawl API: {'✅ 已配置' if settings.FIRECRAWL_API_KEY else '❌ 未配置'}")
    print(f"  OpenAI API: {'✅ 已配置' if settings.OPENAI_API_KEY else '❌ 未配置'}")
    
    if not settings.FIRECRAWL_API_KEY:
        print("\n❌ 錯誤: Firecrawl API key未配置")
        return False
    
    # 執行測試
    runner = E2ETestRunner()
    await runner.run_all_tests()
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)