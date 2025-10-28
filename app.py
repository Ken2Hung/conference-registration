"""
議程管理系統主應用程式
Conference Session Management System
"""
import streamlit as st
from src.ui.dashboard import render_dashboard
from src.ui.session_detail import render_session_detail


# Streamlit 頁面配置
st.set_page_config(
    page_title="議程管理系統",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="collapsed"
)


def initialize_session_state():
    """初始化 session state 預設值。"""
    if "is_authenticated" not in st.session_state:
        st.session_state.is_authenticated = False

    if "current_page" not in st.session_state:
        st.session_state.current_page = "dashboard"

    if "selected_session_id" not in st.session_state:
        st.session_state.selected_session_id = None


def apply_custom_css():
    """套用自訂 CSS 樣式。"""
    st.markdown("""
        <style>
        /* 全域樣式 */
        .stApp {
            background: linear-gradient(135deg, #0f0c29 0%, #1a1a2e 50%, #16213e 100%);
        }

        /* 隱藏 Streamlit 預設元素 */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}

        /* 按鈕樣式 */
        .stButton > button {
            border-radius: 12px;
            font-weight: 600;
            transition: all 0.3s;
            border: none;
        }

        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3);
        }

        /* 主要按鈕 */
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        /* 卡片陰影效果 */
        .element-container {
            transition: transform 0.2s;
        }

        /* 輸入框樣式 */
        .stTextInput > div > div > input {
            background: #16213e;
            border: 1px solid #2d3748;
            border-radius: 8px;
            color: #f1f5f9;
        }

        /* 選擇框樣式 */
        .stSelectbox > div > div > select {
            background: #16213e;
            border: 1px solid #2d3748;
            border-radius: 8px;
            color: #f1f5f9;
        }

        /* 文字區域樣式 */
        .stTextArea > div > div > textarea {
            background: #16213e;
            border: 1px solid #2d3748;
            border-radius: 8px;
            color: #f1f5f9;
        }

        /* 數字輸入框樣式 */
        .stNumberInput > div > div > input {
            background: #16213e;
            border: 1px solid #2d3748;
            border-radius: 8px;
            color: #f1f5f9;
        }

        /* 成功訊息 */
        .stSuccess {
            background: #10b98150;
            border-left: 4px solid #10b981;
            border-radius: 8px;
            color: #d1fae5;
        }

        /* 錯誤訊息 */
        .stError {
            background: #ef444450;
            border-left: 4px solid #ef4444;
            border-radius: 8px;
            color: #fee2e2;
        }

        /* 資訊訊息 */
        .stInfo {
            background: #3b82f650;
            border-left: 4px solid #3b82f6;
            border-radius: 8px;
            color: #dbeafe;
        }

        /* 警告訊息 */
        .stWarning {
            background: #f59e0b50;
            border-left: 4px solid #f59e0b;
            border-radius: 8px;
            color: #fef3c7;
        }

        /* 滾動條樣式 */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }

        ::-webkit-scrollbar-track {
            background: #1a1a2e;
        }

        ::-webkit-scrollbar-thumb {
            background: #667eea;
            border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: #764ba2;
        }
        </style>
    """, unsafe_allow_html=True)


def render_navigation():
    """渲染導航選單。"""
    st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 6, 1])

    with col1:
        if st.button("🏠 首頁", use_container_width=True):
            st.session_state.current_page = "dashboard"
            st.session_state.selected_session_id = None
            st.rerun()

    with col3:
        if st.button("👤 管理員", use_container_width=True):
            st.info("管理員功能將在後續版本提供")


def render_current_page():
    """根據當前頁面狀態渲染對應內容。"""
    try:
        if st.session_state.current_page == "dashboard":
            # 渲染儀表板
            render_dashboard()

        elif st.session_state.current_page == "detail":
            # 渲染議程詳情頁
            if st.session_state.selected_session_id:
                render_session_detail(st.session_state.selected_session_id)
            else:
                st.error("未選擇議程")
                if st.button("返回首頁"):
                    st.session_state.current_page = "dashboard"
                    st.rerun()

        else:
            # 未知頁面
            st.error(f"未知的頁面：{st.session_state.current_page}")
            if st.button("返回首頁"):
                st.session_state.current_page = "dashboard"
                st.rerun()

    except Exception as e:
        # 錯誤邊界
        st.error("發生錯誤，請稍後再試")

        with st.expander("🔍 錯誤詳情"):
            st.code(str(e))

        if st.button("返回首頁"):
            st.session_state.current_page = "dashboard"
            st.session_state.selected_session_id = None
            st.rerun()


def main():
    """主應用程式入口。"""
    # 初始化
    initialize_session_state()

    # 套用樣式
    apply_custom_css()

    # 渲染導航
    render_navigation()

    # 渲染當前頁面
    render_current_page()

    # 頁尾資訊
    st.markdown("""
        <div style="
            text-align: center;
            margin-top: 80px;
            padding: 32px;
            color: #6b7280;
            font-size: 14px;
            border-top: 1px solid #2d3748;
        ">
            <p style="margin: 0;">
                議程管理系統 v1.0.0 |
                Built with ❤️ using
                <a href="https://streamlit.io" target="_blank" style="color: #8b5cf6; text-decoration: none;">Streamlit</a>
            </p>
            <p style="margin: 8px 0 0 0; font-size: 12px;">
                © 2025 Conference Management System. All rights reserved.
            </p>
        </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
