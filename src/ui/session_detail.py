"""Session detail page UI component styled to match the dashboard."""

import base64
import re
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st

from src.models.session import Session
from src.services.session_service import get_session_by_id
from src.services.registration_service import register_for_session, remove_registrant
from src.services.admin_service import login_admin, is_admin_authenticated, logout_admin
from src.ui.html_utils import html_block
from src.ui.transcription_widget import (
    render_transcription_widget,
    render_transcription_feed,
    MODEL_COST_CONFIG,
)
from src.ui.transcript_history import render_transcript_history
from src.services.transcript_summarization_service import summarize_latest_transcript

SESSION_MODEL_SELECTIONS: dict[str, str] = {}

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
    "not_open": {"label": "尚未開放", "color": "#fbbf24"},
}


def _get_image_base64(image_path: str) -> str:
    """
    Convert image file to base64 data URI.
    
    Args:
        image_path: Path to image file
        
    Returns:
        Base64 data URI string, or empty string if file doesn't exist
    """
    try:
        file_path = Path(image_path)
        if not file_path.exists():
            return ""
        
        with open(file_path, "rb") as f:
            image_data = f.read()
        
        # Determine MIME type from extension
        ext = file_path.suffix.lower()
        mime_type = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }.get(ext, "image/jpeg")
        
        # Encode to base64
        b64_data = base64.b64encode(image_data).decode("utf-8")
        return f"data:{mime_type};base64,{b64_data}"
    except Exception:
        return ""


def _sanitize_directory_name(value: str) -> str:
    """Return a filesystem-friendly directory name that keeps Chinese characters."""
    cleaned = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", value.strip())
    cleaned = cleaned.strip("_")
    return cleaned or "session"


def _session_transcription_dir(session: Session) -> Path:
    """
    Build the output directory for session recordings/transcripts.

    Args:
        session: Session metadata

    Returns:
        Path pointing to resource/<sanitized-title>
    """
    base_dir = Path("resource")
    session_name = session.title or session.id
    directory_name = _sanitize_directory_name(session_name)
    return base_dir / directory_name


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
            .detail-speaker-photo {
                width: 120px;
                height: 120px;
                border-radius: 50%;
                object-fit: cover;
                border: 3px solid rgba(236, 72, 153, 0.4);
                box-shadow: 0 8px 24px rgba(236, 72, 153, 0.3);
                margin-bottom: 16px;
                display: block;
            }
            .detail-speaker-content {
                display: flex;
                flex-direction: column;
                align-items: center;
                text-align: center;
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
            .registrants-list {
                display: flex;
                flex-direction: column;
                gap: 8px;
                max-height: 400px;
                overflow-y: auto;
                padding: 4px;
            }
            .registrant-item {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 10px 14px;
                background: rgba(99, 102, 241, 0.08);
                border-radius: 12px;
                border: 1px solid rgba(99, 102, 241, 0.15);
                transition: all 0.2s ease;
            }
            .registrant-item:hover {
                background: rgba(99, 102, 241, 0.12);
                border-color: rgba(99, 102, 241, 0.25);
            }
            .registrant-number {
                display: flex;
                align-items: center;
                justify-content: center;
                width: 28px;
                height: 28px;
                border-radius: 50%;
                background: linear-gradient(135deg, #ec4899 0%, #a855f7 100%);
                color: #18122b;
                font-size: 13px;
                font-weight: 700;
                flex-shrink: 0;
            }
            .registrant-name {
                color: #f8fafc;
                font-size: 14px;
                font-weight: 500;
                letter-spacing: 0.02em;
            }
            .registrants-empty {
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                padding: 32px 16px;
                color: rgba(148, 163, 184, 0.6);
                text-align: center;
                font-size: 14px;
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
    photo_path = session.speaker.photo
    
    # Build image HTML if photo path exists
    img_html = ""
    if photo_path:
        # Handle different path formats
        if photo_path.startswith(("http://", "https://")):
            # External URL - use directly
            img_src = photo_path
        elif photo_path.startswith("data:"):
            # Already a data URI - use directly
            img_src = photo_path
        else:
            # Local file path - convert to base64 data URI
            # Normalize path separators
            photo_path = photo_path.replace("\\", "/")
            
            # Try to locate the file
            file_path = Path(photo_path)
            if not file_path.exists():
                # Try common alternative locations
                alternatives = [
                    Path(f"resource/speaker-photo/{file_path.name}"),
                    Path(f"images/speakers/{file_path.name}"),
                ]
                for alt_path in alternatives:
                    if alt_path.exists():
                        file_path = alt_path
                        break
            
            # Convert to base64 data URI
            img_src = _get_image_base64(str(file_path))
        
        if img_src:
            img_html = f'<img src="{img_src}" alt="{session.speaker.name}" class="detail-speaker-photo" />'
        else:
            # Fallback: create initials-based placeholder
            initials = "".join([word[0] for word in session.speaker.name.split()[:2]]).upper()
            img_html = f'''
            <div class="detail-speaker-photo" style="
                display: flex;
                align-items: center;
                justify-content: center;
                background: linear-gradient(135deg, #ec4899 0%, #a855f7 100%);
                color: #18122b;
                font-size: 36px;
                font-weight: 700;
            ">
                {initials}
            </div>
            '''
    
    return html_block(
        f"""
        <div class="detail-section">
            <h4>講者資訊</h4>
            <div class="detail-speaker-content">
                {img_html}
                <div class="detail-speaker-name">{session.speaker.name}</div>
                <div class="detail-speaker-bio">{session.speaker.bio}</div>
            </div>
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


def _detail_registrants_html(session: Session) -> str:
    """Return registrants list HTML."""
    registrants = session.registrants

    if not registrants:
        empty_message = """
        <div class="registrants-empty">
            <div style="font-size: 32px; margin-bottom: 8px;">👥</div>
            <div>目前尚無報名者</div>
        </div>
        """
        return html_block(
            f"""
            <div class="detail-section">
                <h4>報名名單 ({len(registrants)} 人)</h4>
                {empty_message}
            </div>
            """
        )

    # Build registrants list HTML
    registrants_items = []
    for idx, registrant in enumerate(registrants, 1):
        registrants_items.append(
            f"""
            <div class="registrant-item">
                <div class="registrant-number">{idx}</div>
                <div class="registrant-name">{registrant.name}</div>
            </div>
            """
        )

    registrants_html = "".join(registrants_items)

    return html_block(
        f"""
        <div class="detail-section">
            <h4>報名名單 ({len(registrants)} 人)</h4>
            <div class="registrants-list">
                {registrants_html}
            </div>
        </div>
        """
    )


def _render_admin_registrant_controls(session: Session) -> None:
    """Render admin-only registrant management tools."""
    admin_box = st.expander("🔐 管理者報名管理", expanded=False)

    with admin_box:
        if is_admin_authenticated():
            st.success("已驗證管理者身份")

            logout_col, _ = st.columns([1, 4])
            with logout_col:
                if st.button("🚪 登出管理者", key=f"detail_admin_logout_{session.id}"):
                    logout_admin()
                    st.info("已登出管理者")
                    st.rerun()

            st.markdown("---")
            st.markdown(f"目前報名人數：{len(session.registrants)} 人")

            if not session.registrants:
                st.info("尚無報名者可管理")
                return

            for idx, registrant in enumerate(session.registrants):
                row_col1, row_col2 = st.columns([4, 1])
                row_col1.write(f"{idx + 1}. {registrant.name}")
                with row_col2:
                    if st.button("刪除", key=f"remove_registrant_{session.id}_{idx}"):
                        success, message = remove_registrant(session.id, idx)
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
        else:
            st.info("請輸入管理員帳號以管理報名名單")

            with st.form(f"detail_admin_login_form_{session.id}"):
                username = st.text_input("管理員帳號", key=f"detail_admin_username_{session.id}")
                password = st.text_input(
                    "管理員密碼",
                    type="password",
                    key=f"detail_admin_password_{session.id}"
                )
                submit = st.form_submit_button("登入")

                if submit:
                    success, message = login_admin(username, password)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)


def _render_admin_summary_controls(session: Session) -> None:
    """Render admin-only transcript summary generation tools."""
    st.markdown("---")
    st.markdown("#### 📝 AI 課程總結")

    transcription_dir = _session_transcription_dir(session)

    if not is_admin_authenticated():
        st.info("請登入管理員帳號以使用 AI 總結功能")
        return

    st.caption("使用 GPT-5-mini 將最新的逐字稿潤飾為結構化的課程總結")

    # Check if there are any transcript files
    from src.services.transcript_summarization_service import get_latest_transcript

    latest_transcript = get_latest_transcript(transcription_dir)

    if not latest_transcript:
        st.warning("⚠️ 目前沒有逐字稿檔案，請先完成錄音與轉錄")
        return

    st.info(f"📄 最新逐字稿：`{latest_transcript.name}`")

    # Initialize session state for summary results
    summary_state_key = f"summary_result_{session.id}"
    if summary_state_key not in st.session_state:
        st.session_state[summary_state_key] = None

    col1, col2 = st.columns([3, 1])

    with col1:
        if st.button(
            "🤖 生成 AI 課程總結",
            key=f"generate_summary_{session.id}",
            use_container_width=True,
            type="primary"
        ):
            with st.spinner("正在使用 GPT-5-mini 生成課程總結，請稍候..."):
                success, message, summary_path = summarize_latest_transcript(
                    transcription_dir,
                    session_title=session.title,
                    session_description=session.description,
                    session_learning_outcomes=session.learning_outcomes
                )

                # Store result in session state
                st.session_state[summary_state_key] = {
                    "success": success,
                    "message": message,
                    "summary_path": summary_path
                }

    with col2:
        st.caption("模型：GPT-5-mini")

    # Display results from session state (outside button handler)
    if st.session_state[summary_state_key] is not None:
        result = st.session_state[summary_state_key]

        if result["success"]:
            st.success(f"✅ {result['message']}")

            summary_path = result["summary_path"]
            if summary_path and summary_path.exists():
                summary_content = summary_path.read_text(encoding="utf-8")

                with st.expander("📖 查看總結內容", expanded=True):
                    st.markdown(summary_content)

                st.download_button(
                    "📥 下載總結 (Markdown)",
                    data=summary_content.encode("utf-8"),
                    file_name=summary_path.name,
                    mime="text/markdown",
                    use_container_width=True,
                    key=f"download_summary_{session.id}"
                )
        else:
            st.error(f"❌ {result['message']}")

    # Display existing summaries
    if transcription_dir.exists():
        summary_files = sorted(
            transcription_dir.glob("summary-*.md"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        if summary_files:
            st.markdown("##### 📚 歷史總結")

            for idx, summary_file in enumerate(summary_files[:3], 1):
                modified_time = datetime.fromtimestamp(summary_file.stat().st_mtime)
                time_str = modified_time.strftime("%Y-%m-%d %H:%M:%S")

                with st.expander(f"{summary_file.name} · {time_str}", expanded=False):
                    summary_content = summary_file.read_text(encoding="utf-8")
                    st.markdown(summary_content)

                    st.download_button(
                        "📥 下載此總結",
                        data=summary_content.encode("utf-8"),
                        file_name=summary_file.name,
                        mime="text/markdown",
                        use_container_width=True,
                        key=f"download_history_summary_{session.id}_{idx}"
                    )


def render_session_detail(session_id: str):
    """
    Render the session detail page.

    Args:
        session_id: Session identifier
    """
    global SESSION_MODEL_SELECTIONS
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

    admin_logged_in = is_admin_authenticated()
    transcription_dir = _session_transcription_dir(session)
    directory_name = transcription_dir.name

    main_col, side_col = st.columns([1.6, 1], gap="large")

    with main_col:
        st.markdown(_detail_description_html(session), unsafe_allow_html=True)
        st.markdown(_detail_learning_html(session), unsafe_allow_html=True)
        st.markdown(_detail_registrants_html(session), unsafe_allow_html=True)

        _render_admin_registrant_controls(session)

        st.markdown("---")
        st.markdown("#### 逐字稿轉錄")
        st.caption(f"音訊與逐字稿將儲存在 `resource/{directory_name}/`")

        if admin_logged_in:
            model_state_key = f"session_{session.id}_model_choice"
            model_options = list(MODEL_COST_CONFIG.keys())
            stored_model = SESSION_MODEL_SELECTIONS.get(session.id, model_options[0])
            if model_state_key not in st.session_state:
                st.session_state[model_state_key] = stored_model

            selected_model = st.session_state[model_state_key]

            render_transcription_widget(
                prefix=f"session_{session.id}",
                resource_dir=transcription_dir,
                show_header=False,
                title=None,
                caption=None,
                model_name=selected_model,
            )

            with st.container():
                st.selectbox(
                    "選擇轉錄模型",
                    options=model_options,
                    format_func=lambda opt: f"{MODEL_COST_CONFIG.get(opt, {}).get('label', opt)} ({opt})",
                    key=model_state_key,
                )

            SESSION_MODEL_SELECTIONS[session.id] = st.session_state[model_state_key]

            if st.button(
                "🚪 登出管理者",
                key=f"transcription_admin_logout_{session.id}",
                use_container_width=True,
            ):
                logout_admin()
                st.info("已登出管理者")
                st.rerun()

        else:
            st.info("目前僅提供逐字稿檢視與下載，若需啟動或停止錄音請登入管理員帳號。")
            render_transcription_feed(
                prefix=f"session_{session.id}_viewer",
                title="📡 即時逐字稿（唯讀）",
                empty_message="目前沒有進行中的錄音，或錄音尚未啟動。",
                refresh_interval_ms=2500,
                fallback_model=SESSION_MODEL_SELECTIONS.get(session.id, list(MODEL_COST_CONFIG.keys())[0]),
            )

            with st.form(f"transcription_admin_login_form_{session.id}"):
                username = st.text_input(
                    "管理員帳號",
                    key=f"transcription_admin_username_{session.id}",
                )
                password = st.text_input(
                    "管理員密碼",
                    type="password",
                    key=f"transcription_admin_password_{session.id}",
                )
                submit = st.form_submit_button("登入")

                if submit:
                    success, message = login_admin(username, password)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

        render_transcript_history(
            resource_dir=transcription_dir,
            heading="🗂️ 歷史逐字稿",
            description="以下列表以非同步方式載入最近轉錄結果。",
            empty_message="此議程尚未產生逐字稿檔案。",
            max_entries=6,
            key_prefix=f"session_{session.id}",
        )

        _render_admin_summary_controls(session)

    with side_col:
        st.markdown(_detail_speaker_html(session), unsafe_allow_html=True)
        st.markdown(_detail_registration_html(session), unsafe_allow_html=True)

        # Display session URL
        try:
            import socket

            # Get actual IP address
            hostname = socket.gethostname()
            ip_address = socket.gethostbyname(hostname)

            # Try to get port from headers
            host_header = st.context.headers.get("Host", "")
            if ":" in host_header:
                port = host_header.split(":")[-1]
            else:
                port = "8501"

            protocol = st.context.headers.get("X-Forwarded-Proto", "http")
            session_url = f"{protocol}://{ip_address}:{port}/?session_id={session.id}"

            st.markdown(
                f"""
                <div class="detail-section" style="margin-top: 16px;">
                    <h4>課程連結</h4>
                    <input type="text" value="{session_url}" readonly
                           style="width: 100%; padding: 10px; background: rgba(0,0,0,0.3);
                                  border: 1px solid rgba(148, 163, 184, 0.3); border-radius: 8px;
                                  color: #e2e8f0; font-size: 13px; font-family: monospace;"
                           onclick="this.select(); document.execCommand('copy');" />
                    <div style="color: #cbd5e1; font-size: 11px; margin-top: 6px; text-align: center;">
                        點擊上方連結即可複製
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        except Exception:
            pass

        status = session.status()

        st.markdown("<div class='detail-register'>", unsafe_allow_html=True)

        # Registration form
        if status == "available":
            st.markdown("<h4 style='margin-bottom: 12px; color: #f8fafc;'>報名資訊</h4>", unsafe_allow_html=True)
            attendee_name = st.text_input(
                "您的姓名",
                key=f"name_input_{session.id}",
                placeholder="請輸入您的姓名（1-50字元）",
                max_chars=50,
                help="請輸入您的真實姓名以完成報名"
            )

            if st.button(
                "🎫 立即報名",
                key=f"detail_register_{session.id}",
                use_container_width=True,
                disabled=False,
                type="primary"
            ):
                if not attendee_name or not attendee_name.strip():
                    st.error("❌ 請輸入您的姓名")
                else:
                    success, message = register_for_session(session.id, attendee_name)
                    if success:
                        st.success(f"✅ {message}")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
        else:
            # Show disabled button for non-available sessions
            button_label = {
                "full": "🔴 已額滿",
                "expired": "⏰ 已過期",
                "not_open": "🔒 尚未開放",
            }.get(status, "已關閉")

            st.button(
                button_label,
                key=f"detail_register_{session.id}",
                use_container_width=True,
                disabled=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div></div>", unsafe_allow_html=True)
