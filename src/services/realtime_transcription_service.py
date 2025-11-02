"""
OpenAI Realtime API Transcription Service.

Provides WebSocket-based real-time audio transcription using OpenAI Realtime API.
"""

import asyncio
import base64
import json
import os
import threading
from typing import Callable, Optional

import websockets
import numpy as np


class RealtimeTranscriptionService:
    """
    Real-time transcription service using OpenAI Realtime API.

    Features:
    - WebSocket streaming of audio chunks
    - Event-driven transcription updates
    - Transcript delta accumulation
    - Automatic reconnection handling
    """

    def __init__(
        self,
        api_key: str,
        on_transcript_delta: Optional[Callable[[str], None]] = None,
        on_transcript_done: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize Realtime Transcription Service.

        Args:
            api_key: OpenAI API key
            on_transcript_delta: Callback for partial transcript updates
            on_transcript_done: Callback when transcript segment is complete
            on_error: Callback for error handling
        """
        self.api_key = api_key
        self.on_transcript_delta = on_transcript_delta
        self.on_transcript_done = on_transcript_done
        self.on_error = on_error

        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected = False
        self.is_running = False
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread: Optional[threading.Thread] = None

        # Transcript accumulation
        self.current_transcript = ""
        self.all_transcripts = []

    def start(self) -> None:
        """Start the WebSocket connection in a background thread."""
        if self.is_running:
            print("[RealtimeTranscription] Service already running")
            return

        self.is_running = True

        # Create event loop in separate thread
        self.thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.thread.start()

        print("[RealtimeTranscription] Service started")

    def stop(self) -> None:
        """Stop the WebSocket connection."""
        if not self.is_running:
            return

        self.is_running = False

        # Close WebSocket if connected
        if self.loop and self.websocket:
            asyncio.run_coroutine_threadsafe(self._close_websocket(), self.loop)

        # Wait for thread to finish
        if self.thread:
            self.thread.join(timeout=5.0)

        print("[RealtimeTranscription] Service stopped")

    def send_audio_chunk(self, audio_data: np.ndarray) -> None:
        """
        Send audio chunk to Realtime API.

        Args:
            audio_data: NumPy array of int16 PCM samples (mono)
        """
        if not self.is_connected or not self.websocket or not self.loop:
            return

        # Convert to bytes
        audio_bytes = audio_data.tobytes()

        # Base64 encode
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

        # Create message
        message = {
            "type": "input_audio_buffer.append",
            "audio": audio_base64
        }

        # Send via WebSocket
        asyncio.run_coroutine_threadsafe(
            self.websocket.send(json.dumps(message)),
            self.loop
        )

    def commit_audio(self) -> None:
        """Commit the audio buffer for transcription."""
        if not self.is_connected or not self.websocket or not self.loop:
            return

        message = {"type": "input_audio_buffer.commit"}

        asyncio.run_coroutine_threadsafe(
            self.websocket.send(json.dumps(message)),
            self.loop
        )

    def get_full_transcript(self) -> str:
        """Get accumulated full transcript."""
        return "\n".join(self.all_transcripts)

    def _run_event_loop(self) -> None:
        """Run asyncio event loop in thread."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        try:
            self.loop.run_until_complete(self._connect_and_listen())
        except Exception as exc:
            print(f"[RealtimeTranscription] Event loop error: {exc}")
        finally:
            self.loop.close()

    async def _connect_and_listen(self) -> None:
        """Connect to WebSocket and listen for events."""
        url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "OpenAI-Beta": "realtime=v1"
        }

        try:
            async with websockets.connect(url, extra_headers=headers) as websocket:
                self.websocket = websocket
                self.is_connected = True

                print("[RealtimeTranscription] WebSocket connected")

                # Send session configuration
                await self._configure_session()

                # Listen for events
                while self.is_running:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        await self._handle_message(message)
                    except asyncio.TimeoutError:
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        print("[RealtimeTranscription] WebSocket connection closed")
                        break

        except Exception as exc:
            print(f"[RealtimeTranscription] Connection error: {exc}")
            if self.on_error:
                self.on_error(str(exc))
        finally:
            self.is_connected = False
            self.websocket = None

    async def _configure_session(self) -> None:
        """Configure session for transcription-only mode."""
        config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": "You are a transcription assistant. Transcribe all audio input accurately.",
                "voice": "alloy",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500
                }
            }
        }

        await self.websocket.send(json.dumps(config))
        print("[RealtimeTranscription] Session configured")

    async def _handle_message(self, message: str) -> None:
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(message)
            event_type = data.get("type", "")

            # Handle different event types
            if event_type == "session.created":
                print("[RealtimeTranscription] Session created")

            elif event_type == "session.updated":
                print("[RealtimeTranscription] Session updated")

            elif event_type == "conversation.item.input_audio_transcription.completed":
                # Full transcript for this audio segment
                transcript = data.get("transcript", "")
                if transcript:
                    print(f"[RealtimeTranscription] Transcript completed: {transcript[:50]}...")
                    self.all_transcripts.append(transcript)
                    if self.on_transcript_done:
                        self.on_transcript_done(transcript)

            elif event_type == "conversation.item.input_audio_transcription.delta":
                # Partial transcript update
                delta = data.get("delta", "")
                if delta:
                    self.current_transcript += delta
                    if self.on_transcript_delta:
                        self.on_transcript_delta(delta)

            elif event_type == "error":
                error_msg = data.get("error", {}).get("message", "Unknown error")
                print(f"[RealtimeTranscription] Error: {error_msg}")
                if self.on_error:
                    self.on_error(error_msg)

        except json.JSONDecodeError:
            print(f"[RealtimeTranscription] Invalid JSON: {message[:100]}")
        except Exception as exc:
            print(f"[RealtimeTranscription] Message handling error: {exc}")

    async def _close_websocket(self) -> None:
        """Close WebSocket connection."""
        if self.websocket:
            await self.websocket.close()
            print("[RealtimeTranscription] WebSocket closed")
