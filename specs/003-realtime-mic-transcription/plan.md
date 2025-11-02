# Implementation Plan: Real-time Microphone Voice Transcription

**Branch**: `003-realtime-mic-transcription` | **Date**: 2025-10-29 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-realtime-mic-transcription/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This feature adds real-time microphone voice transcription to the conference registration system. Users can click a button to start recording audio from their browser's microphone, which is captured in small chunks (default 2 seconds), sent to OpenAI's `gpt-4o-mini-transcribe` API for transcription, and displayed in real-time on screen. All transcribed text is automatically saved to persistent files in the `resource/` directory with timestamps. The feature uses `streamlit-webrtc` for browser microphone access, implements Voice Activity Detection (VAD) to reduce API costs, and provides adjustable parameters for chunk duration and VAD threshold.

## Technical Context

**Language/Version**: Python 3.9.6
**Primary Dependencies**: Streamlit 1.28.0, streamlit-webrtc, OpenAI Python SDK, PyAV, NumPy, python-dotenv
**Storage**: Local filesystem (`resource/` directory for transcript files)
**Testing**: pytest (existing project test framework)
**Target Platform**: Web application (browser-based via Streamlit)
**Project Type**: Single project (Streamlit web app)
**Performance Goals**:
- First transcribed text appears within 5 seconds of speaking
- Transcribed text appears within 3 seconds of completing each audio chunk
- File writes complete within 1 second of transcription
- Support 30-minute transcription sessions
- Handle at least 100 audio chunks per session

**Constraints**:
- Audio processing must not block UI responsiveness
- Thread-safe file operations required for concurrent writes
- WebRTC audio capture at 48kHz sample rate (browser standard)
- Queue-based architecture to decouple audio capture from transcription
- Maximum 2-minute timeout for individual API calls

**Scale/Scope**:
- Support multiple concurrent users (each with independent session state)
- Handle audio chunks of 1-5 seconds duration
- Transcript files can grow to several MB for long sessions
- Display up to 400 most recent transcript segments in UI to prevent performance degradation

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Note**: This project does not have a formalized constitution document. The following checks are based on the existing codebase patterns documented in CLAUDE.md:

### Architecture Compliance

- ✅ **Three-layer architecture**: The feature will follow the existing pattern with:
  - UI Layer: New Streamlit page for transcription UI
  - Service Layer: Transcription service and audio processing logic
  - Model Layer: Data classes for transcription sessions and audio chunks

- ✅ **Code patterns**: Will follow established patterns:
  - Service functions with caching (if applicable)
  - Thread-safe file operations using context managers
  - Streamlit session state for UI state management
  - Error handling with user-friendly messages

### Code Quality Standards

- ✅ **PEP 8 compliance**: All Python code will follow PEP 8 style guide
- ✅ **English code, Chinese responses**: Code and comments in English, user documentation in Traditional Chinese
- ✅ **Minimal changes**: Feature will be implemented with minimal disruption to existing codebase
- ✅ **No unused dependencies**: Only add dependencies explicitly required by the feature
- ✅ **Testing required**: Tests will be written and executed before marking feature complete

### Integration with Existing System

- ✅ **UI integration**: New transcription page will be accessible from dashboard (similar to admin panel pattern)
- ✅ **Consistent styling**: Will use existing CSS and theme patterns for visual consistency
- ✅ **File operations**: Will follow existing atomic file write patterns (create backup, lock, write, rename)
- ⚠️ **Separation of concerns**: This is a relatively independent feature with minimal coupling to existing conference registration logic

### Potential Violations

**None identified**. This feature is largely independent and follows existing architectural patterns. The only new pattern is real-time audio streaming, which requires new dependencies (`streamlit-webrtc`, `PyAV`) but is justified by the core requirement.

## Project Structure

### Documentation (this feature)

```text
specs/003-realtime-mic-transcription/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── transcription-service.md  # Service interface documentation
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# Existing structure (from CLAUDE.md)
src/
├── models/
│   ├── session.py           # Existing
│   ├── registrant.py        # Existing
│   └── transcription.py     # NEW: Transcription session and audio chunk models
├── services/
│   ├── session_service.py        # Existing
│   ├── registration_service.py   # Existing
│   ├── admin_service.py          # Existing
│   ├── transcription_service.py  # NEW: OpenAI API integration
│   └── audio_service.py          # NEW: Audio processing and chunking
├── ui/
│   ├── dashboard.py              # Existing
│   ├── session_detail.py         # Existing
│   ├── admin_panel.py            # Existing
│   └── transcription_page.py     # NEW: Real-time transcription UI
└── utils/
    ├── validation.py             # Existing
    ├── html_utils.py             # Existing
    └── audio_utils.py            # NEW: Audio format conversion utilities

# New resource directory for transcript files
resource/                          # NEW: Transcript output directory
└── .gitkeep                      # Ensure directory exists in repo

# Root level files
app.py                            # MODIFIED: Add transcription page routing
requirements.txt                  # MODIFIED: Add new dependencies
.env.example                      # MODIFIED: Add OPENAI_API_KEY documentation

# Tests
tests/
├── unit/
│   ├── models/
│   │   └── test_transcription.py         # NEW
│   ├── services/
│   │   ├── test_transcription_service.py # NEW
│   │   └── test_audio_service.py         # NEW
│   └── utils/
│       └── test_audio_utils.py           # NEW
└── integration/
    └── test_transcription_flow.py        # NEW: End-to-end transcription test
```

**Structure Decision**: Single project structure maintained. The feature adds new modules following the existing three-layer architecture pattern. New `resource/` directory is created at project root for transcript file storage. The transcription feature is implemented as a separate UI page accessed from the dashboard, similar to how the admin panel is structured.

## Complexity Tracking

No constitutional violations identified. This feature introduces necessary complexity for real-time audio processing but follows existing architectural patterns and does not violate any documented project principles.

## Phase 0: Research & Technology Decisions

### Research Topics

The following areas require research to resolve technical unknowns:

1. **streamlit-webrtc Integration**
   - How to properly configure WebRTC for audio-only streaming
   - Audio frame callback patterns and best practices
   - Error handling for microphone permission denial
   - Browser compatibility considerations

2. **OpenAI Audio Transcription API**
   - API endpoint configuration and authentication
   - Supported audio formats (WAV, PCM16)
   - Rate limits and retry strategies
   - Error response handling and user messaging

3. **Audio Processing**
   - Converting PyAV audio frames to NumPy arrays
   - PCM16 format requirements and conversion
   - WAV file header generation for API submission
   - Sample rate handling (48kHz WebRTC → API requirements)

4. **Voice Activity Detection (VAD)**
   - RMS-based threshold calculation
   - Optimal threshold ranges for different environments
   - Balance between cost savings and accuracy

5. **Thread Safety**
   - Queue-based architecture for audio chunk processing
   - File locking mechanisms for concurrent writes
   - Streamlit session state thread safety considerations

6. **Testing Strategy**
   - Mocking WebRTC audio input for unit tests
   - Mocking OpenAI API responses
   - Integration testing approach for audio pipeline
   - Performance benchmarking for latency requirements

### Technology Choices to Validate

1. **streamlit-webrtc vs alternatives**: Is this the best library for browser microphone access in Streamlit?
2. **PyAV for audio processing**: Appropriate choice for audio frame manipulation?
3. **Queue pattern**: Best approach for decoupling audio capture from transcription?
4. **Threading vs asyncio**: Which concurrency model is most appropriate?
5. **File append mode**: Adequate for concurrent writes, or need more sophisticated locking?

### Integration Patterns

1. **Streamlit page routing**: How to add new page to existing single-file `app.py`?
2. **Session state management**: How to prevent state leakage between concurrent users?
3. **Error display**: Follow existing error message patterns from other UI components?
4. **File operations**: Extend existing atomic write patterns to append mode?

## Phase 1: Design Artifacts

To be completed after Phase 0 research is consolidated in `research.md`.

### Expected Outputs

1. **data-model.md**: Entity definitions for:
   - TranscriptionSession
   - AudioChunk
   - TranscriptSegment
   - FileOutputConfig

2. **contracts/transcription-service.md**: Service interface specifications:
   - `transcribe_audio_chunk(wav_bytes: bytes) -> str`
   - `sanitize_filename(filename: str) -> str`
   - `create_transcript_file(file_path: str) -> None`
   - `append_to_transcript(file_path: str, text: str) -> None`

3. **quickstart.md**: Developer guide covering:
   - Environment setup (OpenAI API key)
   - Running the transcription feature locally
   - Testing with microphone input
   - Troubleshooting common issues

4. **Agent context update**: Update `.specify/memory/agents/claude.md` with:
   - streamlit-webrtc usage patterns
   - OpenAI Audio API integration
   - Audio processing pipeline architecture

## Phase 2: Task Generation

This phase is handled by the `/speckit.tasks` command and generates `tasks.md` with implementation steps derived from the design artifacts above.

## Notes

- This feature is relatively isolated from the conference registration logic, making it lower risk for the existing system
- The PR requirements document (`requirements/PR-gpt4o-transcripbe.md`) includes detailed implementation code that will serve as a reference during Phase 0 research
- Performance requirements are clearly defined in success criteria, enabling measurable validation
- The feature uses append-only file writes, which is different from existing atomic replace patterns but justified by the streaming nature of transcription
