"""
Transcription service for real-time microphone voice transcription feature.

This module provides:
- OpenAI Audio Transcription API integration
- File operations for transcript persistence
- Filename sanitization
"""

import os
import re
import threading
from datetime import datetime
from typing import Optional
from io import BytesIO

import openai
from openai import OpenAI


# Global file lock for thread-safe file operations
_file_lock = threading.Lock()


def transcribe_audio_chunk(
    wav_bytes: bytes,
    language: Optional[str] = None,
    prompt: Optional[str] = None
) -> str:
    """
    Transcribe audio chunk using OpenAI API.

    Args:
        wav_bytes: Complete WAV file as bytes (including 44-byte header)
        language: Optional ISO-639-1 language code (e.g., 'zh', 'en')
                  If None, API auto-detects language
        prompt: Optional context to guide transcription (e.g., technical terms)

    Returns:
        Transcribed text as string (stripped of leading/trailing whitespace)
        Empty string if API returns no transcription

    Raises:
        openai.AuthenticationError: Invalid API key in environment
        openai.RateLimitError: API rate limit exceeded
        openai.APIConnectionError: Network connection failed
        openai.APIError: Other API errors (server issues, invalid request)
        ValueError: wav_bytes is empty or invalid format

    Example:
        >>> wav_data = audio_service.create_wav_chunk(pcm_data, 48000)
        >>> text = transcribe_audio_chunk(wav_data)
        >>> print(text)
        "這是一段測試語音"

    Notes:
        - Uses gpt-4o-mini-transcribe model (hardcoded)
        - Response format: "text" (plain string, not JSON)
        - API timeout: 2 minutes (sufficient for 1-5 second chunks)
        - Retries: Not implemented at service layer (handled by caller if needed)
    """
    # Validation
    if not wav_bytes or len(wav_bytes) <= 44:
        raise ValueError(
            f"wav_bytes must be > 44 bytes (header + data), got {len(wav_bytes)} bytes"
        )

    try:
        # Initialize OpenAI client
        client = OpenAI()

        # Create file-like object from bytes
        audio_file = BytesIO(wav_bytes)
        audio_file.name = "audio.wav"  # OpenAI client requires a name attribute

        # Call transcription API
        response = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=audio_file,
            language=language,
            prompt=prompt,
            response_format="text",
            timeout=120  # 2 minutes
        )

        # Extract and clean transcribed text
        text = str(response).strip()
        
        # Filter out prompt content if it appears in response (shouldn't happen but sometimes does)
        if prompt:
            prompt_lower = prompt.lower()
            text_lower = text.lower()
            if prompt_lower in text_lower:
                text = text.replace(prompt, "").replace(prompt_lower, "").strip()
        
        # Remove common artifacts
        text = text.replace("###", "").strip()
        text = text.replace("context:", "").replace("Context:", "").strip()
        
        # Remove prompt-like patterns
        if "transcribe only" in text.lower() or "ignore silence" in text.lower():
            return ""
        
        # Clean up extra whitespace
        text = " ".join(text.split())

        return text

    except openai.AuthenticationError as e:
        # Invalid API key
        raise openai.AuthenticationError(
            "OpenAI API 認證失敗，請檢查 OPENAI_API_KEY 環境變數設定是否正確"
        ) from e

    except openai.RateLimitError as e:
        # Rate limit exceeded
        raise openai.RateLimitError(
            "OpenAI API 速率限制已達上限，請稍後再試或升級 API 方案"
        ) from e

    except openai.APIConnectionError as e:
        # Network connection failed
        raise openai.APIConnectionError(
            "無法連接到 OpenAI API，請檢查網路連線"
        ) from e

    except openai.APIError as e:
        # Other API errors
        raise openai.APIError(
            f"OpenAI API 發生錯誤: {str(e)}"
        ) from e


def sanitize_filename(filename: str) -> str:
    """
    Sanitize user-provided filename for safe file system usage.

    Args:
        filename: User input filename (may include invalid characters)

    Returns:
        Sanitized filename with invalid characters replaced by underscores

    Example:
        >>> sanitize_filename("meeting:notes*2025")
        "meeting_notes_2025"
        >>> sanitize_filename("../../../etc/passwd")
        ".._.._..._etc_passwd"
        >>> sanitize_filename("合法中文檔名")
        "合法中文檔名"

    Logic:
        - Replace invalid filesystem characters: < > : " / \\ | ? * and control chars (0x00-0x1f)
        - Preserve Unicode characters (Chinese, Japanese, etc.)
        - Strip leading/trailing whitespace and dots
        - If result is empty after sanitization, return "transcript"

    Notes:
        - Does NOT add .txt extension (handled by FileOutputConfig)
        - Does NOT validate path traversal (parent directory checks done elsewhere)
        - Does NOT limit filename length (OS handles this)
    """
    # Invalid characters pattern (Windows most restrictive)
    INVALID_CHARS = r'[<>:"/\\|?*\x00-\x1f]'
    REPLACEMENT = '_'

    # Strip whitespace
    filename = filename.strip()

    # Replace invalid characters
    sanitized = re.sub(INVALID_CHARS, REPLACEMENT, filename)

    # Strip leading/trailing dots
    sanitized = sanitized.strip('.')

    # Fallback if empty
    if not sanitized:
        return "transcript"

    return sanitized


def create_transcript_file(
    file_path: str,
    session_id: str,
    start_time: datetime
) -> None:
    """
    Create new transcript file with header.

    Args:
        file_path: Absolute path to transcript file (.txt extension required)
        session_id: Unique identifier for the transcription session
        start_time: When recording started

    Raises:
        ValueError: Invalid file_path or parameters
        OSError: File system errors (permission, disk full, etc.)

    Example:
        >>> create_transcript_file(
        ...     "/path/to/resource/meeting.txt",
        ...     "abc-123",
        ...     datetime.now()
        ... )

    Notes:
        - Creates parent directory if it doesn't exist
        - Uses threading.Lock for thread-safe file creation
        - File is created in append mode to allow multiple sessions
        - Header format: "# START session_id YYYY-MM-DD HH:MM:SS"
    """
    # Validation
    if not file_path.endswith('.txt'):
        raise ValueError(f"file_path must end with .txt, got {file_path}")

    # Ensure parent directory exists
    parent_dir = os.path.dirname(file_path)
    os.makedirs(parent_dir, exist_ok=True)

    # Create file with header (thread-safe)
    with _file_lock:
        with open(file_path, 'a', encoding='utf-8') as f:
            timestamp_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"# START {session_id} {timestamp_str}\n")
            f.write(f"# ========================================\n\n")


def append_to_transcript(
    file_path: str,
    text: str,
    timestamp: Optional[datetime] = None
) -> None:
    """
    Append timestamped transcript segment to file.

    Args:
        file_path: Absolute path to transcript file
        text: Transcribed text to append
        timestamp: When transcription completed (default: now)

    Raises:
        OSError: File system errors

    Example:
        >>> append_to_transcript(
        ...     "/path/to/resource/meeting.txt",
        ...     "這是轉錄的文字",
        ...     datetime.now()
        ... )

    Notes:
        - Uses threading.Lock for thread-safe append
        - Format: "[YYYY-MM-DD HH:MM:SS] text"
        - Automatically adds newline after text
        - Guarantees < 1 second write latency (SC-003)
    """
    if timestamp is None:
        timestamp = datetime.now()

    # Format segment with timestamp
    timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp_str}] {text}\n"

    # Append to file (thread-safe)
    with _file_lock:
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(line)


def finalize_transcript_file(
    file_path: str,
    session_id: str,
    end_time: datetime,
    total_chunks: int,
    dropped_chunks: int
) -> None:
    """
    Append session footer when recording stops.

    Args:
        file_path: Absolute path to transcript file
        session_id: Unique identifier for the transcription session
        end_time: When recording stopped
        total_chunks: Total audio chunks processed
        dropped_chunks: Chunks dropped due to VAD filtering

    Example:
        >>> finalize_transcript_file(
        ...     "/path/to/resource/meeting.txt",
        ...     "abc-123",
        ...     datetime.now(),
        ...     100,
        ...     20
        ... )

    Notes:
        - Uses threading.Lock for thread-safe append
        - Footer includes: end time, session statistics
        - Format:
          # ========================================
          # END session_id YYYY-MM-DD HH:MM:SS
          # Total chunks: 100 | Dropped: 20
    """
    with _file_lock:
        with open(file_path, 'a', encoding='utf-8') as f:
            timestamp_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"\n# ========================================\n")
            f.write(f"# END   {session_id} {timestamp_str}\n")
            f.write(f"# Total chunks: {total_chunks} | Dropped: {dropped_chunks}\n\n")
