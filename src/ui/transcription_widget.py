"""
Reusable Streamlit UI component for real-time voice transcription.

This component powers both the standalone transcription page and session
details where transcription is embedded. It handles the WebRTC microphone
stream, background WAV recording, Whisper API transcription, and stateful
UI updates with configurable prefixes so multiple instances can coexist.
"""

import io
import os
import queue
import threading
import time
import uuid
import wave
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import av
import numpy as np
import streamlit as st
from opencc import OpenCC
from streamlit_webrtc import RTCConfiguration, WebRtcMode, webrtc_streamer

from src.services.audio_service import process_audio_frame, is_voiced_chunk
from src.utils.audio_utils import calculate_rms

SAMPLE_RATE = 48000
SAMPLE_WIDTH = 2  # bytes (int16)
# Multiple STUN servers for better connectivity across different networks
ICE_SERVERS = [
    {"urls": ["stun:stun.l.google.com:19302"]},
    {"urls": ["stun:stun1.l.google.com:19302"]},
    {"urls": ["stun:stun.cloudflare.com:3478"]},
]
AUDIO_GAIN = 2.0  # Volume boost multiplier
TRANSCRIPTION_CHUNK_DURATION = 3.0  # Seconds between transcription calls
VAD_RMS_THRESHOLD = 300.0  # Minimum RMS to consider as speech (filter silence)
TRANSCRIPT_REFRESH_INTERVAL_MS = 1200  # UI polling interval during recording
TRANSCRIPT_REFRESH_INTERVAL_SECONDS = TRANSCRIPT_REFRESH_INTERVAL_MS / 1000.0
VAD_SAMPLE_DENSITY = 0.12  # Minimum proportion of loud samples to treat as speech
VAD_AMPLITUDE_GATE = 1100  # Sample amplitude gate used by density check

MODEL_COST_CONFIG = {
    "whisper-1": {
        "label": "Whisper-1",
        "input_cost_per_min": 0.006,  # USD per audio minute
        "output_cost_per_token": 0.0,
        "output_tokens_per_char": 0.25,  # Approx chars→tokens
    },
    "gpt-4o-mini-transcribe": {
        "label": "GPT-4o Mini-Transcribe",
        "input_cost_per_min": 0.003,  # Approx USD per audio minute
        "output_cost_per_token": 5.0 / 1_000_000,  # USD per token
        "output_tokens_per_char": 0.25,
    },
}

DEFAULT_TITLE = "🎤 即時語音轉錄（Whisper API）"
DEFAULT_CAPTION = "使用 WebRTC 錄音並透過 Whisper API 背景轉錄為逐字稿"

# Initialize OpenCC for Simplified to Traditional Chinese conversion
_opencc_converter = OpenCC("s2t")

# Global state - using token-based system like mic_recorder_page
_recorder_lock = threading.Lock()
_active_token: Optional[str] = None
_audio_queues: dict[str, "queue.Queue"] = {}
_transcription_buffers: dict[str, list] = {}
_transcript_segments: dict[str, list] = {}
_wav_writers: dict[str, wave.Wave_write] = {}
_wav_paths: dict[str, Path] = {}
_bytes_written: dict[str, int] = {}
_last_rms: dict[str, float] = {}
_worker_threads: dict[str, threading.Thread] = {}
_worker_stop_events: dict[str, threading.Event] = {}
_transcription_threads: dict[str, threading.Thread] = {}
_transcription_stop_events: dict[str, threading.Event] = {}
_last_transcription_time: dict[str, float] = {}
_token_models: dict[str, str] = {}
_active_model: Optional[str] = None

# Cache API key check
_api_key_checked = False
_api_key_available = False


@dataclass
class TranscriptionUIConfig:
    """Runtime configuration for transcription UI rendering."""

    prefix: str
    resource_dir: Path
    show_header: bool = True
    title: str = DEFAULT_TITLE
    caption: Optional[str] = DEFAULT_CAPTION
    controls_enabled: bool = True
    controls_disabled_reason: Optional[str] = None
    model_name: str = "whisper-1"


class _SessionState:
    """Wrapper around st.session_state with automatic key prefixing."""

    def __init__(self, prefix: str):
        # Streamlit widget keys cannot contain whitespace
        self.prefix = prefix.replace(" ", "_")

    def key(self, name: str) -> str:
        """Return fully-qualified session key with prefix."""
        return f"{self.prefix}_{name}"

    def ensure(self, name: str, default: Any) -> Any:
        """Ensure a session value exists, returning the stored value."""
        session_key = self.key(name)
        if session_key not in st.session_state:
            st.session_state[session_key] = default
        return st.session_state[session_key]

    def get(self, name: str, default: Any = None) -> Any:
        """Get a prefixed value from session state."""
        return st.session_state.get(self.key(name), default)

    def set(self, name: str, value: Any) -> None:
        """Set a prefixed value in session state."""
        st.session_state[self.key(name)] = value

    def delete(self, name: str) -> None:
        """Delete a prefixed value from session state if it exists."""
        session_key = self.key(name)
        if session_key in st.session_state:
            del st.session_state[session_key]


def _format_transcript_segments(segments: list) -> str:
    """Convert transcript segments into displayable text."""
    formatted_lines: list[str] = []
    for seg in segments:
        if isinstance(seg, dict):
            formatted_lines.append(f"{seg.get('time', '')}  {seg.get('text', '')}")
        else:
            formatted_lines.append(str(seg))
    return "\n".join(formatted_lines)


def _get_model_config(model_name: str) -> dict[str, Any]:
    """Return cost configuration for given model."""
    return MODEL_COST_CONFIG.get(model_name, MODEL_COST_CONFIG["whisper-1"])


def _audio_minutes_from_bytes(byte_count: int) -> float:
    """Convert byte count to minutes based on mono int16 PCM."""
    if byte_count <= 0:
        return 0.0
    frames = byte_count / SAMPLE_WIDTH
    seconds = frames / SAMPLE_RATE
    return seconds / 60.0


def _estimate_transcription_cost(
    model_name: str,
    *,
    audio_minutes: float,
    transcript_text: str,
) -> dict[str, float]:
    """Estimate transcription cost based on audio duration and text length."""
    config = _get_model_config(model_name)
    input_cost = float(audio_minutes) * float(config.get("input_cost_per_min", 0.0))

    char_count = len(transcript_text or "")
    tokens_per_char = float(config.get("output_tokens_per_char", 0.0))
    output_tokens = char_count * tokens_per_char
    output_cost = output_tokens * float(config.get("output_cost_per_token", 0.0))

    total_cost = input_cost + output_cost

    return {
        "total": total_cost,
        "input_cost": input_cost,
        "output_cost": output_cost,
        "audio_minutes": audio_minutes,
        "char_count": char_count,
        "output_tokens": output_tokens,
    }


def _format_cost_caption(cost_info: dict[str, float]) -> str:
    """Format cost info into a human friendly caption."""
    total = cost_info["total"]
    input_cost = cost_info["input_cost"]
    output_cost = cost_info["output_cost"]
    minutes = cost_info["audio_minutes"]
    tokens = int(cost_info["output_tokens"])
    return (
        f"💰 預估費用：${total:.4f} "
        f"(輸入 ${input_cost:.4f} + 輸出 ${output_cost:.4f}) · "
        f"音訊約 {minutes:.2f} 分鐘 · "
        f"輸出約 {tokens:,} tokens"
    )


def _calculate_cost_snapshot(
    token: Optional[str],
    fallback_model: str,
) -> tuple[str, Optional[dict[str, float]], str, int]:
    """
    Return (model_name, cost_info, transcript_text) for the given token.

    Args:
        token: Active recording token.
        fallback_model: Model name to use when token has no explicit mapping.
    """
    if not token:
        return fallback_model, None, "", 0

    with _recorder_lock:
        model_name = _token_models.get(token, fallback_model)
        bytes_written = _bytes_written.get(token, 0)
        segments = list(_transcript_segments.get(token, []))

    transcript_text = _format_transcript_segments(segments)
    audio_minutes = _audio_minutes_from_bytes(bytes_written)
    cost_info = _estimate_transcription_cost(
        model_name,
        audio_minutes=audio_minutes,
        transcript_text=transcript_text,
    )
    return model_name, cost_info, transcript_text, len(segments)


def render_transcription_widget(
    *,
    prefix: str,
    resource_dir: Path,
    show_header: bool = True,
    title: str = DEFAULT_TITLE,
    caption: Optional[str] = DEFAULT_CAPTION,
    controls_enabled: bool = True,
    controls_disabled_reason: Optional[str] = None,
    model_name: str = "whisper-1",
) -> None:
    """
    Render the reusable transcription interface.

    Args:
        prefix: Unique key prefix so multiple widgets do not collide.
        resource_dir: Directory where WAV and transcript files are stored.
        show_header: Whether to render the section as a standalone page (title).
        title: Section title.
        caption: Optional caption/subtitle.
        controls_enabled: Enable start/stop buttons when True.
        controls_disabled_reason: Optional message shown when controls disabled.
    """
    config = TranscriptionUIConfig(
        prefix=prefix,
        resource_dir=resource_dir,
        show_header=show_header,
        title=title,
        caption=caption,
        controls_enabled=controls_enabled,
        controls_disabled_reason=controls_disabled_reason,
        model_name=model_name,
    )
    state = _SessionState(config.prefix)
    _render_transcription_ui(config, state)


def _render_transcription_ui(config: TranscriptionUIConfig, state: _SessionState) -> None:
    """Render shared transcription UI with provided config/state."""
    state.ensure("active", False)
    state.ensure("token", None)
    state.ensure("path", "")
    state.ensure("status", "")
    state.ensure("last_transcript", "")
    state.ensure("last_path", "")
    state.ensure("segment_count", 0)
    state.ensure("last_segment_count", 0)
    state.ensure("mic_permission_requested", False)
    state.ensure("model_name", config.model_name)
    state.ensure("last_model_name", config.model_name)
    state.ensure("last_cost", None)
    state.ensure("last_bytes_written", 0)

    if config.show_header:
        st.title(config.title)
        if config.caption:
            st.caption(config.caption)
    else:
        if config.title:
            st.subheader(config.title)
        if config.caption:
            st.caption(config.caption)

    global _api_key_checked, _api_key_available
    if not _api_key_checked:
        _api_key_available = _check_api_key()
        _api_key_checked = True

    if not _api_key_available:
        _render_api_key_input(state)
        return

    _render_controls(config, state)
    _render_webrtc_stream(config, state)
    _render_status(state)
    _render_transcript_display(config, state)


def _check_api_key() -> bool:
    """Check for API key in environment (only once)."""
    if os.getenv("OPENAI_API_KEY"):
        return True

    # Try loading from .env file (only once)
    try:
        from dotenv import load_dotenv

        load_dotenv()
        return bool(os.getenv("OPENAI_API_KEY"))
    except Exception:
        return False


def _render_api_key_input(state: _SessionState) -> None:
    """Render API key input field."""
    st.warning("⚠️ 請先設定 OpenAI API Key")

    api_key = st.text_input(
        "OpenAI API Key",
        type="password",
        help="輸入您的 OpenAI API Key，或設定在 .env 檔案中",
        key=state.key("api_key_input"),
    )

    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
        global _api_key_available
        _api_key_available = True
        st.rerun()


def _render_controls(config: TranscriptionUIConfig, state: _SessionState) -> None:
    """Render control buttons."""
    st.markdown("#### 🎙️ 錄音控制")

    if not config.controls_enabled:
        disabled_msg = config.controls_disabled_reason or "請先取得操作權限後再開始錄音"
        st.warning(disabled_msg)

    col1, col2 = st.columns(2)
    is_active = state.get("active", False)

    with col1:
        if st.button(
            "▶️ 開始錄音",
            type="primary",
            use_container_width=True,
            disabled=is_active or not config.controls_enabled,
            key=state.key("start_button"),
        ):
            if config.controls_enabled:
                _start_recording(state, config)

    with col2:
        if st.button(
            "⏹️ 停止錄音",
            type="secondary",
            use_container_width=True,
            disabled=not is_active,
            key=state.key("stop_button"),
        ):
            _stop_recording(state, config)

    current_status = state.get("status", "")
    if current_status:
        st.info(current_status)


def _render_webrtc_stream(config: TranscriptionUIConfig, state: _SessionState) -> None:
    """Render WebRTC microphone stream."""
    st.markdown("#### 🎙️ 麥克風串流")

    def audio_callback(frame: av.AudioFrame) -> av.AudioFrame:
        global _active_token

        with _recorder_lock:
            token = _active_token

        if not token:
            return frame

        try:
            # Process audio frame with gain
            pcm_array = process_audio_frame(frame, gain=AUDIO_GAIN)
            pcm_bytes = pcm_array.tobytes()

            # Calculate RMS
            rms = float(calculate_rms(pcm_array))

            # Add to audio queue (for WAV writer)
            with _recorder_lock:
                audio_queue = _audio_queues.get(token)
                if audio_queue:
                    try:
                        audio_queue.put_nowait((pcm_bytes, rms))
                    except queue.Full:
                        pass

                # Add to transcription buffer (for Whisper API)
                transcription_buffer = _transcription_buffers.get(token)
                if transcription_buffer is not None:
                    transcription_buffer.append(pcm_array)

        except Exception as exc:
            print(f"[Transcription] Callback error: {exc}")

        return frame

    rtc_configuration = RTCConfiguration({"iceServers": ICE_SERVERS})

    # Use a stable key to prevent creating multiple PeerConnections on rerun
    # Set desired_playing_state based on active state to prevent auto-restart
    is_active = state.get("active", False)

    webrtc_ctx = webrtc_streamer(
        key=state.key("transcription_mic"),
        mode=WebRtcMode.SENDONLY,
        audio_frame_callback=audio_callback,
        media_stream_constraints={"audio": True, "video": False},
        rtc_configuration=rtc_configuration,
        async_processing=True,
        desired_playing_state=is_active,  # Only auto-start when actively recording
    )

    # Update mic permission status
    if not state.get("mic_permission_requested", False):
        if webrtc_ctx.state.playing:
            state.set("mic_permission_requested", True)

    # Show connection status
    if webrtc_ctx.state.playing:
        if state.get("active", False):
            st.success("🎧 麥克風已連線，正在錄音並即時轉錄...")
        else:
            st.info("✅ 麥克風已就緒，點擊「開始錄音」開始錄音")
    elif webrtc_ctx.state.signalling:
        st.warning("🔄 正在建立 WebRTC 連線，請稍候...")
    else:
        st.warning("⚠️ 請允許瀏覽器存取麥克風權限")


def _render_status(state: _SessionState) -> None:
    """Render recording status."""
    st.markdown("#### 📊 錄音狀態")

    token = state.get("token")
    is_active = state.get("active", False)
    current_model = state.get("model_name", "whisper-1")
    run_interval = TRANSCRIPT_REFRESH_INTERVAL_SECONDS if is_active else None
    state_prefix = state.prefix

    @st.fragment(run_every=run_interval)
    def _status_fragment(
        prefix: str,
        token_value: Optional[str],
        model_hint: str,
        active_flag: bool,
    ) -> None:
        fragment_state = _SessionState(prefix)
        bytes_written = 0
        last_rms = 0.0

        if token_value:
            with _recorder_lock:
                bytes_written = _bytes_written.get(token_value, 0)
                last_rms = _last_rms.get(token_value, 0.0)

        path_str = fragment_state.get("path", "")
        if path_str:
            st.write(f"📁 檔案：`{path_str}`")
        else:
            st.write("📁 尚未開始錄音")

        if bytes_written > 0:
            duration_sec = bytes_written / (SAMPLE_RATE * SAMPLE_WIDTH)
            st.write(f"⏱️ 已錄製：{duration_sec:.1f} 秒")
        else:
            st.write("⏱️ 已錄製：0.0 秒")

        st.write(f"🔊 當前 RMS：{last_rms:.1f}")
        st.write(f"🎚️ 採樣率：{SAMPLE_RATE} Hz")
        st.write(f"📈 音量增益：{AUDIO_GAIN}x")

        cost_info = None
        current_fragment_model = fragment_state.get("model_name", model_hint)
        if active_flag and token_value:
            active_model, cost_info, _, _ = _calculate_cost_snapshot(
                token_value,
                current_fragment_model,
            )
            if active_model != current_fragment_model:
                fragment_state.set("model_name", active_model)
                current_fragment_model = active_model

        if cost_info:
            st.write(_format_cost_caption(cost_info))
            fragment_state.set("last_cost", cost_info)
        else:
            last_cost = fragment_state.get("last_cost")
            if last_cost:
                st.write(_format_cost_caption(last_cost))

        if active_flag:
            st.write(f"📝 已轉錄段數：{fragment_state.get('segment_count', 0)}")

    _status_fragment(state_prefix, token, current_model, is_active)


def _render_transcript_display(config: TranscriptionUIConfig, state: _SessionState) -> None:
    """Render transcript display area with st.empty() for smooth updates."""
    st.markdown("#### 📄 即時轉錄結果")

    token = state.get("token")
    is_active = state.get("active", False)
    state_prefix = state.prefix

    # Show real-time transcript during recording
    if is_active and token:
        current_model = state.get("model_name", config.model_name)

        @st.fragment(run_every=TRANSCRIPT_REFRESH_INTERVAL_SECONDS)
        def _live_transcript_fragment(
            prefix: str,
            token_value: str,
            model_value: str,
        ) -> None:
            fragment_state = _SessionState(prefix)
            with _recorder_lock:
                segments = list(_transcript_segments.get(token_value, []))

            segment_count = len(segments)
            last_segment_count = fragment_state.get("last_segment_count", 0)
            has_new_content = segment_count != last_segment_count

            if has_new_content:
                print(
                    "[Transcription UI] New content detected: "
                    f"{segment_count} segments (was {last_segment_count})"
                )
                fragment_state.set("last_segment_count", segment_count)
                fragment_state.set("segment_count", segment_count)

            current_transcript = _format_transcript_segments(segments)
            last_update_time = datetime.now().strftime("%H:%M:%S")

            if current_transcript:
                display_value = current_transcript
                caption_text = (
                    f"📊 已轉錄：{len(current_transcript)} 字元 | "
                    f"分段數：{segment_count} | 更新時間：{last_update_time}"
                )
            else:
                token_preview = token_value[:8] if token_value else "N/A"
                display_value = (
                    f"🎤 等待轉錄結果...\n\n開始時間：{last_update_time}\n"
                    f"Token：{token_preview}\n\n約 3 秒後會出現第一段轉錄結果"
                )
                caption_text = (
                    f"⏳ 等待中... | 已檢查次數："
                    f"{fragment_state.get('segment_count', 0)} | "
                    f"更新時間：{last_update_time}"
                )

            display_key = fragment_state.key("transcript_display_live")
            st.session_state[display_key] = display_value
            st.text_area(
                f"即時逐字稿 (最後更新：{last_update_time})",
                value=display_value,
                height=300,
                help="格式：yyyy-mm-dd hh:mi:ss + 逐字稿內容 | 自動檢測更新",
                key=display_key,
            )
            st.caption(caption_text)

            snapshot_model, live_cost, _, _ = _calculate_cost_snapshot(
                token_value,
                fragment_state.get("model_name", model_value),
            )
            if snapshot_model != fragment_state.get("model_name", model_value):
                fragment_state.set("model_name", snapshot_model)

            if live_cost:
                st.caption(_format_cost_caption(live_cost))

        _live_transcript_fragment(state_prefix, token, current_model)

    # Show final transcript after recording stopped
    elif state.get("last_transcript"):
        last_transcript = state.get("last_transcript", "")
        last_model_name = state.get("last_model_name", state.get("model_name", "whisper-1"))
        cost_info = state.get("last_cost")
        if not cost_info:
            audio_minutes = _audio_minutes_from_bytes(state.get("last_bytes_written", 0))
            cost_info = _estimate_transcription_cost(
                last_model_name,
                audio_minutes=audio_minutes,
                transcript_text=last_transcript,
            )

        st.text_area(
            "完整逐字稿",
            value=last_transcript,
            height=300,
            help="格式：yyyy-mm-dd hh:mi:ss + 逐字稿內容",
        )

        st.caption(f"📊 字數：{len(last_transcript)} 字元")
        if cost_info:
            st.caption(_format_cost_caption(cost_info))

        last_path = state.get("last_path", "")
        if last_path:
            st.caption(f"💾 已保存至：`{last_path}`")

            st.download_button(
                label="📥 下載逐字稿",
                data=state.get("last_transcript", "").encode("utf-8"),
                file_name=Path(last_path).name,
                mime="text/plain",
                use_container_width=True,
                key=state.key("download_button"),
            )
    else:
        st.info("點擊「開始錄音」後，即時轉錄結果將顯示在此處")


def render_transcription_feed(
    *,
    prefix: str,
    title: str = "📄 即時逐字稿（唯讀）",
    empty_message: str = "目前沒有進行中的錄音",
    height: int = 300,
    refresh_interval_ms: int = TRANSCRIPT_REFRESH_INTERVAL_MS,
    fallback_model: Optional[str] = None,
) -> None:
    """
    Render a read-only view of the active transcription buffer.

    Intended for non-admin viewers who should not control recording but can
    observe the ongoing transcript.
    """
    st.markdown(f"#### {title}")

    run_every = refresh_interval_ms / 1000.0 if refresh_interval_ms else None

    @st.fragment(run_every=run_every)
    def _feed_fragment(
        fragment_prefix: str,
        empty_text: str,
        textarea_height: int,
        fallback: Optional[str],
    ) -> None:
        with _recorder_lock:
            token = _active_token
            active_model = _active_model

        current_fallback = fallback or active_model or "whisper-1"

        if not token:
            st.info(empty_text)
            return

        model_name, cost_info, transcript_text, segment_count = _calculate_cost_snapshot(
            token,
            current_fallback,
        )

        last_update_time = datetime.now().strftime("%H:%M:%S")
        token_preview = token[:8] if token else "N/A"

        if transcript_text:
            caption_text = (
                f"📊 段數：{segment_count} | "
                f"字元：{len(transcript_text)} | "
                f"更新時間：{last_update_time} | Token：{token_preview}"
            )
            display_value = transcript_text
        else:
            caption_text = (
                f"尚未取得轉錄內容，畫面將自動更新 | Token：{token_preview} | "
                f"最後檢查：{last_update_time}"
            )
            display_value = (
                "🎤 正在等待第一段轉錄結果...\n\n"
                "麥克風錄音啟動後，逐字稿會自動出現在此處。"
            )

        text_area_key = f"{fragment_prefix}_feed_text_area"
        st.session_state[text_area_key] = display_value

        st.text_area(
            "即時逐字稿",
            value=display_value,
            height=textarea_height,
            key=text_area_key,
        )
        st.caption(caption_text)
        if cost_info:
            st.caption(_format_cost_caption(cost_info))

        if transcript_text:
            download_name = f"transcript-live-{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt"
            st.download_button(
                "下載目前逐字稿 (.txt)",
                data=transcript_text.encode("utf-8"),
                file_name=download_name,
                mime="text/plain",
                use_container_width=True,
                key=f"{fragment_prefix}_feed_download",
            )

    _feed_fragment(prefix, empty_message, height, fallback_model)


def _start_recording(state: _SessionState, config: TranscriptionUIConfig) -> None:
    """Start recording and transcription."""
    global _active_token, _active_model

    # Prevent multiple simultaneous recordings
    with _recorder_lock:
        if _active_token is not None:
            print(
                "[Transcription] Already recording with token "
                f"{_active_token[:8]}, ignoring duplicate start request"
            )
            return

    # Create new token
    token = str(uuid.uuid4())

    resource_dir = config.resource_dir
    resource_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    wav_filename = f"recording-{timestamp}.wav"
    wav_path = resource_dir / wav_filename

    print(f"[Transcription] Starting recording with token {token[:8]}")
    print(f"[Transcription] WAV path: {wav_path}")

    # Initialize state for this token
    start_time = time.time()
    with _recorder_lock:
        _active_token = token
        _active_model = config.model_name
        _audio_queues[token] = queue.Queue(maxsize=128)
        _transcription_buffers[token] = []
        _transcript_segments[token] = []
        _wav_paths[token] = wav_path
        _bytes_written[token] = 0
        _last_rms[token] = 0.0
        _last_transcription_time[token] = start_time
        _worker_stop_events[token] = threading.Event()
        _transcription_stop_events[token] = threading.Event()
        _token_models[token] = config.model_name

    worker_thread = threading.Thread(target=_audio_worker, args=(token,), daemon=True)
    worker_thread.start()
    with _recorder_lock:
        _worker_threads[token] = worker_thread

    transcription_thread = threading.Thread(
        target=_transcription_worker,
        args=(token,),
        daemon=True,
    )
    transcription_thread.start()
    with _recorder_lock:
        _transcription_threads[token] = transcription_thread

    state.set("active", True)
    state.set("token", token)
    state.set("path", str(wav_path))
    state.set("status", "🔴 錄音中... 即時轉錄結果將在下方顯示")
    state.set("last_transcript", "")
    state.set("last_path", "")
    state.set("segment_count", 0)
    state.set("last_segment_count", 0)
    state.set("model_name", config.model_name)
    state.set("last_model_name", config.model_name)
    state.set("last_cost", None)
    state.set("last_bytes_written", 0)

    # Avoid rerun to prevent WebRTC PeerConnection leaks
    # The fragment auto-refresh will handle UI updates


def _stop_recording(state: _SessionState, config: TranscriptionUIConfig) -> None:
    """Stop recording and save transcript."""
    global _active_token, _active_model

    token = state.get("token")
    if not token:
        return

    print(f"[Transcription] Stopping recording for token {token[:8]}")

    # Stop accepting new audio
    with _recorder_lock:
        _active_token = None
        _active_model = None

    with _recorder_lock:
        worker_stop = _worker_stop_events.get(token)
        transcription_stop = _transcription_stop_events.get(token)
        audio_queue = _audio_queues.get(token)

    if worker_stop:
        worker_stop.set()
        if audio_queue:
            try:
                audio_queue.put(None, timeout=1.0)
            except queue.Full:
                pass

    if transcription_stop:
        transcription_stop.set()

    with _recorder_lock:
        worker_thread = _worker_threads.get(token)
        transcription_thread = _transcription_threads.get(token)

    if worker_thread and worker_thread.is_alive():
        worker_thread.join(timeout=3.0)

    if transcription_thread and transcription_thread.is_alive():
        transcription_thread.join(timeout=3.0)

    with _recorder_lock:
        wav_path = _wav_paths.get(token)
        segments = _transcript_segments.get(token, [])
        bytes_written = _bytes_written.get(token, 0)
        model_used = _token_models.get(token, state.get("model_name", "whisper-1"))

    formatted_lines = []
    for seg in segments:
        if isinstance(seg, dict):
            formatted_lines.append(f"{seg['time']}  {seg['text']}")
        else:
            formatted_lines.append(str(seg))

    final_transcript = "\n".join(formatted_lines)

    state.set("active", False)
    state.set("token", None)
    state.set("last_model_name", model_used)
    state.set("last_bytes_written", bytes_written)

    if wav_path and wav_path.exists():
        file_size = wav_path.stat().st_size
        if file_size > 44 and final_transcript:
            transcript_path = _save_transcript(wav_path, final_transcript)

            state.set("last_transcript", final_transcript)
            state.set("last_path", str(transcript_path))
            state.set("status", "✅ 轉錄完成")

            print(f"[Transcription] Saved transcript: {transcript_path}")
        else:
            state.set("status", "⚠️ 錄音時間太短或未檢測到語音")
    else:
        state.set("status", "❌ 錄音檔案不存在")

    audio_minutes = _audio_minutes_from_bytes(bytes_written)
    cost_info = _estimate_transcription_cost(
        model_used,
        audio_minutes=audio_minutes,
        transcript_text=final_transcript,
    )
    state.set("last_cost", cost_info)

    with _recorder_lock:
        _audio_queues.pop(token, None)
        _transcription_buffers.pop(token, None)
        _transcript_segments.pop(token, None)
        _wav_paths.pop(token, None)
        _wav_writers.pop(token, None)
        _bytes_written.pop(token, None)
        _last_rms.pop(token, None)
        _worker_threads.pop(token, None)
        _worker_stop_events.pop(token, None)
        _transcription_threads.pop(token, None)
        _transcription_stop_events.pop(token, None)
        _last_transcription_time.pop(token, None)
        _token_models.pop(token, None)

    # Avoid rerun to prevent WebRTC PeerConnection leaks
    # The fragment auto-refresh will handle UI updates


def _audio_worker(token: str) -> None:
    """Worker thread to write audio data to WAV file."""
    print(f"[Transcription] Audio worker started for token {token[:8]}")

    with _recorder_lock:
        audio_queue = _audio_queues.get(token)
        wav_path = _wav_paths.get(token)
        stop_event = _worker_stop_events.get(token)

    if not audio_queue or not wav_path or not stop_event:
        print("[Transcription] Audio worker missing resources")
        return

    wav_writer = None
    chunks_processed = 0

    try:
        while not stop_event.is_set():
            try:
                item = audio_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            if item is None:  # Stop signal
                print(
                    "[Transcription] Stop signal received, "
                    f"processed {chunks_processed} chunks"
                )
                break

            pcm_bytes, rms = item

            if wav_writer is None:
                print(f"[Transcription] Opening WAV file: {wav_path}")
                wav_writer = wave.open(str(wav_path), "wb")
                wav_writer.setnchannels(1)
                wav_writer.setsampwidth(SAMPLE_WIDTH)
                wav_writer.setframerate(SAMPLE_RATE)
                with _recorder_lock:
                    _wav_writers[token] = wav_writer

            wav_writer.writeframes(pcm_bytes)
            chunks_processed += 1

            with _recorder_lock:
                _bytes_written[token] = _bytes_written.get(token, 0) + len(pcm_bytes)
                _last_rms[token] = rms

            if chunks_processed == 1:
                print(f"[Transcription] First chunk written, RMS={rms:.1f}")

    finally:
        if wav_writer:
            try:
                wav_writer.close()
                print(f"[Transcription] WAV file closed: {wav_path}")
            except Exception as exc:
                print(f"[Transcription] Error closing WAV: {exc}")

    print(f"[Transcription] Audio worker stopped")


def _transcription_worker(token: str) -> None:
    """Worker thread for background transcription."""
    print(f"[Transcription] Transcription worker started for token {token[:8]}")

    from openai import OpenAI

    client = OpenAI()

    with _recorder_lock:
        stop_event = _transcription_stop_events.get(token)

    if not stop_event:
        print("[Transcription] Transcription worker missing stop event")
        return

    while not stop_event.is_set():
        time.sleep(0.5)

        with _recorder_lock:
            last_time = _last_transcription_time.get(token, 0)

        current_time = time.time()
        elapsed = current_time - last_time

        if elapsed >= TRANSCRIPTION_CHUNK_DURATION:
            with _recorder_lock:
                buffer = _transcription_buffers.get(token)
                if not buffer:
                    _last_transcription_time[token] = current_time
                    continue

                audio_chunk = np.concatenate(buffer)
                buffer.clear()
                _last_transcription_time[token] = current_time

            chunk_rms = float(calculate_rms(audio_chunk))
            if not is_voiced_chunk(
                audio_chunk,
                int(VAD_RMS_THRESHOLD),
                min_density=VAD_SAMPLE_DENSITY,
                amplitude_gate=VAD_AMPLITUDE_GATE,
            ):
                print(
                    "[Transcription] Skipping non-voiced chunk "
                    f"(RMS={chunk_rms:.1f}, density<{VAD_SAMPLE_DENSITY})"
                )
                continue

            try:
                with _recorder_lock:
                    model_name = _token_models.get(token, "whisper-1")

                wav_bytes = _pcm_to_wav_bytes(audio_chunk, SAMPLE_RATE)
                wav_file = io.BytesIO(wav_bytes)
                wav_file.name = "chunk.wav"

                transcript = client.audio.transcriptions.create(
                    model=model_name,
                    file=wav_file,
                    language="zh",
                    response_format="text",
                )

                if transcript and transcript.strip():
                    transcript_text = transcript.strip()
                    transcript_text = _convert_to_traditional_chinese(transcript_text)

                    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    segment_data = {"time": time_str, "text": transcript_text}

                    with _recorder_lock:
                        segments = _transcript_segments.get(token)
                        if segments is not None:
                            segments.append(segment_data)
                            segment_count = len(segments)
                            print(
                                f"[Transcription] Segment {segment_count} "
                                f"[{time_str}] (model={model_name}, RMS={chunk_rms:.1f}): "
                                f"{transcript_text[:50]}..."
                            )
                            print(
                                "[Transcription] Total segments in buffer: "
                                f"{segment_count}"
                            )
                        else:
                            print(
                                "[Transcription] ERROR: segments list is None "
                                f"for token {token[:8]}"
                            )
                else:
                    print(f"[Transcription] Empty transcript (RMS={chunk_rms:.1f})")

            except Exception as exc:
                print(f"[Transcription] Error transcribing: {exc}")

    print("[Transcription] Transcription worker stopped")


def _convert_to_traditional_chinese(text: str) -> str:
    """
    Convert Simplified Chinese to Traditional Chinese.

    Args:
        text: Input text (may contain Simplified Chinese)

    Returns:
        Text with all Simplified Chinese converted to Traditional Chinese
    """
    try:
        converted = _opencc_converter.convert(text)
        if converted != text:
            print(f"[S2T] Converted: '{text}' -> '{converted}'")
        return converted
    except Exception as exc:
        print(f"[S2T] Error converting text: {exc}")
        return text


def _pcm_to_wav_bytes(pcm_data: np.ndarray, sample_rate: int) -> bytes:
    """Convert PCM numpy array to WAV bytes."""
    wav_buffer = io.BytesIO()

    with wave.open(wav_buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_data.tobytes())

    return wav_buffer.getvalue()


def _save_transcript(wav_path: Path, transcript: str) -> Path:
    """Save transcript to text file with timeline format."""
    transcript_filename = wav_path.stem + "-transcript.txt"
    transcript_path = wav_path.parent / transcript_filename

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = f"""語音轉錄結果
時間：{timestamp}
音訊檔案：{wav_path.name}
採樣率：{SAMPLE_RATE} Hz
模型：OpenAI Whisper (whisper-1)
格式：yyyy-mm-dd hh:mi:ss + 逐字稿內容

{'=' * 60}

"""

    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(transcript)

    return transcript_path


__all__ = [
    "render_transcription_widget",
    "render_transcription_feed",
    "TranscriptionUIConfig",
    "MODEL_COST_CONFIG",
]
