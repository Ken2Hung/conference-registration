# Feature Specification: Real-time Microphone Voice Transcription

**Feature Branch**: `003-realtime-mic-transcription`
**Created**: 2025-10-29
**Status**: Draft
**Input**: User description: "即時麥克風語音轉錄功能，使用瀏覽器麥克風錄音並透過 OpenAI gpt-4o-mini-transcribe 模型進行即時逐字稿轉錄，支援實體檔案持久化"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Start and Stop Real-time Transcription (Priority: P1)

As a conference organizer or attendee, I want to click a single button to start recording audio from my microphone and see the transcribed text appear in real-time on screen, so that I can capture spoken content during sessions without manual typing.

**Why this priority**: This is the core value proposition of the feature - immediate voice-to-text conversion without file uploads. Without this, the feature has no utility.

**Independent Test**: Can be fully tested by clicking "Start Transcription", speaking into the microphone, observing text appearing on screen in near real-time (within 2-3 seconds), and clicking "Stop" to end the session.

**Acceptance Scenarios**:

1. **Given** I am on the transcription page, **When** I click "開始轉錄" (Start Transcription) button, **Then** the browser requests microphone permission and begins capturing audio
2. **Given** transcription has started and I am speaking, **When** audio is captured for 2 seconds, **Then** the transcribed text appears in the display area within 3 seconds
3. **Given** transcription is running, **When** I click "停止" (Stop) button, **Then** the recording stops and no new text is added to the transcript
4. **Given** I have stopped transcription, **When** I click "開始轉錄" again, **Then** a new transcription session starts and appends to the existing transcript

---

### User Story 2 - Persistent File Storage (Priority: P1)

As a user, I want my transcribed text to be automatically saved to a file on disk as it's being generated, so that I don't lose my work if the browser crashes or I accidentally close the tab.

**Why this priority**: Data persistence is critical for professional use cases. Without this, users risk losing valuable transcription work.

**Independent Test**: Can be tested by starting transcription, speaking for 30 seconds, checking that a `.txt` file exists in `resource/` directory with the transcribed content, and verifying content persists after browser refresh.

**Acceptance Scenarios**:

1. **Given** I start transcription without providing a filename, **When** transcription begins, **Then** a file is created in `resource/` directory with auto-generated name format `transcript-YYYYMMDD-HHMMSS.txt`
2. **Given** I start transcription with custom filename "meeting-notes", **When** transcription begins, **Then** a file named `meeting-notes.txt` is created in `resource/` directory
3. **Given** transcription is running, **When** new text segments are transcribed, **Then** each segment is immediately appended to the file
4. **Given** I start transcription, **When** the file is created, **Then** it includes a timestamp header with start time
5. **Given** I stop transcription, **When** the stop button is clicked, **Then** a timestamp footer with end time is written to the file

---

### User Story 3 - Download Transcript (Priority: P2)

As a user, I want to download the current transcript as a text file at any time during or after the session, so that I can easily share the content or process it in other applications.

**Why this priority**: While auto-save provides persistence, downloadable format offers portability and sharing capabilities. This is secondary to basic transcription functionality.

**Independent Test**: Can be tested by transcribing some content, clicking the download button, and verifying a `.txt` file downloads with all visible transcript content.

**Acceptance Scenarios**:

1. **Given** I have transcribed some content, **When** I click "下載目前逐字稿 (.txt)" button, **Then** a file named `transcript-live.txt` downloads containing all visible transcript text
2. **Given** transcription is actively running, **When** I click download, **Then** the file contains all content transcribed up to that moment

---

### User Story 4 - Adjustable Recording Parameters (Priority: P3)

As a user, I want to adjust the chunk duration and voice activity detection threshold, so that I can optimize transcription quality and cost based on my speaking style and environment.

**Why this priority**: This enhances user experience but is not essential for basic functionality. Default values work for most use cases.

**Independent Test**: Can be tested by adjusting the chunk duration slider from 2s to 5s, speaking, and observing that text updates occur at the new interval.

**Acceptance Scenarios**:

1. **Given** I am on the transcription page, **When** I adjust the "片段秒數" (Chunk Duration) slider to 3 seconds, **Then** audio is sent for transcription every 3 seconds instead of the default 2 seconds
2. **Given** I adjust the "VAD 音量門檻" (Voice Activity Detection Threshold) slider, **When** I speak softly below the threshold, **Then** quiet segments are filtered out and not sent for transcription
3. **Given** I speak loudly above the VAD threshold, **When** audio exceeds the threshold, **Then** the segment is processed and transcribed

---

### Edge Cases

- What happens when the user denies microphone permission?
  - System should display a clear error message explaining that microphone access is required

- What happens when network connection is lost during transcription?
  - Current audio chunk transcription may fail, error message should appear in transcript area with `[ERROR]` prefix
  - File should still contain all previously transcribed content

- What happens when the `resource/` directory doesn't exist?
  - System must automatically create the directory before writing

- What happens when a file with the same custom filename already exists?
  - Content is appended to the existing file (append mode)

- What happens when the transcription API returns an error?
  - Error message is displayed in the transcript area as `[ERROR] {error details}`
  - System continues running and processes subsequent chunks

- What happens when the user provides an invalid filename?
  - System automatically sanitizes the filename by replacing invalid characters with underscores

- What happens when multiple users run transcription simultaneously on the same server?
  - Each session has independent state in browser memory
  - If they specify the same filename, concurrent writes could corrupt the file - file locking prevents this

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST capture audio from the browser's microphone when user clicks the start button
- **FR-002**: System MUST process audio in configurable chunks (default 2 seconds, adjustable from 1 to 5 seconds)
- **FR-003**: System MUST send each audio chunk to OpenAI's audio transcription API using the `gpt-4o-mini-transcribe` model
- **FR-004**: System MUST display transcribed text in real-time as each chunk is processed
- **FR-005**: System MUST save transcribed text to a persistent file in `resource/` directory
- **FR-006**: System MUST auto-generate filenames in format `transcript-YYYYMMDD-HHMMSS.txt` when user doesn't provide a custom name
- **FR-007**: System MUST append `.txt` extension automatically if user provides a filename without it
- **FR-008**: System MUST create the `resource/` directory if it doesn't exist
- **FR-009**: System MUST write a start timestamp header when transcription begins
- **FR-010**: System MUST write an end timestamp footer when transcription stops
- **FR-011**: System MUST use thread-safe file operations to prevent data corruption during concurrent writes
- **FR-012**: System MUST provide a download button that allows users to save the current transcript
- **FR-013**: System MUST allow users to adjust the audio chunk duration via a slider (1.0 to 5.0 seconds, 0.5 increment)
- **FR-014**: System MUST allow users to adjust the Voice Activity Detection (VAD) threshold via a slider (50 to 1000 RMS)
- **FR-015**: System MUST filter out audio segments below the VAD threshold to reduce unnecessary API calls
- **FR-016**: System MUST handle microphone permission denial gracefully with user-friendly error messages
- **FR-017**: System MUST handle API transcription errors gracefully by displaying `[ERROR]` messages in the transcript
- **FR-018**: System MUST preserve previously transcribed content even when errors occur
- **FR-019**: System MUST display the current output file path to the user during transcription
- **FR-020**: System MUST use UTF-8 encoding for all file operations
- **FR-021**: System MUST sanitize user-provided filenames by replacing invalid characters with underscores

### Key Entities

- **Transcription Session**: Represents a single recording session from start to stop, containing start time, end time, accumulated transcript text, and associated file path
- **Audio Chunk**: A small segment of recorded audio (1-5 seconds), converted to WAV format, ready for transcription
- **Transcript Segment**: A piece of transcribed text resulting from a single audio chunk, stored both in memory and persisted to disk
- **File Output**: The persistent text file in `resource/` directory containing all transcript segments with timestamps

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can start transcription with a single button click and see their first transcribed text appear within 5 seconds of speaking
- **SC-002**: Transcribed text appears on screen within 3 seconds of completing each audio chunk
- **SC-003**: All transcribed content is automatically saved to disk within 1 second of being transcribed
- **SC-004**: Users can conduct a 30-minute transcription session without data loss or system crashes
- **SC-005**: The system successfully handles transcription sessions with at least 100 audio chunks (approximately 3-8 minutes of continuous speech)
- **SC-006**: Downloaded transcript files match the on-screen content with 100% accuracy
- **SC-007**: Users can successfully resume work after browser refresh by accessing their saved file in `resource/` directory
- **SC-008**: System prevents file corruption when multiple concurrent transcription sessions access the file system

## Assumptions

1. **Environment**: Users are running the application in a modern web browser that supports WebRTC and getUserMedia API (Chrome, Firefox, Safari, Edge)
2. **Microphone**: Users have a functional microphone connected to their device
3. **API Access**: Users have a valid OpenAI API key configured in environment variables
4. **Network**: Users have stable internet connection sufficient for streaming small audio chunks (approximately 10-50 KB per 2-second chunk)
5. **Language**: The default transcription language is based on the audio content (OpenAI API auto-detects language)
6. **Audio Quality**: Input audio is sampled at 48kHz as per WebRTC standard
7. **File System**: The application has write permissions to create and modify files in the `resource/` directory
8. **Deployment**: The application runs as a Streamlit web application on the user's local machine or a server they control

## Dependencies

1. **External APIs**: OpenAI Audio Transcription API (`/audio/transcriptions` endpoint with `gpt-4o-mini-transcribe` model)
2. **Browser Capabilities**: WebRTC support for microphone access
3. **Environment Configuration**: `OPENAI_API_KEY` must be configured in `.env` file or environment variables
4. **Storage**: Sufficient disk space in the `resource/` directory for storing transcript files

## Out of Scope

1. **Multi-language Selection**: Users cannot pre-select transcription language (relies on OpenAI's auto-detection)
2. **Real-time Editing**: Users cannot edit transcribed text directly in the interface
3. **Audio Playback**: System does not provide playback of recorded audio
4. **Speaker Identification**: System does not distinguish between multiple speakers
5. **Advanced VAD**: Voice Activity Detection is basic RMS-based threshold, not sophisticated ML-based detection
6. **Lower Latency Mode**: This implementation does not use OpenAI's Realtime API for true real-time bidirectional communication
7. **Audio File Upload**: Users cannot upload pre-recorded audio files for transcription
8. **Cloud Storage**: Transcripts are only saved to local file system, not cloud storage services
9. **Transcript History Management**: No UI for browsing, searching, or managing previously saved transcripts
10. **Export Formats**: Only plain text (.txt) format is supported, not Word, PDF, or other formats
