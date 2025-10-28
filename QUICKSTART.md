# 議程管理系統 - 快速啟動指南

## 🚀 快速啟動

### 1. 安裝依賴

```bash
# 建立虛擬環境（如果還沒有）
python3 -m venv venv

# 啟動虛擬環境
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate     # Windows

# 安裝依賴
pip install -r requirements.txt
```

### 2. 執行測試（可選）

```bash
# 執行所有測試
pytest tests/ -v

# 執行測試並查看覆蓋率
pytest tests/ --cov=src --cov-report=html
```

### 3. 啟動應用程式

```bash
streamlit run app.py
```

應用程式將在瀏覽器自動開啟，預設網址為：http://localhost:8501

---

## 📋 系統需求

- Python 3.8 或更高版本
- 瀏覽器（Chrome、Firefox、Safari 或 Edge）

---

## ✨ 功能說明

### 首頁（Dashboard）

- **過去的議程**：顯示最近 5 個已結束的議程（灰階顯示）
- **即將到來的議程**：顯示最近 5 個未來的議程（彩色顯示）
- 每個議程卡片顯示：
  - 📅 日期與時間
  - 🎯 難度等級徽章
  - 👤 講師姓名
  - 📊 報名狀態與進度條
  - 🏷️ 技術標籤

### 議程詳情頁

點擊「查看詳情」按鈕後可以看到：

- 完整議程資訊（標題、描述、時間、地點）
- 講師詳細資訊（照片、姓名、簡介）
- 技術標籤
- 學習成果說明
- 即時報名狀態
- **立即報名按鈕**（可用議程）

### 報名功能

- ✅ 報名成功：人數 +1，顯示成功訊息與煙火動畫
- ❌ 已額滿：按鈕停用，顯示紅色標籤
- ❌ 已過期：按鈕停用，顯示灰色標籤

---

## 📁 資料檔案

### data/sessions.json

包含 11 個範例議程資料，涵蓋：
- AI Guardrails
- Python 網頁爬蟲
- React 前端開發
- Kubernetes 容器編排
- TensorFlow 機器學習
- AWS 雲端架構
- Agile 敏捷開發
- Git 版本控制
- Pandas 數據分析
- Docker 容器化
- Airflow 數據工作流

### data/config.json

管理員設定（未來版本使用）：
- 預設帳號：admin
- 預設密碼：admin123

---

## 🧪 測試

系統包含 139 個自動化測試：

```bash
# 執行所有測試
pytest tests/

# 執行特定測試檔案
pytest tests/unit/test_session_service.py

# 執行整合測試
pytest tests/integration/

# 查看測試覆蓋率
pytest tests/ --cov=src --cov-report=term-missing
```

---

## 🎨 UI 主題

系統使用深藍紫色漸層主題：

- 主色調：深藍 (#0f0c29) → 深紫 (#1a1a2e) → 藍灰 (#16213e)
- 強調色：紫色 (#667eea, #764ba2)
- 難度徽章：
  - 🔵 初級：青藍色
  - 🟣 中級：紫粉色
  - 🔴 高級：紅橙色

---

## 🐛 常見問題

### Q: 應用程式無法啟動

**A:** 確認已安裝所有依賴：
```bash
pip install -r requirements.txt
```

### Q: 顯示「找不到模組」錯誤

**A:** 確認在專案根目錄執行，且已啟動虛擬環境：
```bash
source venv/bin/activate
streamlit run app.py
```

### Q: 議程資料沒有顯示

**A:** 確認 data/sessions.json 檔案存在且格式正確：
```bash
cat data/sessions.json | python -m json.tool
```

### Q: 報名後人數沒有更新

**A:** 重新整理頁面，或點擊「返回議程列表」後再次進入。

---

## 📚 開發相關

### 專案結構

```
conference-registration/
├── app.py                  # 主應用程式
├── requirements.txt        # Python 依賴
├── pytest.ini             # 測試配置
├── .gitignore             # Git 忽略規則
├── data/                  # 資料檔案
│   ├── sessions.json      # 議程資料
│   └── config.json        # 系統設定
├── src/                   # 原始碼
│   ├── models/            # 資料模型
│   ├── services/          # 業務邏輯
│   ├── ui/                # UI 元件
│   └── utils/             # 工具函數
└── tests/                 # 測試
    ├── unit/              # 單元測試
    └── integration/       # 整合測試
```

### 技術堆疊

- **前端框架**: Streamlit 1.28.0
- **程式語言**: Python 3.8+
- **資料儲存**: JSON 檔案
- **測試框架**: pytest 7.4.3
- **日期處理**: python-dateutil 2.8.2

---

## 📧 支援

如有問題，請查看：
- 測試報告：執行 `pytest tests/ -v`
- 錯誤日誌：應用程式介面會顯示詳細錯誤訊息

---

**享受使用議程管理系統！** 🎉
