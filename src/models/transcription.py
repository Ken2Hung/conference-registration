"""
Data models for real-time microphone voice transcription feature.

This module defines the core entities:
- TranscriptionSession: Manages a recording session lifecycle
- AudioChunk: Represents a segment of recorded audio
- TranscriptSegment: Contains transcribed text from an audio chunk
- FileOutputConfig: Configuration for transcript file output
"""

import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

import numpy as np


@dataclass
class TranscriptionSession:
    """
    Represents a single recording session from start to stop.

    Manages accumulated transcript content and associated file output.
    """

    session_id: str
    start_time: datetime
    file_path: str
    chunk_duration: float = 2.0  # seconds
    vad_threshold: int = 200  # RMS threshold
    end_time: Optional[datetime] = None
    segments: List['TranscriptSegment'] = field(default_factory=list)
    total_chunks: int = 0
    dropped_chunks: int = 0

    def __post_init__(self):
        """Validate session parameters."""
        # Validate chunk_duration
        if not (1.0 <= self.chunk_duration <= 5.0):
            raise ValueError(
                f"chunk_duration must be between 1.0 and 5.0 seconds, got {self.chunk_duration}"
            )

        # Validate vad_threshold
        if not (50 <= self.vad_threshold <= 1000):
            raise ValueError(
                f"vad_threshold must be between 50 and 1000, got {self.vad_threshold}"
            )

        # Validate file_path
        if not self.file_path.endswith('.txt'):
            raise ValueError(
                f"file_path must end with .txt extension, got {self.file_path}"
            )

        # Validate start_time
        if self.start_time > datetime.now():
            raise ValueError(
                f"start_time cannot be in the future: {self.start_time}"
            )

        # Validate end_time if set
        if self.end_time is not None:
            if self.end_time < self.start_time:
                raise ValueError(
                    f"end_time ({self.end_time}) must be after start_time ({self.start_time})"
                )

        # Validate counters
        if self.total_chunks < len(self.segments):
            raise ValueError(
                f"total_chunks ({self.total_chunks}) must be >= segments length ({len(self.segments)})"
            )

        if self.dropped_chunks < 0:
            raise ValueError(
                f"dropped_chunks must be >= 0, got {self.dropped_chunks}"
            )

    def is_active(self) -> bool:
        """Check if session is currently recording."""
        return self.end_time is None

    def duration_seconds(self) -> float:
        """Calculate session duration in seconds."""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()

    def add_segment(self, segment: 'TranscriptSegment') -> None:
        """Add a new transcript segment and increment chunk counter."""
        self.segments.append(segment)
        self.total_chunks += 1

    def get_full_transcript(self) -> str:
        """Join all segments into a single transcript string."""
        return "\n".join(seg.text for seg in self.segments if not seg.is_error())


@dataclass
class AudioChunk:
    """
    Represents a small segment of recorded audio ready for transcription.

    Contains raw PCM data and metadata for processing.
    """

    chunk_id: str
    session_id: str
    pcm_data: np.ndarray
    sample_rate: int
    timestamp: datetime
    rms_value: float = 0.0
    has_voice: bool = False

    def __post_init__(self):
        """Validate audio chunk parameters."""
        # Validate pcm_data
        if not isinstance(self.pcm_data, np.ndarray):
            raise ValueError(f"pcm_data must be numpy array, got {type(self.pcm_data)}")

        if self.pcm_data.ndim != 1:
            raise ValueError(f"pcm_data must be 1D array, got {self.pcm_data.ndim}D")

        if self.pcm_data.dtype != np.int16:
            raise ValueError(f"pcm_data must be int16, got {self.pcm_data.dtype}")

        if len(self.pcm_data) == 0:
            raise ValueError("pcm_data must not be empty")

        # Validate sample_rate
        if self.sample_rate != 48000:
            raise ValueError(
                f"sample_rate must be 48000 Hz (WebRTC standard), got {self.sample_rate}"
            )

        # Validate rms_value
        if self.rms_value < 0.0:
            raise ValueError(f"rms_value must be >= 0.0, got {self.rms_value}")

        # Validate timestamp
        if self.timestamp > datetime.now():
            raise ValueError(f"timestamp cannot be in the future: {self.timestamp}")

    def to_wav_bytes(self) -> bytes:
        """Convert PCM data to WAV format with proper header."""
        from src.utils.audio_utils import pcm16_to_wav_bytes
        return pcm16_to_wav_bytes(self.pcm_data, self.sample_rate)

    def duration_seconds(self) -> float:
        """Calculate chunk duration in seconds."""
        return len(self.pcm_data) / self.sample_rate

    def calculate_rms(self) -> float:
        """Calculate RMS value of PCM data."""
        from src.utils.audio_utils import calculate_rms
        return calculate_rms(self.pcm_data)


@dataclass
class TranscriptSegment:
    """
    Represents a piece of transcribed text resulting from a single audio chunk.

    Can contain either successful transcription or error information.
    """

    segment_id: str
    session_id: str
    text: str
    timestamp: datetime
    chunk_duration: float
    error_message: Optional[str] = None

    def __post_init__(self):
        """Validate segment parameters."""
        # Validate text (can be empty string)
        if not isinstance(self.text, str):
            raise ValueError(f"text must be string, got {type(self.text)}")

        # Validate timestamp
        if self.timestamp > datetime.now():
            raise ValueError(f"timestamp cannot be in the future: {self.timestamp}")

        # Validate chunk_duration
        if self.chunk_duration <= 0.0:
            raise ValueError(f"chunk_duration must be > 0.0, got {self.chunk_duration}")

    def is_error(self) -> bool:
        """Check if segment represents a transcription error."""
        return self.error_message is not None

    def formatted_text(self) -> str:
        """Format segment for display with error prefix if needed."""
        if self.is_error():
            return f"[ERROR] {self.error_message}"
        return self.text

    def to_file_line(self) -> str:
        """Format segment for file output with timestamp."""
        timestamp_str = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        return f"[{timestamp_str}] {self.formatted_text()}"


@dataclass
class FileOutputConfig:
    """
    Configuration for transcript file output behavior.

    Manages file path resolution and directory creation.
    """

    output_directory: str = "resource"
    filename: Optional[str] = None
    append_mode: bool = True
    encoding: str = "utf-8"
    include_timestamps: bool = True
    timestamp_format: str = "%Y-%m-%d %H:%M:%S"

    def __post_init__(self):
        """Validate configuration parameters."""
        # Validate output_directory
        if not self.output_directory:
            raise ValueError("output_directory must not be empty")

        # Validate encoding
        if self.encoding != "utf-8":
            raise ValueError(f"encoding must be 'utf-8', got '{self.encoding}'")

        # Validate timestamp_format
        try:
            datetime.now().strftime(self.timestamp_format)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid timestamp_format: {e}")

        # Create output directory if it doesn't exist
        self.ensure_directory_exists()

    def resolve_file_path(self) -> str:
        """
        Generate absolute file path for transcript file.

        Returns:
            Absolute path with .txt extension

        Logic:
            - If filename provided: sanitize and use it
            - If filename None: auto-generate as 'transcript-YYYYMMDD-HHMMSS.txt'
            - Always append .txt extension if not present
            - Combine with output_directory
        """
        from src.services.transcription_service import sanitize_filename

        if self.filename:
            safe_name = sanitize_filename(self.filename)
        else:
            safe_name = f"transcript-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        base_name, ext = os.path.splitext(safe_name)
        if ext.lower() != ".txt":
            ext = ".txt"

        candidate = os.path.join(self.output_directory, f"{base_name}{ext}")
        counter = 2
        while os.path.exists(candidate):
            candidate = os.path.join(self.output_directory, f"{base_name}_{counter}{ext}")
            counter += 1

        return candidate

    def ensure_directory_exists(self) -> None:
        """Create output directory if it doesn't exist."""
        os.makedirs(self.output_directory, exist_ok=True)


# Helper function to create new session
def create_session(
    file_path: str,
    chunk_duration: float = 2.0,
    vad_threshold: int = 200
) -> TranscriptionSession:
    """
    Create a new transcription session with auto-generated ID.

    Args:
        file_path: Path to transcript output file
        chunk_duration: Audio chunk size in seconds (1.0-5.0)
        vad_threshold: Voice activity detection RMS threshold (50-1000)

    Returns:
        New TranscriptionSession instance
    """
    return TranscriptionSession(
        session_id=str(uuid.uuid4()),
        start_time=datetime.now(),
        file_path=file_path,
        chunk_duration=chunk_duration,
        vad_threshold=vad_threshold
    )


# Helper function to create audio chunk
def create_audio_chunk(
    session_id: str,
    pcm_data: np.ndarray,
    sample_rate: int = 48000
) -> AudioChunk:
    """
    Create a new audio chunk with auto-generated ID.

    Args:
        session_id: Parent session identifier
        pcm_data: PCM16 audio samples as NumPy array
        sample_rate: Audio sample rate in Hz

    Returns:
        New AudioChunk instance
    """
    from src.utils.audio_utils import calculate_rms

    chunk = AudioChunk(
        chunk_id=str(uuid.uuid4()),
        session_id=session_id,
        pcm_data=pcm_data,
        sample_rate=sample_rate,
        timestamp=datetime.now(),
        rms_value=calculate_rms(pcm_data)
    )

    return chunk


# Helper function to create transcript segment
def create_transcript_segment(
    session_id: str,
    text: str,
    chunk_duration: float,
    error_message: Optional[str] = None
) -> TranscriptSegment:
    """
    Create a new transcript segment with auto-generated ID.

    Args:
        session_id: Parent session identifier
        text: Transcribed text
        chunk_duration: Duration of source audio chunk
        error_message: Error details if transcription failed

    Returns:
        New TranscriptSegment instance
    """
    return TranscriptSegment(
        segment_id=str(uuid.uuid4()),
        session_id=session_id,
        text=text,
        timestamp=datetime.now(),
        chunk_duration=chunk_duration,
        error_message=error_message
    )
