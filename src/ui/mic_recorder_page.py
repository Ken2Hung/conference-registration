"""
Simple microphone capture page using WebRTC to save raw WAV files.
"""

import queue
import threading
import time
import uuid
import wave
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import av
import numpy as np
import streamlit as st
from streamlit_webrtc import RTCConfiguration, WebRtcMode, webrtc_streamer

from src.utils.audio_utils import calculate_rms
from src.services.audio_service import process_audio_frame

SAMPLE_RATE = 48000
SAMPLE_WIDTH = 2  # bytes (int16)
ICE_SERVERS = [{"urls": ["stun:stun.l.google.com:19302"]}]
AUDIO_GAIN = 2.0  # Volume boost multiplier (1.0 = original, 2.0 = double)

@dataclass
class RecorderStats:
    bytes_written: int = 0
    last_rms: float = 0.0
    detected_sample_rate: int = 48000  # Actual sample rate from WebRTC


_recorder_lock = threading.Lock()
_active_recorders: dict[str, wave.Wave_write] = {}
_recorder_stats: dict[str, RecorderStats] = {}
_recorder_threads: dict[str, threading.Thread] = {}
_recorder_stop_events: dict[str, threading.Event] = {}
_recorder_paths: dict[str, Path] = {}
_recorder_queues: dict[str, "queue.Queue[Optional[tuple[bytes, float]]]"] = {}
_current_token: Optional[str] = None
_current_token_lock = threading.Lock()
_callback_count: dict[str, int] = {}  # Track callback count per token


def render_mic_recorder_page() -> None:
    """Render standalone microphone capture page."""
    st.title("🎧 麥克風錄音測試")
    st.caption("使用瀏覽器授權麥克風，將原始音訊以 WAV 檔寫入 `resource/` 目錄。")

    _initialize_state()
    _render_controls()
    _render_webrtc_stream()
    _render_status_panel()


def _initialize_state() -> None:
    if "mic_capture_active" not in st.session_state:
        st.session_state.mic_capture_active = False
    if "mic_capture_token" not in st.session_state:
        st.session_state.mic_capture_token = None
    if "mic_capture_path" not in st.session_state:
        st.session_state.mic_capture_path = ""
    if "mic_capture_bytes" not in st.session_state:
        st.session_state.mic_capture_bytes = 0
    if "mic_capture_started_at" not in st.session_state:
        st.session_state.mic_capture_started_at = None
    if "mic_capture_status" not in st.session_state:
        st.session_state.mic_capture_status = ""
    if "mic_capture_last_refresh" not in st.session_state:
        st.session_state.mic_capture_last_refresh = 0.0
    if "mic_capture_last_bytes" not in st.session_state:
        st.session_state.mic_capture_last_bytes = 0
    if "mic_capture_last_rms" not in st.session_state:
        st.session_state.mic_capture_last_rms = 0.0
    if "mic_capture_worker_active" not in st.session_state:
        st.session_state.mic_capture_worker_active = False


def _render_controls() -> None:
    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "▶️ 開始錄音",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.mic_capture_active,
        ):
            _start_recording()

    with col2:
        if st.button(
            "⏹️ 停止錄音",
            type="secondary",
            use_container_width=True,
            disabled=not st.session_state.mic_capture_active,
        ):
            _stop_recording()

    status = st.session_state.mic_capture_status
    if status:
        st.info(status)


def _render_webrtc_stream() -> None:
    st.markdown("#### 🎙️ 麥克風串流")

    def audio_callback(frame: av.AudioFrame) -> av.AudioFrame:
        with _current_token_lock:
            token = _current_token

        if not token:
            return frame

        # Increment callback count for this token
        with _recorder_lock:
            count = _callback_count.get(token, 0) + 1
            _callback_count[token] = count

        try:
            # Get original frame info for debugging
            orig_rate = frame.sample_rate
            orig_samples = frame.samples

            # Use the tested and working conversion from audio_service.py
            # Apply volume gain to boost quiet recordings
            pcm_array = process_audio_frame(frame, gain=AUDIO_GAIN)
            pcm_bytes = pcm_array.tobytes()

            # Validate sample count
            actual_samples = len(pcm_array)

            if count == 1:
                print(f"[MicRecorder] === First Audio Frame ===")
                print(f"  Frame: sample_rate={orig_rate}, samples={orig_samples}")
                print(f"  Expected samples (mono): {orig_samples}")
                print(f"  Actual samples after conversion: {actual_samples}")
                if actual_samples != orig_samples:
                    print(f"  ⚠️  SAMPLE COUNT MISMATCH! Ratio: {actual_samples / orig_samples:.2f}x")
                else:
                    print(f"  ✅ Sample count correct!")
                print(f"  Final chunk: {len(pcm_bytes)} bytes = {actual_samples} samples * 2")
                print(f"  Duration: {actual_samples / orig_rate:.3f}s @ {orig_rate}Hz")

            # Update detected sample rate in stats (first time only)
            with _recorder_lock:
                stats = _recorder_stats.get(token)
                if stats:
                    if count == 1:
                        stats.detected_sample_rate = orig_rate
                        print(f"  ✅ Using sample rate: {orig_rate} Hz")
                    elif stats.detected_sample_rate != orig_rate:
                        print(f"[MicRecorder] Warning: sample rate changed from {stats.detected_sample_rate} to {orig_rate}")
                        stats.detected_sample_rate = orig_rate
        except Exception as exc:
            print(f"[MicRecorder] Callback error: {exc}")
            import traceback
            traceback.print_exc()
            return frame

        rms = float(calculate_rms(pcm_array)) if pcm_array.size else 0.0

        with _recorder_lock:
            q = _recorder_queues.get(token)

        if q is not None:
            try:
                q.put_nowait((pcm_bytes, rms))
                if count == 1:
                    print(f"[MicRecorder] First chunk queued successfully, RMS={rms:.1f}")
            except queue.Full:
                print(f"[MicRecorder] Warning: queue full at callback #{count}, dropping chunk")
        else:
            if count <= 5:
                print(f"[MicRecorder] Warning: No queue found for token {token[:8]} at callback #{count}")

        if count % 100 == 0:
            print(f"[MicRecorder] Audio callback progress: {count} frames processed")

        return frame

    rtc_configuration = RTCConfiguration({"iceServers": ICE_SERVERS})
    webrtc_ctx = webrtc_streamer(
        key="mic-recorder",
        mode=WebRtcMode.SENDONLY,
        audio_frame_callback=audio_callback,
        media_stream_constraints={"audio": True, "video": False},
        rtc_configuration=rtc_configuration,
        async_processing=True,
        desired_playing_state=st.session_state.mic_capture_active,
    )

    if st.session_state.mic_capture_active:
        if webrtc_ctx.state.playing:
            st.success("已取得麥克風串流，正在錄音中。")
        elif webrtc_ctx.state.signalling:
            st.warning("正在嘗試建立 WebRTC 連線，請確認瀏覽器已授權麥克風。")
        else:
            st.error("無法取得麥克風串流，請檢查瀏覽器權限。")
    else:
        st.info("點擊「開始錄音」後，瀏覽器會要求授權麥克風並開始保存音訊。")


def _render_status_panel() -> None:
    st.markdown("#### 📊 錄音狀態")

    token = st.session_state.get("mic_capture_token")
    bytes_written = st.session_state.get("mic_capture_last_bytes", 0)
    last_rms = st.session_state.get("mic_capture_last_rms", 0.0)
    detected_sample_rate = SAMPLE_RATE  # default

    if token:
        with _recorder_lock:
            stats = _recorder_stats.get(token)
        if stats:
            bytes_written = stats.bytes_written
            last_rms = stats.last_rms
            detected_sample_rate = stats.detected_sample_rate

    st.session_state.mic_capture_last_bytes = bytes_written
    st.session_state.mic_capture_last_rms = last_rms

    if st.session_state.mic_capture_path:
        st.write(f"📁 檔案：`{st.session_state.mic_capture_path}`")
    else:
        st.write("📁 尚未建立音訊檔案")

    minutes = 0.0
    if bytes_written:
        seconds = bytes_written / (detected_sample_rate * SAMPLE_WIDTH)
        minutes = seconds / 60.0
        st.write(f"⏱️ 已錄製：約 {seconds:.1f} 秒（{minutes:.2f} 分）")
    else:
        st.write("⏱️ 已錄製：0.0 秒")

    st.write(f"🔊 最新 RMS：{last_rms:.1f}")
    st.write(f"🎚️ 樣本率：{detected_sample_rate} Hz")

    if st.session_state.mic_capture_started_at:
        start_str = datetime.fromtimestamp(
            st.session_state.mic_capture_started_at
        ).strftime("%Y-%m-%d %H:%M:%S")
        st.write(f"🕒 開始時間：{start_str}")

def _recorder_worker(token: str) -> None:
    print(f"[MicRecorder] Worker thread started for token {token[:8]}...")

    with _recorder_lock:
        audio_queue = _recorder_queues.get(token)
        path = _recorder_paths.get(token)
        stats = _recorder_stats.get(token)
        stop_event = _recorder_stop_events.get(token)

    if audio_queue is None or path is None or stats is None or stop_event is None:
        print("[MicRecorder] Worker thread missing resources, exiting")
        return

    writer: Optional[wave.Wave_write] = None
    chunks_processed = 0
    total_bytes = 0

    while not stop_event.is_set():
        try:
            item = audio_queue.get(timeout=1.0)
        except queue.Empty:
            continue

        if item is None:
            print(f"[MicRecorder] Stop signal received, processed {chunks_processed} chunks, {total_bytes} bytes")
            break

        pcm_bytes, rms = item
        if not pcm_bytes:
            continue

        try:
            if writer is None:
                # Use detected sample rate from WebRTC, fallback to default
                sample_rate_to_use = stats.detected_sample_rate if stats.detected_sample_rate else SAMPLE_RATE
                print(f"[MicRecorder] Opening WAV file: {path}")
                print(f"[MicRecorder] Sample rate: {sample_rate_to_use} Hz")
                writer = wave.open(str(path), "wb")
                writer.setnchannels(1)
                writer.setsampwidth(SAMPLE_WIDTH)
                writer.setframerate(sample_rate_to_use)
                with _recorder_lock:
                    _active_recorders[token] = writer

            writer.writeframes(pcm_bytes)
            chunks_processed += 1
            total_bytes += len(pcm_bytes)

            if chunks_processed == 1:
                print(f"[MicRecorder] First chunk written: {len(pcm_bytes)} bytes, RMS={rms:.1f}")

            with _recorder_lock:
                stats.bytes_written += len(pcm_bytes)
                stats.last_rms = rms

            # Log progress every 50 chunks (~1-2 seconds)
            if chunks_processed % 50 == 0:
                duration = total_bytes / (stats.detected_sample_rate * SAMPLE_WIDTH)
                print(f"[MicRecorder] Progress: {chunks_processed} chunks, {duration:.1f}s")

        except Exception as exc:
            print(f"[MicRecorder] Worker write error: {exc}")
            import traceback
            traceback.print_exc()
            break

    # Close writer
    if writer:
        try:
            print(f"[MicRecorder] Closing WAV file, total: {total_bytes} bytes")
            writer.close()
        except Exception as exc:
            print(f"[MicRecorder] Error closing writer: {exc}")

    # Cleanup
    with _recorder_lock:
        _active_recorders.pop(token, None)
        _recorder_threads.pop(token, None)
        _recorder_stop_events.pop(token, None)
        _recorder_queues.pop(token, None)

    print(f"[MicRecorder] Worker thread finished")

def _ensure_worker_started(webrtc_ctx) -> None:
    token = st.session_state.get("mic_capture_token")
    if not token or st.session_state.get("mic_capture_worker_active"):
        return

    receiver = webrtc_ctx.audio_receiver
    if receiver is None:
        return

    stop_event = threading.Event()

    def worker() -> None:
        while not stop_event.is_set():
            try:
                frame = receiver.get_frame(timeout=1)
            except queue.Empty:
                continue
            except Exception as exc:
                print(f"Mic worker receiver error: {exc}")
                break

            try:
                pcm = process_audio_frame(frame)
            except Exception as exc:
                print(f"Mic worker frame decode error: {exc}")
                continue

            rms = float(calculate_rms(pcm)) if pcm.size else 0.0
            pcm_bytes = pcm.tobytes()

            with _recorder_lock:
                writer = _active_recorders.get(token)
                stats = _recorder_stats.get(token)
                path = _recorder_paths.get(token)

            if stats is None or path is None:
                continue

            if writer is None:
                sample_rate = getattr(frame, "sample_rate", 0) or SAMPLE_RATE
                try:
                    new_writer = wave.open(str(path), "wb")
                    new_writer.setnchannels(1)
                    new_writer.setsampwidth(SAMPLE_WIDTH)
                    new_writer.setframerate(sample_rate)
                except Exception as exc:
                    print(f"Mic worker open error: {exc}")
                    break
                with _recorder_lock:
                    _active_recorders[token] = new_writer
                    writer = new_writer
                    stats.sample_rate = sample_rate

            if writer is None:
                continue

            try:
                writer.writeframes(pcm_bytes)
            except Exception as exc:
                print(f"Mic worker write error: {exc}")
                break

            with _recorder_lock:
                stats.bytes_written += len(pcm_bytes)
                stats.last_rms = rms

        with _recorder_lock:
            _recorder_threads.pop(token, None)
            _recorder_stop_events.pop(token, None)
        st.session_state.mic_capture_worker_active = False

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    with _recorder_lock:
        _recorder_threads[token] = thread
        _recorder_stop_events[token] = stop_event

    st.session_state.mic_capture_worker_active = True


def _start_recording() -> None:
    if st.session_state.mic_capture_active:
        print("[MicRecorder] Already recording, ignoring start request")
        return

    resource_dir = Path("resource")
    resource_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"mic-record-{timestamp}.wav"
    filepath = resource_dir / filename

    token = str(uuid.uuid4())
    audio_queue: "queue.Queue[Optional[tuple[bytes, float]]]" = queue.Queue(maxsize=128)
    stop_event = threading.Event()

    print(f"[MicRecorder] === Starting new recording ===")
    print(f"[MicRecorder] Token: {token[:8]}...")
    print(f"[MicRecorder] File: {filepath}")

    with _recorder_lock:
        _active_recorders[token] = None
        _recorder_stats[token] = RecorderStats()
        _recorder_paths[token] = filepath
        _recorder_queues[token] = audio_queue
        _recorder_stop_events[token] = stop_event
        _callback_count[token] = 0  # Initialize callback counter

    thread = threading.Thread(target=_recorder_worker, args=(token,), daemon=True)
    thread.start()
    print(f"[MicRecorder] Worker thread started: {thread.name}")

    with _recorder_lock:
        _recorder_threads[token] = thread

    with _current_token_lock:
        global _current_token
        _current_token = token
        print(f"[MicRecorder] Current token set to: {token[:8]}...")

    st.session_state.mic_capture_active = True
    st.session_state.mic_capture_token = token
    st.session_state.mic_capture_path = str(filepath)
    st.session_state.mic_capture_started_at = time.time()
    st.session_state.mic_capture_status = f"開始錄音：{filename}"
    st.session_state.mic_capture_last_bytes = 0
    st.session_state.mic_capture_last_rms = 0.0
    st.session_state.mic_capture_worker_active = True

    print("[MicRecorder] Recording state initialized, waiting for WebRTC stream...")


def _stop_recording() -> None:
    if not st.session_state.mic_capture_active:
        return

    global _current_token
    with _current_token_lock:
        token = _current_token

    if not token:
        st.session_state.mic_capture_active = False
        return

    # First, send stop signal to queue and wait for worker to finish
    with _recorder_lock:
        audio_queue = _recorder_queues.get(token)
        stop_event = _recorder_stop_events.get(token)
        thread = _recorder_threads.get(token)

    # Send stop signal to worker
    if audio_queue is not None:
        try:
            audio_queue.put_nowait(None)
        except Exception:
            pass

    if stop_event:
        stop_event.set()

    # Wait for worker thread to finish processing queue (increased timeout)
    if thread and thread.is_alive():
        thread.join(timeout=3.0)

    # Now collect resources after worker has finished
    writer: Optional[wave.Wave_write] = None
    path: Optional[Path] = None

    with _recorder_lock:
        writer = _active_recorders.pop(token, None)
        stats = _recorder_stats.pop(token, None)
        _recorder_threads.pop(token, None)
        _recorder_stop_events.pop(token, None)
        path = _recorder_paths.pop(token, None)
        _recorder_queues.pop(token, None)
        callback_count = _callback_count.pop(token, 0)

    if writer:
        try:
            writer.close()
        except Exception:
            pass

    # Update stats - removed auto-delete of short recordings
    if stats:
        st.session_state.mic_capture_last_bytes = stats.bytes_written
        st.session_state.mic_capture_last_rms = stats.last_rms

        print(f"[MicRecorder] === Recording Summary ===")
        print(f"  Total callbacks: {callback_count}")
        print(f"  Bytes written: {stats.bytes_written}")
        print(f"  Sample rate: {stats.detected_sample_rate} Hz")

        # Log if recording was very short but don't delete
        if stats.bytes_written == 0:
            print(f"[MicRecorder] ⚠️  WARNING: No audio data written to {path}")
            if callback_count == 0:
                print(f"[MicRecorder] ⚠️  Audio callback was NEVER called - WebRTC stream may not have started")
            else:
                print(f"[MicRecorder] ⚠️  Audio callback was called {callback_count} times but no data was written")
                print(f"[MicRecorder] ⚠️  This suggests queue/worker issue - check logs above")
            st.session_state.mic_capture_status = "錄音已停止（未檢測到音訊數據）"
        else:
            duration_sec = stats.bytes_written / (stats.detected_sample_rate * SAMPLE_WIDTH)
            print(f"[MicRecorder] ✅ Recording successful: {duration_sec:.1f} seconds")
            st.session_state.mic_capture_status = f"錄音已停止（{duration_sec:.1f} 秒）"

    st.session_state.mic_capture_active = False
    st.session_state.mic_capture_token = None
    st.session_state.mic_capture_last_refresh = 0.0
    st.session_state.mic_capture_worker_active = False

    with _current_token_lock:
        _current_token = None
