# Conference Registration System

議程管理系統 - 使用 Streamlit 建立的現代化會議議程管理平台

## Features

- 📅 議程瀏覽：分類顯示過去和即將到來的議程
- 👤 講者資訊：圓形講者照片顯示，附帶降級處理
- 🎯 議程詳情：完整的議程資訊和報名狀態
- 📊 報名管理：即時顯示報名進度和容量
- 🎨 深色主題：現代化的深色主題 UI 設計

## Requirements

- Python 3.8+
- Streamlit
- PIL/Pillow (圖片處理)
- python-dateutil

## Installation

```bash
# 安裝依賴
pip install -r requirements.txt

# 運行應用程式
streamlit run app.py
```

## Project Structure

```
conference-registration/
├── app.py                  # 主應用程式入口
├── src/
│   ├── models/            # 資料模型
│   │   ├── session.py     # 議程模型
│   │   └── speaker.py     # 講者模型
│   ├── services/          # 業務邏輯
│   │   └── session_service.py
│   └── ui/                # UI 組件
│       ├── dashboard.py   # 儀表板頁面
│       └── session_detail.py  # 議程詳情頁面
├── data/                  # 資料檔案
│   └── sessions.json      # 議程資料
├── images/               # 圖片資源
│   └── speakers/         # 講者照片
└── tests/                # 測試檔案
    └── ui/               # UI 測試
```

## Speaker Photo Requirements

### 照片位置
所有講者照片應放置在 `images/speakers/` 目錄中。

### 支援格式
- JPG (推薦)
- PNG
- WEBP

### 照片要求
- **檔案大小**: 建議 < 10KB 每張
- **尺寸**: 任意尺寸（系統會自動縮放到 50px 圓形）
- **命名**: 使用連字號分隔的小寫名稱（例如：`john-doe.jpg`）
- **路徑格式**: 在 `sessions.json` 中使用相對路徑（例如：`images/speakers/john-doe.jpg`）

### 缺失照片處理
如果講者照片檔案不存在，系統會自動顯示：
- 漸層色背景的圓形佔位符
- 講者姓名的首字母
- 與實際照片相同的尺寸和樣式

不會顯示破圖圖示或錯誤訊息。

## Data Format

### sessions.json

議程資料儲存在 `data/sessions.json`，包含以下欄位：

```json
{
  "sessions": [
    {
      "id": "session_001",
      "title": "議程標題",
      "description": "議程描述",
      "date": "2025-11-15",
      "time": "14:00-16:00",
      "location": "線上 Zoom 會議室",
      "level": "中",
      "tags": ["Python", "AI"],
      "capacity": 100,
      "registered": 67,
      "speaker": {
        "name": "講者姓名",
        "photo": "images/speakers/speaker-name.jpg",
        "bio": "講者簡介"
      }
    }
  ]
}
```

## Testing

```bash
# 運行所有測試
pytest

# 運行特定測試
pytest tests/ui/test_dashboard.py

# 運行測試並檢查覆蓋率
pytest --cov=src --cov-report=term-missing
```

## Development

### Constitution Compliance

本專案遵循 `.specify/memory/constitution.md` 中定義的開發規範：

- ✅ 最少註解：程式碼自我說明
- ✅ 強制測試：所有功能都有單元測試
- ✅ 完整錯誤處理：優雅處理邊界情況
- ✅ 慣例提交：遵循 Conventional Commits 規範
- ✅ 技術堆疊：Streamlit + Python + JSON

### Adding New Speakers

1. 準備講者照片（JPG/PNG/WEBP，< 10KB）
2. 將照片放入 `images/speakers/` 目錄
3. 更新 `data/sessions.json`，在 `speaker.photo` 欄位中設定正確路徑
4. 重新啟動應用程式

## License

MIT License

## Support

如有問題，請參考：
- [QUICKSTART.md](QUICKSTART.md) - 快速入門指南
- [specs/](specs/) - 功能規格文件
