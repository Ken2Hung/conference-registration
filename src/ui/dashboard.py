"""Dashboard UI component for displaying sessions."""
import streamlit as st
from typing import List
from src.models.session import Session
from src.services.session_service import get_past_sessions, get_upcoming_sessions
from src.ui.html_utils import html_block


def _get_difficulty_badge(level: str) -> str:
    """取得難度徽章顯示文字。"""
    badges = {
        "初": "🔵 初級",
        "中": "🟣 中級",
        "高": "🔴 高級"
    }
    return badges.get(level, "🔵 初級")


def _render_speaker_avatar(
    photo_path: str,
    speaker_name: str,
    size: int = 50,
    is_past: bool = False
) -> str:
    """
    渲染講者頭像，自動處理缺失照片的降級顯示。

    Args:
        photo_path: 照片檔案相對路徑（從專案根目錄）
        speaker_name: 講者姓名（用於 alt 文字和首字母佔位符）
        size: 頭像直徑（像素）
        is_past: 是否為過去的議程（會降低透明度）

    Returns:
        HTML 字串，包含照片或佔位符頭像
    """
    initial = speaker_name[0].upper() if speaker_name else "?"
    opacity = "0.6" if is_past else "1.0"

    return html_block(
        f"""
        <div style="
            display: inline-block;
            position: relative;
            width: {size}px;
            height: {size}px;
            vertical-align: middle;
            margin-right: 12px;
        ">
            <!-- 佔位符（首字母）：預設顯示 -->
            <div style="
                width: {size}px;
                height: {size}px;
                border-radius: 50%;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border: 2px solid #2d3748;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: {int(size * 0.5)}px;
                font-weight: 600;
                color: #ffffff;
                opacity: {opacity};
                position: absolute;
                top: 0;
                left: 0;
            ">
                {initial}
            </div>

            <!-- 實際照片：如果載入成功會覆蓋佔位符 -->
            <img
                src="{photo_path}"
                alt="{speaker_name}"
                style="
                    width: {size}px;
                    height: {size}px;
                    border-radius: 50%;
                    object-fit: cover;
                    border: 2px solid #2d3748;
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
                    opacity: {opacity};
                    position: absolute;
                    top: 0;
                    left: 0;
                    z-index: 1;
                "
                onerror="this.style.display='none';"
            />
        </div>
        """
    )


def _render_session_card(session: Session, is_past: bool = False):
    """
    渲染單一議程卡片。

    Args:
        session: 議程物件
        is_past: 是否為過去的議程
    """
    # 設定容器樣式
    if is_past:
        container_style = "background-color: #1a1a2e; opacity: 0.7; filter: grayscale(20%);"
    else:
        container_style = "background-color: #16213e;"

    # 狀態標籤
    status = session.status()
    status_labels = {
        "available": "🟢 可報名",
        "full": "🔴 已額滿",
        "expired": "⏰ 已過期"
    }
    status_label = status_labels.get(status, "")

    # 計算報名百分比
    registration_pct = session.registration_percentage()

    # 生成講者頭像 HTML
    avatar_html = _render_speaker_avatar(
        session.speaker.photo,
        session.speaker.name,
        size=50,
        is_past=is_past
    )

    # 使用 container 建立卡片
    with st.container():
        st.markdown(
            html_block(
                f"""
                <div style="
                    {container_style}
                    padding: 20px;
                    border-radius: 12px;
                    border: 1px solid #2d3748;
                    margin-bottom: 16px;
                ">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
                        <span style="color: #94a3b8; font-size: 14px;">📅 {session.date} {session.time}</span>
                        <span style="color: #94a3b8; font-size: 12px;">{_get_difficulty_badge(session.level)}</span>
                    </div>

                    <div style="color: #f1f5f9; font-size: 18px; font-weight: 600; margin-bottom: 8px;">
                        {session.title}
                    </div>

                    <div style="color: #cbd5e1; font-size: 14px; margin-bottom: 12px; display: flex; align-items: center;">
                        {avatar_html}
                        <span>{session.speaker.name}</span>
                    </div>

                    <div style="margin-bottom: 8px;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                            <span style="color: #94a3b8; font-size: 13px;">{status_label}</span>
                            <span style="color: #94a3b8; font-size: 13px;">{session.registered}/{session.capacity} 人</span>
                        </div>
                        <div style="width: 100%; height: 6px; background: #334155; border-radius: 3px; overflow: hidden;">
                            <div style="width: {registration_pct}%; height: 100%; background: linear-gradient(90deg, #06b6d4, #8b5cf6);"></div>
                        </div>
                    </div>

                    <div style="display: flex; flex-wrap: wrap; gap: 6px; margin-top: 12px;">
                        {"".join([f'<span style="background: #334155; color: #94a3b8; padding: 3px 10px; border-radius: 10px; font-size: 12px;">#{tag}</span>' for tag in session.tags])}
                    </div>
                </div>
                """
            ),
            unsafe_allow_html=True
        )

        # 查看詳情按鈕
        if st.button(f"查看詳情 »", key=f"view_{session.id}", use_container_width=True):
            st.session_state.selected_session_id = session.id
            st.session_state.current_page = "detail"
            st.rerun()


def _render_section_title(icon: str, title: str):
    """渲染區段標題。"""
    st.markdown(html_block(
        f"""
        <h2 style="
            color: #cbd5e1;
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 24px;
            padding-bottom: 12px;
            border-bottom: 2px solid #334155;
        ">
            {icon} {title}
        </h2>
        """
    ), unsafe_allow_html=True)


def render_dashboard():
    """渲染主儀表板頁面。"""
    # 頁面標題
    st.markdown(html_block("""
        <h1 style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            font-size: 48px;
            font-weight: 800;
            text-align: center;
            margin-bottom: 40px;
        ">
            📅 議程管理系統
        </h1>
    """), unsafe_allow_html=True)

    # 取得議程資料
    try:
        past_sessions = get_past_sessions(limit=5)
        upcoming_sessions = get_upcoming_sessions(limit=5)
    except Exception as e:
        st.error(f"載入議程時發生錯誤: {str(e)}")
        return

    # 分成兩欄顯示
    col1, col2 = st.columns(2)

    # 過去的議程（左欄）
    with col1:
        _render_section_title("⏮️", "過去的議程")

        if past_sessions:
            for session in past_sessions:
                _render_session_card(session, is_past=True)
        else:
            st.info("暫無過去的議程")

    # 即將到來的議程（右欄）
    with col2:
        _render_section_title("⏭️", "即將到來的議程")

        if upcoming_sessions:
            for session in upcoming_sessions:
                _render_session_card(session, is_past=False)
        else:
            st.info("暫無即將到來的議程")
