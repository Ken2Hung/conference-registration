#!/usr/bin/env python3
"""
WebRTC Setup Verification Script
驗證 WebRTC 配置是否正確
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_config_file():
    """Check Streamlit config.toml"""
    config_path = project_root / ".streamlit" / "config.toml"

    print("🔍 檢查 Streamlit 配置...")

    if not config_path.exists():
        print("   ❌ 找不到 .streamlit/config.toml")
        return False

    with open(config_path, "r") as f:
        content = f.read()

    checks = {
        "enableCORS": "enableCORS = true" in content,
        "address": "address = " in content,
        "port": "port = 8501" in content,
        "websocket": "enableWebsocketCompression" in content,
    }

    all_passed = True
    for check_name, passed in checks.items():
        status = "✅" if passed else "⚠️"
        print(f"   {status} {check_name}: {'已設定' if passed else '未設定'}")
        if not passed:
            all_passed = False

    # Check SSL config (commented lines are OK)
    has_ssl_enabled = (
        "sslCertFile" in content and
        not all(line.strip().startswith("#") for line in content.split("\n") if "sslCertFile" in line)
    )

    if has_ssl_enabled:
        print("   ✅ HTTPS: 已啟用")
        cert_path = project_root / ".streamlit" / "ssl" / "cert.pem"
        key_path = project_root / ".streamlit" / "ssl" / "key.pem"

        if cert_path.exists() and key_path.exists():
            print("   ✅ SSL 證書檔案存在")
        else:
            print("   ❌ SSL 證書檔案不存在")
            all_passed = False
    else:
        print("   ℹ️  HTTPS: 未啟用（使用 HTTP，僅限本機 localhost）")
        print("      💡 遠端訪問需要 HTTPS，請執行: ./scripts/setup-https.sh")

    return all_passed


def check_ice_servers():
    """Check ICE servers configuration in transcription_widget.py"""
    widget_path = project_root / "src" / "ui" / "transcription_widget.py"

    print("\n🔍 檢查 ICE Servers 配置...")

    if not widget_path.exists():
        print("   ❌ 找不到 transcription_widget.py")
        return False

    with open(widget_path, "r") as f:
        content = f.read()

    # Check for multiple STUN servers
    stun_servers = [
        "stun.l.google.com",
        "stun1.l.google.com",
        "stun.cloudflare.com",
    ]

    all_found = True
    for server in stun_servers:
        if server in content:
            print(f"   ✅ {server}")
        else:
            print(f"   ❌ {server} 未設定")
            all_found = False

    return all_found


def check_rerun_issues():
    """Check if st.rerun() has been properly handled"""
    widget_path = project_root / "src" / "ui" / "transcription_widget.py"

    print("\n🔍 檢查 st.rerun() 優化...")

    with open(widget_path, "r") as f:
        lines = f.readlines()

    # Find st.rerun() calls
    rerun_lines = []
    for i, line in enumerate(lines, 1):
        if "st.rerun()" in line and not line.strip().startswith("#"):
            rerun_lines.append((i, line.strip()))

    if not rerun_lines:
        print("   ✅ 所有不必要的 st.rerun() 已移除")
        return True

    print(f"   ⚠️  發現 {len(rerun_lines)} 個 st.rerun() 呼叫：")
    for line_num, line in rerun_lines:
        print(f"      Line {line_num}: {line}")

    # Check if they are in _render_api_key_input (acceptable)
    acceptable_contexts = []
    for ln, _ in rerun_lines:
        # Get context around the rerun call
        start = max(0, ln - 30)
        end = min(len(lines), ln + 5)
        context = "".join(lines[start:end])

        # Check if in acceptable function
        is_acceptable = (
            "_render_api_key_input" in context or
            "api_key" in context.lower()
        )
        acceptable_contexts.append(is_acceptable)

    if all(acceptable_contexts):
        print("   ✅ 僅在必要的地方使用 st.rerun()（API key 設定）")
        return True

    return False


def check_desired_playing_state():
    """Check if desired_playing_state is properly configured"""
    widget_path = project_root / "src" / "ui" / "transcription_widget.py"

    print("\n🔍 檢查 WebRTC 生命週期管理...")

    with open(widget_path, "r") as f:
        content = f.read()

    # Check for proper desired_playing_state usage
    if "desired_playing_state=is_active" in content:
        print("   ✅ desired_playing_state 已優化（僅在錄音時啟動）")
        return True
    elif "desired_playing_state=True" in content:
        print("   ⚠️  desired_playing_state 恆為 True（可能導致 PeerConnection 累積）")
        return False
    else:
        print("   ❓ 找不到 desired_playing_state 設定")
        return False


def check_dependencies():
    """Check if required packages are installed"""
    print("\n🔍 檢查相依套件...")

    required = [
        ("streamlit", "Streamlit"),
        ("streamlit_webrtc", "streamlit-webrtc"),
        ("av", "PyAV"),
        ("numpy", "NumPy"),
        ("openai", "OpenAI Python SDK"),
    ]

    all_installed = True
    for module, name in required:
        try:
            __import__(module)
            print(f"   ✅ {name}")
        except ImportError:
            print(f"   ❌ {name} 未安裝")
            all_installed = False

    return all_installed


def main():
    print("=" * 60)
    print("WebRTC 設定驗證工具")
    print("=" * 60)
    print()

    results = {
        "配置檔": check_config_file(),
        "ICE Servers": check_ice_servers(),
        "Rerun 優化": check_rerun_issues(),
        "生命週期管理": check_desired_playing_state(),
        "相依套件": check_dependencies(),
    }

    print("\n" + "=" * 60)
    print("驗證結果摘要")
    print("=" * 60)

    for check_name, passed in results.items():
        status = "✅ 通過" if passed else "❌ 失敗"
        print(f"{check_name:20s} {status}")

    all_passed = all(results.values())

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有檢查通過！")
        print("\n下一步：")
        print("  1. 如果需要遠端訪問，請執行: ./scripts/setup-https.sh")
        print("  2. 啟動應用: ./start.sh")
        print("  3. 本機測試: http://localhost:8501")
        print("  4. 遠端測試: https://your-ip:8501")
    else:
        print("⚠️  部分檢查未通過，請參考上述訊息進行修正")
        print("\n參考文件: docs/WEBRTC_SETUP.md")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
