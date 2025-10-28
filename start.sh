#!/bin/bash

# 議程管理系統啟動腳本

echo "🚀 正在啟動議程管理系統..."
echo ""

# 確保在正確的目錄
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "📁 工作目錄: $(pwd)"
echo ""

# 檢查虛擬環境
if [ ! -d "venv" ]; then
    echo "❌ 找不到虛擬環境，請先執行："
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# 啟動虛擬環境
echo "🔧 啟動虛擬環境..."
source venv/bin/activate

# 檢查依賴
if ! python3 -c "import streamlit" 2>/dev/null; then
    echo "❌ Streamlit 未安裝，正在安裝依賴..."
    pip install -r requirements.txt
fi

# 驗證資料檔案
if [ ! -f "data/sessions.json" ]; then
    echo "❌ 找不到 data/sessions.json"
    exit 1
fi

echo "✅ 所有檢查通過"
echo ""
echo "🌐 正在啟動 Streamlit 伺服器..."
echo "   應用程式將在瀏覽器自動開啟"
echo "   網址: http://localhost:8501"
echo ""
echo "💡 提示: 按 Ctrl+C 可停止伺服器"
echo ""

# 啟動 Streamlit
streamlit run app.py
