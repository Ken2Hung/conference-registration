# Data Model: Real-time Microphone Voice Transcription

**Feature**: 003-realtime-mic-transcription
**Date**: 2025-10-29
**Related**: [spec.md](spec.md) | [research.md](research.md) | [plan.md](plan.md)

---

## Overview

This document defines the data entities used in the real-time microphone voice transcription feature. All entities follow the project's dataclass pattern with built-in validation (see `src/models/session.py` for reference).

---

## Entity Definitions

### 1. TranscriptionSession

Represents a single recording session from start to stop, managing accumulated transcript content and associated file output.

**Location**: `src/models/transcription.py`

**Fields**:

| Field Name | Type | Description | Validation Rules |
|------------|------|-------------|-----------------|
| `session_id` | `str` | Unique identifier for the session | Auto-generated UUID format, read-only after creation |
| `start_time` | `datetime` | When recording started | Must be <= current time, required |
| `end_time` | `Optional[datetime]` | When recording stopped | Must be > start_time if set, None for active sessions |
| `file_path` | `str` | Absolute path to transcript file | Must end with `.txt`, parent directory must exist |
| `chunk_duration` | `float` | Audio chunk size in seconds | Range: 1.0-5.0, default: 2.0 |
| `vad_threshold` | `int` | Voice activity detection RMS threshold | Range: 50-1000, default: 200 |
| `segments` | `List[TranscriptSegment]` | Accumulated transcript segments | Default: empty list, append-only |
| `total_chunks` | `int` | Total audio chunks processed | >= 0, incremented on each chunk |
| `dropped_chunks` | `int` | Chunks dropped due to VAD filtering | >= 0, incremented when VAD filters silence |

**Methods**:

```python
def is_active(self) -> bool:
    """Check if session is currently recording."""
    return self.end_time is None

def duration_seconds(self) -> float:
    """Calculate session duration in seconds."""
    end = self.end_time or datetime.now()
    return (end - self.start_time).total_seconds()

def add_segment(self, segment: TranscriptSegment) -> None:
    """Add a new transcript segment and increment chunk counter."""
    self.segments.append(segment)
    self.total_chunks += 1

def get_full_transcript(self) -> str:
    """Join all segments into a single transcript string."""
    return "\n".join(seg.text for seg in self.segments)
```

**Validation Rules** (enforced in `__post_init__`):

- `chunk_duration` must be between 1.0 and 5.0 seconds
- `vad_threshold` must be between 50 and 1000
- `file_path` must have `.txt` extension
- `start_time` cannot be in the future
- If `end_time` is set, it must be after `start_time`
- `total_chunks` must be >= length of `segments` (accounts for VAD filtering)
- `dropped_chunks` must be >= 0

**State Transitions**:

```
Created (end_time=None)
    → Active (recording in progress)
    → Stopped (end_time set)
```

---

### 2. AudioChunk

Represents a small segment of recorded audio ready for transcription.

**Location**: `src/models/transcription.py`

**Fields**:

| Field Name | Type | Description | Validation Rules |
|------------|------|-------------|-----------------|
| `chunk_id` | `str` | Unique identifier for chunk | Auto-generated UUID format |
| `session_id` | `str` | Parent session identifier | Must reference valid TranscriptionSession |
| `pcm_data` | `np.ndarray` | Raw PCM16 audio samples | dtype must be int16, 1D array, length > 0 |
| `sample_rate` | `int` | Audio sample rate in Hz | Must be 48000 (WebRTC standard) |
| `timestamp` | `datetime` | When chunk was captured | Required, must be <= current time |
| `rms_value` | `float` | Root Mean Square audio level | >= 0.0, calculated from pcm_data |
| `has_voice` | `bool` | VAD result (True if voice detected) | Calculated based on RMS vs threshold |

**Methods**:

```python
def to_wav_bytes(self) -> bytes:
    """Convert PCM data to WAV format with proper header."""
    # Uses utility function from audio_utils
    from src.utils.audio_utils import pcm16_to_wav_bytes
    return pcm16_to_wav_bytes(self.pcm_data, self.sample_rate)

def duration_seconds(self) -> float:
    """Calculate chunk duration in seconds."""
    return len(self.pcm_data) / self.sample_rate

def calculate_rms(self) -> float:
    """Calculate RMS value of PCM data."""
    # Implementation delegated to audio_utils
    from src.utils.audio_utils import calculate_rms
    return calculate_rms(self.pcm_data)
```

**Validation Rules** (enforced in `__post_init__`):

- `pcm_data` must be 1D NumPy array with dtype int16
- `pcm_data` must not be empty (len > 0)
- `sample_rate` must be exactly 48000 Hz (WebRTC standard)
- `rms_value` must be >= 0.0
- `timestamp` cannot be in the future

**Lifecycle**:

1. Created from PyAV audio frames in WebRTC callback
2. Passes through VAD filter (sets `has_voice` flag)
3. If `has_voice=True`, queued for transcription
4. If `has_voice=False`, discarded (increments `dropped_chunks`)

---

### 3. TranscriptSegment

Represents a piece of transcribed text resulting from a single audio chunk.

**Location**: `src/models/transcription.py`

**Fields**:

| Field Name | Type | Description | Validation Rules |
|------------|------|-------------|-----------------|
| `segment_id` | `str` | Unique identifier for segment | Auto-generated UUID format |
| `session_id` | `str` | Parent session identifier | Must reference valid TranscriptionSession |
| `text` | `str` | Transcribed text from API | Can be empty string if API returns no text |
| `timestamp` | `datetime` | When transcription completed | Required, must be <= current time |
| `chunk_duration` | `float` | Duration of source audio chunk | > 0.0, typically 1.0-5.0 seconds |
| `error_message` | `Optional[str]` | Error details if transcription failed | None for successful transcriptions |

**Methods**:

```python
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
```

**Validation Rules** (enforced in `__post_init__`):

- `text` must be string (can be empty)
- `timestamp` cannot be in the future
- `chunk_duration` must be > 0.0
- If `error_message` is set, `text` should typically be empty (not enforced)

**Creation Patterns**:

- **Success case**: `error_message=None`, `text` contains transcribed content
- **Error case**: `error_message` contains error description, `text` may be empty
- **Empty speech case**: `error_message=None`, `text=""` (valid but unusual)

---

### 4. FileOutputConfig

Configuration for transcript file output behavior.

**Location**: `src/models/transcription.py`

**Fields**:

| Field Name | Type | Description | Validation Rules |
|------------|------|-------------|-----------------|
| `output_directory` | `str` | Directory for transcript files | Must be absolute path, default: `resource/` |
| `filename` | `Optional[str]` | Custom filename (without extension) | If None, auto-generate timestamp-based name |
| `append_mode` | `bool` | Whether to append to existing file | Default: True |
| `encoding` | `str` | File encoding | Must be "utf-8" (project standard) |
| `include_timestamps` | `bool` | Whether to include timestamps in file | Default: True |
| `timestamp_format` | `str` | Format string for timestamps | Default: "%Y-%m-%d %H:%M:%S" |

**Methods**:

```python
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

    if not safe_name.endswith('.txt'):
        safe_name += '.txt'

    return os.path.join(self.output_directory, safe_name)

def ensure_directory_exists(self) -> None:
    """Create output directory if it doesn't exist."""
    os.makedirs(self.output_directory, exist_ok=True)
```

**Validation Rules** (enforced in `__post_init__`):

- `output_directory` must be non-empty string
- `encoding` must be "utf-8"
- `timestamp_format` must be valid strftime format (checked by attempting format)
- `output_directory` is created automatically if it doesn't exist

**Usage Pattern**:

```python
# User provides custom filename
config = FileOutputConfig(filename="meeting-notes")
file_path = config.resolve_file_path()
# Result: resource/meeting-notes.txt

# User provides None (auto-generate)
config = FileOutputConfig(filename=None)
file_path = config.resolve_file_path()
# Result: resource/transcript-20251029-143022.txt
```

---

## Relationships Between Entities

```
TranscriptionSession (1)
    ├─── FileOutputConfig (1) [composition]
    ├─── AudioChunk (0..N) [transient - not stored in session]
    └─── TranscriptSegment (0..N) [aggregation]
```

**Explanation**:

- **One TranscriptionSession** manages the lifecycle of a recording session
- **One FileOutputConfig** defines output behavior (embedded in session)
- **Multiple AudioChunks** are processed during session but not stored (streaming nature)
- **Multiple TranscriptSegments** are accumulated in the session's `segments` list

**Data Flow**:

1. User starts transcription → Create `TranscriptionSession` with `FileOutputConfig`
2. WebRTC captures audio frames → Create `AudioChunk` from frames
3. AudioChunk passes VAD → Queued for transcription (or dropped)
4. OpenAI API processes chunk → Create `TranscriptSegment` with result
5. Segment added to session → Append to file via `append_to_transcript()`
6. User stops transcription → Set `session.end_time`, write footer

---

## Validation Constraints Summary

### FR-006: Auto-generated Filenames

```python
# Format: transcript-YYYYMMDD-HHMMSS.txt
pattern = r"^transcript-\d{8}-\d{6}\.txt$"
example = "transcript-20251029-143022.txt"
```

### FR-007: Automatic .txt Extension

```python
# Always append if missing
if not filename.endswith('.txt'):
    filename += '.txt'
```

### FR-013: Chunk Duration Range

```python
# Enforced in TranscriptionSession.__post_init__
if not (1.0 <= chunk_duration <= 5.0):
    raise ValueError("chunk_duration must be between 1.0 and 5.0 seconds")
```

### FR-014: VAD Threshold Range

```python
# Enforced in TranscriptionSession.__post_init__
if not (50 <= vad_threshold <= 1000):
    raise ValueError("vad_threshold must be between 50 and 1000")
```

### FR-020: UTF-8 Encoding

```python
# Enforced in FileOutputConfig.__post_init__
if encoding != 'utf-8':
    raise ValueError("encoding must be 'utf-8'")
```

### FR-021: Filename Sanitization

```python
# Invalid characters replaced with underscores
invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
sanitized = re.sub(invalid_chars, '_', filename)
```

---

## State Management

### TranscriptionSession State Diagram

```
┌─────────┐
│ Created │ (end_time=None, segments=[], total_chunks=0)
└────┬────┘
     │ User clicks "Start"
     ▼
┌─────────┐
│ Active  │ (end_time=None, receiving chunks)
└────┬────┘
     │ User clicks "Stop"
     ▼
┌─────────┐
│ Stopped │ (end_time set, no more chunks)
└─────────┘
```

**State Predicates**:

- `is_active()` returns `True` if `end_time is None`
- `is_active()` returns `False` if `end_time` is set

**Allowed Transitions**:

- Created → Active: Automatic on initialization (start_time set, end_time=None)
- Active → Stopped: User action or error (sets end_time)
- Stopped → Created: New session creation (separate instance)

**Disallowed Transitions**:

- Stopped → Active: Cannot restart a stopped session (must create new session)

---

## Integration with Existing Patterns

### Similarity to Session Model

- Both use dataclasses with `__post_init__` validation
- Both have status-checking methods (`is_active()` similar to `is_full()`, `is_past()`)
- Both manage collections of related entities (`segments` similar to `registrants`)
- Both enforce business rules through validation

### Differences from Session Model

- TranscriptionSession uses `datetime` objects directly (Session uses string dates)
- TranscriptionSession has streaming/temporal nature (Session is more static)
- TranscriptionSession doesn't persist to JSON (append-only file writes)
- TranscriptionSession uses NumPy arrays (Session uses primitive types only)

### Consistency with Project Standards

- ✅ English code with docstrings
- ✅ Type hints on all fields and methods
- ✅ Validation in `__post_init__` following PEP 8
- ✅ Dataclass pattern with default factories for mutable defaults
- ✅ Descriptive error messages for validation failures

---

## Testing Considerations

### Unit Test Coverage Required

1. **Validation Tests**:
   - Invalid chunk_duration values (0.5, 6.0)
   - Invalid vad_threshold values (49, 1001)
   - Invalid file_path values (no .txt extension, relative paths)
   - Invalid timestamps (future dates)

2. **Method Tests**:
   - `is_active()` with various end_time values
   - `duration_seconds()` calculation accuracy
   - `add_segment()` increments total_chunks correctly
   - `get_full_transcript()` joins segments properly
   - `to_wav_bytes()` produces valid WAV headers

3. **Edge Cases**:
   - Empty segments list
   - Zero dropped_chunks
   - Very long transcript (100+ segments)
   - Special characters in filenames

### Integration Test Scenarios

1. Full transcription session lifecycle (Create → Add segments → Stop)
2. File path resolution with custom and auto-generated names
3. VAD filtering updates dropped_chunks correctly
4. Error segments formatted with [ERROR] prefix

---

## Future Considerations

### Potential Extensions (Out of Scope for Current Feature)

- **Language Detection**: Add `language: str` field to TranscriptSegment
- **Confidence Scores**: Add `confidence: float` field if API provides it
- **Speaker Diarization**: Add `speaker_id: str` field for multi-speaker support
- **Edit History**: Track manual edits to transcript segments
- **Session Metadata**: Add tags, notes, or categorization

These extensions would require additional research and specification.

---

## References

- **Project Pattern**: `/src/models/session.py` (dataclass validation pattern)
- **Specification**: [spec.md](spec.md) (functional requirements)
- **Research**: [research.md](research.md) (audio processing decisions)
- **Implementation Plan**: [plan.md](plan.md) (architecture overview)
