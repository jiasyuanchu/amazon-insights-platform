# Amazon Insights Platform - 故障排除指南

## 🚨 常見問題診斷

### 1. 容器無法啟動

#### 問題：Docker 容器啟動失敗

**診斷步驟**：
```bash
# 檢查所有容器狀態
docker-compose ps

# 查看特定服務日誌
docker-compose logs -f api
docker-compose logs -f postgres
docker-compose logs -f redis

# 檢查容器資源使用
docker stats
```

**常見原因與解決方案**：

| 錯誤訊息 | 原因 | 解決方案 |
|---------|------|----------|
| `port already in use` | 端口衝突 | `docker-compose down` 然後重新啟動 |
| `connection refused` | 服務未就緒 | 等待依賴服務完全啟動 |
| `out of memory` | 記憶體不足 | 增加 Docker 記憶體限制或系統記憶體 |
| `permission denied` | 權限問題 | 檢查文件權限和 Docker 用戶組 |

#### 問題：API 服務無法連接資料庫

**診斷命令**：
```bash
# 測試資料庫連接
docker exec amazon_insights_postgres pg_isready -U postgres

# 檢查資料庫是否可以登入
docker exec -it amazon_insights_postgres psql -U postgres -d amazon_insights

# 查看資料庫日誌
docker-compose logs postgres | tail -50
```

**解決步驟**：
1. 確認 `DATABASE_URL` 環境變數正確
2. 檢查資料庫用戶權限
3. 驗證網路連接

### 2. 性能問題

#### 問題：API 響應緩慢

**診斷工具**：
```bash
# 檢查 API 響應時間
curl -w "@curl-format.txt" -o /dev/null -s "http://localhost:8000/api/v1/health/"

# 監控容器資源使用
docker stats --no-stream

# 檢查資料庫連接池
docker exec amazon_insights_postgres psql -U postgres -c "SELECT * FROM pg_stat_activity;"
```

**curl-format.txt**：
```
     time_namelookup:  %{time_namelookup}\n
        time_connect:  %{time_connect}\n
     time_appconnect:  %{time_appconnect}\n
    time_pretransfer:  %{time_pretransfer}\n
       time_redirect:  %{time_redirect}\n
  time_starttransfer:  %{time_starttransfer}\n
                     ----------\n
          time_total:  %{time_total}\n
```

**優化建議**：
- 增加 API workers 數量
- 調整資料庫連接池設定
- 檢查慢查詢日誌
- 啟用 Redis 快取

#### 問題：記憶體使用過高

**診斷步驟**：
```bash
# 檢查系統記憶體
free -h

# 檢查容器記憶體使用
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"

# 檢查 Python 記憶體泄露
docker exec amazon_insights_api python -c "
import gc
import sys
print('Objects in memory:', len(gc.get_objects()))
print('Memory usage:', sys.getsizeof(gc.get_objects()))
"
```

### 3. 資料庫問題

#### 問題：資料庫連接用盡

**診斷查詢**：
```sql
-- 查看當前連接
SELECT 
    pid,
    usename,
    application_name,
    client_addr,
    state,
    query_start,
    query
FROM pg_stat_activity 
WHERE state = 'active';

-- 查看連接統計
SELECT 
    count(*) as total_connections,
    count(*) FILTER (WHERE state = 'active') as active_connections,
    count(*) FILTER (WHERE state = 'idle') as idle_connections
FROM pg_stat_activity;
```

**解決方案**：
```bash
# 重啟資料庫服務
docker-compose restart postgres

# 調整 postgresql.conf
# max_connections = 200
# shared_buffers = 256MB
```

#### 問題：資料庫遷移失敗

**診斷步驟**：
```bash
# 檢查 Alembic 版本
docker exec amazon_insights_api alembic current

# 查看遷移歷史
docker exec amazon_insights_api alembic history

# 手動運行遷移
docker exec amazon_insights_api alembic upgrade head
```

### 4. Redis 快取問題

#### 問題：Redis 連接失敗

**診斷命令**：
```bash
# 測試 Redis 連接
docker exec amazon_insights_redis redis-cli ping

# 檢查 Redis 記憶體使用
docker exec amazon_insights_redis redis-cli info memory

# 查看 Redis 日誌
docker-compose logs redis | tail -20
```

**解決步驟**：
1. 檢查 `REDIS_URL` 環境變數
2. 驗證 Redis 服務狀態
3. 清除損壞的 Redis 資料

#### 問題：快取命中率低

**診斷查詢**：
```bash
# 檢查快取統計
docker exec amazon_insights_redis redis-cli info stats

# 查看快取鍵
docker exec amazon_insights_redis redis-cli keys "*" | head -10

# 檢查快取大小
docker exec amazon_insights_redis redis-cli dbsize
```

### 5. Celery 任務問題

#### 問題：Celery Worker 無法啟動

**診斷步驟**：
```bash
# 檢查 Celery worker 狀態
docker-compose logs celery

# 檢查 Celery 配置
docker exec amazon_insights_celery celery -A src.app.tasks.celery_app inspect active

# 查看任務隊列
docker exec amazon_insights_celery celery -A src.app.tasks.celery_app inspect reserved
```

#### 問題：任務執行失敗

**故障排除**：
```bash
# 查看失敗任務詳情
docker exec amazon_insights_celery celery -A src.app.tasks.celery_app events

# 檢查 Flower 監控
# 瀏覽 http://localhost:5555

# 清空任務隊列
docker exec amazon_insights_redis redis-cli FLUSHALL
```

### 6. 認證問題

#### 問題：JWT Token 驗證失敗

**診斷步驟**：
```bash
# 檢查 JWT 配置
echo $SECRET_KEY
echo $ACCESS_TOKEN_EXPIRE_MINUTES

# 測試 Token 生成
curl -X POST "http://localhost:8000/api/v1/auth/token" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=testuser&password=testpass"

# 驗證 Token
TOKEN="your_token_here"
curl -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/v1/users/me"
```

#### 問題：用戶無法註冊或登入

**檢查項目**：
1. 密碼雜湊算法設定
2. 資料庫用戶表結構
3. 環境變數配置

```bash
# 檢查用戶表
docker exec amazon_insights_postgres psql -U postgres -d amazon_insights \
  -c "SELECT id, username, email, is_active FROM users LIMIT 5;"
```

### 7. 外部 API 整合問題

#### 問題：OpenAI API 調用失敗

**診斷步驟**：
```bash
# 檢查 API Key
echo $OPENAI_API_KEY

# 測試 API 連接
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     "https://api.openai.com/v1/models"

# 檢查 API 使用量
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     "https://api.openai.com/v1/usage"
```

#### 問題：Firecrawl API 整合問題

**故障排除**：
```bash
# 驗證 Firecrawl API Key
echo $FIRECRAWL_API_KEY

# 測試簡單抓取
curl -X POST "https://api.firecrawl.dev/v0/scrape" \
     -H "Authorization: Bearer $FIRECRAWL_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://example.com"}'
```

### 8. 網路和連接問題

#### 問題：服務間無法通信

**診斷網路**：
```bash
# 檢查 Docker 網路
docker network ls
docker network inspect amazon-insights-platform_default

# 測試容器間連接
docker exec amazon_insights_api ping postgres
docker exec amazon_insights_api ping redis

# 檢查端口監聽
docker exec amazon_insights_api netstat -tlnp
```

#### 問題：外部無法訪問服務

**檢查防火牆**：
```bash
# Ubuntu/Debian
sudo ufw status

# CentOS/RHEL
sudo firewall-cmd --list-all

# 檢查端口監聽
sudo netstat -tlnp | grep :8000
```

### 9. SSL/TLS 問題

#### 問題：SSL 憑證問題

**診斷步驟**：
```bash
# 檢查憑證有效性
openssl x509 -in /path/to/certificate.crt -text -noout

# 驗證憑證鏈
openssl verify -CAfile ca.crt certificate.crt

# 測試 SSL 連接
openssl s_client -connect your-domain.com:443
```

### 10. 日誌分析

#### 集中式日誌檢查

**API 日誌**：
```bash
# 查看 API 錯誤日誌
docker-compose logs api | grep -i error

# 查看特定時間範圍的日誌
docker-compose logs --since="2024-01-01T00:00:00" api

# 查看實時日誌
docker-compose logs -f api
```

**系統日誌**：
```bash
# 系統資源日誌
dmesg | tail -20

# 檢查磁碟空間
df -h

# 檢查 inode 使用
df -i
```

## 🛠️ 常用修復腳本

### 完全重置環境

```bash
#!/bin/bash
# reset_environment.sh

echo "Stopping all services..."
docker-compose down -v

echo "Removing all containers and images..."
docker system prune -af
docker volume prune -f

echo "Rebuilding and starting services..."
docker-compose build --no-cache
docker-compose up -d

echo "Waiting for services to be ready..."
sleep 30

echo "Running database migrations..."
docker exec amazon_insights_api alembic upgrade head

echo "Environment reset complete!"
```

### 健康檢查腳本

```bash
#!/bin/bash
# health_check.sh

API_URL="http://localhost:8000/api/v1/health/"
FLOWER_URL="http://localhost:5555"
PROMETHEUS_URL="http://localhost:9090"

echo "=== Amazon Insights Platform Health Check ==="

# API 健康檢查
echo -n "API Health: "
if curl -f -s $API_URL > /dev/null; then
    echo "✅ OK"
else
    echo "❌ FAILED"
fi

# 資料庫連接檢查
echo -n "Database: "
if docker exec amazon_insights_postgres pg_isready -U postgres > /dev/null 2>&1; then
    echo "✅ OK"
else
    echo "❌ FAILED"
fi

# Redis 檢查
echo -n "Redis: "
if docker exec amazon_insights_redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ OK"
else
    echo "❌ FAILED"
fi

# Celery 檢查
echo -n "Celery Worker: "
if docker-compose ps celery | grep -q "Up"; then
    echo "✅ OK"
else
    echo "❌ FAILED"
fi

# Flower 檢查
echo -n "Flower Monitoring: "
if curl -f -s $FLOWER_URL > /dev/null; then
    echo "✅ OK"
else
    echo "❌ FAILED"
fi

echo "=== Health Check Complete ==="
```

### 備份腳本

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/opt/backups/amazon-insights"
DATE=$(date +"%Y%m%d_%H%M%S")

mkdir -p $BACKUP_DIR

# 資料庫備份
echo "Backing up database..."
docker exec amazon_insights_postgres pg_dump -U postgres amazon_insights > \
  $BACKUP_DIR/postgres_$DATE.sql

# Redis 備份
echo "Backing up Redis..."
docker exec amazon_insights_redis redis-cli SAVE
docker cp amazon_insights_redis:/data/dump.rdb $BACKUP_DIR/redis_$DATE.rdb

# 配置文件備份
echo "Backing up configuration..."
tar -czf $BACKUP_DIR/config_$DATE.tar.gz .env docker-compose*.yml nginx/

# 壓縮所有備份
echo "Compressing backups..."
tar -czf $BACKUP_DIR/full_backup_$DATE.tar.gz $BACKUP_DIR/*_$DATE.*

# 清理舊備份
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR/full_backup_$DATE.tar.gz"
```

## 📞 獲取幫助

### 日誌收集

當需要技術支援時，請收集以下資訊：

```bash
# 系統資訊收集腳本
#!/bin/bash
# collect_logs.sh

LOG_DIR="support_logs_$(date +%Y%m%d_%H%M%S)"
mkdir -p $LOG_DIR

echo "Collecting system information..."
docker --version > $LOG_DIR/docker_version.txt
docker-compose --version > $LOG_DIR/compose_version.txt
cat /etc/os-release > $LOG_DIR/os_info.txt

echo "Collecting service logs..."
docker-compose logs --no-color > $LOG_DIR/all_services.log
docker-compose ps > $LOG_DIR/container_status.txt

echo "Collecting system stats..."
docker stats --no-stream > $LOG_DIR/container_stats.txt
df -h > $LOG_DIR/disk_usage.txt
free -h > $LOG_DIR/memory_usage.txt

echo "Collecting configuration..."
cp .env $LOG_DIR/env_config.txt
cp docker-compose.yml $LOG_DIR/

tar -czf support_logs.tar.gz $LOG_DIR/
rm -rf $LOG_DIR

echo "Support logs collected: support_logs.tar.gz"
```

### 聯繫資訊

- **GitHub Issues**: 提交詳細的錯誤報告
- **Email**: support@amazon-insights.com
- **文件**: 查看線上文件和 FAQ
- **社區**: 加入討論群組獲取幫助

### 錯誤報告範本

```
## 問題描述
[詳細描述問題]

## 環境資訊
- OS: [作業系統版本]
- Docker: [Docker 版本]
- Docker Compose: [Compose 版本]

## 復現步驟
1. [步驟一]
2. [步驟二]
3. [步驟三]

## 期望結果
[描述期望的行為]

## 實際結果
[描述實際發生的情況]

## 錯誤日誌
[貼上相關的錯誤日誌]

## 其他資訊
[任何其他相關資訊]
```