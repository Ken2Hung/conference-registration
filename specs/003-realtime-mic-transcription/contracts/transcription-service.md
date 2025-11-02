# Service Contracts: Transcription Services

**Feature**: 003-realtime-mic-transcription
**Date**: 2025-10-29
**Related**: [data-model.md](../data-model.md) | [research.md](../research.md)

---

## Overview

This document defines the service layer interfaces for the real-time microphone voice transcription feature. Services are organized into two modules:

1. **TranscriptionService** (`src/services/transcription_service.py`): OpenAI API integration and file operations
2. **AudioService** (`src/services/audio_service.py`): Audio processing and chunking logic

All services follow the project's existing patterns (see `src/services/session_service.py` for reference).

---

## TranscriptionService

**Module**: `src/services/transcription_service.py`

### Purpose

Handles OpenAI Audio Transcription API integration and persistent file operations for transcript storage.

---

### Function: `transcribe_audio_chunk`

**Signature**:

```python
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
```

**Pre-conditions**:

- `OPENAI_API_KEY` environment variable must be set
- `wav_bytes` must be valid WAV format with header
- `wav_bytes` size must be > 44 bytes (header + data)
- If `language` provided, must be valid ISO-639-1 code

**Post-conditions**:

- On success: Returns transcribed text (may be empty string)
- On API error: Raises specific exception with details
- API call logged for debugging (not error cases)

**Error Handling**:

| Error Type | HTTP Code | When It Occurs | Recommended Action |
|------------|-----------|----------------|-------------------|
| `AuthenticationError` | 401 | Invalid API key | Check `.env` configuration |
| `RateLimitError` | 429 | Exceeded rate limit | Reduce chunk frequency or upgrade API tier |
| `APIConnectionError` | N/A | Network failure | Retry with exponential backoff |
| `APIError` | 500, 503 | Server error | Retry once, then display error to user |
| `ValueError` | N/A | Invalid input | Log and skip chunk |

**Performance Characteristics**:

- **Latency**: 1-3 seconds for 2-second audio chunk (typical)
- **Throughput**: Sequential processing (no parallelization at service layer)
- **Memory**: Allocates temporary BytesIO object (~10-50KB per call)

**Testing Strategy**:

- Mock `OpenAI` client in unit tests
- Verify API called with correct parameters (model, file, language)
- Test error handling for all exception types
- Validate return value stripping and empty string handling

---

### Function: `sanitize_filename`

**Signature**:

```python
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
```

**Pre-conditions**:

- `filename` is a string (may be empty)

**Post-conditions**:

- Returns safe filename for all major OS (Windows, macOS, Linux)
- Result contains only valid filesystem characters
- Minimum result length is 1 (fallback to "transcript" if empty)

**Validation Rules** (FR-021):

```python
# Invalid characters pattern (Windows most restrictive)
INVALID_CHARS = r'[<>:"/\\|?*\x00-\x1f]'

# Replacement character
REPLACEMENT = '_'

# Edge cases
assert sanitize_filename("") == "transcript"
assert sanitize_filename("...") == "transcript"
assert sanitize_filename("   ") == "transcript"
```

**Testing Strategy**:

- Test all invalid characters individually
- Test path traversal attempts (`../`, `../../`)
- Test empty and whitespace-only inputs
- Test Unicode characters (Chinese, emoji)
- Test maximum length filenames (255 characters)

---

### Function: `create_transcript_file`

**Signature**:

```python
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
        ValueError: file_path is relative or doesn't end with .txt
        OSError: Cannot create parent directory or write file
        PermissionError: Insufficient write permissions

    Side Effects:
        - Creates parent directory if it doesn't exist
        - Creates new file (overwrites if exists)
        - Writes UTF-8 BOM-less header with session metadata

    File Format:
        ========================================
        Transcription Session: {session_id}
        Started: {start_time in YYYY-MM-DD HH:MM:SS format}
        ========================================

        (transcript segments appear below)

    Example:
        >>> from datetime import datetime
        >>> create_transcript_file(
        ...     "/path/to/resource/transcript-20251029-143022.txt",
        ...     "uuid-1234-5678",
        ...     datetime.now()
        ... )
        # File created with header

    Thread Safety:
        - Uses threading.Lock (stored in session state) for file operations
        - Safe for concurrent calls from single Streamlit session
        - NOT safe for multi-process writes (use file locking if needed)
    """
```

**Pre-conditions**:

- `file_path` is absolute path
- `file_path` ends with `.txt`
- Parent directory is writable

**Post-conditions**:

- File exists at `file_path`
- File contains session header (3 lines + blank line)
- File encoding is UTF-8 without BOM
- File cursor positioned at end (ready for appends)

**File Operations**:

```python
# Pseudo-code
1. Validate file_path (absolute, .txt extension)
2. Extract directory from file_path
3. Create directory if not exists (os.makedirs with exist_ok=True)
4. Acquire file lock (threading.Lock from session state)
5. Open file in write mode ('w', encoding='utf-8')
6. Write header with session_id and start_time
7. Write blank separator line
8. Close file
9. Release lock
```

**Error Recovery**:

- If directory creation fails: Propagate OSError to caller
- If file write fails: Propagate OSError, file may be partially written
- If lock acquisition fails: Should not occur (threading.Lock blocks)

**Testing Strategy**:

- Test successful file creation with valid paths
- Test directory auto-creation
- Test file overwriting behavior
- Test invalid path formats (relative, no extension)
- Test permission errors (mock filesystem)

---

### Function: `append_to_transcript`

**Signature**:

```python
def append_to_transcript(
    file_path: str,
    text: str,
    timestamp: datetime
) -> None:
    """
    Append transcribed text segment to file.

    Args:
        file_path: Absolute path to existing transcript file
        text: Transcribed text to append (may include [ERROR] prefix)
        timestamp: When transcription completed

    Raises:
        FileNotFoundError: file_path does not exist
        ValueError: file_path is not absolute or text is empty
        OSError: File write error

    Side Effects:
        - Appends line to file in format: [{timestamp}] {text}
        - Adds newline after each segment
        - Flushes buffer to ensure data persisted

    File Format:
        [{YYYY-MM-DD HH:MM:SS}] Transcribed text here
        [{YYYY-MM-DD HH:MM:SS}] Another segment
        [{YYYY-MM-DD HH:MM:SS}] [ERROR] API error message

    Example:
        >>> append_to_transcript(
        ...     "/path/to/transcript.txt",
        ...     "這是轉錄的文字",
        ...     datetime(2025, 10, 29, 14, 30, 45)
        ... )
        # Appends: [2025-10-29 14:30:45] 這是轉錄的文字\n

    Thread Safety:
        - Uses threading.Lock for all file operations
        - Append mode ('a') with newline ensures atomic line writes
        - Safe for concurrent appends from single session
    """
```

**Pre-conditions**:

- File at `file_path` must exist (created by `create_transcript_file`)
- `file_path` is absolute path
- `text` is non-empty string (caller should skip empty results)

**Post-conditions**:

- One new line appended to file
- File remains valid UTF-8
- Buffer flushed to disk

**Performance Characteristics**:

- **Latency**: < 1ms for typical append (SC-003 requirement)
- **I/O Pattern**: Append-only, no seek operations
- **Buffering**: Python file buffer auto-flushes on newline
- **Locking**: Minimal contention (single writer per session)

**Concurrency Guarantees**:

```python
# Thread-safe pattern (in implementation)
with st.session_state.file_lock:  # Acquire lock
    with open(file_path, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {text}\n")
# Lock released, file closed
```

**Testing Strategy**:

- Test appending single segment
- Test appending multiple segments sequentially
- Test Unicode text (Chinese characters)
- Test error messages with [ERROR] prefix
- Test file growth over 100 segments
- Mock file operations to test error handling

---

### Function: `finalize_transcript_file`

**Signature**:

```python
def finalize_transcript_file(
    file_path: str,
    session_id: str,
    end_time: datetime,
    total_chunks: int,
    dropped_chunks: int
) -> None:
    """
    Append session footer to transcript file.

    Args:
        file_path: Absolute path to transcript file
        session_id: Session identifier (for verification)
        end_time: When recording stopped
        total_chunks: Total audio chunks processed
        dropped_chunks: Chunks filtered by VAD

    Raises:
        FileNotFoundError: file_path does not exist
        ValueError: Invalid arguments

    Side Effects:
        - Appends footer with session statistics
        - Closes session metadata

    File Format:
        ========================================
        Session Ended: {end_time in YYYY-MM-DD HH:MM:SS format}
        Total Chunks Processed: {total_chunks}
        Chunks Dropped (VAD): {dropped_chunks}
        ========================================

    Example:
        >>> finalize_transcript_file(
        ...     "/path/to/transcript.txt",
        ...     "uuid-1234-5678",
        ...     datetime(2025, 10, 29, 14, 35, 22),
        ...     87,
        ...     23
        ... )

    Thread Safety:
        - Uses threading.Lock for file append
        - Called once per session (on stop button click)
    """
```

**Pre-conditions**:

- File exists and contains header from `create_transcript_file`
- `end_time` > start_time (not validated here)
- `total_chunks` >= 0
- `dropped_chunks` >= 0

**Post-conditions**:

- File contains complete session record (header + segments + footer)
- File ready for download or archival

**Testing Strategy**:

- Test footer format matches specification
- Test statistics values appear correctly
- Test Unicode handling in session_id

---

## AudioService

**Module**: `src/services/audio_service.py`

### Purpose

Handles audio frame processing, chunking, format conversion, and Voice Activity Detection.

---

### Function: `process_audio_frame`

**Signature**:

```python
def process_audio_frame(frame: av.AudioFrame) -> np.ndarray:
    """
    Convert PyAV AudioFrame to mono int16 PCM NumPy array.

    Args:
        frame: PyAV AudioFrame from WebRTC (typically 48000Hz, 10-20ms duration)

    Returns:
        1D NumPy array of int16 samples (mono)

    Example:
        >>> # In WebRTC callback
        >>> def audio_frame_callback(frame: av.AudioFrame) -> av.AudioFrame:
        ...     pcm = process_audio_frame(frame)
        ...     # Process pcm_data...
        ...     return frame

    Logic:
        1. Extract PCM data using frame.to_ndarray()
        2. If stereo (2D array), mix to mono by averaging channels
        3. Convert to int16 format if not already
           - If float32 [-1.0, 1.0]: Scale to int16 [-32768, 32767]
           - Otherwise: Direct cast to int16
        4. Return 1D array

    Notes:
        - WebRTC typically provides float32 format
        - Stereo mixing uses simple average (not perceptual weighting)
        - Clipping may occur if float32 values exceed [-1.0, 1.0]
    """
```

**Pre-conditions**:

- `frame` is valid PyAV AudioFrame
- Frame contains audio data (not null)

**Post-conditions**:

- Returns 1D NumPy array with dtype=int16
- Array length matches frame sample count (accounting for mono conversion)

**Performance**:

- **Latency**: < 1ms for typical 10ms frame (480 samples)
- **Memory**: In-place operations where possible (NumPy copy=False)

---

### Function: `calculate_rms`

**Signature**:

```python
def calculate_rms(pcm: np.ndarray) -> float:
    """
    Calculate Root Mean Square (RMS) of audio signal.

    Args:
        pcm: 1D NumPy array of int16 samples

    Returns:
        RMS value (range: 0.0 to 32767.0 for int16)

    Example:
        >>> silent = np.zeros(1000, dtype=np.int16)
        >>> calculate_rms(silent)
        0.0
        >>> loud = np.full(1000, 10000, dtype=np.int16)
        >>> calculate_rms(loud)
        10000.0

    Formula:
        RMS = sqrt(mean(samples^2))

    Notes:
        - Converts to float64 internally to prevent overflow
        - Return value is float (not int)
        - Used for Voice Activity Detection threshold comparison
    """
```

**Pre-conditions**:

- `pcm` is 1D NumPy array with dtype=int16
- `pcm` is not empty

**Post-conditions**:

- Returns non-negative float
- Returns 0.0 for silent audio (all zeros)

**Accuracy**:

- Uses NumPy's sqrt and mean (double precision)
- Result accurate to ~6 decimal places

---

### Function: `has_voice_activity`

**Signature**:

```python
def has_voice_activity(pcm: np.ndarray, threshold: int) -> bool:
    """
    Detect voice activity in audio chunk using RMS threshold.

    Args:
        pcm: 1D NumPy array of int16 samples
        threshold: RMS threshold value (range: 50-1000)

    Returns:
        True if RMS >= threshold (voice detected)
        False if RMS < threshold (silence or noise)

    Example:
        >>> pcm = generate_audio_samples()  # Hypothetical
        >>> has_voice_activity(pcm, threshold=200)
        True  # Speech detected

    Decision Logic:
        - Calculate RMS of entire chunk
        - Compare to threshold
        - Return boolean result

    Tuning:
        - Low threshold (50-150): More sensitive, fewer drops, higher API cost
        - Mid threshold (150-300): Balanced (default: 200)
        - High threshold (300-1000): Less sensitive, more drops, lower API cost

    Limitations:
        - Cannot distinguish speech from loud non-speech sounds
        - May cut off soft speech below threshold
        - No temporal smoothing (each chunk independent)
    """
```

**Pre-conditions**:

- `pcm` is valid int16 NumPy array
- `threshold` is in valid range (50-1000)

**Post-conditions**:

- Returns boolean decision
- Decision is consistent (same input → same output)

**Testing Strategy**:

- Test with silent audio (all zeros) → False
- Test with loud audio (high RMS) → True
- Test threshold boundary cases (RMS == threshold)
- Test different threshold values affect results

---

### Function: `create_wav_chunk`

**Signature**:

```python
def create_wav_chunk(pcm: np.ndarray, sample_rate: int) -> bytes:
    """
    Convert PCM16 NumPy array to complete WAV file bytes.

    Args:
        pcm: 1D NumPy array of int16 samples
        sample_rate: Sample rate in Hz (typically 48000)

    Returns:
        Complete WAV file as bytes (header + PCM data)

    Example:
        >>> pcm_data = np.array([0, 100, 200, -100], dtype=np.int16)
        >>> wav_bytes = create_wav_chunk(pcm_data, 48000)
        >>> len(wav_bytes)
        52  # 44-byte header + 8 bytes PCM data
        >>> wav_bytes[:4]
        b'RIFF'

    WAV Header Format (44 bytes):
        Offset | Size | Field          | Value
        -------|------|----------------|-------
        0      | 4    | ChunkID        | "RIFF"
        4      | 4    | ChunkSize      | 36 + data_size
        8      | 4    | Format         | "WAVE"
        12     | 4    | Subchunk1ID    | "fmt "
        16     | 4    | Subchunk1Size  | 16 (PCM)
        20     | 2    | AudioFormat    | 1 (PCM)
        22     | 2    | NumChannels    | 1 (mono)
        24     | 4    | SampleRate     | 48000
        28     | 4    | ByteRate       | SampleRate * NumChannels * BitsPerSample/8
        32     | 2    | BlockAlign     | NumChannels * BitsPerSample/8
        34     | 2    | BitsPerSample  | 16
        36     | 4    | Subchunk2ID    | "data"
        40     | 4    | Subchunk2Size  | len(pcm) * 2
        44     | N    | PCM Data       | pcm.tobytes()

    Notes:
        - Uses little-endian byte order (struct.pack with '<')
        - No extra chunks (no metadata, no padding)
        - Compatible with OpenAI API requirements
    """
```

**Pre-conditions**:

- `pcm` is 1D NumPy array with dtype=int16
- `pcm` is not empty (len > 0)
- `sample_rate` > 0 (typically 48000)

**Post-conditions**:

- Returns valid WAV file bytes
- Header matches PCM data size
- Total size = 44 + (len(pcm) * 2) bytes

**Validation**:

```python
# Verify WAV structure
assert wav_bytes[:4] == b'RIFF'
assert wav_bytes[8:12] == b'WAVE'
assert wav_bytes[12:16] == b'fmt '
assert wav_bytes[36:40] == b'data'
assert len(wav_bytes) == 44 + len(pcm) * 2
```

**Testing Strategy**:

- Test with various PCM lengths (short, typical, long)
- Verify header fields are correct
- Test audio can be loaded by audio libraries (wave module)
- Test OpenAI API accepts generated WAV bytes

---

### Class: `AudioChunker`

**Purpose**: Accumulate audio frames into configurable-duration chunks with Voice Activity Detection.

**Signature**:

```python
class AudioChunker:
    """
    Accumulate audio frames into chunks for transcription.

    Attributes:
        sample_rate: Audio sample rate in Hz (default: 48000)
        chunk_duration: Target chunk size in seconds (default: 2.0)
        vad_threshold: Voice activity detection RMS threshold (default: 200)
        buffer: Internal PCM sample buffer (NumPy array)

    Example:
        >>> chunker = AudioChunker(sample_rate=48000, chunk_duration=2.0, vad_threshold=200)
        >>> # In WebRTC callback
        >>> def audio_frame_callback(frame):
        ...     pcm = process_audio_frame(frame)
        ...     chunk = chunker.push(pcm)
        ...     if chunk is not None:
        ...         # Process complete chunk
        ...         wav_bytes = create_wav_chunk(chunk, 48000)
        ...         # Send for transcription
        ...     return frame
    """

    def __init__(
        self,
        sample_rate: int = 48000,
        chunk_duration: float = 2.0,
        vad_threshold: int = 200
    ):
        """
        Initialize audio chunker.

        Args:
            sample_rate: Audio sample rate in Hz
            chunk_duration: Target chunk size in seconds (1.0-5.0)
            vad_threshold: RMS threshold for VAD (50-1000)

        Raises:
            ValueError: Invalid parameter values
        """

    def push(self, pcm: np.ndarray) -> Optional[np.ndarray]:
        """
        Add PCM samples to buffer and return chunk if complete.

        Args:
            pcm: 1D NumPy array of int16 samples (mono)

        Returns:
            Complete chunk (NumPy array) if buffer full AND voice detected
            None if buffer not full OR voice not detected

        Side Effects:
            - Accumulates samples in internal buffer
            - Extracts chunk and keeps remainder when buffer full
            - Applies VAD filter (discards silent chunks)

        Logic:
            1. Concatenate pcm to buffer
            2. Check if buffer length >= chunk_size
            3. If yes:
               a. Extract first chunk_size samples
               b. Keep remainder in buffer
               c. Calculate RMS of chunk
               d. If RMS >= vad_threshold: return chunk
               e. Else: return None (silent chunk dropped)
            4. If no: return None (accumulating)
        """

    def reset(self):
        """
        Clear internal buffer.

        Used when starting new session or after errors.
        """

    def get_buffer_duration(self) -> float:
        """
        Get duration of buffered audio in seconds.

        Returns:
            Duration in seconds of samples currently in buffer
        """
```

**Pre-conditions**:

- `chunk_duration` in range 1.0-5.0 seconds
- `vad_threshold` in range 50-1000

**Post-conditions**:

- Internal buffer never exceeds 2x chunk_size (prevents unbounded growth)
- Returned chunks always have exact length = chunk_size (except edge cases)

**State Management**:

```python
# Initial state
buffer: np.array([], dtype=np.int16)

# After push() calls
buffer: np.array([...], dtype=np.int16)  # Grows until chunk_size

# After chunk extracted
buffer: np.array([...], dtype=np.int16)  # Remainder kept
```

**Thread Safety**:

- NOT thread-safe (designed for single-threaded WebRTC callback)
- Each Streamlit session has independent chunker instance

**Testing Strategy**:

- Test accumulation over multiple push() calls
- Test chunk extraction when buffer full
- Test VAD filtering (silent chunks return None)
- Test buffer remainder handling
- Test reset() clears state
- Test get_buffer_duration() calculation

---

## Cross-Service Dependencies

### TranscriptionService depends on AudioService

```python
# In transcription workflow
from src.services import audio_service, transcription_service

# 1. Audio processing
pcm = audio_service.process_audio_frame(frame)

# 2. Chunking
chunk = chunker.push(pcm)  # AudioChunker instance

# 3. Format conversion
if chunk is not None:
    wav_bytes = audio_service.create_wav_chunk(chunk, 48000)

    # 4. Transcription
    text = transcription_service.transcribe_audio_chunk(wav_bytes)

    # 5. File persistence
    transcription_service.append_to_transcript(file_path, text, datetime.now())
```

### UI Layer depends on both services

```python
# In src/ui/transcription_page.py
from src.services.transcription_service import (
    create_transcript_file,
    sanitize_filename
)
from src.services.audio_service import AudioChunker

# Session initialization
chunker = AudioChunker(
    sample_rate=48000,
    chunk_duration=st.session_state.chunk_duration,
    vad_threshold=st.session_state.vad_threshold
)

# File creation
file_path = create_transcript_file(...)

# WebRTC callback uses both services
def audio_frame_callback(frame):
    pcm = audio_service.process_audio_frame(frame)
    chunk = chunker.push(pcm)
    # ... transcription workflow
```

---

## Error Handling Strategy

### Service-Level Error Categories

| Category | Services Affected | Handling Strategy |
|----------|------------------|-------------------|
| **API Errors** | TranscriptionService | Catch, format error message, return to caller |
| **File Errors** | TranscriptionService | Propagate to UI layer with user-friendly message |
| **Audio Errors** | AudioService | Log and skip invalid frames (graceful degradation) |
| **Validation Errors** | Both | Raise ValueError with clear message |

### User-Facing Error Messages

| Technical Error | User Message (Traditional Chinese) |
|----------------|-----------------------------------|
| `AuthenticationError` | ❌ 無效的 API 金鑰，請檢查環境變數 OPENAI_API_KEY |
| `RateLimitError` | ⚠️ API 請求超過限制，請稍後再試或升級帳號等級 |
| `APIConnectionError` | ⚠️ 網路連線失敗，請檢查網路連線 |
| `FileNotFoundError` | ❌ 找不到逐字稿檔案，請重新開始轉錄 |
| `PermissionError` | ❌ 無法寫入檔案，請檢查資料夾權限 |

---

## Performance Requirements

### Latency Targets (from Success Criteria)

| Operation | Target | Measured By |
|-----------|--------|-------------|
| First text appears | < 5 seconds | From start button to first display |
| Chunk transcription | < 3 seconds | From chunk complete to text display |
| File write | < 1 second | From transcription to file persisted |

### Service-Level Latency Budgets

| Service Function | Budget | Notes |
|-----------------|--------|-------|
| `process_audio_frame` | < 1ms | Must not block WebRTC callback |
| `create_wav_chunk` | < 10ms | Includes header generation |
| `transcribe_audio_chunk` | 1-3s | Network I/O, API processing |
| `append_to_transcript` | < 10ms | File I/O with locking |

---

## Testing Requirements

### Unit Test Coverage

**TranscriptionService**:
- ✅ Test API success case (mocked OpenAI client)
- ✅ Test each error type with appropriate mock responses
- ✅ Test filename sanitization with edge cases
- ✅ Test file creation and append operations
- ✅ Test footer generation with session statistics

**AudioService**:
- ✅ Test frame conversion (stereo to mono, float32 to int16)
- ✅ Test RMS calculation accuracy
- ✅ Test VAD threshold logic
- ✅ Test WAV header generation
- ✅ Test AudioChunker accumulation and extraction

### Integration Test Coverage

- ✅ Complete pipeline: Frame → PCM → Chunk → WAV → Transcription → File
- ✅ VAD filtering reduces API calls
- ✅ File locking prevents corruption with concurrent writes
- ✅ Error in one chunk doesn't stop processing

### Manual Test Coverage

- ✅ Real microphone input transcribed correctly
- ✅ Chinese and English speech both work
- ✅ VAD threshold adjustment affects behavior
- ✅ Files persist across browser refresh

---

## References

- **Data Model**: [data-model.md](../data-model.md) (entity definitions)
- **Research**: [research.md](../research.md) (technical decisions)
- **Specification**: [spec.md](../spec.md) (functional requirements)
- **Project Pattern**: `/src/services/session_service.py` (service structure)
