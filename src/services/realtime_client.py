"""
OpenAI Realtime transcription client.

This module manages a WebSocket connection to the OpenAI Realtime API
(`gpt-4o-mini-realtime`) so audio can be streamed and transcribed with
token-level updates.
"""

import base64
import json
import os
import queue
import ssl
import threading
import time
from typing import Optional

import websocket


class RealtimeConnectionError(RuntimeError):
    """Raised when the realtime client cannot connect or authenticate."""


class OpenAIRealtimeClient:
    """
    Thread-safe client for streaming audio to OpenAI Realtime API.

    Usage:
        output_q = queue.Queue()
        client = OpenAIRealtimeClient(output_queue=output_q)
        client.start()
        client.send_pcm_chunk(pcm_bytes, sample_rate=24000)
        ...
        client.close()
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini-realtime-preview",
        output_queue: Optional["queue.Queue[str]"] = None,
        system_prompt: Optional[str] = None,
    ) -> None:
        self.model = model
        self.output_queue = output_queue or queue.Queue()
        self.system_prompt = system_prompt or (
            "You transcribe Mandarin speech into Traditional Chinese text. "
            "Return only the spoken words without additional commentary."
        )

        self._ws: Optional[websocket.WebSocketApp] = None
        self._ws_thread: Optional[threading.Thread] = None
        self._sender_lock = threading.Lock()
        self._connected_event = threading.Event()
        self._closed_event = threading.Event()
        self._response_active = threading.Event()
        self._response_active.clear()

    # ------------------------------------------------------------------ #
    # Lifecycle management
    # ------------------------------------------------------------------ #
    def start(self) -> None:
        """Initialize and start the websocket client in a background thread."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RealtimeConnectionError(
                "OPENAI_API_KEY is not set; cannot establish realtime session."
            )

        url = f"wss://api.openai.com/v1/realtime?model={self.model}"
        headers = [
            f"Authorization: Bearer {api_key}",
            "OpenAI-Beta: realtime=v1",
        ]

        def on_open(_: websocket.WebSocketApp) -> None:
            self._configure_session()
            self._connected_event.set()

        def on_message(_: websocket.WebSocketApp, message: str) -> None:
            self._handle_message(message)

        def on_error(_: websocket.WebSocketApp, error: Exception) -> None:
            if not self._closed_event.is_set():
                self.output_queue.put_nowait(f"[Realtime error] {error}")

        def on_close(_: websocket.WebSocketApp, __: Optional[str], ___: Optional[str]) -> None:
            self._closed_event.set()
            self._connected_event.clear()

        self._ws = websocket.WebSocketApp(
            url,
            header=headers,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )

        self._ws_thread = threading.Thread(
            target=self._ws.run_forever,
            kwargs={
                "sslopt": {"cert_reqs": ssl.CERT_REQUIRED},
                "ping_interval": 10,
                "ping_timeout": 5,
            },
            daemon=True,
        )
        self._ws_thread.start()

        # Wait briefly for connection
        if not self._connected_event.wait(timeout=5):
            raise RealtimeConnectionError(
                "Failed to establish realtime WebSocket connection within 5 seconds."
            )

    def close(self) -> None:
        """Close websocket connection gracefully."""
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
        if self._ws_thread and self._ws_thread.is_alive():
            self._ws_thread.join(timeout=2)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def send_pcm_chunk(self, pcm_data: bytes, sample_rate: int) -> None:
        """
        Send PCM16 mono audio bytes to the realtime API.

        Args:
            pcm_data: PCM16 mono audio bytes.
            sample_rate: Sample rate in Hz (must match session configuration).
        """
        if not self._ws:
            raise RuntimeError("Realtime client not started.")

        if self._response_active.is_set():
            waited = 0.0
            while self._response_active.is_set() and waited < 5.0:
                time.sleep(0.05)
                waited += 0.05

            if self._response_active.is_set():
                try:
                    self.output_queue.put_nowait("[Realtime error] Timeout waiting for previous response to complete")
                except queue.Full:
                    pass
                return

        audio_b64 = base64.b64encode(pcm_data).decode("ascii")
        payloads = [
            {"type": "input_audio_buffer.append", "audio": audio_b64},
            {"type": "input_audio_buffer.commit"},
            {
                "type": "response.create",
                "response": {
                    "modalities": ["text"],
                    "instructions": self.system_prompt,
                },
            },
        ]

        with self._sender_lock:
            for payload in payloads:
                self._send_json(payload)
            self._response_active.set()

    def is_connected(self) -> bool:
        """Return True if websocket handshake completed."""
        return self._connected_event.is_set() and not self._closed_event.is_set()

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _configure_session(self) -> None:
        # Configure audio format to match PCM16 mono 24kHz (downsampled)
        payload = {
            "type": "session.update",
            "session": {
                "input_audio_format": "pcm16",
                "input_audio_sample_rate_hz": 24000,
                "input_audio_channels": 1,
                "modalities": ["text"],
            },
        }
        self._send_json(payload)

    def _handle_message(self, message: str) -> None:
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            return

        event_type = data.get("type")

        if event_type == "response.output_text.delta":
            delta = data.get("delta", "")
            if delta:
                self.output_queue.put_nowait(delta)

        elif event_type == "response.completed":
            self.output_queue.put_nowait("\n")  # signal completion of chunk
            self._response_active.clear()

        elif event_type in {"error", "response.error"}:
            message = data.get("error", {}).get("message") or data.get("message")
            if message:
                self.output_queue.put_nowait(f"[Realtime error] {message}")
            self._response_active.clear()

    def _send_json(self, payload: dict) -> None:
        if not self._ws:
            return
        try:
            self._ws.send(json.dumps(payload))
        except Exception as exc:
            self.output_queue.put_nowait(f"[Realtime error] {exc}")
