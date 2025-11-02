# Implementation Tasks: Real-time Microphone Voice Transcription

**Feature**: 003-realtime-mic-transcription
**Created**: 2025-10-29
**Branch**: `003-realtime-mic-transcription`
**Related**: [spec.md](spec.md) | [plan.md](plan.md) | [data-model.md](data-model.md) | [contracts/transcription-service.md](contracts/transcription-service.md)

---

## Task Summary

- **Total Tasks**: 42
- **User Story 1 Tasks**: 13 (P1 - Start and Stop Real-time Transcription)
- **User Story 2 Tasks**: 8 (P1 - Persistent File Storage)
- **User Story 3 Tasks**: 3 (P2 - Download Transcript)
- **User Story 4 Tasks**: 4 (P3 - Adjustable Parameters)
- **Setup Tasks**: 5
- **Foundational Tasks**: 2
- **Polish Tasks**: 7

---

## Task Format

```
- [ ] [TaskID] [P?] [Story?] Description with exact file path
```

Where:
- **TaskID**: Sequential identifier (T001, T002, etc.)
- **[P]**: Indicates task can be parallelized (different files, no blocking dependencies)
- **[Story]**: User story reference ([US1], [US2], [US3], [US4]) - only for user story tasks
- **Description**: Clear action with exact file path

---

## Phase 1: Setup (Shared Infrastructure)

**Goal**: Create project directories and update configuration files for the new feature.

- [ ] [T001] [P] Create resource/ directory at project root for transcript file storage
- [ ] [T002] [P] Create .gitkeep file at resource/.gitkeep to ensure directory exists in repository
- [ ] [T003] [P] Update requirements.txt to add streamlit-webrtc, openai>=1.0.0, PyAV>=10.0.0, numpy>=1.24.0, python-dotenv>=1.0.0 dependencies
- [ ] [T004] [P] Update .env.example to add OPENAI_API_KEY configuration with documentation comment
- [ ] [T005] Verify all setup directories and files exist by running ls commands to confirm structure

---

## Phase 2: Foundational (Blocking Prerequisites)

**Goal**: Create utility modules that all user stories depend on.

- [ ] [T006] Create src/utils/audio_utils.py with calculate_rms() function for Voice Activity Detection RMS calculation
- [ ] [T007] Implement pcm16_to_wav_bytes() function in src/utils/audio_utils.py to generate WAV file headers for OpenAI API submission

**Notes**:
- These utility functions are used by both AudioService and data models
- Tests for utilities belong to their respective user stories (US1)
- No tests are created in this phase per specification requirements

---

## Phase 3: User Story 1 - Start and Stop Real-time Transcription (P1)

**Goal**: Users can click start/stop buttons and see real-time transcription appear on screen.

**Independent Test**: Click start, speak into microphone, see text appear within 5 seconds, click stop.

### Data Models

- [ ] [T008] [US1] Create src/models/transcription.py with TranscriptionSession dataclass including session_id, start_time, end_time, file_path, chunk_duration, vad_threshold, segments, total_chunks, dropped_chunks fields
- [ ] [T009] [US1] Add TranscriptionSession validation in __post_init__ method to enforce chunk_duration (1.0-5.0s), vad_threshold (50-1000), and file_path (.txt extension) constraints
- [ ] [T010] [US1] Implement TranscriptionSession methods: is_active(), duration_seconds(), add_segment(), get_full_transcript() in src/models/transcription.py
- [ ] [T011] [US1] Create AudioChunk dataclass in src/models/transcription.py with chunk_id, session_id, pcm_data (np.ndarray), sample_rate, timestamp, rms_value, has_voice fields
- [ ] [T012] [US1] Add AudioChunk validation in __post_init__ to enforce pcm_data is 1D int16 NumPy array, sample_rate=48000Hz, and rms_value>=0.0
- [ ] [T013] [US1] Implement AudioChunk methods: to_wav_bytes(), duration_seconds(), calculate_rms() in src/models/transcription.py
- [ ] [T014] [US1] Create TranscriptSegment dataclass in src/models/transcription.py with segment_id, session_id, text, timestamp, chunk_duration, error_message fields
- [ ] [T015] [US1] Implement TranscriptSegment methods: is_error(), formatted_text(), to_file_line() in src/models/transcription.py

### Audio Service

- [ ] [T016] [US1] Create src/services/audio_service.py with process_audio_frame() function to convert PyAV AudioFrame to mono int16 PCM NumPy array
- [ ] [T017] [US1] Implement calculate_rms() function in src/services/audio_service.py to calculate Root Mean Square audio level for Voice Activity Detection
- [ ] [T018] [US1] Implement has_voice_activity() function in src/services/audio_service.py to detect voice using RMS threshold comparison
- [ ] [T019] [US1] Implement create_wav_chunk() function in src/services/audio_service.py to generate complete WAV file bytes with 44-byte header
- [ ] [T020] [US1] Create AudioChunker class in src/services/audio_service.py with __init__, push(), reset(), get_buffer_duration() methods for accumulating audio frames into configurable-duration chunks

### Transcription Service

- [ ] [T021] [US1] Create src/services/transcription_service.py with transcribe_audio_chunk() function to call OpenAI gpt-4o-mini-transcribe API
- [ ] [T022] [US1] Implement error handling in transcribe_audio_chunk() for AuthenticationError, RateLimitError, APIConnectionError, APIError with user-friendly Chinese error messages
- [ ] [T023] [US1] Implement sanitize_filename() function in src/services/transcription_service.py to replace invalid filesystem characters with underscores

### UI Implementation

- [ ] [T024] [US1] Create src/ui/transcription_page.py with render_transcription_page() function including page title, session state initialization, and basic layout structure
- [ ] [T025] [US1] Add WebRTC audio component to src/ui/transcription_page.py using webrtc_streamer() with audio-only configuration
- [ ] [T026] [US1] Implement audio_frame_callback() function in src/ui/transcription_page.py to process PyAV frames, accumulate chunks using AudioChunker, and queue chunks for transcription
- [ ] [T027] [US1] Create queue-based worker thread in src/ui/transcription_page.py to dequeue audio chunks, call transcribe_audio_chunk(), and update session state with results
- [ ] [T028] [US1] Add start/stop button handlers in src/ui/transcription_page.py to manage TranscriptionSession lifecycle (create session, start WebRTC, stop recording)
- [ ] [T029] [US1] Implement real-time transcript display area in src/ui/transcription_page.py showing accumulated TranscriptSegments with [ERROR] prefix for failures
- [ ] [T030] Update app.py to add transcription page routing using st.sidebar navigation and conditional page rendering

---

## Phase 4: User Story 2 - Persistent File Storage (P1)

**Goal**: Automatically save transcripts to resource/ directory as text is generated.

**Independent Test**: Start transcription, speak for 30 seconds, verify file exists in resource/ with content, refresh browser and verify persistence.

### File Output Configuration

- [ ] [T031] [US2] Create FileOutputConfig dataclass in src/models/transcription.py with output_directory, filename, append_mode, encoding, include_timestamps, timestamp_format fields
- [ ] [T032] [US2] Add FileOutputConfig validation in __post_init__ to enforce encoding="utf-8" and valid timestamp_format
- [ ] [T033] [US2] Implement FileOutputConfig methods: resolve_file_path() (auto-generate filename if None) and ensure_directory_exists() in src/models/transcription.py

### File Operations

- [ ] [T034] [US2] Implement create_transcript_file() function in src/services/transcription_service.py to create new file with session header (session_id, start_time) using threading.Lock
- [ ] [T035] [US2] Implement append_to_transcript() function in src/services/transcription_service.py to append timestamped transcript segments to file with thread-safe locking
- [ ] [T036] [US2] Implement finalize_transcript_file() function in src/services/transcription_service.py to append session footer (end_time, total_chunks, dropped_chunks) when recording stops

### UI Integration

- [ ] [T037] [US2] Add filename input field to src/ui/transcription_page.py with sanitization using sanitize_filename() and auto-generation fallback
- [ ] [T038] [US2] Integrate create_transcript_file() call in start button handler in src/ui/transcription_page.py to initialize file when recording begins
- [ ] [T039] [US2] Update worker thread in src/ui/transcription_page.py to call append_to_transcript() immediately after each successful transcription
- [ ] [T040] [US2] Add finalize_transcript_file() call in stop button handler in src/ui/transcription_page.py to write session footer
- [ ] [T041] [US2] Display current transcript file path in UI below transcript display area in src/ui/transcription_page.py

---

## Phase 5: User Story 3 - Download Transcript (P2)

**Goal**: Users can download current transcript as .txt file during or after recording.

**Independent Test**: Transcribe some content, click download button, verify downloaded file contains all visible transcript text.

- [ ] [T042] [US3] Add download button to src/ui/transcription_page.py using st.download_button() with transcript-live.txt default filename
- [ ] [T043] [US3] Implement get_download_content() helper function in src/ui/transcription_page.py to format transcript with header, segments, and statistics for download
- [ ] [T044] [US3] Wire download button to current session transcript using TranscriptionSession.get_full_transcript() method in src/ui/transcription_page.py

---

## Phase 6: User Story 4 - Adjustable Parameters (P3)

**Goal**: Users can adjust chunk duration and VAD threshold via UI sliders.

**Independent Test**: Adjust chunk duration slider from 2s to 5s, speak, observe text updates occur at new interval.

- [ ] [T045] [US4] Add chunk duration slider (1.0-5.0s, step=0.5, default=2.0) to src/ui/transcription_page.py UI controls section
- [ ] [T046] [US4] Add VAD threshold slider (50-1000 RMS, step=10, default=200) to src/ui/transcription_page.py UI controls section
- [ ] [T047] [US4] Store slider values in Streamlit session state (st.session_state.chunk_duration, st.session_state.vad_threshold) in src/ui/transcription_page.py
- [ ] [T048] [US4] Update AudioChunker initialization in src/ui/transcription_page.py to use dynamic session state values for chunk_duration and vad_threshold

---

## Phase 7: Polish & Cross-Cutting Concerns

**Goal**: Improve error handling, performance, code quality, and validate against design documents.

- [ ] [T049] [P] Add graceful error handling for microphone permission denial in src/ui/transcription_page.py with Chinese user message "需要麥克風權限才能開始轉錄"
- [ ] [T050] [P] Add error handling for missing OPENAI_API_KEY environment variable with startup validation in src/services/transcription_service.py
- [ ] [T051] [P] Add limit to displayed transcript segments (most recent 400) in src/ui/transcription_page.py to prevent UI performance degradation during long sessions
- [ ] [T052] [P] Add session statistics display (total_chunks, dropped_chunks, duration) below transcript area in src/ui/transcription_page.py
- [ ] [T053] [P] Update start.sh to source .env file for loading OPENAI_API_KEY environment variable
- [ ] [T054] Perform code cleanup to ensure all code follows PEP 8 style guide and has English comments with no Chinese comments
- [ ] [T055] Validate implementation against quickstart.md requirements by running complete end-to-end transcription test with real microphone input

---

## Dependency Graph

### Story Completion Order

```
Setup (T001-T005)
    ↓
Foundational (T006-T007)
    ↓
US1: Start/Stop Transcription (T008-T030) ← MVP Required
    ↓
US2: Persistent File Storage (T031-T041) ← MVP Required
    ↓
US3: Download Transcript (T042-T044) ← Secondary Priority
    ↓
US4: Adjustable Parameters (T045-T048) ← Nice-to-Have
    ↓
Polish (T049-T055)
```

### Within-Story Task Dependencies

**US1 (Start/Stop Transcription)**:
```
Models (T008-T015) → Audio Service (T016-T020) → Transcription Service (T021-T023) → UI (T024-T030)
```

**US2 (Persistent File Storage)**:
```
File Config Model (T031-T033) → File Operations (T034-T036) → UI Integration (T037-T041)
```

**US3 (Download)**: Sequential (T042 → T043 → T044)

**US4 (Parameters)**: Sequential (T045 → T046 → T047 → T048)

---

## Parallel Execution Examples

### Phase 1: Setup (All Parallelizable)
```
Execute T001, T002, T003, T004 in parallel → Then T005 (verification)
```

### Phase 3: User Story 1
```
Parallel Group 1 (Models):
- T008, T011, T014 (create dataclasses)

Sequential within models:
- T009, T010 (complete TranscriptionSession)
- T012, T013 (complete AudioChunk)
- T015 (complete TranscriptSegment)

Parallel Group 2 (Services - after models complete):
- T016-T020 (AudioService)
- T021-T023 (TranscriptionService)

Sequential (UI - after services complete):
- T024 → T025 → T026 → T027 → T028 → T029 → T030
```

### Phase 7: Polish
```
Execute T049, T050, T051, T052, T053 in parallel → Then T054, T055 (cleanup and validation)
```

---

## Implementation Strategy

### MVP Scope (P1 Stories)

**Must Complete First**:
- User Story 1: Start and Stop Real-time Transcription (T008-T030)
- User Story 2: Persistent File Storage (T031-T041)

These two stories deliver the core value proposition: real-time voice transcription with automatic file persistence.

### Secondary Features (P2-P3 Stories)

**Complete After MVP**:
- User Story 3: Download Transcript (T042-T044) - Enhances portability
- User Story 4: Adjustable Parameters (T045-T048) - Power user feature

### Testing Strategy

**Per Specification**: No test tasks are included as the specification does not request automated tests. Manual testing is performed via independent test scenarios defined in spec.md:

1. **US1 Test**: Click start, speak, verify text appears within 5 seconds, click stop
2. **US2 Test**: Transcribe 30 seconds, verify file exists in resource/, refresh browser to verify persistence
3. **US3 Test**: Click download button, verify file downloads with correct content
4. **US4 Test**: Adjust sliders, verify behavior changes (chunk frequency, silence filtering)

### Critical Path

```
T001-T005 (Setup) → T006-T007 (Foundational) → T008-T030 (US1) → T031-T041 (US2)
```

This path must complete successfully to achieve MVP. US3 and US4 can be deferred if needed.

---

## Task Execution Guidelines

### Before Starting

1. Ensure you are on branch `003-realtime-mic-transcription`
2. Create virtual environment and install dependencies from requirements.txt
3. Add OPENAI_API_KEY to .env file
4. Review design documents: spec.md, plan.md, data-model.md, contracts/transcription-service.md

### During Implementation

1. **Follow exact file paths** specified in task descriptions
2. **Maintain existing project patterns** from CLAUDE.md (dataclass validation, service structure, UI components)
3. **Write code in English** with English comments only (no Chinese comments)
4. **Use PEP 8 style guide** for all Python code
5. **Test incrementally** using the independent test scenarios after completing each user story

### After Completing Each User Story

1. Run the independent test scenario defined in spec.md
2. Verify success criteria from spec.md are met
3. Check that files persist and behavior matches acceptance scenarios
4. Document any deviations or issues encountered

### Code Quality Checklist

- [ ] All functions have type hints
- [ ] All classes use dataclasses with __post_init__ validation
- [ ] Error messages are in Traditional Chinese for user-facing errors
- [ ] File operations use threading.Lock for thread safety
- [ ] Audio processing functions do not block WebRTC callbacks (<1ms latency)
- [ ] OpenAI API calls include proper error handling
- [ ] UI components follow existing Streamlit session state patterns

---

## Notes

1. **No Test Tasks**: Per specification requirements, no automated test tasks are included. Testing is performed manually using independent test scenarios.

2. **File Paths Are Exact**: All task descriptions include exact file paths (e.g., `src/models/transcription.py`). Do not deviate from these paths.

3. **Parallelization Opportunities**: Tasks marked with [P] can be executed in parallel if working with multiple developers or parallel workflows.

4. **Story Labels**: [US1], [US2], [US3], [US4] labels ONLY appear on tasks within user story phases (Phase 3-6), not Setup/Foundational/Polish phases.

5. **Blocking Dependencies**: Within each user story, models must complete before services, and services must complete before UI integration.

6. **Performance Budget**: Keep audio processing functions under 1ms latency to avoid blocking WebRTC callbacks. API transcription calls have 1-3 second budget.

7. **Thread Safety**: Use threading.Lock for all file operations to prevent corruption. Each Streamlit session has independent state.

8. **Validation Against Design**: Task T055 validates the final implementation against quickstart.md and all design documents to ensure completeness.

---

## References

- **Specification**: [spec.md](spec.md) - User stories and acceptance scenarios
- **Implementation Plan**: [plan.md](plan.md) - Architecture and technical stack
- **Data Model**: [data-model.md](data-model.md) - Entity definitions and validation rules
- **Service Contracts**: [contracts/transcription-service.md](contracts/transcription-service.md) - Function signatures and error handling
- **Project Standards**: `/CLAUDE.md` - Coding conventions and existing patterns

---

**Generated**: 2025-10-29
**Total Tasks**: 42 (5 Setup + 2 Foundational + 23 US1 + 11 US2 + 3 US3 + 4 US4 + 7 Polish)
