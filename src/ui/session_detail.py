"""Session detail page UI component styled to match the dashboard."""

import streamlit as st

from src.models.session import Session
from src.services.session_service import get_session_by_id, register_for_session
from src.ui.html_utils import html_block

LEVEL_STYLES = {
    "初": {
        "label": "初級",
        "badge": "linear-gradient(135deg, #60a5fa 0%, #a855f7 100%)",
        "shadow": "0 24px 45px rgba(96, 165, 250, 0.28)",
    },
    "中": {
        "label": "中級",
        "badge": "linear-gradient(135deg, #a855f7 0%, #ec4899 100%)",
        "shadow": "0 24px 45px rgba(168, 85, 247, 0.28)",
    },
    "高": {
        "label": "高級",
        "badge": "linear-gradient(135deg, #f97316 0%, #ef4444 100%)",
        "shadow": "0 24px 45px rgba(239, 68, 68, 0.28)",
    },
}

STATUS_CONFIG = {
    "available": {"label": "可報名", "color": "#22d3ee"},
    "full": {"label": "已額滿", "color": "#f87171"},
    "expired": {"label": "已過期", "color": "#94a3b8"},
}


def _inject_detail_styles():
    """Inject detail page specific styles."""
    st.markdown(
        html_block(
            """
            <style>
            .detail-wrapper {
                max-width: 960px;
                margin: 0 auto;
            }
            .detail-card {
                background: rgba(15, 17, 40, 0.96);
                border-radius: 24px;
                padding: 28px 32px;
                border: 1px solid rgba(148, 163, 184, 0.18);
                box-shadow: 0 24px 55px rgba(15, 17, 40, 0.55);
                display: flex;
                flex-direction: column;
                gap: 22px;
            }
            .detail-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 16px;
            }
            .detail-title {
                color: #f8fafc;
                font-size: 28px;
                font-weight: 700;
                margin: 0;
                flex: 1;
            }
            .detail-level {
                padding: 8px 18px;
                border-radius: 999px;
                font-weight: 600;
                letter-spacing: 0.06em;
                color: #18122b;
            }
            .detail-meta {
                display: flex;
                flex-wrap: wrap;
                gap: 12px;
                color: #cbd5f5;
                font-size: 13px;
                letter-spacing: 0.04em;
            }
            .detail-meta span::before {
                content: "•";
                margin-right: 6px;
                color: rgba(148, 163, 184, 0.4);
            }
            .detail-meta span:first-child::before {
                content: "";
                margin: 0;
            }
            .detail-grid {
                display: grid;
                grid-template-columns: minmax(0, 1.6fr) minmax(0, 1fr);
                gap: 22px;
                align-items: start;
            }
            .detail-section {
                background: rgba(39, 44, 74, 0.65);
                border-radius: 18px;
                padding: 18px 20px;
                border: 1px solid rgba(148, 163, 184, 0.18);
            }
            .detail-section h4 {
                margin: 0 0 12px;
                color: #e2e8f0;
                font-size: 15px;
                letter-spacing: 0.05em;
                font-weight: 600;
            }
            .detail-description {
                color: #cbd5e1;
                font-size: 15px;
                line-height: 1.55;
            }
            .detail-tags {
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                margin-top: 12px;
            }
            .detail-tag {
                padding: 6px 16px;
                border-radius: 999px;
                background: rgba(148, 163, 184, 0.12);
                color: #e2e8f0;
                font-size: 12px;
                border: 1px solid rgba(148, 163, 184, 0.2);
            }
            .detail-speaker-name {
                color: #f8fafc;
                font-size: 16px;
                font-weight: 600;
                margin-bottom: 6px;
            }
            .detail-speaker-bio {
                color: #cbd5e1;
                font-size: 13px;
                line-height: 1.5;
            }
            .detail-progress-track {
                width: 100%;
                height: 10px;
                border-radius: 999px;
                background: rgba(99, 102, 241, 0.2);
                overflow: hidden;
                margin-top: 12px;
            }
            .detail-progress-fill {
                height: 100%;
                border-radius: inherit;
                transition: width 0.3s ease;
            }
            .detail-progress-text {
                text-align: right;
                font-size: 12px;
                color: rgba(226, 232, 240, 0.85);
                margin-top: 8px;
                letter-spacing: 0.05em;
            }
            .detail-register {
                display: flex;
                flex-direction: column;
                gap: 12px;
                margin-top: 16px;
            }
            .detail-register button {
                width: 100%;
                border-radius: 999px !important;
                font-weight: 600 !important;
                letter-spacing: 0.08em !important;
                background: linear-gradient(135deg, #ec4899 0%, #a855f7 100%) !important;
                color: #18122b !important;
                border: none !important;
                padding: 12px 0 !important;
            }
            .detail-register button:disabled {
                background: rgba(148, 163, 184, 0.3) !important;
                color: rgba(15, 17, 40, 0.55) !important;
            }
            .detail-back {
                margin-bottom: 12px;
            }
            .detail-back button {
                border-radius: 999px !important;
                background: rgba(236, 72, 153, 0.12) !important;
                color: #f5d0ff !important;
                border: 1px solid rgba(236, 72, 153, 0.35) !important;
                padding: 6px 18px !important;
                font-weight: 600 !important;
            }
            .detail-back button:hover {
                background: linear-gradient(135deg, #ec4899 0%, #a855f7 100%) !important;
                color: #18122b !important;
            }
            </style>
            """
        ),
        unsafe_allow_html=True,
    )


def _detail_header_html(session: Session) -> str:
    """Return header HTML for the detail card."""
    level_style = LEVEL_STYLES.get(session.level, LEVEL_STYLES["初"])
    meta_items = [
        session.date,
        session.time,
        session.location,
    ]

    meta_html = "".join([f"<span>{item}</span>" for item in meta_items])

    return html_block(
        f"""
        <div class="detail-header">
            <h2 class="detail-title">{session.title}</h2>
            <div class="detail-level" style="background: {level_style['badge']}; box-shadow: {level_style['shadow']};">
                {level_style['label']}
            </div>
        </div>
        <div class="detail-meta">
            {meta_html}
        </div>
        """
    )


def _detail_description_html(session: Session) -> str:
    """Return description block HTML."""
    visible_tags = session.tags[:3]
    tags_html = "".join([f'<span class="detail-tag">#{tag}</span>' for tag in visible_tags])

    return html_block(
        f"""
        <div class="detail-section">
            <h4>議程簡介</h4>
            <div class="detail-description">{session.description}</div>
            <div class="detail-tags">{tags_html}</div>
        </div>
        """
    )


def _detail_learning_html(session: Session) -> str:
    """Return learning outcomes block HTML."""
    outcomes = session.learning_outcomes

    return html_block(
        f"""
        <div class="detail-section">
            <h4>學習重點</h4>
            <div class="detail-description">{outcomes}</div>
        </div>
        """
    )


def _detail_speaker_html(session: Session) -> str:
    """Return speaker block HTML."""
    return html_block(
        f"""
        <div class="detail-section">
            <h4>講者資訊</h4>
            <div class="detail-speaker-name">{session.speaker.name}</div>
            <div class="detail-speaker-bio">{session.speaker.bio}</div>
        </div>
        """
    )


def _detail_registration_html(session: Session) -> str:
    """Return registration status HTML."""
    registration_pct = session.registration_percentage()
    status = session.status()
    config = STATUS_CONFIG.get(status, STATUS_CONFIG["available"])

    return html_block(
        f"""
        <div class="detail-section">
            <h4>報名狀態</h4>
            <div style="color: {config['color']}; font-weight: 600; font-size: 15px;">
                {config['label']} · {session.registered}/{session.capacity} 人
            </div>
            <div class="detail-progress-track">
                <div class="detail-progress-fill" style="width: {registration_pct}%; background: linear-gradient(135deg, #ec4899 0%, #a855f7 100%);"></div>
            </div>
            <div class="detail-progress-text">{registration_pct:.1f}% 已報名</div>
        </div>
        """
    )


def render_session_detail(session_id: str):
    """
    Render the session detail page.

    Args:
        session_id: Session identifier
    """
    session = get_session_by_id(session_id)

    if session is None:
        st.error(f"找不到議程：{session_id}")
        if st.button("⬅️ 返回議程列表"):
            st.session_state.current_page = "dashboard"
            st.session_state.selected_session_id = None
            st.rerun()
        return

    _inject_detail_styles()

    back_container = st.container()
    back_container.markdown("<div class='detail-back'>", unsafe_allow_html=True)
    if back_container.button(
        "⬅️ 返回議程列表",
        key="detail_back",
        help="返回列表",
        use_container_width=False,
    ):
        st.session_state.current_page = "dashboard"
        st.session_state.selected_session_id = None
        st.rerun()
    back_container.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='detail-wrapper'>", unsafe_allow_html=True)
    st.markdown("<div class='detail-card'>", unsafe_allow_html=True)
    st.markdown(_detail_header_html(session), unsafe_allow_html=True)

    main_col, side_col = st.columns([1.6, 1], gap="large")

    with main_col:
        st.markdown(_detail_description_html(session), unsafe_allow_html=True)
        st.markdown(_detail_learning_html(session), unsafe_allow_html=True)

    with side_col:
        st.markdown(_detail_speaker_html(session), unsafe_allow_html=True)
        st.markdown(_detail_registration_html(session), unsafe_allow_html=True)

        status = session.status()
        disabled = status != "available"
        button_label = {
            "available": "🎫 立即報名",
            "full": "🔴 已額滿",
            "expired": "⏰ 已過期",
        }.get(status, "🎫 立即報名")

        st.markdown("<div class='detail-register'>", unsafe_allow_html=True)
        if st.button(
            button_label,
            key=f"detail_register_{session.id}",
            use_container_width=True,
            disabled=disabled,
        ):
            success, message = register_for_session(session.id)
            if success:
                st.success(message)
                st.balloons()
                st.rerun()
            else:
                st.error(message)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div></div>", unsafe_allow_html=True)
