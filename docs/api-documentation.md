# Amazon Business Intelligence Platform API Documentation

## 概述

Amazon Business Intelligence Platform API 是專為 Amazon 賣家設計的全面性商業智慧 API，提供產品追蹤、競品分析和市場洞察功能。

## 🚀 快速開始

### 前置需求

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 14+
- Redis 6+

### 安裝與啟動

```bash
# 克隆專案
git clone <repository-url>
cd amazon-insights-platform

# 使用 Docker Compose 啟動
docker-compose up -d

# 檢查服務狀態
curl http://localhost:8000/api/v1/health/
```

### API 基本信息

- **Base URL**: `http://localhost:8000/api/v1`
- **文件**: `http://localhost:8000/api/v1/docs`
- **Authentication**: JWT Bearer Token
- **Content-Type**: `application/json`

## 🔐 認證

### 註冊用戶

```bash
POST /api/v1/auth/register
```

**請求體**:
```json
{
  "username": "your_username",
  "email": "user@example.com", 
  "password": "secure_password123"
}
```

**響應**:
```json
{
  "id": 1,
  "username": "your_username",
  "email": "user@example.com",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

### 登入取得 Token

```bash
POST /api/v1/auth/token
Content-Type: application/x-www-form-urlencoded

username=your_username&password=secure_password123
```

**響應**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 使用 Token

在所有需要認證的請求中加入 Header:
```bash
Authorization: Bearer <your_access_token>
```

## 📦 產品管理 API

### 新增產品追蹤

```bash
POST /api/v1/products/
Authorization: Bearer <token>
```

**請求體**:
```json
{
  "asin": "B08N5WRWNW",
  "title": "Echo Dot (4th Gen)",
  "brand": "Amazon",
  "category": "Electronics",
  "description": "Smart speaker with Alexa"
}
```

### 取得產品清單

```bash
GET /api/v1/products/
Authorization: Bearer <token>
```

**響應**:
```json
[
  {
    "id": 1,
    "asin": "B08N5WRWNW",
    "title": "Echo Dot (4th Gen)",
    "current_price": 49.99,
    "current_bsr": 12345,
    "current_rating": 4.5,
    "current_review_count": 25000,
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

### 更新產品資料

```bash
POST /api/v1/products/{product_id}/update-metrics
Authorization: Bearer <token>
```

### 設定價格警報

```bash
POST /api/v1/products/{product_id}/alerts
Authorization: Bearer <token>
```

**請求體**:
```json
{
  "alert_type": "price_change",
  "threshold_value": 10.0,
  "threshold_type": "percentage",
  "is_active": true
}
```

## 🔍 競品分析 API

### 發現競品

```bash
POST /api/v1/competitors/discover
Authorization: Bearer <token>
```

**請求體**:
```json
{
  "product_id": 1,
  "max_competitors": 5
}
```

**響應**:
```json
[
  {
    "id": 1,
    "competitor_asin": "B09B8V1LZ3",
    "title": "Competitor Echo Dot",
    "current_price": 45.99,
    "similarity_score": 0.85,
    "is_direct_competitor": 1
  }
]
```

### 競品分析

```bash
POST /api/v1/competitors/{competitor_id}/analyze
Authorization: Bearer <token>
```

**響應**:
```json
{
  "price_comparison": {
    "main_price": 49.99,
    "competitor_price": 45.99,
    "difference": 4.0,
    "price_position": "premium"
  },
  "performance_comparison": {
    "bsr_difference": -1000,
    "rating_difference": 0.1,
    "performance_score": 75.0
  },
  "market_position": "competitive",
  "recommendations": [
    {
      "type": "pricing",
      "action": "Consider price reduction",
      "priority": "high"
    }
  ]
}
```

### 競爭摘要

```bash
GET /api/v1/competitors/product/{product_id}/competitive-summary
Authorization: Bearer <token>
```

**響應**:
```json
{
  "total_competitors": 5,
  "direct_competitors": 3,
  "price_position": "competitive",
  "competitive_strength": "moderate",
  "average_competitor_price": 47.50,
  "recommendations": [
    "Monitor competitor pricing closely",
    "Focus on product differentiation"
  ]
}
```

### AI 競品情報報告

```bash
POST /api/v1/competitors/product/{product_id}/intelligence-report
Authorization: Bearer <token>
```

**響應**:
```json
{
  "product_id": 1,
  "analyzed_at": "2024-01-01T12:00:00Z",
  "ai_competitive_intelligence": {
    "market_position_analysis": "Your product is positioned as a premium option...",
    "competitive_advantages": [
      "Higher customer satisfaction rating",
      "Better brand recognition"
    ],
    "strategic_recommendations": [
      "Focus on premium positioning",
      "Emphasize quality in marketing"
    ],
    "threat_assessment": [
      "Price-competitive alternatives",
      "New market entrants"
    ]
  },
  "intelligence_summary": {
    "market_position": "Premium leader in smart speaker category",
    "key_advantages": ["Quality", "Brand", "Features"],
    "priority_actions": ["Maintain quality", "Monitor pricing"]
  }
}
```

### 市場概覽

```bash
GET /api/v1/competitors/insights/market-overview
Authorization: Bearer <token>
```

## 📊 監控與管理

### 系統健康檢查

```bash
GET /api/v1/health/
```

**響應**:
```json
{
  "status": "healthy",
  "service": "Amazon Insights Platform",
  "version": "0.1.0",
  "database": "connected",
  "redis": "connected"
}
```

### 快取統計

```bash
GET /api/v1/competitors/cache/stats
Authorization: Bearer <token>
```

**響應**:
```json
{
  "cache_statistics": {
    "active_keys": {
      "competitor_data": 25,
      "analysis_reports": 12,
      "intelligence_reports": 5
    },
    "memory_usage": "15.2MB"
  }
}
```

### 清除快取

```bash
DELETE /api/v1/competitors/cache/product/{product_id}
Authorization: Bearer <token>
```

## 🔄 背景任務

### Celery 任務

系統包含以下背景任務：

- **產品更新**: 每小時更新產品指標
- **競品發現**: 每日發現新競品
- **指標更新**: 每 6 小時更新競品指標  
- **報告生成**: 按需生成競品報告

### Flower 監控

- **URL**: `http://localhost:5555`
- **功能**: 監控 Celery 任務狀態
- **指標**: 任務成功率、執行時間、錯誤統計

## 📝 資料模型

### 產品模型

```json
{
  "id": "integer",
  "asin": "string(10)",
  "title": "string",
  "brand": "string",
  "category": "string", 
  "current_price": "float",
  "current_bsr": "integer",
  "current_rating": "float",
  "current_review_count": "integer",
  "is_active": "boolean",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### 競品模型

```json
{
  "id": "integer",
  "main_product_id": "integer",
  "competitor_asin": "string(10)",
  "title": "string",
  "similarity_score": "float(0-1)",
  "is_direct_competitor": "integer(1-2)",
  "current_price": "float",
  "current_bsr": "integer", 
  "current_rating": "float",
  "created_at": "datetime"
}
```

## ⚠️ 錯誤處理

### 常見錯誤碼

- **400 Bad Request**: 請求參數錯誤
- **401 Unauthorized**: 認證失敗或 token 無效
- **403 Forbidden**: 沒有權限存取資源
- **404 Not Found**: 資源不存在
- **422 Unprocessable Entity**: 資料驗證失敗
- **429 Too Many Requests**: 超過速率限制
- **500 Internal Server Error**: 服務器內部錯誤

### 錯誤響應格式

```json
{
  "detail": "Error description",
  "error_code": "SPECIFIC_ERROR_CODE",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## 🔧 配置參數

### 環境變數

```env
# 基本配置
APP_NAME=Amazon Insights Platform
APP_VERSION=0.1.0
ENVIRONMENT=development

# 資料庫
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/db
REDIS_URL=redis://localhost:6379/0

# API Keys
OPENAI_API_KEY=your_openai_key
FIRECRAWL_API_KEY=your_firecrawl_key

# JWT 設定
SECRET_KEY=your_secret_key
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# 功能開關
PROMETHEUS_ENABLED=true
LOG_FORMAT=json
```

## 🚦 速率限制

### 限制規則

| 端點類型 | 限制 | 時間窗口 |
|---------|------|----------|
| 認證相關 | 5 次 | 1 分鐘 |
| 一般 API | 100 次 | 1 分鐘 |
| 資料密集 | 20 次 | 1 分鐘 |
| AI 分析 | 10 次 | 1 分鐘 |

### 響應 Headers

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## 📈 監控指標

### Prometheus 指標

可在 `/metrics` 端點取得：

- `http_requests_total`: HTTP 請求總數
- `http_request_duration_seconds`: 請求處理時間
- `database_connections_active`: 活躍資料庫連接
- `redis_operations_total`: Redis 操作總數
- `celery_tasks_total`: Celery 任務統計

## 🔍 除錯和日誌

### 日誌格式

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "logger": "src.app.api.endpoints.products",
  "event": "product_created",
  "user_id": 1,
  "product_id": 5,
  "asin": "B08N5WRWNW"
}
```

### 日誌級別

- **DEBUG**: 詳細的除錯信息
- **INFO**: 一般操作信息
- **WARNING**: 警告信息
- **ERROR**: 錯誤信息
- **CRITICAL**: 嚴重錯誤

## 📞 支援與聯繫

- **文件**: 查看 `/docs` 取得互動式 API 文件
- **問題回報**: 提交 GitHub Issues
- **Email**: support@amazon-insights.com

## 📜 版本歷史

### v0.1.0 (目前版本)
- ✅ 產品追蹤功能
- ✅ 競品分析引擎
- ✅ AI 洞察報告
- ✅ 快取系統
- ✅ 背景任務
- ✅ API 文件

### 未來版本計劃
- 🔄 實時數據同步
- 📊 高級分析儀表板
- 🔔 多渠道通知系統
- 📱 移動端 API 優化