"""Session detail page UI component."""
import streamlit as st
from src.services.session_service import get_session_by_id, register_for_session
from src.models.session import Session
from src.ui.html_utils import html_block


def _render_speaker_info(session: Session):
    """
    渲染講師資訊區塊。

    Args:
        session: 議程物件
    """
    st.markdown(html_block("""
        <h3 style="
            color: #cbd5e1;
            font-size: 20px;
            font-weight: 600;
            margin-top: 32px;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 2px solid #334155;
        ">
            👤 講師資訊
        </h3>
    """), unsafe_allow_html=True)

    # 講師資訊佈局
    col1, col2 = st.columns([1, 3])

    with col1:
        # 講師照片
        try:
            st.image(session.speaker.photo, use_column_width=True)
        except:
            # 如果照片無法載入，顯示佔位符
            st.markdown(html_block("""
                <div style="
                    width: 100%;
                    aspect-ratio: 1;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border-radius: 12px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 48px;
                ">
                    👤
                </div>
            """), unsafe_allow_html=True)

    with col2:
        # 講師姓名
        st.markdown(html_block(f"""
            <div style="
                color: #f1f5f9;
                font-size: 24px;
                font-weight: 600;
                margin-bottom: 8px;
            ">
                {session.speaker.name}
            </div>
        """), unsafe_allow_html=True)

        # 講師簡介
        st.markdown(html_block(f"""
            <div style="
                color: #cbd5e1;
                font-size: 14px;
                line-height: 1.6;
            ">
                {session.speaker.bio}
            </div>
        """), unsafe_allow_html=True)


def _render_session_info(session: Session):
    """
    渲染議程基本資訊。

    Args:
        session: 議程物件
    """
    # 難度徽章樣式
    badge_styles = {
        "初": {"color": "#06b6d4", "bg": "#cffafe", "label": "初級"},
        "中": {"color": "#a855f7", "bg": "#f3e8ff", "label": "中級"},
        "高": {"color": "#ef4444", "bg": "#fee2e2", "label": "高級"}
    }
    badge = badge_styles.get(session.level, badge_styles["初"])

    # 標題與難度徽章
    st.markdown(html_block(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
            <h1 style="
                color: #f1f5f9;
                font-size: 36px;
                font-weight: 700;
                margin: 0;
                flex: 1;
            ">
                {session.title}
            </h1>
            <div style="
                background: {badge['bg']};
                color: {badge['color']};
                padding: 8px 16px;
                border-radius: 16px;
                font-size: 14px;
                font-weight: 600;
                margin-left: 16px;
            ">
                {badge['label']}
            </div>
        </div>
    """), unsafe_allow_html=True)

    # 描述
    st.markdown(html_block(f"""
        <div style="
            color: #cbd5e1;
            font-size: 16px;
            line-height: 1.8;
            margin-bottom: 24px;
        ">
            {session.description}
        </div>
    """), unsafe_allow_html=True)

    # 議程資訊卡片
    info_items = [
        ("📅 日期", session.date),
        ("⏰ 時間", session.time),
        ("📍 地點", session.location),
    ]

    cols = st.columns(3)
    for col, (label, value) in zip(cols, info_items):
        with col:
            st.markdown(html_block(f"""
                <div style="
                    background: #16213e;
                    padding: 16px;
                    border-radius: 12px;
                    border: 1px solid #2d3748;
                ">
                    <div style="
                        color: #94a3b8;
                        font-size: 12px;
                        margin-bottom: 4px;
                    ">
                        {label}
                    </div>
                    <div style="
                        color: #f1f5f9;
                        font-size: 16px;
                        font-weight: 600;
                    ">
                        {value}
                    </div>
                </div>
            """), unsafe_allow_html=True)


def _render_tags(session: Session):
    """
    渲染技術標籤。

    Args:
        session: 議程物件
    """
    st.markdown(html_block("""
        <h3 style="
            color: #cbd5e1;
            font-size: 20px;
            font-weight: 600;
            margin-top: 32px;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 2px solid #334155;
        ">
            🏷️ 技術標籤
        </h3>
    """), unsafe_allow_html=True)

    tags_html = " ".join([
        f"""<span style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 500;
            display: inline-block;
            margin-right: 8px;
            margin-bottom: 8px;
        ">#{tag}</span>"""
        for tag in session.tags
    ])

    st.markdown(f'<div>{tags_html}</div>', unsafe_allow_html=True)


def _render_learning_outcomes(session: Session):
    """
    渲染學習成果。

    Args:
        session: 議程物件
    """
    st.markdown(html_block("""
        <h3 style="
            color: #cbd5e1;
            font-size: 20px;
            font-weight: 600;
            margin-top: 32px;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 2px solid #334155;
        ">
            🎯 學習成果
        </h3>
    """), unsafe_allow_html=True)

    st.markdown(html_block(f"""
        <div style="
            background: #16213e;
            padding: 20px;
            border-radius: 12px;
            border-left: 4px solid #a855f7;
            color: #cbd5e1;
            font-size: 15px;
            line-height: 1.8;
        ">
            {session.learning_outcomes}
        </div>
    """), unsafe_allow_html=True)


def _render_registration_status(session: Session):
    """
    渲染報名狀態與按鈕。

    Args:
        session: 議程物件
    """
    st.markdown(html_block("""
        <h3 style="
            color: #cbd5e1;
            font-size: 20px;
            font-weight: 600;
            margin-top: 32px;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 2px solid #334155;
        ">
            📊 報名狀態
        </h3>
    """), unsafe_allow_html=True)

    # 計算報名資訊
    registration_pct = session.registration_percentage()
    status = session.status()

    # 狀態樣式
    status_config = {
        "available": {
            "icon": "🟢",
            "text": "開放報名",
            "color": "#10b981",
            "button_color": "#059669"
        },
        "full": {
            "icon": "🔴",
            "text": "已額滿",
            "color": "#ef4444",
            "button_color": "#9ca3af"
        },
        "expired": {
            "icon": "⏰",
            "text": "已過期",
            "color": "#6b7280",
            "button_color": "#9ca3af"
        }
    }

    config = status_config.get(status, status_config["available"])

    # 報名進度卡片
    st.markdown(html_block(f"""
        <div style="
            background: #16213e;
            padding: 24px;
            border-radius: 12px;
            border: 1px solid #2d3748;
        ">
            <div style="
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 16px;
            ">
                <div style="
                    color: {config['color']};
                    font-size: 18px;
                    font-weight: 600;
                ">
                    {config['icon']} {config['text']}
                </div>
                <div style="
                    color: #f1f5f9;
                    font-size: 24px;
                    font-weight: 700;
                ">
                    {session.registered} / {session.capacity}
                </div>
            </div>

            <!-- 進度條 -->
            <div style="
                width: 100%;
                height: 12px;
                background: #334155;
                border-radius: 6px;
                overflow: hidden;
                margin-bottom: 8px;
            ">
                <div style="
                    width: {registration_pct}%;
                    height: 100%;
                    background: linear-gradient(90deg, #06b6d4, #8b5cf6);
                    transition: width 0.3s;
                "></div>
            </div>

            <div style="
                color: #94a3b8;
                font-size: 14px;
                text-align: right;
            ">
                {registration_pct:.1f}% 已報名
            </div>
        </div>
    """), unsafe_allow_html=True)

    # 報名按鈕
    st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)

    if status == "available":
        if st.button(
            "🎫 立即報名",
            key="register_button",
            use_container_width=True,
            type="primary"
        ):
            # 執行報名
            success, message = register_for_session(session.id)

            if success:
                st.success(message)
                st.balloons()
                # 重新載入頁面以更新資料
                st.rerun()
            else:
                st.error(message)

    elif status == "full":
        st.button(
            "🔴 已額滿",
            key="full_button",
            use_container_width=True,
            disabled=True
        )

    else:  # expired
        st.button(
            "⏰ 已過期",
            key="expired_button",
            use_container_width=True,
            disabled=True
        )


def render_session_detail(session_id: str):
    """
    渲染議程詳情頁面。

    Args:
        session_id: 議程 ID
    """
    # 取得議程資料
    session = get_session_by_id(session_id)

    if session is None:
        st.error(f"找不到議程：{session_id}")

        if st.button("⬅️ 返回議程列表"):
            st.session_state.current_page = "dashboard"
            st.session_state.selected_session_id = None
            st.rerun()

        return

    # 返回按鈕
    if st.button("⬅️ 返回議程列表", key="back_button"):
        st.session_state.current_page = "dashboard"
        st.session_state.selected_session_id = None
        st.rerun()

    st.markdown("<div style='margin-bottom: 32px;'></div>", unsafe_allow_html=True)

    # 渲染各個區塊
    _render_session_info(session)
    _render_speaker_info(session)
    _render_tags(session)
    _render_learning_outcomes(session)
    _render_registration_status(session)
