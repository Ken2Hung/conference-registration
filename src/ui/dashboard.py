"""Dashboard UI component for displaying sessions."""
from itertools import islice
from typing import Iterable, List, Optional

import streamlit as st

from src.models.session import Session
from src.services.session_service import get_all_sessions
from src.ui.html_utils import html_block

LEVEL_STYLES = {
    "初": {
        "label": "初級",
        "badge": "linear-gradient(135deg, #60a5fa 0%, #a855f7 100%)",
        "shadow": "rgba(96, 165, 250, 0.45)",
    },
    "中": {
        "label": "中級",
        "badge": "linear-gradient(135deg, #a855f7 0%, #ec4899 100%)",
        "shadow": "rgba(168, 85, 247, 0.45)",
    },
    "高": {
        "label": "高級",
        "badge": "linear-gradient(135deg, #f97316 0%, #ef4444 100%)",
        "shadow": "rgba(239, 68, 68, 0.45)",
    },
}

STATUS_CONFIG = {
    "available": {"label": "可報名", "color": "#22d3ee"},
    "full": {"label": "已額滿", "color": "#f87171"},
    "expired": {"label": "已過期", "color": "#94a3b8"},
}


def _chunk(items: Iterable[Session], size: int) -> Iterable[List[Session]]:
    """Yield successive chunks from iterable."""
    iterator = iter(items)
    while True:
        batch = list(islice(iterator, size))
        if not batch:
            break
        yield batch


def _session_card_html(session: Session, selected_tag: Optional[str] = None) -> str:
    """產生議程卡片的 HTML。"""
    level_style = LEVEL_STYLES.get(
        session.level,
        {
            "label": "一般",
            "badge": "linear-gradient(135deg, #5eead4 0%, #22d3ee 100%)",
            "shadow": "rgba(34, 211, 238, 0.45)",
        },
    )
    status_style = STATUS_CONFIG.get(session.status(), STATUS_CONFIG["available"])
    progress = session.registration_percentage()

    visible_tags = session.tags[:3]
    tags_html = "".join(
        [
            f'<span class="session-card__tag{" session-card__tag--active" if tag == selected_tag else ""}">#{tag}</span>'
            for tag in visible_tags
        ]
    )

    return html_block(
        f"""
        <div class="session-card" style="box-shadow: 0 20px 40px 0 {level_style['shadow']};">
            <div class="session-card__badge" style="background: {level_style['badge']};">
                <span>{session.level}</span>
            </div>
            <div class="session-card__meta">
                <span>{session.date}</span>
                <span>{session.time}</span>
                <span>{session.location}</span>
            </div>
            <h3 class="session-card__title">{session.title}</h3>
            <div class="session-card__speaker">
                <div class="session-card__speaker-name">{session.speaker.name}</div>
                <div class="session-card__speaker-level">{level_style['label']}</div>
            </div>
            <div class="session-card__progress">
                <div class="session-card__progress-track">
                    <div class="session-card__progress-fill" style="width: {progress}%; background: {level_style['badge']};"></div>
                </div>
                <div class="session-card__progress-text" style="color: {status_style['color']};">
                    {session.registered}/{session.capacity} 人 · {status_style['label']}
                </div>
            </div>
            <div class="session-card__tags">
                {tags_html}
            </div>
        </div>
        """
    )


def _inject_dashboard_styles():
    """注入儀表板專用 CSS。"""
    st.markdown(
        html_block(
            """
            <style>
            .dashboard-heading {
                text-align: center;
                margin-bottom: 14px;
            }
            .dashboard-heading__title {
                font-size: 28px;
                font-weight: 800;
                background: linear-gradient(135deg, #6d28d9 0%, #ec4899 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                margin: 0;
            }
            .dashboard-heading__desc {
                margin-top: 4px;
                color: #cbd5f5;
                letter-spacing: 0.05em;
                font-size: 13px;
            }
            div[data-testid="stRadio"] > div[role="radiogroup"] {
                display: flex;
                flex-wrap: wrap;
                justify-content: center;
                gap: 12px;
                margin-bottom: 8px;
            }
            div[data-testid="stRadio"] input[type="radio"] {
                display: none;
            }
            div[data-testid="stRadio"] > div[role="radiogroup"] > label {
                background: rgba(236, 72, 153, 0.12);
                border-radius: 999px;
                border: 1px solid rgba(236, 72, 153, 0.35);
                padding: 0;
                overflow: hidden;
                transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.2s ease;
            }
            div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(236, 72, 153, 0.18);
            }
            div[data-testid="stRadio"] > div[role="radiogroup"] > label > div:first-child {
                display: none !important;
            }
            div[data-testid="stRadio"] > div[role="radiogroup"] > label > div:last-child {
                padding: 8px 20px;
                font-weight: 600;
                color: #f5d0ff;
                font-size: 14px;
                letter-spacing: 0.03em;
                border-radius: inherit;
            }
            div[data-testid="stRadio"] > div[role="radiogroup"] > label > div[role="radio"] {
                background: transparent;
                border: none;
                border-radius: inherit;
            }
            div[data-testid="stRadio"] > div[role="radiogroup"] > label > div[role="radio"][aria-checked="true"] {
                background: linear-gradient(135deg, #ec4899 0%, #a855f7 100%);
                color: #18122b;
                box-shadow: 0 10px 25px rgba(168, 85, 247, 0.35);
            }
            .dashboard-tags__toggle {
                display: flex;
                justify-content: center;
                margin-top: 6px;
            }
            .dashboard-tags__toggle button {
                background: rgba(236, 72, 153, 0.12) !important;
                border-radius: 999px !important;
                border: 1px solid rgba(236, 72, 153, 0.35) !important;
                color: #f5d0ff !important;
                padding: 6px 18px !important;
                font-weight: 600 !important;
                letter-spacing: 0.05em !important;
            }
            .dashboard-tags__toggle button:hover {
                background: linear-gradient(135deg, #ec4899 0%, #a855f7 100%) !important;
                color: #18122b !important;
            }
            [data-testid="stAppViewContainer"] h1 > a:first-child,
            [data-testid="stAppViewContainer"] h2 > a:first-child,
            [data-testid="stAppViewContainer"] h3 > a:first-child {
                display: none !important;
            }
            .session-card-wrapper {
                position: relative;
                display: block;
                height: 100%;
            }
            .session-card-wrapper:hover .session-card {
                transform: translateY(-3px);
                box-shadow: 0 24px 45px 0 rgba(168, 85, 247, 0.28);
            }
            .session-card-wrapper > div[data-testid="stButton"] {
                position: absolute;
                inset: 0;
                border-radius: 20px;
                margin: 0 !important;
                padding: 0 !important;
                background: transparent !important;
                box-shadow: none !important;
            }
            .session-card-wrapper > div[data-testid="stButton"] button {
                position: absolute;
                inset: 0;
                width: 100%;
                height: 100%;
                opacity: 0;
                cursor: pointer;
                border-radius: 20px;
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
                margin: 0 !important;
                padding: 0 !important;
                color: transparent !important;
            }
            .session-card-wrapper > div[data-testid="stButton"] button:focus-visible {
                outline: 2px solid #a855f7;
            }
            .session-card {
                background: rgba(15, 17, 40, 0.92);
                border-radius: 20px;
                padding: 22px;
                position: relative;
                min-height: 280px;
                display: flex;
                flex-direction: column;
                gap: 16px;
                border: 1px solid rgba(148, 163, 184, 0.18);
                width: 100%;
                transition: transform 0.2s ease, box-shadow 0.2s ease;
                cursor: pointer;
            }
            .session-card:focus-visible {
                outline: 2px solid #a855f7;
            }
            .session-card__badge {
                position: absolute;
                top: -12px;
                left: 22px;
                padding: 8px 14px;
                border-radius: 0 0 12px 12px;
                font-weight: 700;
                letter-spacing: 0.08em;
                color: #161030;
                text-transform: uppercase;
                box-shadow: 0 12px 30px rgba(15,17,40,0.65);
            }
            .session-card__meta {
                display: flex;
                gap: 10px;
                color: #cbd5f5;
                font-size: 13px;
                justify-content: flex-end;
            }
            .session-card__meta span::before {
                content: "•";
                margin-right: 6px;
                color: rgba(148, 163, 184, 0.4);
            }
            .session-card__meta span:first-child::before {
                content: "";
                margin: 0;
            }
            .session-card__title {
                margin: 0;
                font-size: 22px;
                font-weight: 700;
                color: #f8fafc;
                line-height: 1.4;
                min-height: 65px;
            }
            .session-card__speaker {
                display: flex;
                flex-direction: column;
                gap: 4px;
            }
            .session-card__speaker-name {
                font-size: 15px;
                color: #e2e8f0;
                font-weight: 600;
            }
            .session-card__speaker-level {
                color: rgba(148, 163, 184, 0.85);
                font-size: 13px;
                letter-spacing: 0.04em;
            }
            .session-card__progress-track {
                width: 100%;
                height: 8px;
                border-radius: 999px;
                background: rgba(99, 102, 241, 0.2);
                overflow: hidden;
            }
            .session-card__progress-fill {
                height: 100%;
                border-radius: inherit;
                transition: width 0.3s ease;
            }
            .session-card__progress-text {
                text-align: right;
                font-size: 12px;
                margin-top: 8px;
                font-weight: 600;
                letter-spacing: 0.05em;
            }
            .session-card__tags {
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
            }
            .session-card__tag {
                padding: 6px 16px;
                border-radius: 999px;
                background: rgba(148, 163, 184, 0.12);
                color: #e2e8f0;
                font-size: 13px;
                border: 1px solid rgba(148, 163, 184, 0.2);
            }
            .session-card__tag--active {
                background: linear-gradient(135deg, #ec4899 0%, #a855f7 100%);
                color: #1f172d;
                border-color: transparent;
                font-weight: 700;
            }
            </style>
            """
        ),
        unsafe_allow_html=True,
    )


def render_dashboard():
    """渲染主儀表板頁面。"""
    _inject_dashboard_styles()

    st.markdown(html_block("""
        <div class="dashboard-heading">
            <h2 class="dashboard-heading__title">演講類別</h2>
            <div class="dashboard-heading__desc">探索議程主題，找到最適合你的精彩分享</div>
        </div>
    """), unsafe_allow_html=True)

    # 取得所有議程資料
    try:
        sessions = get_all_sessions()
    except Exception as exc:
        st.error(f"載入議程時發生錯誤: {exc}")
        return

    if not sessions:
        st.info("目前尚未建立任何議程。")
        return

    # 建立分類清單
    all_tags = sorted({tag for session in sessions for tag in session.tags})
    categories = ["全選"] + all_tags

    if "dashboard_category" not in st.session_state:
        st.session_state.dashboard_category = "全選"
    if "dashboard_show_all_tags" not in st.session_state:
        st.session_state.dashboard_show_all_tags = False

    try:
        _ = categories.index(st.session_state.dashboard_category)
    except ValueError:
        default_index = 0
        st.session_state.dashboard_category = categories[0]
    else:
        default_index = 0  # will set later after we build visible list

    show_all = st.session_state.dashboard_show_all_tags
    max_visible = 5

    if show_all:
        visible_categories = categories
    else:
        visible_categories = categories[:max_visible]
        selected = st.session_state.dashboard_category
        if selected not in visible_categories and selected in categories:
            visible_categories = categories[: max_visible - 1] + [selected]
        visible_categories = list(dict.fromkeys(visible_categories))

    try:
        default_index = visible_categories.index(st.session_state.dashboard_category)
    except ValueError:
        default_index = 0
        st.session_state.dashboard_category = visible_categories[0]

    selected_category = st.radio(
        "演講類別",
        visible_categories,
        horizontal=True,
        index=default_index,
        key="dashboard_category_radio",
        label_visibility="collapsed",
    )
    st.session_state.dashboard_category = selected_category

    if len(categories) > max_visible:
        toggle_label = "收合" if show_all else "..."
        toggle_cols = st.columns([1, 0.2, 1])
        with toggle_cols[1]:
            st.markdown("<div class='dashboard-tags__toggle'>", unsafe_allow_html=True)
            if st.button(toggle_label, key="dashboard_tags_toggle"):
                st.session_state.dashboard_show_all_tags = not show_all
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    if selected_category == "全選":
        filtered_sessions = sessions
        highlight_tag = None
    else:
        filtered_sessions = [s for s in sessions if selected_category in s.tags]
        highlight_tag = selected_category

    if not filtered_sessions:
        st.warning("該分類目前沒有對應的議程。")
        return

    cards_per_row = 4
    for row in _chunk(filtered_sessions, cards_per_row):
        cols = st.columns(cards_per_row, gap="large")
        for col, session in zip(cols, row):
            with col:
                card_container = st.container()
                card_container.markdown(
                    "<div class='session-card-wrapper'>", unsafe_allow_html=True
                )
                card_container.markdown(
                    _session_card_html(session, selected_tag=highlight_tag),
                    unsafe_allow_html=True,
                )
                if card_container.button(
                    "",
                    key=f"card_click_{session.id}",
                ):
                    st.session_state.selected_session_id = session.id
                    st.session_state.current_page = "detail"
                    st.rerun()
                card_container.markdown("</div>", unsafe_allow_html=True)
