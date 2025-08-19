```markdown
# 部署架構設計

## Kubernetes 部署架構

### 服務部署配置

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: amazon-insights

---
# API Gateway Service
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
  namespace: amazon-insights
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api-gateway
  template:
    metadata:
      labels:
        app: api-gateway
    spec:
      containers:
      - name: api-gateway
        image: amazon-insights/api-gateway:latest
        ports:
        - containerPort: 8000
        env:
        - name: REDIS_URL
          value: "redis://redis-cluster:6379"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: database-url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
水平擴展策略
yaml# Horizontal Pod Autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-gateway-hpa
  namespace: amazon-insights
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-gateway
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
服務發現與負載均衡
yaml# Service Discovery
apiVersion: v1
kind: Service
metadata:
  name: product-service
  namespace: amazon-insights
spec:
  selector:
    app: product-service
  ports:
  - port: 8001
    targetPort: 8001
  type: ClusterIP

---
# Load Balancer for external access
apiVersion: v1
kind: Service
metadata:
  name: api-gateway-lb
  namespace: amazon-insights
spec:
  selector:
    app: api-gateway
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
災難恢復架構
多可用區部署
Primary Region (us-east-1)
├── AZ-1a: Master DB + API Servers
├── AZ-1b: Slave DB + API Servers  
└── AZ-1c: Cache + Queue Servers

Secondary Region (us-west-2)
├── AZ-2a: DR Database
├── AZ-2b: Standby Services
└── AZ-2c: Backup Storage
備份策略

資料庫: 每日全量備份 + 實時 WAL 歸檔
Redis: 每小時 RDB 快照 + AOF 持久化
應用程式: 容器映像版本控制 + 配置備份
檔案: S3 跨區域複製 + 版本控制

恢復時間目標 (RTO/RPO)

RTO: < 4 小時 (系統完全恢復)
RPO: < 1 小時 (數據丟失容忍度)
自動故障轉移: < 5 分鐘 (服務層級)
資料庫故障轉移: < 30 分鐘 (含數據驗證)

水平擴展策略
系統組件當前容量擴展閾值擴展方式目標容量Web服務3 QPSCPU > 70%增加實例10 QPS背景任務1000產品/小時佇列長度 > 500Worker擴展5000產品/小時資料庫500GB存儲 > 80%分庫分表2TB快取層8GB記憶體 > 80%Redis集群32GB
業務成長應對
成長指標觸發條件應對策略用戶數成長1000 → 5000用戶API Gateway限流 + CDN產品數成長1000 → 10000產品分區策略 + 並行數據採集請求量成長30K → 150K requests/日微服務拆分 + 負載均衡