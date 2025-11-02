# Implementation Plan: Registration Enhancement with Admin Management

**Branch**: `001-registration-enhancement` | **Date**: 2025-10-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-registration-enhancement/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This feature enhances the conference registration system with named registration tracking, duplicate prevention, attendee list display, improved card navigation UX, and full admin management capabilities (create/edit/delete sessions). The implementation extends the existing three-layer Streamlit architecture with new data models for registrants, enhanced service layer methods for registration logic with file locking, admin authentication using Streamlit session state, and UI enhancements for both attendee and admin workflows.

## Technical Context

**Language/Version**: Python 3.9.6
**Primary Dependencies**: Streamlit 1.28.0, python-dateutil 2.8.2, Pillow 10.1.0
**Storage**: JSON files in `data/` directory with atomic write operations and file locking
**Testing**: pytest 7.4.3 with pytest-cov 4.1.0 (139 existing tests covering all layers)
**Target Platform**: Cross-platform web application (runs on macOS/Linux/Windows via Streamlit server)
**Project Type**: Single web application with three-layer architecture (UI/Service/Model)
**Performance Goals**: <2 seconds page load, <5 seconds for admin operations, handle 10+ concurrent registrations
**Constraints**: File-based storage requires file locking for concurrency, browser session-based auth (no external auth service), Chinese UI text throughout
**Scale/Scope**: Small-to-medium conference system (~100 sessions, ~1000 registrations per session), single admin user, 11 existing sessions in production data

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Constitution Status**: No project constitution file found (`.specify/memory/constitution.md` contains only template placeholders). This feature will follow the existing project conventions documented in CLAUDE.md:

- ✅ **Code Style**: Python code follows PEP 8, English code/comments, Chinese UI text
- ✅ **Minimal Changes**: Extend existing architecture without major refactoring
- ✅ **No New Dependencies**: Use existing dependencies only (Streamlit, pytest, Pillow, python-dateutil)
- ✅ **Testing Required**: Maintain test coverage with pytest, delete test code after verification
- ✅ **Existing Patterns**: Follow existing patterns for Excel generation, provider access, logging

**Re-evaluation after Phase 1**: Will verify adherence to three-layer architecture, file locking patterns, and testing conventions.

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
app.py                          # Main Streamlit application entry point

src/
├── models/
│   ├── session.py              # Existing: Session dataclass (WILL ENHANCE: add registrants field)
│   ├── speaker.py              # Existing: Speaker dataclass
│   └── registrant.py           # NEW: Registrant dataclass for registration tracking
├── services/
│   ├── session_service.py      # Existing (WILL ENHANCE): add registration methods, admin CRUD
│   ├── storage_service.py      # Existing: JSON file operations with atomic writes
│   ├── admin_service.py        # NEW: Admin authentication and authorization logic
│   └── registration_service.py # NEW: Registration business logic with duplicate checking
├── ui/
│   ├── dashboard.py            # Existing (WILL ENHANCE): clickable cards, admin button
│   ├── session_detail.py       # Existing (WILL ENHANCE): registration form, attendee list
│   ├── admin_panel.py          # NEW: Admin UI for create/edit/delete sessions
│   └── html_utils.py           # Existing: HTML rendering utilities
└── utils/
    ├── file_lock.py            # Existing: File locking mechanism
    └── validation.py           # NEW: Input validation utilities

data/
└── sessions.json               # Existing (WILL ENHANCE): add registrants array to each session

tests/
├── unit/
│   ├── models/                 # Test model validation and logic
│   ├── services/               # Test service methods
│   └── utils/                  # Test utilities
└── integration/
    ├── test_registration.py    # NEW: End-to-end registration tests
    └── test_admin_workflow.py  # NEW: End-to-end admin workflow tests
```

**Structure Decision**: Using existing single-project structure with three-layer architecture (UI/Service/Model). The feature extends all three layers:
- **Model Layer**: Add `Registrant` model, enhance `Session` model
- **Service Layer**: Add `admin_service.py` and `registration_service.py`, enhance `session_service.py`
- **UI Layer**: Add `admin_panel.py`, enhance `dashboard.py` and `session_detail.py`

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations detected. The implementation follows existing project patterns and adds minimal complexity:
- Uses existing file locking mechanism for concurrency control
- Extends existing three-layer architecture without introducing new patterns
- Reuses existing Streamlit session state for admin authentication (no external auth library)
- Follows established JSON storage patterns with atomic writes
