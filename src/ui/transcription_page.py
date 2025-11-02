"""
Real-time microphone voice transcription UI page.

Uses WebRTC for audio capture and Whisper API for transcription:
- Single WAV file for entire recording session
- Background chunking and transcription (every 3 seconds)
- Accumulated transcript display with controlled UI updates
"""

import os
import queue
import threading
import time
import wave
import io
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import av
import numpy as np
import streamlit as st
from streamlit_webrtc import RTCConfiguration, WebRtcMode, webrtc_streamer
from opencc import OpenCC

from src.services.audio_service import process_audio_frame
from src.utils.audio_utils import calculate_rms

SAMPLE_RATE = 48000
SAMPLE_WIDTH = 2  # bytes (int16)
ICE_SERVERS = [{"urls": ["stun:stun.l.google.com:19302"]}]
AUDIO_GAIN = 2.0  # Volume boost multiplier
TRANSCRIPTION_CHUNK_DURATION = 3.0  # Transcribe every 3 seconds
VAD_RMS_THRESHOLD = 300.0  # Minimum RMS to consider as speech (filter silence)

# Initialize OpenCC for Simplified to Traditional Chinese conversion
# s2t = Simplified Chinese to Traditional Chinese
_opencc_converter = OpenCC('s2t')


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
        return text  # Return original text if conversion fails


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

# Cache API key check
_api_key_checked = False
_api_key_available = False


def render_transcription_page() -> None:
    """Render real-time voice transcription page."""
    st.title("🎤 即時語音轉錄（Whisper API）")
    st.caption("使用 WebRTC 錄音並透過 Whisper API 背景轉錄為逐字稿")

    _initialize_session_state()

    # Check API key only once per session
    global _api_key_checked, _api_key_available
    if not _api_key_checked:
        _api_key_available = _check_api_key()
        _api_key_checked = True

    if not _api_key_available:
        _render_api_key_input()
        return

    _render_controls()
    _render_webrtc_stream()
    _render_status()
    _render_transcript_display()


def _initialize_session_state() -> None:
    """Initialize session state variables."""
    if "transcription_active" not in st.session_state:
        st.session_state.transcription_active = False
    if "transcription_token" not in st.session_state:
        st.session_state.transcription_token = None
    if "transcription_path" not in st.session_state:
        st.session_state.transcription_path = ""
    if "transcription_status" not in st.session_state:
        st.session_state.transcription_status = ""
    if "last_transcript" not in st.session_state:
        st.session_state.last_transcript = ""
    if "last_transcript_path" not in st.session_state:
        st.session_state.last_transcript_path = ""
    if "segment_count" not in st.session_state:
        st.session_state.segment_count = 0
    if "last_ui_update" not in st.session_state:
        st.session_state.last_ui_update = 0.0
    if "mic_permission_requested" not in st.session_state:
        st.session_state.mic_permission_requested = False


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


def _render_api_key_input() -> None:
    """Render API key input field."""
    st.warning("⚠️ 請先設定 OpenAI API Key")

    api_key = st.text_input(
        "OpenAI API Key",
        type="password",
        help="輸入您的 OpenAI API Key，或設定在 .env 檔案中",
        key="api_key_input"
    )

    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
        global _api_key_available
        _api_key_available = True
        st.rerun()


def _render_controls() -> None:
    """Render control buttons."""
    st.markdown("#### 🎙️ 錄音控制")

    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "▶️ 開始錄音",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.transcription_active,
        ):
            _start_recording()

    with col2:
        if st.button(
            "⏹️ 停止錄音",
            type="secondary",
            use_container_width=True,
            disabled=not st.session_state.transcription_active,
        ):
            _stop_recording()

    if st.session_state.transcription_status:
        st.info(st.session_state.transcription_status)


def _render_webrtc_stream() -> None:
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
    webrtc_ctx = webrtc_streamer(
        key="transcription-mic",
        mode=WebRtcMode.SENDONLY,
        audio_frame_callback=audio_callback,
        media_stream_constraints={"audio": True, "video": False},
        rtc_configuration=rtc_configuration,
        async_processing=True,
        desired_playing_state=True,  # Always request mic permission on page load
    )

    # Update mic permission status
    if not st.session_state.mic_permission_requested:
        if webrtc_ctx.state.playing:
            st.session_state.mic_permission_requested = True

    # Show connection status
    if webrtc_ctx.state.playing:
        if st.session_state.transcription_active:
            st.success("🎧 麥克風已連線，正在錄音並即時轉錄...")
        else:
            st.info("✅ 麥克風已就緒，點擊「開始錄音」開始錄音")
    elif webrtc_ctx.state.signalling:
        st.warning("🔄 正在建立 WebRTC 連線，請稍候...")
    else:
        st.warning("⚠️ 請允許瀏覽器存取麥克風權限")


def _render_status() -> None:
    """Render recording status."""
    st.markdown("#### 📊 錄音狀態")

    token = st.session_state.transcription_token
    bytes_written = 0
    last_rms = 0.0

    if token:
        with _recorder_lock:
            bytes_written = _bytes_written.get(token, 0)
            last_rms = _last_rms.get(token, 0.0)

    if st.session_state.transcription_path:
        st.write(f"📁 檔案：`{st.session_state.transcription_path}`")
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

    if st.session_state.transcription_active:
        st.write(f"📝 已轉錄段數：{st.session_state.segment_count}")


def _render_transcript_display() -> None:
    """Render transcript display area."""
    st.markdown("#### 📄 即時轉錄結果")

    token = st.session_state.transcription_token

    # Debug: Print current state
    print(f"[Transcription UI] Active: {st.session_state.transcription_active}, Token: {token[:8] if token else 'None'}")

    # Show real-time transcript during recording
    if st.session_state.transcription_active and token:
        with _recorder_lock:
            segments = _transcript_segments.get(token, [])

        print(f"[Transcription UI] Retrieved {len(segments)} segments from token {token[:8]}")

        # Debug: Print segments info to console
        if segments:
            print(f"[Transcription UI] Displaying {len(segments)} segments")

        # Format segments with timeline
        formatted_lines = []
        for seg in segments:
            if isinstance(seg, dict):
                formatted_lines.append(f"{seg['time']}  {seg['text']}")
            else:
                # Fallback for old format (backward compatibility)
                formatted_lines.append(str(seg))

        current_transcript = "\n".join(formatted_lines)
        segment_count = len(segments)

        st.session_state.segment_count = segment_count

        # Add timestamp to show live updates
        last_update_time = datetime.now().strftime("%H:%M:%S")

        # Debug: Print what we're about to display
        print(f"[Transcription UI] Current transcript length: {len(current_transcript)}")
        if segments:
            print(f"[Transcription UI] Latest segment: {segments[-1] if segments else 'None'}")

        # Prepare display content
        if current_transcript:
            display_value = current_transcript
            caption_text = f"📊 已轉錄：{len(current_transcript)} 字元 | 分段數：{segment_count} | 更新時間：{last_update_time}"
        else:
            display_value = f"🎤 等待轉錄結果...\n\n開始時間：{last_update_time}\nToken：{token[:8]}\n\n約 3 秒後會出現第一段轉錄結果"
            caption_text = f"⏳ 等待中... | 已檢查次數：{st.session_state.segment_count} | 更新時間：{last_update_time}"

        # Single text area - always displayed with same structure
        st.text_area(
            f"即時逐字稿 (最後更新：{last_update_time})",
            value=display_value,
            height=300,
            help="格式：yyyy-mm-dd hh:mi:ss + 逐字稿內容 | 每 0.5 秒自動更新"
        )
        st.caption(caption_text)

        # Auto-refresh every 0.5 seconds to show updates more frequently (like WebSocket)
        current_time = time.time()
        if current_time - st.session_state.last_ui_update >= 0.5:
            st.session_state.last_ui_update = current_time
            time.sleep(0.05)  # Small delay to prevent overwhelming
            st.rerun()

    # Show final transcript after recording stopped
    elif st.session_state.last_transcript:
        st.text_area(
            "完整逐字稿",
            value=st.session_state.last_transcript,
            height=300,
            help="格式：yyyy-mm-dd hh:mi:ss + 逐字稿內容"
        )

        st.caption(f"📊 字數：{len(st.session_state.last_transcript)} 字元")

        if st.session_state.last_transcript_path:
            st.caption(f"💾 已保存至：`{st.session_state.last_transcript_path}`")

            # Download button
            st.download_button(
                label="📥 下載逐字稿",
                data=st.session_state.last_transcript.encode("utf-8"),
                file_name=Path(st.session_state.last_transcript_path).name,
                mime="text/plain",
                use_container_width=True
            )
    else:
        st.info("點擊「開始錄音」後，即時轉錄結果將顯示在此處")


def _start_recording() -> None:
    """Start recording and transcription."""
    global _active_token

    # Prevent multiple simultaneous recordings
    with _recorder_lock:
        if _active_token is not None:
            print(f"[Transcription] Already recording with token {_active_token[:8]}, ignoring duplicate start request")
            return

    # Create new token
    token = str(uuid.uuid4())

    # Create resource directory
    resource_dir = Path("resource")
    resource_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    wav_filename = f"recording-{timestamp}.wav"
    wav_path = resource_dir / wav_filename

    print(f"[Transcription] Starting recording with token {token[:8]}")
    print(f"[Transcription] WAV path: {wav_path}")

    # Initialize state for this token
    start_time = time.time()
    with _recorder_lock:
        _active_token = token
        _audio_queues[token] = queue.Queue(maxsize=128)
        _transcription_buffers[token] = []
        _transcript_segments[token] = []
        _wav_paths[token] = wav_path
        _bytes_written[token] = 0
        _last_rms[token] = 0.0
        _last_transcription_time[token] = start_time
        _worker_stop_events[token] = threading.Event()
        _transcription_stop_events[token] = threading.Event()

    # Start audio worker thread
    worker_thread = threading.Thread(target=_audio_worker, args=(token,), daemon=True)
    worker_thread.start()
    with _recorder_lock:
        _worker_threads[token] = worker_thread

    # Start transcription worker thread
    transcription_thread = threading.Thread(target=_transcription_worker, args=(token,), daemon=True)
    transcription_thread.start()
    with _recorder_lock:
        _transcription_threads[token] = transcription_thread

    # Update session state
    st.session_state.transcription_active = True
    st.session_state.transcription_token = token
    st.session_state.transcription_path = str(wav_path)
    st.session_state.transcription_status = "🔴 錄音中... 即時轉錄結果將在下方顯示"
    st.session_state.last_transcript = ""
    st.session_state.last_transcript_path = ""
    st.session_state.segment_count = 0
    st.session_state.last_ui_update = time.time()

    st.rerun()


def _stop_recording() -> None:
    """Stop recording and save transcript."""
    global _active_token

    token = st.session_state.transcription_token
    if not token:
        return

    print(f"[Transcription] Stopping recording for token {token[:8]}")

    # Stop accepting new audio
    with _recorder_lock:
        _active_token = None

    # Stop worker threads
    with _recorder_lock:
        worker_stop = _worker_stop_events.get(token)
        transcription_stop = _transcription_stop_events.get(token)
        audio_queue = _audio_queues.get(token)

    if worker_stop:
        worker_stop.set()
        # Send stop signal to worker
        if audio_queue:
            try:
                audio_queue.put(None, timeout=1.0)
            except queue.Full:
                pass

    if transcription_stop:
        transcription_stop.set()

    # Wait for threads to finish
    with _recorder_lock:
        worker_thread = _worker_threads.get(token)
        transcription_thread = _transcription_threads.get(token)

    if worker_thread and worker_thread.is_alive():
        worker_thread.join(timeout=3.0)

    if transcription_thread and transcription_thread.is_alive():
        transcription_thread.join(timeout=3.0)

    # Get final path and transcript
    with _recorder_lock:
        wav_path = _wav_paths.get(token)
        segments = _transcript_segments.get(token, [])

    # Format segments with timeline
    formatted_lines = []
    for seg in segments:
        if isinstance(seg, dict):
            formatted_lines.append(f"{seg['time']}  {seg['text']}")
        else:
            # Fallback for old format
            formatted_lines.append(str(seg))

    final_transcript = "\n".join(formatted_lines)

    # Update session state
    st.session_state.transcription_active = False
    st.session_state.transcription_token = None

    if wav_path and wav_path.exists():
        file_size = wav_path.stat().st_size
        if file_size > 44 and final_transcript:
            # Save transcript
            transcript_path = _save_transcript(wav_path, final_transcript)

            st.session_state.last_transcript = final_transcript
            st.session_state.last_transcript_path = str(transcript_path)
            st.session_state.transcription_status = "✅ 轉錄完成"

            print(f"[Transcription] Saved transcript: {transcript_path}")
        else:
            st.session_state.transcription_status = "⚠️ 錄音時間太短或未檢測到語音"
    else:
        st.session_state.transcription_status = "❌ 錄音檔案不存在"

    # Cleanup
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

    st.rerun()


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
                print(f"[Transcription] Stop signal received, processed {chunks_processed} chunks")
                break

            pcm_bytes, rms = item

            if wav_writer is None:
                # Open WAV file
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
        # Close WAV file
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
            # Get accumulated audio
            with _recorder_lock:
                buffer = _transcription_buffers.get(token)
                if not buffer:
                    _last_transcription_time[token] = current_time
                    continue

                # Concatenate and clear buffer
                audio_chunk = np.concatenate(buffer)
                buffer.clear()
                _last_transcription_time[token] = current_time

            # Voice Activity Detection (VAD) - check RMS
            chunk_rms = float(calculate_rms(audio_chunk))

            if chunk_rms < VAD_RMS_THRESHOLD:
                print(f"[Transcription] Skipping silent chunk (RMS={chunk_rms:.1f} < {VAD_RMS_THRESHOLD})")
                continue

            # Transcribe
            try:
                wav_bytes = _pcm_to_wav_bytes(audio_chunk, SAMPLE_RATE)
                wav_file = io.BytesIO(wav_bytes)
                wav_file.name = "chunk.wav"

                # Transcribe with Traditional Chinese language setting
                # Note: DO NOT use prompt parameter - Whisper will transcribe it as content
                # language="zh" defaults to Traditional Chinese for most cases
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=wav_file,
                    language="zh",
                    response_format="text"
                )

                if transcript and transcript.strip():
                    # Convert to Traditional Chinese immediately after getting transcript
                    transcript_text = transcript.strip()
                    transcript_text = _convert_to_traditional_chinese(transcript_text)

                    # Use actual clock time (yyyy-mm-dd hh:mi:ss)
                    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    segment_data = {
                        "time": time_str,
                        "text": transcript_text
                    }

                    with _recorder_lock:
                        segments = _transcript_segments.get(token)
                        if segments is not None:
                            segments.append(segment_data)
                            segment_count = len(segments)
                            # Use converted text in console output
                            print(f"[Transcription] Segment {segment_count} [{time_str}] (RMS={chunk_rms:.1f}): {transcript_text[:50]}...")
                            print(f"[Transcription] Total segments in buffer: {segment_count}")
                        else:
                            print(f"[Transcription] ERROR: segments list is None for token {token[:8]}")
                else:
                    print(f"[Transcription] Empty transcript (RMS={chunk_rms:.1f})")

            except Exception as exc:
                print(f"[Transcription] Error transcribing: {exc}")

    print(f"[Transcription] Transcription worker stopped")


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
