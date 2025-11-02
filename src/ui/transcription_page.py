"""
Real-time microphone voice transcription UI page.

Uses WebRTC for audio capture and Whisper API for transcription:
- Single WAV file for entire recording session
- Background chunking and transcription (every 3 seconds)
- Accumulated transcript display with minimal UI updates
"""

import os
import queue
import threading
import time
import wave
import io
from datetime import datetime
from pathlib import Path
from typing import Optional

import av
import numpy as np
import streamlit as st
from streamlit_webrtc import RTCConfiguration, WebRtcMode, webrtc_streamer

from src.services.audio_service import process_audio_frame
from src.utils.audio_utils import calculate_rms

SAMPLE_RATE = 48000
SAMPLE_WIDTH = 2  # bytes (int16)
ICE_SERVERS = [{"urls": ["stun:stun.l.google.com:19302"]}]
AUDIO_GAIN = 2.0  # Volume boost multiplier
TRANSCRIPTION_CHUNK_DURATION = 3.0  # Transcribe every 3 seconds

# Global state
_audio_queue: queue.Queue = queue.Queue(maxsize=128)
_transcription_queue: queue.Queue = queue.Queue(maxsize=32)
_recording_active = False
_recording_lock = threading.Lock()
_wav_writer: Optional[wave.Wave_write] = None
_wav_path: Optional[Path] = None
_wav_lock = threading.Lock()
_bytes_written = 0
_last_rms = 0.0
_rms_lock = threading.Lock()
_audio_worker_thread: Optional[threading.Thread] = None
_audio_worker_stop = threading.Event()
_transcription_worker_thread: Optional[threading.Thread] = None
_transcription_worker_stop = threading.Event()

# Transcript accumulation
_transcript_segments = []  # List of transcript strings
_transcript_lock = threading.Lock()

# Audio buffer for transcription
_transcription_buffer = []  # List of numpy arrays
_transcription_buffer_lock = threading.Lock()
_last_transcription_time = 0


def render_transcription_page() -> None:
    """Render real-time voice transcription page."""
    st.title("🎤 即時語音轉錄（Whisper API）")
    st.caption("使用 WebRTC 錄音並透過 Whisper API 背景轉錄為逐字稿")

    _initialize_session_state()
    _check_api_key()

    if not st.session_state.api_key_set:
        _render_api_key_input()
        return

    _render_controls()
    _render_webrtc_stream()
    _render_status()
    _render_transcript_display()


def _initialize_session_state() -> None:
    """Initialize session state variables."""
    if "api_key_set" not in st.session_state:
        st.session_state.api_key_set = False
    if "recording_active" not in st.session_state:
        st.session_state.recording_active = False
    if "recording_path" not in st.session_state:
        st.session_state.recording_path = ""
    if "recording_start_time" not in st.session_state:
        st.session_state.recording_start_time = None
    if "last_transcript" not in st.session_state:
        st.session_state.last_transcript = ""
    if "last_transcript_path" not in st.session_state:
        st.session_state.last_transcript_path = ""
    if "transcription_status" not in st.session_state:
        st.session_state.transcription_status = ""
    if "mic_ready" not in st.session_state:
        st.session_state.mic_ready = False
    if "total_bytes" not in st.session_state:
        st.session_state.total_bytes = 0
    if "current_rms" not in st.session_state:
        st.session_state.current_rms = 0.0
    if "realtime_transcript" not in st.session_state:
        st.session_state.realtime_transcript = ""
    if "segment_count" not in st.session_state:
        st.session_state.segment_count = 0
    if "last_ui_update" not in st.session_state:
        st.session_state.last_ui_update = 0


def _check_api_key() -> None:
    """Check for API key in environment."""
    from dotenv import load_dotenv
    load_dotenv()

    if os.getenv("OPENAI_API_KEY"):
        st.session_state.api_key_set = True
    elif "OPENAI_API_KEY_MANUAL" in st.session_state:
        if st.session_state.OPENAI_API_KEY_MANUAL:
            os.environ["OPENAI_API_KEY"] = st.session_state.OPENAI_API_KEY_MANUAL
            st.session_state.api_key_set = True


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
        st.session_state.OPENAI_API_KEY_MANUAL = api_key
        os.environ["OPENAI_API_KEY"] = api_key
        st.session_state.api_key_set = True
        st.rerun()


def _render_controls() -> None:
    """Render control buttons."""
    st.markdown("#### 🎙️ 錄音控制")

    col1, col2 = st.columns(2)

    with col1:
        can_start = (
            not st.session_state.recording_active and
            st.session_state.api_key_set
        )

        if st.button(
            "▶️ 開始錄音",
            type="primary",
            use_container_width=True,
            disabled=not can_start,
            help="開始錄音前請確認麥克風權限已授予"
        ):
            if st.session_state.mic_ready:
                _start_recording()
                st.rerun()
            else:
                st.error("⚠️ 請先等待麥克風連線成功（綠色訊息），然後再點擊開始錄音")

    with col2:
        if st.button(
            "⏹️ 停止錄音",
            type="secondary",
            use_container_width=True,
            disabled=not st.session_state.recording_active
        ):
            _stop_recording()
            st.rerun()

    if st.session_state.recording_active:
        st.info("🔴 錄音中... 即時轉錄結果將在下方顯示")
    elif not st.session_state.mic_ready:
        st.warning("🎤 等待麥克風連線... 請確認瀏覽器已授權麥克風權限")
    else:
        st.success("✅ 麥克風已就緒，可以開始錄音")


def _render_webrtc_stream() -> None:
    """Render WebRTC microphone stream."""
    st.markdown("#### 🎙️ 麥克風串流")

    def audio_callback(frame: av.AudioFrame) -> av.AudioFrame:
        global _last_rms

        # Process audio frame with gain
        pcm_array = process_audio_frame(frame, gain=AUDIO_GAIN)

        # Calculate RMS
        rms = float(calculate_rms(pcm_array))
        with _rms_lock:
            _last_rms = rms

        # Add to queues if recording
        with _recording_lock:
            if _recording_active:
                # Add to WAV writer queue
                try:
                    _audio_queue.put_nowait(pcm_array.tobytes())
                except queue.Full:
                    pass

                # Add to transcription buffer
                with _transcription_buffer_lock:
                    _transcription_buffer.append(pcm_array)

        return frame

    rtc_configuration = RTCConfiguration({"iceServers": ICE_SERVERS})
    webrtc_ctx = webrtc_streamer(
        key="transcription-mic",
        mode=WebRtcMode.SENDONLY,
        audio_frame_callback=audio_callback,
        media_stream_constraints={"audio": True, "video": False},
        rtc_configuration=rtc_configuration,
        async_processing=True,
        desired_playing_state=True,
    )

    # Update mic ready status
    if webrtc_ctx.state.playing:
        st.session_state.mic_ready = True
        st.success("🎧 麥克風已連線，音訊串流正常")
    elif webrtc_ctx.state.signalling:
        st.session_state.mic_ready = False
        st.info("🔄 正在建立 WebRTC 連線，請稍候...")
    else:
        st.session_state.mic_ready = False
        st.warning("⚠️ 麥克風未連線，請檢查瀏覽器權限")


def _render_status() -> None:
    """Render recording status."""
    st.markdown("#### 📊 錄音狀態")

    if st.session_state.recording_path:
        st.write(f"📁 檔案：`{st.session_state.recording_path}`")
    else:
        st.write("📁 尚未開始錄音")

    # Update from global state
    with _wav_lock:
        total_bytes = _bytes_written
    with _rms_lock:
        current_rms = _last_rms

    st.session_state.total_bytes = total_bytes
    st.session_state.current_rms = current_rms

    if total_bytes > 0:
        duration_sec = total_bytes / (SAMPLE_RATE * SAMPLE_WIDTH)
        st.write(f"⏱️ 已錄製：{duration_sec:.1f} 秒")
    else:
        st.write("⏱️ 已錄製：0.0 秒")

    st.write(f"🔊 當前 RMS：{current_rms:.1f}")
    st.write(f"🎚️ 採樣率：{SAMPLE_RATE} Hz")
    st.write(f"📈 音量增益：{AUDIO_GAIN}x")

    if st.session_state.recording_active:
        st.write(f"📝 已轉錄段數：{st.session_state.segment_count}")

    if st.session_state.recording_start_time:
        elapsed = time.time() - st.session_state.recording_start_time
        st.write(f"🕒 錄音時長：{elapsed:.1f} 秒")


def _render_transcript_display() -> None:
    """Render transcript display area."""
    st.markdown("#### 📄 即時轉錄結果")

    if st.session_state.transcription_status:
        st.info(st.session_state.transcription_status)

    # Show real-time transcript during recording
    if st.session_state.recording_active:
        # Update from global state
        with _transcript_lock:
            current_transcript = "\n".join(_transcript_segments)
            segment_count = len(_transcript_segments)

        st.session_state.realtime_transcript = current_transcript
        st.session_state.segment_count = segment_count

        if current_transcript:
            st.text_area(
                "即時逐字稿（錄音中...）",
                value=current_transcript,
                height=300,
                help="即時轉錄的結果（每 3 秒更新）"
            )
            st.caption(f"📊 已轉錄：{len(current_transcript)} 字元 | 分段數：{segment_count}")
        else:
            st.info("🎤 錄音中，等待第一段轉錄結果（約 3 秒後）...")

        # Auto-refresh every 2 seconds to show updates (not too frequent)
        current_time = time.time()
        if current_time - st.session_state.last_ui_update >= 2.0:
            st.session_state.last_ui_update = current_time
            time.sleep(0.1)
            st.rerun()

    # Show final transcript after recording stopped
    elif st.session_state.last_transcript:
        st.text_area(
            "完整逐字稿",
            value=st.session_state.last_transcript,
            height=300,
            help="最終完整的轉錄結果"
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
    global _recording_active, _wav_writer, _wav_path, _bytes_written
    global _audio_worker_thread, _transcription_worker_thread
    global _transcript_segments, _transcription_buffer, _last_transcription_time

    # Create resource directory
    resource_dir = Path("resource")
    resource_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    wav_filename = f"recording-{timestamp}.wav"
    wav_path = resource_dir / wav_filename

    # Open WAV file (will write continuously to this single file)
    try:
        wav_writer = wave.open(str(wav_path), "wb")
        wav_writer.setnchannels(1)
        wav_writer.setsampwidth(SAMPLE_WIDTH)
        wav_writer.setframerate(SAMPLE_RATE)
    except Exception as exc:
        st.error(f"無法建立音訊檔案：{exc}")
        return

    with _wav_lock:
        _wav_writer = wav_writer
        _wav_path = wav_path
        _bytes_written = 0

    # Clear queues
    while not _audio_queue.empty():
        try:
            _audio_queue.get_nowait()
        except queue.Empty:
            break

    # Clear transcription state
    with _transcript_lock:
        _transcript_segments.clear()

    with _transcription_buffer_lock:
        _transcription_buffer.clear()

    _last_transcription_time = time.time()

    # Start audio worker thread
    _audio_worker_stop.clear()
    _audio_worker_thread = threading.Thread(target=_audio_worker, daemon=True)
    _audio_worker_thread.start()

    # Start transcription worker thread
    _transcription_worker_stop.clear()
    _transcription_worker_thread = threading.Thread(target=_transcription_worker, daemon=True)
    _transcription_worker_thread.start()

    with _recording_lock:
        _recording_active = True

    # Update session state
    st.session_state.recording_active = True
    st.session_state.recording_path = str(wav_path)
    st.session_state.recording_start_time = time.time()
    st.session_state.transcription_status = "🔄 即時轉錄中..."
    st.session_state.last_transcript = ""
    st.session_state.last_transcript_path = ""
    st.session_state.realtime_transcript = ""
    st.session_state.segment_count = 0
    st.session_state.last_ui_update = time.time()

    print("[Transcription] Recording started")


def _stop_recording() -> None:
    """Stop recording and save transcript."""
    global _recording_active, _wav_writer, _wav_path
    global _audio_worker_thread, _transcription_worker_thread

    print("[Transcription] Stopping recording...")

    # Stop recording
    with _recording_lock:
        _recording_active = False

    # Stop worker threads
    _audio_worker_stop.set()
    if _audio_worker_thread and _audio_worker_thread.is_alive():
        _audio_worker_thread.join(timeout=2.0)

    _transcription_worker_stop.set()
    if _transcription_worker_thread and _transcription_worker_thread.is_alive():
        _transcription_worker_thread.join(timeout=3.0)

    # Close WAV file
    wav_file_path = None
    with _wav_lock:
        if _wav_writer:
            try:
                _wav_writer.close()
                print(f"[Transcription] WAV file closed: {_wav_path}")
            except Exception as exc:
                print(f"[Transcription] Error closing WAV: {exc}")
            wav_file_path = _wav_path
        _wav_writer = None
        _wav_path = None

    # Update session state
    st.session_state.recording_active = False
    st.session_state.recording_start_time = None

    # Check if we have a valid recording
    if not wav_file_path or not wav_file_path.exists():
        st.error("錄音檔案不存在")
        return

    file_size = wav_file_path.stat().st_size
    if file_size <= 44:  # Only WAV header
        st.warning("錄音時間太短，未檢測到音訊數據")
        wav_file_path.unlink()
        return

    # Get final transcript
    with _transcript_lock:
        final_transcript = "\n".join(_transcript_segments)

    if final_transcript:
        # Save transcript
        transcript_path = _save_transcript(wav_file_path, final_transcript)

        # Update session state
        st.session_state.last_transcript = final_transcript
        st.session_state.last_transcript_path = str(transcript_path)
        st.session_state.transcription_status = "✅ 轉錄完成"

        print(f"[Transcription] Transcript saved: {transcript_path}")
        print(f"[Transcription] Total segments: {len(_transcript_segments)}")
    else:
        st.session_state.transcription_status = "⚠️ 未檢測到語音內容"


def _audio_worker() -> None:
    """Worker thread to write audio data to single WAV file."""
    global _bytes_written

    print("[Transcription] Audio worker started")

    while not _audio_worker_stop.is_set():
        try:
            audio_data = _audio_queue.get(timeout=0.5)
        except queue.Empty:
            continue

        with _wav_lock:
            if _wav_writer:
                try:
                    _wav_writer.writeframes(audio_data)
                    _bytes_written += len(audio_data)
                except Exception as exc:
                    print(f"[Transcription] Error writing audio: {exc}")

    print("[Transcription] Audio worker stopped")


def _transcription_worker() -> None:
    """Worker thread for background transcription every N seconds."""
    from openai import OpenAI
    global _last_transcription_time

    client = OpenAI()

    print("[Transcription] Transcription worker started")

    while not _transcription_worker_stop.is_set():
        time.sleep(0.5)  # Check every 0.5 seconds

        current_time = time.time()
        elapsed = current_time - _last_transcription_time

        # Transcribe every TRANSCRIPTION_CHUNK_DURATION seconds
        if elapsed >= TRANSCRIPTION_CHUNK_DURATION:
            # Get accumulated audio
            with _transcription_buffer_lock:
                if not _transcription_buffer:
                    _last_transcription_time = current_time
                    continue

                # Concatenate all buffers
                audio_chunk = np.concatenate(_transcription_buffer)
                _transcription_buffer.clear()

            _last_transcription_time = current_time

            # Convert to WAV bytes
            try:
                wav_bytes = _pcm_to_wav_bytes(audio_chunk, SAMPLE_RATE)

                # Create in-memory file
                wav_file = io.BytesIO(wav_bytes)
                wav_file.name = "chunk.wav"

                # Transcribe using Whisper API
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=wav_file,
                    language="zh",
                    response_format="text"
                )

                # Add to segments if not empty
                if transcript and transcript.strip():
                    with _transcript_lock:
                        _transcript_segments.append(transcript.strip())

                    print(f"[Transcription] Segment {len(_transcript_segments)}: {transcript[:50]}...")

            except Exception as exc:
                print(f"[Transcription] Error transcribing: {exc}")

    print("[Transcription] Transcription worker stopped")


def _pcm_to_wav_bytes(pcm_data: np.ndarray, sample_rate: int) -> bytes:
    """Convert PCM numpy array to WAV bytes."""
    wav_buffer = io.BytesIO()

    with wave.open(wav_buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)  # int16
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_data.tobytes())

    return wav_buffer.getvalue()


def _save_transcript(wav_path: Path, transcript: str) -> Path:
    """
    Save transcript to text file.

    Args:
        wav_path: Path to corresponding WAV file
        transcript: Transcribed text

    Returns:
        Path to saved transcript file
    """
    # Generate transcript filename based on WAV filename
    transcript_filename = wav_path.stem + "-transcript.txt"
    transcript_path = wav_path.parent / transcript_filename

    # Create header
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = f"""語音轉錄結果
時間：{timestamp}
音訊檔案：{wav_path.name}
採樣率：{SAMPLE_RATE} Hz
模型：OpenAI Whisper (whisper-1)

{'=' * 60}

"""

    # Write transcript
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(transcript)

    return transcript_path
