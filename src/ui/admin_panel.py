"""Admin panel UI component for session management."""
import logging
import re
import traceback
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from src.services.admin_service import (
    login_admin,
    logout_admin,
    is_admin_authenticated
)
from src.services.session_service import (
    get_all_sessions,
    get_session_by_id,
    create_session,
    update_session,
    delete_session,
)
from src.utils.exceptions import SessionNotFoundError
from src.ui.html_utils import html_block


logger = logging.getLogger(__name__)

SPEAKER_PHOTO_DIR = Path("resource/speaker-photo")
SESSION_INTRO_PHOTO_DIR = Path("resource/session_intro_pic")
ALLOWED_PHOTO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif"}


def _show_admin_exception(error: Exception, context: str) -> None:
    """Display error details in UI and log full traceback."""
    logger.exception("Admin panel error during %s", context)

    st.error(f"❌ {context}失敗：{error}")
    with st.expander("🔍 錯誤詳情", expanded=isinstance(error, RecursionError)):
        st.code("".join(traceback.format_exception(type(error), error, error.__traceback__)))


def _scroll_to(element_id: str) -> None:
    """Scroll to the element with the given ID using smooth scrolling."""
    components.html(
        f"""
        <script>
        const target = parent.document.getElementById('{element_id}');
        if (target) {{
            target.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
        }}
        </script>
        """,
        height=0,
    )


def _sanitize_filename(name: str) -> str:
    """Generate a safe filename fragment from speaker name."""
    sanitized = re.sub(r"[^A-Za-z0-9_-]+", "_", name.strip())
    sanitized = sanitized.strip("_").lower()
    return sanitized or "speaker"


def _save_speaker_photo(uploaded_file: object, speaker_name: str) -> str:
    """Persist uploaded speaker photo and return relative path."""
    if uploaded_file is None:
        raise ValueError("請上傳講者照片")

    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix not in ALLOWED_PHOTO_EXTENSIONS:
        raise ValueError("不支援的圖片格式，請上傳 png/jpg/jpeg/gif 檔案")

    SPEAKER_PHOTO_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"{_sanitize_filename(speaker_name)}_{int(datetime.now().timestamp())}{suffix}"
    file_path = SPEAKER_PHOTO_DIR / filename

    try:
        file_path.write_bytes(uploaded_file.getbuffer())
    except Exception as error:  # pragma: no cover - filesystem issues
        raise ValueError(f"無法儲存講者照片：{error}") from error

    return str(file_path)


def _save_session_intro_photo(uploaded_file: object, session_title: str) -> str:
    """Persist uploaded session intro photo and return relative path."""
    if uploaded_file is None:
        raise ValueError("請上傳課程照片")

    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix not in ALLOWED_PHOTO_EXTENSIONS:
        raise ValueError("不支援的圖片格式，請上傳 png/jpg/jpeg/gif 檔案")

    SESSION_INTRO_PHOTO_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"{_sanitize_filename(session_title)}_{int(datetime.now().timestamp())}{suffix}"
    file_path = SESSION_INTRO_PHOTO_DIR / filename

    try:
        file_path.write_bytes(uploaded_file.getbuffer())
    except Exception as error:
        raise ValueError(f"無法儲存課程照片：{error}") from error

    return str(file_path)


def _get_existing_session_intro_photos() -> list[Path]:
    """Get list of existing session intro photos in the photo directory."""
    if not SESSION_INTRO_PHOTO_DIR.exists():
        return []
    
    photos = []
    for ext in ALLOWED_PHOTO_EXTENSIONS:
        photos.extend(SESSION_INTRO_PHOTO_DIR.glob(f"*{ext}"))
    
    return sorted(photos, key=lambda p: p.stat().st_mtime, reverse=True)


def _get_existing_speaker_photos() -> list[Path]:
    """Get list of existing speaker photos in the photo directory."""
    if not SPEAKER_PHOTO_DIR.exists():
        return []
    
    photos = []
    for ext in ALLOWED_PHOTO_EXTENSIONS:
        photos.extend(SPEAKER_PHOTO_DIR.glob(f"*{ext}"))
    
    return sorted(photos, key=lambda p: p.stat().st_mtime, reverse=True)


def _render_speaker_photo_selector(
    prefix: str,
    current_photo: str = None,
    speaker_name: str = ""
) -> tuple[str, object]:
    """
    Render speaker photo selection UI with two modes: select existing or upload new.
    
    Args:
        prefix: Unique prefix for widget keys
        current_photo: Current photo path (optional)
        speaker_name: Speaker name for generating filename
        
    Returns:
        Tuple of (photo_mode, photo_path_or_upload)
        - photo_mode: "existing" or "upload"
        - photo_path_or_upload: Path string if existing, UploadedFile if upload
    """
    existing_photos = _get_existing_speaker_photos()
    
    st.markdown("#### 📸 講者照片")
    
    if current_photo:
        st.caption(f"目前照片：`{current_photo}`")
    
    photo_mode = st.radio(
        "選擇照片方式",
        options=["從現有圖片選擇", "上傳新圖片"],
        key=f"{prefix}_photo_mode",
        horizontal=True,
    )
    
    if photo_mode == "從現有圖片選擇":
        if not existing_photos:
            st.warning("⚠️ 目前沒有可用的講者照片，請選擇上傳新圖片")
            return "upload", None
        
        # Display photo gallery
        photo_options = {str(p): p.name for p in existing_photos}
        
        # Dropdown selection
        selected_dropdown = st.selectbox(
            "選擇現有照片",
            options=list(photo_options.keys()),
            format_func=lambda x: photo_options[x],
            key=f"{prefix}_photo_dropdown",
        )
        
        # Preview selected photo
        if selected_dropdown:
            col1, col2 = st.columns([1, 2])
            with col1:
                try:
                    st.image(selected_dropdown, caption="預覽", width='stretch')
                except Exception:
                    st.error("無法載入預覽")
            with col2:
                st.info(f"✓ 已選擇：{photo_options[selected_dropdown]}")
        
        return "existing", selected_dropdown
    
    else:  # Upload new
        uploaded = st.file_uploader(
            "上傳講者照片",
            type=["png", "jpg", "jpeg", "gif"],
            key=f"{prefix}_photo_upload",
            help="支援 PNG、JPG、JPEG、GIF 格式，建議檔案大小 < 10MB"
        )
        
        if uploaded:
            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(uploaded, caption="預覽", width='stretch')
            with col2:
                st.success(f"✓ 已上傳：{uploaded.name}")
        
        return "upload", uploaded


def _render_session_intro_photo_selector(
    prefix: str,
    current_photo: str = None,
    session_title: str = ""
) -> tuple[str, object]:
    """
    Render session intro photo selection UI (optional field).
    
    Args:
        prefix: Unique prefix for widget keys
        current_photo: Current photo path (optional)
        session_title: Session title for generating filename
        
    Returns:
        Tuple of (photo_mode, photo_path_or_upload)
        - photo_mode: "keep", "none", "existing" or "upload"
        - photo_path_or_upload: current path, None, Path string if existing, UploadedFile if upload
    """
    existing_photos = _get_existing_session_intro_photos()
    
    st.markdown("#### 🖼️ 課程簡介照片（選填）")
    
    if current_photo:
        photo_path = Path(current_photo.replace("\\", "/"))
        st.caption(f"目前照片：`{photo_path.name}`")
        col1, col2 = st.columns([1, 3])
        with col1:
            try:
                if photo_path.exists():
                    st.image(str(photo_path), caption="目前照片", width=150)
            except Exception:
                pass
    
    if current_photo:
        photo_options = ["保留目前照片", "不使用照片", "從現有圖片選擇", "上傳新圖片"]
        default_index = 0
    else:
        photo_options = ["不使用照片", "從現有圖片選擇", "上傳新圖片"]
        default_index = 0
    
    radio_key = f"{prefix}_intro_photo_mode"
    if radio_key in st.session_state:
        stored_value = st.session_state[radio_key]
        if stored_value in photo_options:
            default_index = photo_options.index(stored_value)
        else:
            default_index = 0
    
    photo_mode = st.radio(
        "選擇照片方式",
        options=photo_options,
        key=radio_key,
        horizontal=True,
        index=default_index,
    )
    
    selected_dropdown = None
    uploaded = None
    
    if existing_photos:
        photo_options_map = {str(p): p.name for p in existing_photos}
        options_list = list(photo_options_map.keys())
        
        dropdown_key = f"{prefix}_intro_photo_dropdown"
        
        default_select_index = 0
        if current_photo:
            current_photo_normalized = current_photo.replace("\\", "/")
            for i, opt in enumerate(options_list):
                if opt.replace("\\", "/") == current_photo_normalized or Path(opt).name == Path(current_photo_normalized).name:
                    default_select_index = i
                    break
        
        if dropdown_key in st.session_state:
            stored_selection = st.session_state[dropdown_key]
            if stored_selection in options_list:
                default_select_index = options_list.index(stored_selection)
        
        selected_dropdown = st.selectbox(
            "選擇現有照片（若選擇「從現有圖片選擇」模式）",
            options=options_list,
            format_func=lambda x: photo_options_map[x],
            key=dropdown_key,
            index=default_select_index,
        )
        
        if selected_dropdown and photo_mode == "從現有圖片選擇":
            col1, col2 = st.columns([1, 2])
            with col1:
                try:
                    st.image(selected_dropdown, caption="選擇的照片預覽", width='stretch')
                except Exception:
                    st.error("無法載入預覽")
            with col2:
                st.caption(f"檔案：{photo_options_map[selected_dropdown]}")
                st.info(f"路徑：{selected_dropdown}")
    elif photo_mode == "從現有圖片選擇":
        st.warning("⚠️ 目前沒有可用的課程照片，請選擇上傳新圖片或不使用照片")
    
    uploaded = st.file_uploader(
        "上傳新課程照片（若選擇「上傳新圖片」模式）",
        type=["png", "jpg", "jpeg", "gif"],
        key=f"{prefix}_intro_photo_upload",
        help="支援 PNG、JPG、JPEG、GIF 格式，建議檔案大小 < 10MB",
    )
    
    if uploaded and photo_mode == "上傳新圖片":
        col1, col2 = st.columns([1, 2])
        with col1:
            st.image(uploaded, caption="新上傳照片預覽", width='stretch')
        with col2:
            st.success(f"✓ 已上傳：{uploaded.name}")
    
    if photo_mode == "保留目前照片":
        return "keep", current_photo
    elif photo_mode == "不使用照片":
        return "none", None
    elif photo_mode == "從現有圖片選擇":
        if not existing_photos:
            return "none", None
        return "existing", selected_dropdown
    else:
        return "upload", uploaded


def _inject_admin_styles():
    """Inject admin panel styles."""
    st.markdown(
        html_block(
            """
            <style>
            .admin-header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 24px 32px;
                border-radius: 16px;
                margin-bottom: 24px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .admin-title {
                color: #ffffff;
                font-size: 28px;
                font-weight: 700;
                margin: 0;
            }
            .admin-subtitle {
                color: rgba(255, 255, 255, 0.85);
                font-size: 14px;
                margin-top: 4px;
            }
            form[data-testid="stForm"][aria-label="admin_login_form"] {
                max-width: 420px;
                margin: 80px auto;
                background: rgba(15, 17, 40, 0.96);
                border-radius: 24px;
                padding: 36px 40px;
                border: 1px solid rgba(148, 163, 184, 0.18);
                box-shadow: 0 24px 55px rgba(15, 17, 40, 0.55);
            }
            form[data-testid="stForm"][aria-label="admin_login_form"] > div:first-child {
                display: flex;
                flex-direction: column;
                gap: 18px;
            }
            .login-title {
                color: #f8fafc;
                font-size: 30px;
                font-weight: 700;
                text-align: center;
                margin-bottom: 8px;
            }
            .login-description {
                color: rgba(203, 213, 225, 0.85);
                font-size: 14px;
                text-align: center;
            }
            .session-table {
                background: rgba(15, 17, 40, 0.92);
                border-radius: 16px;
                padding: 20px;
                margin-top: 16px;
            }
            .session-row {
                display: grid;
                grid-template-columns: 2fr 1fr 1fr 1fr 140px;
                gap: 16px;
                padding: 16px;
                border-bottom: 1px solid rgba(148, 163, 184, 0.12);
                align-items: center;
            }
            .session-row:last-child {
                border-bottom: none;
            }
            .session-row-header {
                font-weight: 700;
                color: #a855f7;
                font-size: 13px;
                text-transform: uppercase;
                letter-spacing: 0.08em;
            }
            .session-cell {
                color: #f8fafc;
                font-size: 14px;
            }
            .session-cell-title {
                font-weight: 600;
                color: #f8fafc;
            }
            .session-cell-meta {
                font-size: 12px;
                color: rgba(148, 163, 184, 0.7);
                margin-top: 4px;
            }
            .session-actions {
                display: flex;
                gap: 8px;
            }
            </style>
            """
        ),
        unsafe_allow_html=True,
    )


def render_login_page():
    """Render admin login page."""
    _inject_admin_styles()

    with st.form("admin_login_form", clear_on_submit=False):
        st.markdown("<h1 class='login-title'>🔐 管理員登入</h1>", unsafe_allow_html=True)
        st.markdown("<div class='login-description'>請輸入管理員帳號與密碼以繼續</div>", unsafe_allow_html=True)

        username = st.text_input("帳號", placeholder="請輸入管理員帳號", key="admin_username_input")
        password = st.text_input("密碼", type="password", placeholder="請輸入密碼", key="admin_password_input")

        submit_col, cancel_col = st.columns(2, gap="small")
        with submit_col:
            submit = st.form_submit_button("登入", width='stretch', type="primary")
        with cancel_col:
            cancel = st.form_submit_button("返回", width='stretch')

        if submit:
            if not username or not password:
                st.error("❌ 請輸入帳號和密碼")
            else:
                success, message = login_admin(username, password)
                if success:
                    st.success(f"✅ {message}")
                else:
                    st.error(f"❌ {message}")

        if cancel:
            st.session_state.current_page = "dashboard"


def render_admin_panel():
    """Render admin management panel."""
    try:
        if not is_admin_authenticated():
            render_login_page()
            return

        _inject_admin_styles()

        feedback = st.session_state.get("admin_feedback")
        if feedback:
            level, message = feedback

            if level == "success":
                st.success(message)
            elif level == "error":
                st.error(message)
            elif level == "warning":
                st.warning(message)
            else:
                st.info(message)

            del st.session_state["admin_feedback"]

        # Header
        st.markdown(
            html_block(
                """
                <div class="admin-header">
                    <div>
                        <h1 class="admin-title">📊 管理員面板</h1>
                        <div class="admin-subtitle">議程管理與設定</div>
                    </div>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )

        # Action buttons
        action_col1, action_col2, action_col3, action_col4 = st.columns([2, 1, 1, 1], gap="small")
        with action_col1:
            st.markdown("### 議程列表")
        with action_col2:
            if st.button("➕ 新增議程", width='stretch'):
                st.session_state.admin_action = "create"
                st.session_state.admin_scroll_target = "create"
        with action_col3:
            if st.button("🏠 返回首頁", width='stretch'):
                st.session_state.current_page = "dashboard"
                st.rerun()
        with action_col4:
            if st.button("🚪 登出", width='stretch'):
                logout_admin()
                st.session_state.current_page = "dashboard"
                st.success("已登出")
                return

        # Session list
        sessions = get_all_sessions()

        if not sessions:
            st.info("📝 目前沒有任何議程")
            return

        # Table header
        st.markdown(
            html_block(
                """
                <div class="session-table">
                    <div class="session-row session-row-header">
                        <div>議程標題</div>
                        <div>日期</div>
                        <div>難度</div>
                        <div>報名狀態</div>
                        <div>操作</div>
                    </div>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )

        # Session rows
        for session in sessions:
            col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1.4], gap="small")

            with col1:
                st.markdown(f"**{session.title}**")
                st.caption(f"{session.time} · {session.location}")

            with col2:
                st.text(session.date)

            with col3:
                level_emoji = {"初": "🔵", "中": "🟣", "高": "🔴"}
                st.text(f"{level_emoji.get(session.level, '')} {session.level}級")

            with col4:
                status = session.status()
                status_emoji = {
                    "available": "✅",
                    "full": "🔴",
                    "expired": "⏰"
                }
                st.text(f"{status_emoji.get(status, '')} {session.registered}/{session.capacity}")

            with col5:
                btn_col1, btn_col2 = st.columns(2, gap="small")
                with btn_col1:
                    if st.button("✏️", key=f"edit_{session.id}", help="編輯"):
                        st.session_state.admin_action = "edit"
                        st.session_state.edit_session_id = session.id
                with btn_col2:
                    if st.button("🗑️", key=f"delete_{session.id}", help="刪除"):
                        st.session_state.admin_action = "delete"
                        st.session_state.delete_session_id = session.id

        # Handle actions
        if st.session_state.get("admin_action") == "create":
            render_create_session_form()
        elif st.session_state.get("admin_action") == "edit":
            render_edit_session_form()
        elif st.session_state.get("admin_action") == "delete":
            render_delete_confirmation()
    except Exception as error:
        _show_admin_exception(error, "載入管理員面板")


def render_create_session_form():
    """Render create session form dialog."""
    st.markdown("<div id='admin-create-session-anchor'></div>", unsafe_allow_html=True)

    if st.session_state.pop("admin_scroll_target", None) == "create":
        _scroll_to("admin-create-session-anchor")

    if "create_form_id" not in st.session_state:
        st.session_state.create_form_id = int(datetime.now().timestamp())
    
    form_id = st.session_state.create_form_id

    st.markdown("---")
    st.markdown("### ➕ 新增議程")

    with st.form("create_session_form", clear_on_submit=False):
        title = st.text_input("議程標題*", placeholder="例：Python 網頁爬蟲入門")
        description = st.text_area("議程描述*", placeholder="詳細說明議程內容...")

        col1, col2 = st.columns(2, gap="small")
        with col1:
            date_mode = st.radio(
                "日期模式",
                options=["具體日期", "TBD"],
                horizontal=True,
                index=0,
                key="create_date_mode"
            )

            date = None
            if date_mode == "具體日期":
                date = st.date_input("日期*", value=datetime.now().date(), key="create_session_date")
            else:
                st.info("日期將設定為 TBD（待定）")

        with col2:
            time_mode = st.radio(
                "時間模式",
                options=["具體時間", "TBD"],
                horizontal=True,
                index=0,
                key="create_time_mode"
            )

            start_time = end_time = None
            if time_mode == "具體時間":
                now = datetime.now()
                default_start = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0).time()
                default_end = (datetime.combine(now.date(), default_start) + timedelta(hours=2)).time()
                start_col, end_col = st.columns(2, gap="small")
                with start_col:
                    start_time = st.time_input("開始時間*", value=default_start, key="create_session_start_time")
                with end_col:
                    end_time = st.time_input("結束時間*", value=default_end, key="create_session_end_time")

        registration_start_date = st.date_input(
            "開始報名日期",
            value=None,
            help="留空表示建立後立即開放報名",
            key="create_registration_start_date"
        )

        location = st.text_input("地點*", placeholder="例：線上 Zoom 會議室")

        col1, col2 = st.columns(2, gap="small")
        with col1:
            level = st.selectbox("難度*", ["初", "中", "高"])
        with col2:
            capacity = st.number_input("容量*", min_value=1, value=50, step=1)

        tags = st.text_input("標籤*", placeholder="用逗號分隔，例：Python,Web Scraping")
        learning_outcomes = st.text_area("學習成果*", placeholder="學員將學到什麼...")

        intro_photo_mode, intro_photo_data = _render_session_intro_photo_selector(
            prefix=f"create_session_{form_id}",
            current_photo=None,
            session_title=title
        )

        st.markdown("#### 講者資訊")
        speaker_name = st.text_input("講者姓名*")
        
        # Use new photo selector
        photo_mode, photo_data = _render_speaker_photo_selector(
            prefix=f"create_session_{form_id}",
            current_photo=None,
            speaker_name=speaker_name
        )
        
        speaker_bio = st.text_area("講者簡介*")

        col1, col2 = st.columns(2, gap="small")
        with col1:
            submit = st.form_submit_button("✅ 建立", type="primary", width='stretch')
        with col2:
            cancel = st.form_submit_button("❌ 取消", width='stretch')

        if submit:
            tags_list = [tag.strip() for tag in tags.split(",") if tag.strip()]

            # Handle date mode
            if date_mode == "具體日期":
                date_value = date.isoformat()
            else:
                date_value = "TBD"

            if time_mode == "具體時間":
                if end_time <= start_time:
                    st.error("❌ 結束時間必須晚於開始時間")
                    return
                time_value = f"{start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}"
            else:
                time_value = "TBD"

            # Validate registration start date
            from src.utils.validation import validate_registration_start_date

            registration_start_date_str = None
            if registration_start_date:
                registration_start_date_str = registration_start_date.isoformat()
                is_valid, error_msg = validate_registration_start_date(
                    registration_start_date_str,
                    date_value
                )
                if not is_valid:
                    st.error(f"❌ {error_msg}")
                    return

            # Prepare speaker name
            speaker_name_value = speaker_name.strip()
            
            # Handle photo based on mode
            if photo_mode == "existing":
                if not photo_data:
                    st.error("❌ 請選擇講者照片")
                    return
                photo_path = photo_data
            else:  # upload
                if photo_data is None:
                    st.error("❌ 請上傳講者照片")
                    return

                try:
                    photo_path = _save_speaker_photo(photo_data, speaker_name_value or "speaker")
                except ValueError as error:
                    st.error(f"❌ 上傳失敗：{error}")
                    return

            intro_photo_path = None
            if intro_photo_mode == "existing":
                intro_photo_path = intro_photo_data
            elif intro_photo_mode == "upload" and intro_photo_data is not None:
                try:
                    intro_photo_path = _save_session_intro_photo(
                        intro_photo_data, title.strip() or "session"
                    )
                except ValueError as error:
                    st.error(f"❌ 課程照片上傳失敗：{error}")
                    return

            session_payload = {
                "title": title.strip(),
                "description": description.strip(),
                "date": date_value,
                "time": time_value,
                "location": location.strip(),
                "level": level,
                "tags": tags_list,
                "learning_outcomes": learning_outcomes.strip(),
                "capacity": int(capacity),
                "speaker": {
                    "name": speaker_name_value,
                    "photo": photo_path,
                    "bio": speaker_bio.strip(),
                },
                "registration_start_date": registration_start_date_str,
                "intro_photo": intro_photo_path,
            }

            try:
                new_session_id = create_session(session_payload)
            except ValueError as error:
                st.error(f"❌ 建立失敗：{error}")
            except Exception as error:  # pragma: no cover - defensive logging for Streamlit UI
                _show_admin_exception(error, "建立議程")
            else:
                st.session_state.admin_feedback = (
                    "success",
                    f"✅ 議程已建立（ID: {new_session_id}）",
                )
                st.session_state.admin_action = None
                if "create_form_id" in st.session_state:
                    del st.session_state.create_form_id

        if cancel:
            del st.session_state.admin_action
            if "create_form_id" in st.session_state:
                del st.session_state.create_form_id


def render_edit_session_form():
    """Render edit session form dialog."""
    st.markdown("---")
    st.markdown("### ✏️ 編輯議程")
    session_id = st.session_state.get("edit_session_id")

    if not session_id:
        st.error("❌ 找不到要編輯的議程 ID")
        if st.button("返回列表"):
            st.session_state.admin_action = None
        return

    session = get_session_by_id(session_id)
    if session is None:
        st.error("❌ 找不到指定的議程")
        if st.button("返回列表"):
            st.session_state.admin_action = None
            st.session_state.edit_session_id = None
        return

    # Determine default date mode
    is_date_tbd = session.date.upper() == "TBD"
    default_date = None
    if not is_date_tbd:
        try:
            default_date = datetime.strptime(session.date, "%Y-%m-%d").date()
        except ValueError:
            default_date = datetime.now().date()

    tags_default = ", ".join(session.tags)

    with st.form("edit_session_form", clear_on_submit=False):
        title = st.text_input("議程標題*", value=session.title)
        description = st.text_area("議程描述*", value=session.description)

        col1, col2 = st.columns(2, gap="small")
        with col1:
            date_mode = st.radio(
                "日期模式",
                options=["具體日期", "TBD"],
                horizontal=True,
                index=0 if not is_date_tbd else 1,
                key=f"edit_date_mode_{session_id}"
            )

            date = None
            if date_mode == "具體日期":
                date = st.date_input(
                    "日期*",
                    value=default_date or datetime.now().date(),
                    key=f"edit_session_date_{session_id}"
                )
            else:
                st.info("日期將設定為 TBD（待定）")

        with col2:
            time_mode = st.radio(
                "時間模式",
                options=["具體時間", "TBD"],
                horizontal=True,
                index=0 if session.time != "TBD" else 1,
                key=f"edit_time_mode_{session_id}"
            )

            start_time = end_time = None
            if time_mode == "具體時間":
                try:
                    start_str, end_str = [part.strip() for part in session.time.split("-")]
                    start_default = datetime.strptime(start_str, "%H:%M").time()
                    end_default = datetime.strptime(end_str, "%H:%M").time()
                except (ValueError, AttributeError):
                    start_default = datetime.now().replace(minute=0, second=0, microsecond=0).time()
                    end_default = (datetime.combine(datetime.now().date(), start_default) + timedelta(hours=2)).time()
                start_col, end_col = st.columns(2, gap="small")
                with start_col:
                    start_time = st.time_input(
                        "開始時間*",
                        value=start_default,
                        key=f"edit_session_start_{session_id}"
                    )
                with end_col:
                    end_time = st.time_input(
                        "結束時間*",
                        value=end_default,
                        key=f"edit_session_end_{session_id}"
                    )

        default_reg_start_date = None
        if session.registration_start_date:
            try:
                default_reg_start_date = datetime.strptime(session.registration_start_date, "%Y-%m-%d").date()
            except (ValueError, AttributeError):
                pass

        registration_start_date = st.date_input(
            "開始報名日期",
            value=default_reg_start_date,
            help="留空表示立即開放報名",
            key=f"edit_registration_start_date_{session_id}"
        )

        location = st.text_input("地點*", value=session.location)

        col1, col2 = st.columns(2, gap="small")
        with col1:
            level = st.selectbox("難度*", ["初", "中", "高"], index=["初", "中", "高"].index(session.level))
        with col2:
            capacity = st.number_input("容量*", min_value=1, value=session.capacity, step=1)

        tags = st.text_input("標籤*", value=tags_default)
        learning_outcomes = st.text_area("學習成果*", value=session.learning_outcomes)

        intro_photo_mode, intro_photo_data = _render_session_intro_photo_selector(
            prefix=f"edit_session_{session_id}",
            current_photo=session.intro_photo,
            session_title=title
        )

        st.markdown("#### 講者資訊")
        speaker_name = st.text_input("講者姓名*", value=session.speaker.name)
        
        # Use new photo selector
        photo_mode, photo_data = _render_speaker_photo_selector(
            prefix=f"edit_session_{session_id}",
            current_photo=session.speaker.photo,
            speaker_name=speaker_name
        )
        
        speaker_bio = st.text_area("講者簡介*", value=session.speaker.bio)

        col1, col2 = st.columns(2, gap="small")
        with col1:
            submit = st.form_submit_button("💾 儲存變更", type="primary", width='stretch')
        with col2:
            cancel = st.form_submit_button("❌ 取消", width='stretch')

        if submit:
            tags_list = [tag.strip() for tag in tags.split(",") if tag.strip()]

            # Handle date mode
            if date_mode == "具體日期":
                date_value = date.isoformat()
            else:
                date_value = "TBD"

            if time_mode == "具體時間":
                if end_time <= start_time:
                    st.error("❌ 結束時間必須晚於開始時間")
                    return
                time_value = f"{start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}"
            else:
                time_value = "TBD"

            # Validate registration start date
            from src.utils.validation import validate_registration_start_date

            registration_start_date_str = None
            if registration_start_date:
                registration_start_date_str = registration_start_date.isoformat()
                is_valid, error_msg = validate_registration_start_date(
                    registration_start_date_str,
                    date_value
                )
                if not is_valid:
                    st.error(f"❌ {error_msg}")
                    return

            # Handle photo based on mode
            photo_path = session.speaker.photo  # Keep current by default
            
            if photo_mode == "existing":
                if photo_data:
                    photo_path = photo_data
            else:  # upload
                if photo_data is not None:
                    try:
                        photo_path = _save_speaker_photo(photo_data, speaker_name.strip() or "speaker")
                    except ValueError as error:
                        st.error(f"❌ 上傳失敗：{error}")
                        return

            intro_photo_path = session.intro_photo
            if intro_photo_mode == "keep":
                intro_photo_path = session.intro_photo
            elif intro_photo_mode == "none":
                intro_photo_path = None
            elif intro_photo_mode == "existing":
                if intro_photo_data:
                    intro_photo_path = intro_photo_data
                else:
                    intro_photo_path = session.intro_photo
            elif intro_photo_mode == "upload":
                if intro_photo_data is not None:
                    try:
                        intro_photo_path = _save_session_intro_photo(
                            intro_photo_data, title.strip() or "session"
                        )
                    except ValueError as error:
                        st.error(f"❌ 課程照片上傳失敗：{error}")
                        return
                else:
                    intro_photo_path = session.intro_photo

            updates = {
                "title": title.strip(),
                "description": description.strip(),
                "date": date_value,
                "time": time_value,
                "location": location.strip(),
                "level": level,
                "tags": tags_list,
                "learning_outcomes": learning_outcomes.strip(),
                "capacity": int(capacity),
                "speaker": {
                    "name": speaker_name.strip(),
                    "photo": photo_path,
                    "bio": speaker_bio.strip(),
                },
                "registration_start_date": registration_start_date_str,
                "intro_photo": intro_photo_path,
            }

            try:
                update_session(session_id, updates)
            except SessionNotFoundError:
                st.error("❌ 找不到此議程，請重新整理列表")
            except ValueError as error:
                st.error(f"❌ 更新失敗：{error}")
            except Exception as error:  # pragma: no cover - defensive logging for Streamlit UI
                _show_admin_exception(error, "更新議程")
            else:
                st.session_state.admin_feedback = (
                    "success",
                    f"✅ 已更新議程（ID: {session_id}）",
                )
                st.session_state.admin_action = None
                st.session_state.edit_session_id = None

        if cancel:
            del st.session_state.admin_action
            if "edit_session_id" in st.session_state:
                del st.session_state.edit_session_id


def render_delete_confirmation():
    """Render delete confirmation dialog as a modal."""
    session_id = st.session_state.get("delete_session_id")

    if not session_id:
        st.session_state.admin_action = None
        return

    session = get_session_by_id(session_id)

    if session is None:
        st.session_state.admin_feedback = ("error", "❌ 找不到要刪除的議程")
        st.session_state.admin_action = None
        st.session_state.pop("delete_session_id", None)
        return

    with st.container():
        st.markdown(
            """
            <div style="
                border: 1px solid rgba(248, 113, 113, 0.45);
                background: rgba(248, 113, 113, 0.1);
                padding: 20px;
                border-radius: 16px;
                margin-top: 16px;
            ">
            """,
            unsafe_allow_html=True,
        )

        st.error("⚠️ 此操作無法復原，確定要刪除這個議程嗎？")
        st.markdown(f"**{session.title}**")
        st.caption(f"{session.date} · {session.time} · {session.location}")

        confirm_col, cancel_col = st.columns(2, gap="small")

        with confirm_col:
            if st.button("✅ 確定刪除", type="primary", width='stretch', key=f"confirm_delete_{session_id}"):
                try:
                    success = delete_session(session_id)
                except Exception as error:  # pragma: no cover - defensive
                    _show_admin_exception(error, "刪除議程")
                    success = False

                if success:
                    st.session_state.admin_feedback = (
                        "success",
                        f"✅ 已刪除議程：{session.title}"
                    )
                else:
                    if "admin_feedback" not in st.session_state:
                        st.session_state.admin_feedback = (
                            "error",
                            "❌ 刪除失敗，請稍後再試"
                        )

                st.session_state.admin_action = None
                st.session_state.pop("delete_session_id", None)
                st.rerun()

        with cancel_col:
            if st.button("❌ 取消", width='stretch', key=f"cancel_delete_{session_id}"):
                st.session_state.admin_action = None
                st.session_state.pop("delete_session_id", None)
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
