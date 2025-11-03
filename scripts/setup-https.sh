#!/bin/bash

# HTTPS Setup Script for Streamlit WebRTC
# 為 Streamlit WebRTC 功能設定 HTTPS

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SSL_DIR="$PROJECT_ROOT/.streamlit/ssl"
CONFIG_FILE="$PROJECT_ROOT/.streamlit/config.toml"

echo "🔐 Streamlit WebRTC HTTPS 設定工具"
echo "=================================="
echo ""

# Check if OpenSSL is available
if ! command -v openssl &> /dev/null; then
    echo "❌ 錯誤：找不到 openssl 命令"
    echo "   macOS: brew install openssl"
    echo "   Ubuntu: sudo apt-get install openssl"
    exit 1
fi

echo "選擇設定方式："
echo "1) 生成自簽 SSL 證書（開發/測試用）"
echo "2) 使用 ngrok（推薦，最簡單）"
echo "3) 顯示現有證書資訊"
echo "4) 移除 HTTPS 設定（恢復 HTTP）"
echo ""
read -p "請選擇 (1-4): " choice

case $choice in
    1)
        echo ""
        echo "📝 生成自簽 SSL 證書..."
        echo ""

        # Create SSL directory
        mkdir -p "$SSL_DIR"

        # Generate certificate
        read -p "請輸入證書的 Common Name（通常是 IP 或域名，預設 localhost）: " cn
        cn=${cn:-localhost}

        openssl req -x509 -newkey rsa:4096 \
            -keyout "$SSL_DIR/key.pem" \
            -out "$SSL_DIR/cert.pem" \
            -days 365 -nodes \
            -subj "/CN=$cn"

        echo ""
        echo "✅ SSL 證書已生成："
        echo "   證書: $SSL_DIR/cert.pem"
        echo "   私鑰: $SSL_DIR/key.pem"
        echo "   有效期: 365 天"
        echo ""

        # Update config.toml
        echo "📝 更新 Streamlit 配置..."

        # Check if SSL config already exists
        if grep -q "sslCertFile" "$CONFIG_FILE"; then
            echo "⚠️  配置檔中已有 SSL 設定"
            read -p "是否覆蓋？(y/n): " overwrite
            if [ "$overwrite" != "y" ]; then
                echo "取消更新配置"
                exit 0
            fi
            # Remove old SSL config
            sed -i.bak '/sslCertFile/d' "$CONFIG_FILE"
            sed -i.bak '/sslKeyFile/d' "$CONFIG_FILE"
        fi

        # Add SSL config after [server] section
        sed -i.bak '/\[server\]/a\
sslCertFile = ".streamlit/ssl/cert.pem"\
sslKeyFile = ".streamlit/ssl/key.pem"
' "$CONFIG_FILE"

        echo "✅ 配置已更新"
        echo ""
        echo "🚀 啟動說明："
        echo "   1. 執行: ./start.sh"
        echo "   2. 訪問: https://$cn:8501"
        echo "   3. 瀏覽器會警告「不安全」，點擊「繼續前往」"
        echo ""
        echo "⚠️  注意：自簽證書僅供開發測試使用"
        ;;

    2)
        echo ""
        echo "🌐 使用 ngrok 設定 HTTPS"
        echo ""

        # Check if ngrok is installed
        if ! command -v ngrok &> /dev/null; then
            echo "❌ ngrok 未安裝"
            echo ""
            echo "安裝方式："
            echo "  macOS:  brew install ngrok"
            echo "  其他:   https://ngrok.com/download"
            echo ""
            echo "安裝後請重新執行此腳本"
            exit 1
        fi

        echo "✅ ngrok 已安裝"
        echo ""
        echo "📝 使用步驟："
        echo "   1. 在一個終端視窗執行: ./start.sh"
        echo "   2. 在另一個終端視窗執行: ngrok http 8501"
        echo "   3. ngrok 會顯示 HTTPS 網址，例如: https://abc123.ngrok.io"
        echo "   4. 使用該網址從任何裝置訪問"
        echo ""
        echo "💡 提示：ngrok 免費版的網址每次重啟會變化"
        echo ""

        read -p "是否現在啟動 ngrok？(y/n): " start_ngrok
        if [ "$start_ngrok" = "y" ]; then
            echo ""
            echo "🚀 啟動 ngrok（請確保 Streamlit 已在另一個視窗啟動）..."
            ngrok http 8501
        fi
        ;;

    3)
        echo ""
        if [ -f "$SSL_DIR/cert.pem" ]; then
            echo "📋 現有證書資訊："
            echo ""
            openssl x509 -in "$SSL_DIR/cert.pem" -text -noout | grep -A2 "Subject:"
            openssl x509 -in "$SSL_DIR/cert.pem" -text -noout | grep -A2 "Validity"
            echo ""
            echo "證書位置: $SSL_DIR/cert.pem"
        else
            echo "❌ 找不到證書檔案"
        fi
        ;;

    4)
        echo ""
        echo "🗑️  移除 HTTPS 設定..."

        # Remove SSL config from config.toml
        if grep -q "sslCertFile" "$CONFIG_FILE"; then
            sed -i.bak '/sslCertFile/d' "$CONFIG_FILE"
            sed -i.bak '/sslKeyFile/d' "$CONFIG_FILE"
            echo "✅ 已從配置中移除 SSL 設定"
        fi

        # Optionally remove certificate files
        if [ -d "$SSL_DIR" ]; then
            read -p "是否刪除證書檔案？(y/n): " remove_files
            if [ "$remove_files" = "y" ]; then
                rm -rf "$SSL_DIR"
                echo "✅ 證書檔案已刪除"
            fi
        fi

        echo ""
        echo "✅ HTTPS 設定已移除，應用將使用 HTTP"
        ;;

    *)
        echo "無效選擇"
        exit 1
        ;;
esac

echo ""
echo "完成！"
