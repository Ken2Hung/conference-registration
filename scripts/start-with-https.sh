#!/bin/bash

# 啟動前自動生成匹配當前 IP 的 SSL 證書
# 解決 IP 變動導致證書失效的問題

echo "🚀 啟動支援遠端訪問的議程管理系統"
echo "===================================="
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Get current IP
echo "🔍 偵測當前 IP 位址..."
CURRENT_IP=$(ipconfig getifaddr en0 || ipconfig getifaddr en1 || echo "")

if [ -z "$CURRENT_IP" ]; then
    echo "❌ 無法偵測 IP 位址"
    echo ""
    echo "💡 解決方案："
    echo "   1. 檢查網路連線"
    echo "   2. 或只在本機測試：./start.sh"
    exit 1
fi

echo "✅ 當前 IP：$CURRENT_IP"
echo ""

# Check if certificate exists and matches current IP
SSL_DIR=".streamlit/ssl"
CERT_FILE="$SSL_DIR/cert.pem"
NEED_REGENERATE=false

if [ -f "$CERT_FILE" ]; then
    CERT_CN=$(openssl x509 -in "$CERT_FILE" -noout -subject 2>/dev/null | sed -n 's/.*CN=\([^,]*\).*/\1/p')
    echo "📋 現有證書 CN：$CERT_CN"

    if [ "$CERT_CN" != "$CURRENT_IP" ] && [ "$CERT_CN" != "localhost" ]; then
        echo "⚠️  證書 IP 不匹配（$CERT_CN ≠ $CURRENT_IP）"
        NEED_REGENERATE=true
    fi
else
    echo "📋 證書不存在"
    NEED_REGENERATE=true
fi

# Generate certificate if needed
if [ "$NEED_REGENERATE" = true ]; then
    echo ""
    echo "🔐 生成新的 SSL 證書..."
    mkdir -p "$SSL_DIR"

    # Generate certificate with both IP and localhost
    openssl req -x509 -newkey rsa:4096 \
        -keyout "$SSL_DIR/key.pem" \
        -out "$SSL_DIR/cert.pem" \
        -days 365 -nodes \
        -subj "/CN=$CURRENT_IP" \
        2>/dev/null

    if [ $? -eq 0 ]; then
        echo "✅ 證書已生成（CN=$CURRENT_IP）"
    else
        echo "❌ 證書生成失敗"
        exit 1
    fi
fi

# Update config.toml to enable HTTPS
CONFIG_FILE=".streamlit/config.toml"
echo ""
echo "📝 啟用 HTTPS 配置..."

# Check if SSL config is commented out
if grep -q "^# sslCertFile" "$CONFIG_FILE" || ! grep -q "sslCertFile" "$CONFIG_FILE"; then
    # Need to enable SSL
    if grep -q "# sslCertFile" "$CONFIG_FILE"; then
        # Uncomment existing lines
        sed -i.bak 's/^# sslCertFile/sslCertFile/' "$CONFIG_FILE"
        sed -i.bak 's/^# sslKeyFile/sslKeyFile/' "$CONFIG_FILE"
    else
        # Add SSL config after [server] section
        sed -i.bak '/\[server\]/a\
sslCertFile = ".streamlit/ssl/cert.pem"\
sslKeyFile = ".streamlit/ssl/key.pem"
' "$CONFIG_FILE"
    fi
    echo "✅ HTTPS 已啟用"
else
    echo "✅ HTTPS 已是啟用狀態"
fi

# Check if port 8501 is in use
if lsof -ti :8501 > /dev/null 2>&1; then
    echo ""
    echo "⚠️  Port 8501 已被佔用"
    read -p "是否終止舊程序？(y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kill $(lsof -ti :8501) 2>/dev/null
        sleep 2
        echo "✅ 舊程序已終止"
    else
        echo "❌ 啟動取消"
        exit 1
    fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 訪問網址："
echo ""
echo "   本機：  https://localhost:8501"
echo "   遠端：  https://$CURRENT_IP:8501"
echo ""
echo "⚠️  瀏覽器會警告「不安全」（自簽證書）"
echo "   請點擊「進階」→「繼續前往」"
echo ""
echo "💡 提示："
echo "   • 必須使用 HTTPS 才能使用麥克風"
echo "   • 推薦使用 Chrome 或 Edge 瀏覽器"
echo "   • 按 Ctrl+C 可停止伺服器"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Activate virtual environment
source venv/bin/activate

# Start Streamlit
streamlit run app.py --logger.level=warning
