# Implementation Plan: Speaker Image Rendering in Dashboard

**Branch**: `002-speaker-image-rendering` | **Date**: 2025-10-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-speaker-image-rendering/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Replace the current HTML-based speaker photo rendering with `st.image()` component approach in the dashboard session cards. The implementation will check file existence before rendering, display circular speaker photos with CSS styling, and provide graceful fallback to initial-letter badges for missing photos. This addresses the issue where speaker photos are not being rendered correctly in the frontend.

## Technical Context

**Language/Version**: Python 3.9.6
**Primary Dependencies**: Streamlit 1.28.0, Pillow 10.1.0
**Storage**: Local file system (speaker photos in `images/` directory)
**Testing**: pytest 7.4.3, pytest-cov 4.1.0
**Target Platform**: Web application (Streamlit server)
**Project Type**: Single web application
**Performance Goals**: Dashboard loads within 2 seconds with all photos rendered
**Constraints**: Support 10+ session cards without blocking UI, handle missing images gracefully
**Scale/Scope**: ~10-20 concurrent session cards, photo files <1MB each

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Status**: ✅ PASSED

**Rationale**: This feature is a UI enhancement modifying existing dashboard rendering code. No constitution file is defined for this project (template placeholders only). Standard quality gates applied:

- ✅ **Testing**: Existing test infrastructure (pytest) will be used for unit and integration tests
- ✅ **Simplicity**: Modifies single component (`_render_speaker_avatar` in `dashboard.py`) without introducing new architecture
- ✅ **Dependencies**: Uses existing dependencies (Streamlit, os module) - no new external packages required
- ✅ **Scope**: Focused UI enhancement within well-defined boundaries (dashboard session cards only)

**No violations** or complexity additions identified.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
conference-registration/
├── app.py                        # Main Streamlit application entry point
├── src/
│   ├── models/
│   │   ├── speaker.py           # Speaker model (contains photo field)
│   │   └── session.py           # Session model (references Speaker)
│   ├── services/
│   │   ├── session_service.py   # Session data retrieval
│   │   └── storage_service.py   # Data persistence
│   ├── ui/
│   │   ├── dashboard.py         # 🎯 PRIMARY MODIFICATION TARGET
│   │   └── session_detail.py   # Session detail view
│   └── utils/
│       ├── validation.py
│       └── date_utils.py
├── tests/
│   ├── ui/
│   │   └── test_dashboard.py   # 🎯 TEST TARGET
│   ├── integration/
│   │   └── test_dashboard_flow.py
│   └── unit/
│       ├── test_session.py
│       └── test_session_service.py
├── images/
│   └── speakers/                # Speaker photo storage location
└── requirements.txt             # Dependencies (Streamlit, Pillow, pytest)
```

**Structure Decision**: Single Python web application using Streamlit framework. The primary modification target is `src/ui/dashboard.py::_render_speaker_avatar` function, which currently uses HTML `<img>` tags but needs to be refactored to use `st.image()` with proper file existence checking.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**Status**: N/A - No violations identified.

---

## Phase 1 Design Review

### Constitution Check Re-evaluation (Post-Design)

**Status**: ✅ PASSED - No changes from initial evaluation

**Design Artifacts Created**:
- ✅ research.md - Technical research complete (HTML-based approach documented)
- ✅ data-model.md - No data model changes required (confirmed)
- ✅ quickstart.md - Implementation guide complete
- ✅ No API contracts needed (UI-only feature)

**Post-Design Validation**:
- ✅ **Simplicity Maintained**: Single function modification (`_render_speaker_avatar`)
- ✅ **No New Dependencies**: Uses Streamlit built-ins and Python standard library only
- ✅ **Test Coverage**: 9 unit tests documented in quickstart guide
- ✅ **Error Handling**: Graceful fallback via HTML `onerror` attribute
- ✅ **Performance**: File-based approach with browser caching (no server-side processing)

**Note on Implementation Approach**:
The existing research.md and quickstart.md documents recommend the HTML `<img>` tag approach (current implementation). However, the clarification session in spec.md recommends using `st.image()` instead. This discrepancy should be noted during implementation:

- **Current docs recommend**: HTML `<img>` tags with `onerror` fallback
- **Clarifications recommend**: `st.image()` component with `os.path.exists()` check

The implementation team should evaluate both approaches and choose based on:
1. Which resolves the "app.py不照圖片渲染前端" issue
2. Performance characteristics
3. Ease of styling (circular shape with CSS)

**Recommendation**: Start with `st.image()` approach (per clarifications), fall back to HTML approach if styling proves difficult.
