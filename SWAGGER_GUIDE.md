# Swagger UI 使用指南

## 🎯 理解Swagger UI介面

### 介面元素說明

1. **頂部描述區域**
   - 包含Markdown格式的API說明文檔
   - 顯示emoji、標題、列表等格式化內容
   - 這是正常的，不是錯誤

2. **分類標籤（Tags）**
   - `health`、`authentication`、`products`等是分組標籤
   - 它們不是API端點，只是用來組織相關API
   - 點擊標籤可以展開/收起該分類下的所有端點

3. **實際的API端點**
   - 在每個分類標籤下方
   - 格式：`[HTTP方法] /api/v1/路徑`
   - 例如：`POST /api/v1/auth/register`

## 📊 完整的API端點列表

### 🏥 Health（健康檢查）
- `GET /api/v1/health/` - 基本健康檢查
- `GET /api/v1/health/ready` - 就緒檢查
- `GET /api/v1/health/live` - 存活檢查

### 🔐 Authentication（認證）
- `POST /api/v1/auth/register` - 用戶註冊
- `POST /api/v1/auth/token` - 獲取訪問令牌（登入）

### 👤 Users（用戶）
- `GET /api/v1/users/me` - 獲取當前用戶資訊

### 📦 Products（產品）
- `GET /api/v1/products/` - 獲取產品列表
- `POST /api/v1/products/` - 創建新產品
- `GET /api/v1/products/{product_id}` - 獲取單個產品
- `PUT /api/v1/products/{product_id}` - 更新產品
- `DELETE /api/v1/products/{product_id}` - 刪除產品
- `GET /api/v1/products/{product_id}/insights` - 獲取產品洞察
- `GET /api/v1/products/{product_id}/price-history` - 獲取價格歷史

### 🔍 Competitors（競爭對手）
- `POST /api/v1/competitors/discover` - 發現競爭對手
- `GET /api/v1/competitors/{product_id}` - 獲取產品的競爭對手
- `POST /api/v1/competitors/analyze` - 執行競爭分析
- `GET /api/v1/competitors/insights/{product_id}` - 獲取競爭洞察

### 💾 Cache（快取管理）
- `DELETE /api/v1/cache/clear` - 清除快取
- `GET /api/v1/cache/stats` - 獲取快取統計

### 🚦 Rate Limits（速率限制）
- `GET /api/v1/rate-limits/status` - 檢查速率限制狀態

## 🚀 如何使用Swagger UI測試

### Step 1: 訪問Swagger UI
```
http://localhost:8000/api/v1/docs
```

### Step 2: 認證（重要！）
1. 先執行註冊（如果沒有帳號）：
   - 找到 `POST /api/v1/auth/register`
   - 點擊展開
   - 點擊 "Try it out"
   - 填寫JSON：
     ```json
     {
       "username": "testuser",
       "email": "test@example.com",
       "password": "Test123!",
       "full_name": "Test User"
     }
     ```
   - 點擊 "Execute"

2. 登入獲取Token：
   - 找到 `POST /api/v1/auth/token`
   - 點擊展開
   - 點擊 "Try it out"
   - 填寫表單：
     - username: testuser
     - password: Test123!
   - 點擊 "Execute"
   - 複製返回的 `access_token`

3. 設置全局認證：
   - 點擊頁面右上角的 "Authorize" 按鈕
   - 在彈出框中貼上token
   - 點擊 "Authorize"
   - 點擊 "Close"

### Step 3: 測試其他端點
現在你已經認證成功，可以測試所有需要認證的端點了！

例如測試創建產品：
1. 找到 `POST /api/v1/products/`
2. 點擊展開
3. 點擊 "Try it out"
4. 填寫JSON：
   ```json
   {
     "asin": "B08N5WRWNW",
     "title": "Echo Dot (4th Gen)",
     "category": "Smart Home"
   }
   ```
5. 點擊 "Execute"
6. 查看響應結果

## 🎨 Swagger UI 功能說明

### 顏色代碼
- 🟢 **綠色 GET**: 讀取操作
- 🔵 **藍色 POST**: 創建操作
- 🟡 **黃色 PUT**: 更新操作
- 🔴 **紅色 DELETE**: 刪除操作

### 響應代碼
- `200`: 成功
- `201`: 創建成功
- `400`: 請求錯誤
- `401`: 未認證
- `403`: 無權限
- `404`: 未找到
- `422`: 驗證錯誤
- `500`: 服務器錯誤

## 💡 使用技巧

1. **查看模型定義**
   - 滾動到頁面底部的 "Schemas" 部分
   - 可以看到所有請求和響應的數據結構

2. **下載API規範**
   - 訪問 `http://localhost:8000/openapi.json`
   - 獲取完整的OpenAPI規範文件

3. **測試不同場景**
   - 正常請求：填寫正確的參數
   - 錯誤處理：故意填寫錯誤的參數查看錯誤響應
   - 邊界測試：測試極限值

4. **查看請求詳情**
   - Execute後可以看到：
     - Curl命令（可複製用於命令行）
     - Request URL
     - Response body
     - Response headers

## ❓ 常見問題

### Q: 為什麼看到Markdown文字？
A: 這是正常的，FastAPI支援Markdown格式的API描述，會被渲染成格式化文字。

### Q: 為什麼分類標題不能點擊執行？
A: 分類標題（tags）只是組織工具，實際的API端點在標題下方。

### Q: 為什麼有些端點返回401？
A: 需要先認證。按照上面的Step 2進行認證。

### Q: 如何查看請求的實際格式？
A: 點擊Execute後，查看Curl命令，這顯示了實際的HTTP請求格式。

## 🎯 快速測試清單

- [ ] 能看到Swagger UI頁面
- [ ] 能成功註冊新用戶
- [ ] 能成功登入獲取Token
- [ ] 能使用Authorize按鈕設置Token
- [ ] 能成功調用需認證的API
- [ ] 能看到正確的響應結果

---

現在你應該能順利使用Swagger UI測試所有API功能了！🚀