# Amazon Insights Platform - 手動測試指南

## 🚀 準備工作

### 1. 確認系統運行狀態
```bash
# 檢查所有容器是否運行
docker ps

# 應該看到以下容器:
# - amazon_insights_api (API服務)
# - amazon_insights_postgres (資料庫)
# - amazon_insights_redis (快取)
# - amazon_insights_celery_worker (背景任務)
# - amazon_insights_celery_beat (定時任務)
# - amazon_insights_flower (任務監控)
```

### 2. 訪問系統介面
- **API文檔**: http://localhost:8000/api/v1/docs
- **Flower監控**: http://localhost:5555
- **API根路徑**: http://localhost:8000/

---

## 📋 基本功能測試

### Test 1: 用戶註冊與登入

#### 1.1 註冊新用戶
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser2",
    "email": "testuser2@example.com",
    "password": "SecurePass123!",
    "full_name": "Test User"
  }'
```

**預期結果**: 返回新用戶資訊，包含 user_id

#### 1.2 用戶登入
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser2&password=SecurePass123!"
```

**預期結果**: 返回 JWT token
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

#### 1.3 保存Token供後續使用
```bash
# 將token保存為環境變數
export TOKEN="你的access_token"
```

---

### Test 2: 產品管理 (CRUD)

#### 2.1 創建產品
```bash
curl -X POST "http://localhost:8000/api/v1/products" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "asin": "B0BSHF7LLL",
    "title": "Apple Watch Series 9",
    "category": "Electronics",
    "product_url": "https://www.amazon.com/dp/B0BSHF7LLL"
  }'
```

**預期結果**: 返回創建的產品資訊，包含 product_id

#### 2.2 查詢所有產品
```bash
curl -X GET "http://localhost:8000/api/v1/products" \
  -H "Authorization: Bearer $TOKEN"
```

**預期結果**: 返回產品列表

#### 2.3 查詢單個產品
```bash
# 使用上一步返回的product_id
curl -X GET "http://localhost:8000/api/v1/products/{product_id}" \
  -H "Authorization: Bearer $TOKEN"
```

#### 2.4 更新產品
```bash
curl -X PUT "http://localhost:8000/api/v1/products/{product_id}" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Apple Watch Series 9 - Updated",
    "is_active": true
  }'
```

#### 2.5 刪除產品
```bash
curl -X DELETE "http://localhost:8000/api/v1/products/{product_id}" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🎯 進階功能測試

### Feature 1: 真實Amazon資料抓取與分析

#### Step 1: 添加真實Amazon產品
```bash
# 添加iPhone 15 Pro
curl -X POST "http://localhost:8000/api/v1/products" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "asin": "B0CJK5Y7R5",
    "title": "iPhone 15 Pro",
    "category": "Electronics"
  }'
```

記錄返回的 `product_id`

#### Step 2: 觸發產品資料抓取
```bash
curl -X POST "http://localhost:8000/api/v1/scraping/products/{product_id}/scrape" \
  -H "Authorization: Bearer $TOKEN"
```

**預期結果**: 返回任務ID
```json
{
  "task_id": "abc123...",
  "status": "PENDING"
}
```

#### Step 3: 檢查抓取狀態
```bash
curl -X GET "http://localhost:8000/api/v1/scraping/status/{task_id}" \
  -H "Authorization: Bearer $TOKEN"
```

**預期結果**: 顯示任務進度
```json
{
  "task_id": "abc123...",
  "status": "SUCCESS",
  "result": {
    "price": "$999.00",
    "rating": "4.5",
    "availability": "In Stock"
  }
}
```

#### Step 4: 查看更新後的產品資訊
```bash
curl -X GET "http://localhost:8000/api/v1/products/{product_id}" \
  -H "Authorization: Bearer $TOKEN"
```

**預期結果**: 產品資訊包含最新抓取的數據

---

### Feature 2: 競爭對手發現與分析

#### Step 1: 觸發競爭對手發現
```bash
curl -X POST "http://localhost:8000/api/v1/competitors/discover" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": {product_id},
    "max_competitors": 5
  }'
```

**預期結果**: 返回發現的競爭對手列表
```json
{
  "competitors": [
    {
      "competitor_id": 1,
      "asin": "B0CHX1W1H3",
      "title": "Samsung Galaxy S24",
      "price": "$899.00",
      "similarity_score": 0.92
    }
  ]
}
```

#### Step 2: 執行競爭分析
```bash
curl -X POST "http://localhost:8000/api/v1/competitors/analyze" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": {product_id},
    "competitor_id": {competitor_id}
  }'
```

**預期結果**: 返回詳細競爭分析
```json
{
  "price_comparison": {
    "price_difference": 100.00,
    "price_position": "premium"
  },
  "performance_comparison": {
    "rating_difference": 0.2,
    "review_count_difference": 500
  },
  "market_position": "leader"
}
```

#### Step 3: 獲取AI競爭洞察
```bash
curl -X GET "http://localhost:8000/api/v1/competitors/insights/{product_id}" \
  -H "Authorization: Bearer $TOKEN"
```

**預期結果**: 返回AI生成的競爭策略建議
```json
{
  "market_position_analysis": "產品定位於高端市場...",
  "competitive_advantages": ["品牌認知度高", "技術領先"],
  "threat_assessment": ["價格競爭激烈", "新進入者威脅"],
  "strategic_recommendations": [
    "考慮推出中端產品線",
    "加強售後服務差異化"
  ]
}
```

---

### Feature 3: AI驅動的商業洞察

#### Step 1: 生成產品洞察
```bash
curl -X POST "http://localhost:8000/api/v1/insights/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": {product_id},
    "insight_type": "comprehensive"
  }'
```

**預期結果**: AI生成的綜合分析
```json
{
  "summary": "產品在過去30天表現穩定...",
  "pricing_insights": {
    "recommendation": "當前定價策略合理",
    "optimal_price_range": "$950-$1050"
  },
  "market_trends": {
    "trend": "上升",
    "seasonal_factors": "即將進入購物季"
  },
  "action_items": [
    "準備庫存應對季節性需求",
    "監控競爭對手促銷活動"
  ]
}
```

#### Step 2: 查看歷史指標與趨勢
```bash
curl -X GET "http://localhost:8000/api/v1/metrics/products/{product_id}?days=7" \
  -H "Authorization: Bearer $TOKEN"
```

**預期結果**: 返回7天的歷史數據
```json
{
  "metrics": [
    {
      "date": "2024-01-20",
      "price": 999.00,
      "bsr": 1234,
      "rating": 4.5,
      "review_count": 1500
    }
  ],
  "trends": {
    "price_trend": "stable",
    "bsr_trend": "improving",
    "review_trend": "increasing"
  }
}
```

#### Step 3: 獲取市場分析報告
```bash
curl -X GET "http://localhost:8000/api/v1/insights/market-analysis/{product_id}" \
  -H "Authorization: Bearer $TOKEN"
```

**預期結果**: 完整的市場分析報告

---

## 🔍 透過UI測試 (使用Swagger)

### 1. 打開API文檔
瀏覽器訪問: http://localhost:8000/api/v1/docs

### 2. 認證
1. 點擊右上角 "Authorize" 按鈕
2. 輸入用戶名和密碼
3. 點擊 "Authorize" 完成認證

### 3. 測試各個端點
在Swagger UI中可以直接測試所有API端點：
- 點擊端點展開詳情
- 點擊 "Try it out"
- 填寫參數
- 點擊 "Execute"
- 查看響應結果

---

## 📊 監控與驗證

### 1. 查看Celery任務執行情況
訪問 Flower: http://localhost:5555
- 查看 Tasks 頁面了解任務執行狀態
- 查看 Workers 頁面確認worker運行狀態

### 2. 檢查資料庫數據
```bash
# 進入PostgreSQL
docker exec -it amazon_insights_postgres psql -U user -d amazon_insights

# 查看產品表
SELECT * FROM products LIMIT 5;

# 查看指標表
SELECT * FROM product_metrics ORDER BY scraped_at DESC LIMIT 5;

# 查看競爭對手表
SELECT * FROM competitors LIMIT 5;

# 退出
\q
```

### 3. 查看Redis快取
```bash
# 進入Redis
docker exec -it amazon_insights_redis redis-cli

# 查看所有keys
KEYS *

# 查看特定快取
GET "product:1"

# 退出
exit
```

---

## ✅ 測試檢查清單

### 基本功能
- [ ] 用戶註冊成功
- [ ] 用戶登入獲得Token
- [ ] 創建產品成功
- [ ] 查詢產品列表
- [ ] 更新產品資訊
- [ ] 刪除產品

### 進階功能1: 資料抓取
- [ ] 觸發Amazon產品抓取
- [ ] 抓取任務成功完成
- [ ] 產品資訊更新（價格、評分、庫存）
- [ ] 歷史指標記錄

### 進階功能2: 競爭分析
- [ ] 發現競爭對手
- [ ] 執行競爭分析
- [ ] 價格比較正確
- [ ] AI競爭洞察生成

### 進階功能3: AI洞察
- [ ] 生成產品洞察
- [ ] 獲取歷史趨勢
- [ ] 市場分析報告
- [ ] 策略建議合理

---

## 🐛 常見問題排查

### 1. 401 Unauthorized
**問題**: API返回401錯誤
**解決**: 
- 確認Token正確
- Token可能過期，重新登入獲取新Token

### 2. 資料抓取失敗
**問題**: Firecrawl API錯誤
**解決**:
- 檢查.env中的FIRECRAWL_API_KEY
- 確認網路連接正常
- 查看docker logs amazon_insights_api

### 3. AI洞察無內容
**問題**: OpenAI API未返回結果
**解決**:
- 檢查.env中的OPENAI_API_KEY
- 確認API額度充足

### 4. Celery任務卡住
**問題**: 任務狀態一直是PENDING
**解決**:
```bash
# 重啟Celery worker
docker restart amazon_insights_celery_worker
docker restart amazon_insights_celery_beat
```

---

## 📝 測試結果記錄

### 測試資訊
- **測試日期**: ___________
- **測試人員**: ___________
- **環境**: Development

### 測試結果
| 功能類別 | 測試項目 | 結果 | 備註 |
|---------|---------|------|------|
| 基本功能 | 用戶管理 | ⬜ Pass ⬜ Fail | |
| 基本功能 | 產品CRUD | ⬜ Pass ⬜ Fail | |
| 進階功能1 | Amazon抓取 | ⬜ Pass ⬜ Fail | |
| 進階功能2 | 競爭分析 | ⬜ Pass ⬜ Fail | |
| 進階功能3 | AI洞察 | ⬜ Pass ⬜ Fail | |

### 發現的問題
1. ___________
2. ___________
3. ___________

---

## 🎯 下一步

完成手動測試後，你可以：
1. 部署到生產環境
2. 設定自動化測試
3. 配置監控告警
4. 優化系統效能

祝測試順利！🚀