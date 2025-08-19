# 安全配置指南

Amazon Insights Platform 的完整安全配置和最佳實踐指南。

## 🔐 安全功能概覽

### 已實施的安全措施

#### 1. 認證與授權
- **JWT Token 認證**: 使用 HS256 算法的 JWT token
- **密碼哈希**: 使用 bcrypt 進行密碼哈希
- **API Key 認證**: 支援 API key 進行程式化訪問
- **權限管理**: 基於角色的訪問控制

#### 2. 速率限制
- **多層速率限制**: 分鐘、小時、日限制
- **智能限制策略**: 不同端點採用不同限制
- **突發流量控制**: Token bucket 算法防止突發攻擊
- **Redis 支援**: 分佈式速率限制

#### 3. 輸入驗證與清理
- **XSS 防護**: 自動清理危險 HTML 標籤
- **SQL 注入防護**: 使用 ORM 和參數化查詢
- **輸入長度限制**: 防止過長輸入攻擊
- **ASIN 格式驗證**: 嚴格的 Amazon ASIN 格式檢查

#### 4. 安全標頭
- **X-Content-Type-Options**: nosniff
- **X-Frame-Options**: DENY
- **X-XSS-Protection**: 1; mode=block
- **Strict-Transport-Security**: HTTPS 強制
- **Content-Security-Policy**: 內容安全策略

#### 5. CSRF 保護
- **CSRF Token**: 狀態變更操作的 CSRF token 驗證
- **Same-Origin 檢查**: 來源驗證
- **安全例外**: API key 和安全端點例外

#### 6. 請求監控
- **結構化日誌**: 完整的請求審計追蹤
- **可疑活動檢測**: 自動檢測和記錄可疑行為
- **請求 ID 追蹤**: 每個請求的唯一標識符

## ⚙️ 配置選項

### 環境變數配置

```env
# 基本安全
SECRET_KEY=your-super-secure-secret-key-here  # 至少64字符
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# 速率限制
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# CORS 設定
BACKEND_CORS_ORIGINS=["http://localhost:3000","https://yourdomain.com"]

# 安全標頭
HTTPS_ONLY=true  # 生產環境
SECURE_COOKIES=true  # 生產環境

# 監控
SENTRY_DSN=your-sentry-dsn  # 錯誤追蹤
PROMETHEUS_ENABLED=true  # 指標監控
```

### 速率限制規則

```python
RATE_LIMIT_RULES = {
    "default": {
        "per_minute": 60,
        "per_hour": 1000,
        "per_day": 10000,
        "burst_limit": 10
    },
    "auth": {
        "per_minute": 5,
        "per_hour": 30,
        "per_day": 100,
        "burst_limit": 3
    },
    "api_heavy": {
        "per_minute": 20,
        "per_hour": 200,
        "per_day": 1000,
        "burst_limit": 5
    },
    "ai_analysis": {
        "per_minute": 10,
        "per_hour": 100,
        "per_day": 500,
        "burst_limit": 2
    }
}
```

## 🛡️ 部署安全檢查清單

### 生產部署前檢查

- [ ] **Secret Key**: 生成強密鑰 (64+ 字符)
- [ ] **環境變數**: 敏感資訊不在代碼中
- [ ] **HTTPS**: 強制使用 HTTPS
- [ ] **防火牆**: 只開放必要端口 (80, 443, 22)
- [ ] **資料庫**: 使用強密碼，限制網路訪問
- [ ] **Redis**: 啟用認證，限制網路訪問
- [ ] **日誌**: 啟用安全日誌和監控
- [ ] **備份**: 加密備份和災難恢復計劃

### 定期安全檢查

#### 每週檢查
- [ ] 檢查異常請求模式
- [ ] 審查錯誤日誌
- [ ] 監控速率限制觸發

#### 每月檢查
- [ ] 更新依賴套件
- [ ] 審查用戶權限
- [ ] 檢查 SSL 憑證有效期

#### 每季檢查
- [ ] 完整安全掃描
- [ ] 滲透測試
- [ ] 安全配置審查

## 🔧 安全工具使用

### 安全管理腳本

```bash
# 生成 API key
python scripts/security_tools.py api-key generate username

# 檢查速率限制狀態
python scripts/security_tools.py rate-limit check

# 清除特定用戶的速率限制
python scripts/security_tools.py rate-limit clear --identifier user:123

# 生成安全密鑰
python scripts/security_tools.py secret-key

# 測試 JWT token
python scripts/security_tools.py jwt-test username

# 安全審計
python scripts/security_tools.py audit
```

### API 端點管理

```bash
# 檢查速率限制狀態
GET /api/v1/rate-limits/status

# 查看速率限制規則
GET /api/v1/rate-limits/rules

# 重設速率限制 (管理員)
POST /api/v1/rate-limits/reset
```

## 🚨 安全事件回應

### 可疑活動指標

1. **異常請求模式**
   - 短時間內大量請求
   - 來自單一 IP 的過多失敗登入
   - 非標準 User-Agent 字符串

2. **攻擊嘗試**
   - SQL 注入嘗試
   - XSS 攻擊載荷
   - 路徑遍歷嘗試

3. **認證異常**
   - 多次無效 token 使用
   - 密碼暴力破解嘗試
   - 異常 API key 使用

### 回應流程

1. **自動回應**
   - 速率限制自動觸發
   - 可疑 IP 自動封鎖
   - 錯誤日誌自動記錄

2. **手動介入**
   - 分析日誌和模式
   - 調整安全規則
   - 通知相關人員

3. **事後檢討**
   - 事件原因分析
   - 安全措施改進
   - 預防措施實施

## 📊 安全監控

### 關鍵指標

- **認證失敗率**: 每小時失敗登入次數
- **速率限制觸發**: 被限制的請求數量
- **錯誤率**: 4xx/5xx 錯誤比例
- **回應時間**: 異常慢的請求

### 告警設定

```yaml
alerts:
  - name: "High Authentication Failure Rate"
    condition: "auth_failures > 10 per 5m"
    severity: "warning"
  
  - name: "Rate Limit Exceeded"
    condition: "rate_limit_hits > 100 per 1m"
    severity: "info"
  
  - name: "Suspicious Activity"
    condition: "suspicious_patterns > 5 per 10m"
    severity: "critical"
```

## 🔍 漏洞管理

### 定期掃描

1. **依賴掃描**
   ```bash
   # 檢查已知漏洞
   python -m pip audit
   
   # 更新依賴
   pip-review --local --interactive
   ```

2. **靜態代碼分析**
   ```bash
   # 安全檢查
   bandit -r src/
   
   # 代碼質量
   flake8 src/
   mypy src/
   ```

3. **動態測試**
   ```bash
   # 滲透測試
   nmap -sS -O target-host
   
   # Web 應用掃描
   nikto -h http://target-host
   ```

### 漏洞修復流程

1. **識別**: 自動掃描或手動報告
2. **評估**: 風險等級和影響範圍
3. **修復**: 開發和測試補丁
4. **部署**: 快速部署修復
5. **驗證**: 確認修復有效

## 🔐 最佳實踐

### 開發團隊

1. **安全編碼**
   - 永不硬編碼機密資訊
   - 使用參數化查詢
   - 驗證所有用戶輸入
   - 最小權限原則

2. **代碼審查**
   - 安全相關代碼雙人審查
   - 使用安全檢查清單
   - 自動化安全掃描

3. **測試**
   - 安全功能測試
   - 負面測試案例
   - 滲透測試

### 運維團隊

1. **環境管理**
   - 生產和開發環境隔離
   - 定期安全更新
   - 監控和日誌管理

2. **事件回應**
   - 明確的回應流程
   - 定期演練
   - 快速恢復能力

## 📚 相關資源

### 文檔
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI 安全指南](https://fastapi.tiangolo.com/tutorial/security/)
- [JWT 最佳實踐](https://tools.ietf.org/html/rfc8725)

### 工具
- [Bandit](https://bandit.readthedocs.io/) - Python 安全掃描
- [Safety](https://pyup.io/safety/) - 依賴漏洞檢查
- [OWASP ZAP](https://www.zaproxy.org/) - Web 應用安全掃描

### 標準
- [ISO 27001](https://www.iso.org/isoiec-27001-information-security.html) - 資訊安全管理
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework) - 網路安全框架

---

**記住**: 安全是一個持續的過程，不是一次性的設定。定期審查和更新安全措施是保護平台的關鍵。