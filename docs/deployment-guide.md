# Amazon Insights Platform - 部署指南

## 🚀 快速部署

### 開發環境部署

**前置需求**:
- Docker 20.10+
- Docker Compose 2.0+
- Git

**部署步驟**:

```bash
# 1. 克隆專案
git clone <repository-url>
cd amazon-insights-platform

# 2. 複製環境配置
cp .env.example .env

# 3. 編輯環境變數 (重要!)
nano .env

# 4. 啟動所有服務
docker-compose up -d

# 5. 檢查服務狀態
docker-compose ps

# 6. 查看日誌
docker-compose logs -f api

# 7. 驗證部署
curl http://localhost:8000/api/v1/health/
```

### 生產環境部署

**前置需求**:
- Ubuntu 20.04+ / CentOS 8+
- Docker 20.10+
- Docker Compose 2.0+
- SSL 憑證 (可選)
- 至少 4GB RAM, 20GB 硬碟空間

**部署步驟**:

```bash
# 1. 系統準備
sudo apt update
sudo apt install -y docker.io docker-compose-v2 nginx certbot

# 2. 創建部署目錄
sudo mkdir -p /opt/amazon-insights
cd /opt/amazon-insights

# 3. 下載專案
sudo git clone <repository-url> .
sudo chown -R $USER:$USER .

# 4. 配置環境
cp docker-compose.prod.yml docker-compose.yml
cp .env.prod .env

# 5. 編輯生產配置
nano .env

# 6. 啟動服務
docker-compose up -d

# 7. 配置 Nginx 反向代理
sudo cp nginx/amazon-insights.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/amazon-insights.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# 8. 設定 SSL (可選)
sudo certbot --nginx -d your-domain.com
```

## 🔧 環境配置

### 開發環境 (.env)

```env
# 應用程式設定
APP_NAME=Amazon Insights Platform
APP_VERSION=0.1.0
ENVIRONMENT=development
DEBUG=true

# API 設定
API_V1_STR=/api/v1
SECRET_KEY=dev-secret-key-change-in-production

# 資料庫配置
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/amazon_insights

# Redis 配置
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# 外部 API 金鑰 (可選)
OPENAI_API_KEY=your-openai-api-key
FIRECRAWL_API_KEY=your-firecrawl-api-key

# JWT 設定
ACCESS_TOKEN_EXPIRE_MINUTES=1440
ALGORITHM=HS256

# CORS 設定
BACKEND_CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]

# 功能開關
PROMETHEUS_ENABLED=true
LOG_FORMAT=json

# Celery 設定
CELERY_TASK_ROUTES={"src.app.tasks.*": {"queue": "default"}}
CELERY_BEAT_SCHEDULE_ENABLED=true
```

### 生產環境 (.env.prod)

```env
# 應用程式設定
APP_NAME=Amazon Insights Platform
APP_VERSION=0.1.0
ENVIRONMENT=production
DEBUG=false

# API 設定
API_V1_STR=/api/v1
SECRET_KEY=your-super-secure-secret-key-here

# 資料庫配置 (使用外部資料庫)
DATABASE_URL=postgresql+asyncpg://user:password@your-db-host:5432/amazon_insights

# Redis 配置 (使用外部 Redis)
REDIS_URL=redis://your-redis-host:6379/0
CELERY_BROKER_URL=redis://your-redis-host:6379/1
CELERY_RESULT_BACKEND=redis://your-redis-host:6379/2

# 外部 API 金鑰
OPENAI_API_KEY=your-production-openai-key
FIRECRAWL_API_KEY=your-production-firecrawl-key

# JWT 設定
ACCESS_TOKEN_EXPIRE_MINUTES=480
ALGORITHM=HS256

# CORS 設定
BACKEND_CORS_ORIGINS=["https://your-frontend-domain.com"]

# 安全設定
HTTPS_ONLY=true
SECURE_COOKIES=true

# 效能設定
WORKERS=4
MAX_CONNECTIONS=100
KEEPALIVE_TIMEOUT=65

# 監控設定
PROMETHEUS_ENABLED=true
LOG_FORMAT=json
LOG_LEVEL=INFO

# 快取設定
CACHE_TTL=3600
REDIS_MAX_CONNECTIONS=50
```

## 🐳 Docker 配置

### 生產環境 Docker Compose

創建 `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile.prod
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - FIRECRAWL_API_KEY=${FIRECRAWL_API_KEY}
    depends_on:
      - redis
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health/"]
      interval: 30s
      timeout: 10s
      retries: 3

  celery:
    build:
      context: .
      dockerfile: Dockerfile.prod
    command: celery -A src.app.tasks.celery_app worker -l info
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}
      - CELERY_BROKER_URL=${CELERY_BROKER_URL}
      - CELERY_RESULT_BACKEND=${CELERY_RESULT_BACKEND}
    depends_on:
      - redis
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'

  celery-beat:
    build:
      context: .
      dockerfile: Dockerfile.prod
    command: celery -A src.app.tasks.celery_app beat -l info
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - CELERY_BROKER_URL=${CELERY_BROKER_URL}
    depends_on:
      - redis
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped

  flower:
    build:
      context: .
      dockerfile: Dockerfile.prod
    command: celery -A src.app.tasks.celery_app flower
    ports:
      - "5555:5555"
    environment:
      - CELERY_BROKER_URL=${CELERY_BROKER_URL}
      - CELERY_RESULT_BACKEND=${CELERY_RESULT_BACKEND}
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
      - ./redis/redis.conf:/usr/local/etc/redis/redis.conf
    command: redis-server /usr/local/etc/redis/redis.conf
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 512M

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/amazon-insights.conf:/etc/nginx/conf.d/default.conf
      - ./ssl:/etc/ssl/certs
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - api
    restart: unless-stopped

volumes:
  redis_data:
  logs:
```

### 生產環境 Dockerfile

創建 `Dockerfile.prod`:

```dockerfile
FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 複製需求檔案
COPY requirements.txt .

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式代碼
COPY . .

# 創建非 root 使用者
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# 設定環境變數
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/v1/health/ || exit 1

# 暴露端口
EXPOSE 8000

# 啟動命令
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

## 🌐 Nginx 配置

### 基本配置 (nginx/amazon-insights.conf)

```nginx
upstream app_server {
    server api:8000;
}

upstream flower_server {
    server flower:5555;
}

# HTTP to HTTPS redirect
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    # SSL Configuration
    ssl_certificate /etc/ssl/certs/your-domain.crt;
    ssl_certificate_key /etc/ssl/certs/your-domain.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 10240;
    gzip_proxied expired no-cache no-store private must-revalidate auth;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/json;

    # Main API
    location /api/ {
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_pass http://app_server;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Body size limit
        client_max_body_size 10M;
    }

    # Flower monitoring (protected)
    location /flower/ {
        auth_basic "Flower Monitoring";
        auth_basic_user_file /etc/nginx/htpasswd;
        proxy_pass http://flower_server/;
        proxy_set_header Host $host;
        proxy_redirect off;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Metrics endpoint (protected)
    location /metrics {
        auth_basic "Metrics";
        auth_basic_user_file /etc/nginx/htpasswd;
        proxy_pass http://app_server;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files (如果有的話)
    location /static/ {
        alias /app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Health check
    location /health {
        access_log off;
        proxy_pass http://app_server/api/v1/health/;
    }

    # Logs
    access_log /var/log/nginx/amazon-insights.access.log;
    error_log /var/log/nginx/amazon-insights.error.log;
}
```

## 🔐 安全配置

### 1. 創建受保護的監控密碼

```bash
# 創建 htpasswd 檔案保護 Flower 和 Metrics
sudo htpasswd -c /etc/nginx/htpasswd admin
```

### 2. 防火牆設定

```bash
# Ubuntu UFW
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw --force enable

# CentOS/RHEL firewalld
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### 3. SSL 憑證設定

```bash
# 使用 Let's Encrypt
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# 設定自動續約
sudo crontab -e
# 添加: 0 12 * * * /usr/bin/certbot renew --quiet
```

## 📊 監控設定

### 1. 系統監控 (Prometheus + Grafana)

添加到 `docker-compose.prod.yml`:

```yaml
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources

volumes:
  prometheus_data:
  grafana_data:
```

### 2. 日誌監控

創建 `monitoring/filebeat.yml`:

```yaml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /app/logs/*.log
  json.keys_under_root: true
  json.add_error_key: true

output.elasticsearch:
  hosts: ["your-elasticsearch-host:9200"]
  index: "amazon-insights-%{+yyyy.MM.dd}"

logging.level: info
logging.to_files: true
logging.files:
  path: /var/log/filebeat
  name: filebeat
  keepfiles: 7
  permissions: 0644
```

## 🚀 部署自動化

### GitHub Actions 部署

創建 `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Docker Buildx
      uses: docker/setup-buildx-action@v2
    
    - name: Login to Container Registry
      uses: docker/login-action@v2
      with:
        registry: ghcr.io
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Build and push Docker image
      uses: docker/build-push-action@v4
      with:
        context: .
        file: ./Dockerfile.prod
        push: true
        tags: ghcr.io/${{ github.repository }}:latest
    
    - name: Deploy to server
      uses: appleboy/ssh-action@v0.1.5
      with:
        host: ${{ secrets.HOST }}
        username: ${{ secrets.USERNAME }}
        key: ${{ secrets.SSH_KEY }}
        script: |
          cd /opt/amazon-insights
          docker-compose pull
          docker-compose up -d
          docker system prune -f
```

## 🔄 備份與恢復

### 資料庫備份

```bash
# 建立備份腳本
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/backups/amazon-insights"
DATE=$(date +"%Y%m%d_%H%M%S")

# 創建備份目錄
mkdir -p $BACKUP_DIR

# 資料庫備份
docker exec amazon_insights_postgres pg_dump -U postgres amazon_insights > \
  $BACKUP_DIR/postgres_$DATE.sql

# Redis 備份
docker exec amazon_insights_redis redis-cli SAVE
docker cp amazon_insights_redis:/data/dump.rdb $BACKUP_DIR/redis_$DATE.rdb

# 壓縮備份
tar -czf $BACKUP_DIR/backup_$DATE.tar.gz $BACKUP_DIR/*_$DATE.*

# 清理舊備份 (保留 7 天)
find $BACKUP_DIR -name "backup_*.tar.gz" -mtime +7 -delete

echo "Backup completed: backup_$DATE.tar.gz"
EOF

chmod +x backup.sh

# 設定每日自動備份
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/amazon-insights/backup.sh") | crontab -
```

### 資料恢復

```bash
# 恢復資料庫
docker exec -i amazon_insights_postgres psql -U postgres -d amazon_insights < backup.sql

# 恢復 Redis
docker cp redis_backup.rdb amazon_insights_redis:/data/dump.rdb
docker restart amazon_insights_redis
```

## 📋 部署檢查清單

### 部署前檢查

- [ ] 環境變數已正確設定
- [ ] SECRET_KEY 已更改為安全密鑰
- [ ] 資料庫連接字串已更新
- [ ] API 金鑰已配置
- [ ] SSL 憑證已準備
- [ ] 防火牆規則已設定
- [ ] 監控系統已配置

### 部署後檢查

- [ ] 所有服務都在運行 (`docker-compose ps`)
- [ ] API 健康檢查通過 (`curl /api/v1/health/`)
- [ ] Flower 監控可訪問
- [ ] Prometheus 指標可訪問
- [ ] 日誌正常輸出
- [ ] SSL 憑證有效
- [ ] 備份作業正常運行

## 🆘 故障排除

### 常見問題

1. **容器啟動失敗**
   ```bash
   docker-compose logs <service_name>
   docker-compose restart <service_name>
   ```

2. **資料庫連接問題**
   ```bash
   docker exec amazon_insights_postgres psql -U postgres -c "SELECT version();"
   ```

3. **Redis 連接問題**
   ```bash
   docker exec amazon_insights_redis redis-cli ping
   ```

4. **API 響應慢**
   - 檢查資料庫查詢性能
   - 調整 workers 數量
   - 檢查記憶體使用情況

5. **磁碟空間不足**
   ```bash
   docker system prune -a
   docker volume prune
   ```

聯繫支援: support@amazon-insights.com