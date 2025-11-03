#!/bin/bash

echo "🔍 WebRTC 連線診斷工具"
echo "========================"
echo ""

# Get IP address
IP=$(ipconfig getifaddr en0 || ipconfig getifaddr en1 || echo "未知")
echo "📍 本機 IP 位址: $IP"
echo ""

# Check if Streamlit is running
if lsof -i :8501 > /dev/null 2>&1; then
    echo "✅ Streamlit 正在執行 (port 8501)"
else
    echo "❌ Streamlit 未執行，請先執行: ./start.sh"
    exit 1
fi

echo ""
echo "🌐 訪問網址："
echo "   本機：https://localhost:8501"
echo "   區網：https://$IP:8501"
echo ""

# Check SSL certificate
if [ -f ".streamlit/ssl/cert.pem" ]; then
    echo "✅ SSL 證書存在"
    echo ""
    echo "📋 證書資訊："
    openssl x509 -in .streamlit/ssl/cert.pem -noout -subject -dates 2>/dev/null | sed 's/^/   /'
else
    echo "❌ SSL 證書不存在"
fi

echo ""
echo "💡 測試提示："
echo "   1. 用瀏覽器訪問上述 HTTPS 網址"
echo "   2. 接受證書警告（自簽證書是正常的）"
echo "   3. 點擊「開始錄音」"
echo "   4. 允許瀏覽器存取麥克風"
echo "   5. 開始說話測試轉錄功能"
echo ""

# Check firewall
echo "🔥 防火牆狀態："
FW_STATE=$(sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate 2>/dev/null | grep -o "enabled\|disabled")
if [ "$FW_STATE" = "enabled" ]; then
    echo "   ⚠️  防火牆已啟用（可能需要允許 Python 連線）"
else
    echo "   ✅ 防火牆已停用"
fi

echo ""
echo "🔍 如果仍有問題，請檢查："
echo "   • 瀏覽器是 Chrome/Edge（不要用 Safari）"
echo "   • 已接受 HTTPS 證書警告"
echo "   • 網路防火牆允許 8501 port"
echo "   • 瀏覽器開發者工具的 Console 是否有錯誤"
