# 系統架構總覽

## 整體系統架構圖

```mermaid
graph 
TB
subgraph "前端層"
FE[React Dashboard]
MOBILE[Mobile App]
endsubgraph "API層"
    GW[API Gateway<br/>認證 + 限流]
    LB[Load Balancer]
endsubgraph "業務服務層"
    TRACK[產品追蹤服務<br/>選項1]
    COMPETE[競品分析服務<br/>選項2] 
    OPT[優化建議服務<br/>選項3]
    USER[用戶管理服務]
    ALERT[警報服務]
endsubgraph "數據處理層"
    CRAWLER[數據採集服務<br/>封裝 Firecrawl API]
    AI[AI分析服務<br/>封裝 OpenAI API]
    PROC[數據處理服務]
endsubgraph "基礎設施層"
    CACHE[(Redis<br/>快取層)]
    QUEUE[任務佇列<br/>Celery + Redis]
    DB[(PostgreSQL<br/>主資料庫)]
    TS[(時間序列存儲)]
endsubgraph "外部服務"
    OPENAI[OpenAI APIs]
    FIRE[Firecrawl APIs]
end%% 連接關係
FE --> LB
MOBILE --> LB
LB --> GW
GW --> TRACK
GW --> COMPETE
GW --> OPT
GW --> USERTRACK --> CACHE
COMPETE --> CACHE
OPT --> CACHETRACK --> DB
COMPETE --> DB
OPT --> DB
USER --> DBCRAWLER --> QUEUE
AI --> QUEUE
PROC --> QUEUEQUEUE --> TRACK
QUEUE --> COMPETE
QUEUE --> OPT
QUEUE --> ALERTCRAWLER --> FIRE
AI --> OPENAIPROC --> TS
ALERT --> USERclassDef frontend fill:#e1f5fe
classDef api fill:#f3e5f5
classDef business fill:#e8f5e8
classDef data fill:#fff3e0
classDef infra fill:#fce4ec
classDef external fill:#f5f5f5class FE,MOBILE frontend
class GW,LB api
class TRACK,COMPETE,OPT,USER,ALERT business
class CRAWLER,AI,PROC data
class CACHE,QUEUE,DB,TS infra
class OPENAI,FIRE external
```

## 核心組件關係

| 組件類型 | 組件名稱 | 職責 | 依賴關係 |
|---------|----------|------|----------|
| **核心業務組件** | 產品追蹤服務 | 產品表現監控與分析 | 數據採集服務、警報服務 |
| | 競品分析服務 | 競爭情報收集與分析 | 數據採集服務、AI分析服務 |
| | 優化建議服務 | AI驅動的優化建議 | AI分析服務、數據處理服務 |
| **共享服務** | 數據採集服務 | 封裝 Firecrawl API | Firecrawl API、任務佇列 |
| | AI分析服務 | 封裝 OpenAI API | OpenAI API、任務佇列 |
| | 數據處理服務 | 數據清理與標準化 | PostgreSQL、Redis |
| **基礎組件** | Redis快取 | 高性能快取層 | - |
| | PostgreSQL | 主要資料庫 | - |
| | Celery任務佇列 | 背景任務處理 | Redis |

## 技術選型決策

| 組件 | 選擇 | 理由 |
|------|------|------|
| **Web框架** | FastAPI | 高性能、自動API文檔、異步支持 |
| **資料庫** | PostgreSQL | 關聯式數據、JSON支持、時間序列優化 |
| **快取** | Redis | 高性能、支持複雜數據結構 |
| **任務佇列** | Celery + Redis | 成熟穩定、支持定時任務 |
| **數據採集** | Firecrawl API | 專業反爬、維護成本低 |
| **AI服務** | OpenAI API | 成熟LLM、結構化輸出 |

## 架構特點

- **讀寫分離**: 查詢走快取，批次寫入資料庫
- **異步處理**: 數據採集和AI分析使用背景任務
- **分層快取**: 不同TTL策略降低外部API成本
- **模組化設計**: 3個核心功能可獨立擴展
- **API優先**: 使用專業API服務降低技術複雜度

## 性能策略

- **快取優先**: 90%查詢走Redis快取
- **批次處理**: 數據採集批次入庫
- **智能調度**: 錯峰執行重型任務
- **預計算**: 熱門分析結果預先計算

