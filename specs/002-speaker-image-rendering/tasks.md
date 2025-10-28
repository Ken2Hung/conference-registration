# Implementation Tasks: Speaker Image Rendering in Dashboard

**Feature**: 002-speaker-image-rendering
**Branch**: 002-speaker-image-rendering
**Created**: 2025-10-28
**Status**: ✅ COMPLETED
**Completed**: 2025-10-28

---

## Overview

This document contains the complete task breakdown for implementing circular speaker profile photos in the Streamlit dashboard. Tasks are organized by user story to enable independent implementation and testing.

**Total Estimated Time**: 2-3 hours
**Recommended Approach**: Complete tasks sequentially within each phase

---

## Task Summary

| Phase | Tasks | Can Parallelize | Description |
|-------|-------|-----------------|-------------|
| Phase 1: Setup | 2 | No | Environment validation |
| Phase 2: Foundational | 0 | N/A | No blocking prerequisites |
| Phase 3: US1 - Display Speaker Photos | 7 | Yes (2 groups) | Core photo rendering |
| Phase 4: US2 - Handle Missing Photos | 4 | Yes (tests) | Fallback mechanism |
| Phase 5: US3 - Responsive Design | 3 | No | Visual consistency |
| Phase 6: Polish | 4 | Yes (docs) | Documentation and validation |
| **Total** | **20** | **8** | **Complete feature** |

---

## Phase 1: Setup & Environment Validation

**Goal**: Ensure development environment is ready for implementation

**Prerequisites**: None

### Tasks

- [X] T001 Verify current branch is `002-speaker-image-rendering`
  - Command: `git branch --show-current`
  - Expected: `002-speaker-image-rendering`
  - If not: `git checkout -b 002-speaker-image-rendering`

- [X] T002 Verify all design documents exist in `specs/002-speaker-image-rendering/`
  - Required files: spec.md, plan.md, research.md, quickstart.md, data-model.md
  - Command: `ls -la specs/002-speaker-image-rendering/`

---

## Phase 2: Foundational Tasks

**Goal**: N/A - No blocking prerequisites needed

**Rationale**: All required infrastructure already exists (Speaker model, JSON data, Streamlit setup). Implementation can proceed directly to user stories.

---

## Phase 3: User Story 1 - Display Speaker Photos

**User Story**: As a conference attendee, I want to see speaker profile photos in session cards so that I can visually identify speakers while browsing sessions.

**Acceptance Criteria**:
- ✅ Speaker photos display as 50px circular thumbnails
- ✅ Photos positioned to the left of speaker names
- ✅ Consistent styling (border, shadow) across all cards
- ✅ Photos maintain circular shape with proper cropping

**Independent Test**:
```python
# Manual test: Run dashboard and verify
streamlit run app.py
# Expected: All sessions with valid photo paths show circular photos
```

### Implementation Tasks

#### Group A: Helper Function (Sequential)

- [X] T003 [US1] Create `_render_speaker_avatar()` helper function in `src/ui/dashboard.py`
  - Location: After imports, before `_render_session_card()`
  - Function signature: `_render_speaker_avatar(photo_path: str, speaker_name: str, size: int = 50, is_past: bool = False) -> str`
  - Returns: HTML string with photo `<img>` tag
  - Reference: `specs/002-speaker-image-rendering/research.md` (Appendix section)

- [X] T004 [US1] Add CSS styling for circular photos in `_render_speaker_avatar()`
  - border-radius: 50%
  - object-fit: cover
  - Border: 2px solid #2d3748
  - Shadow: 0 2px 8px rgba(0, 0, 0, 0.3)
  - Size: 50px × 50px
  - Reference: `specs/002-speaker-image-rendering/plan.md` (UI/UX Design section)

- [X] T005 [US1] Implement opacity control for past sessions in `_render_speaker_avatar()`
  - If `is_past=True`: set `opacity: 0.6`
  - If `is_past=False`: set `opacity: 1.0`
  - Apply to both photo `<img>` and fallback placeholder

#### Group B: Integration (Depends on Group A)

- [X] T006 [US1] Update `_render_session_card()` in `src/ui/dashboard.py` to call `_render_speaker_avatar()`
  - Add call before rendering card HTML: `avatar_html = _render_speaker_avatar(session.speaker.photo, session.speaker.name, is_past=is_past)`
  - Pass result to card template

- [X] T007 [US1] Modify speaker display section in `_render_session_card()` HTML template
  - Find: `<div style="color: #cbd5e1; ...">👤 {session.speaker.name}</div>`
  - Replace with: `<div style="...display: flex; align-items: center;">{avatar_html}<span>{session.speaker.name}</span></div>`
  - Remove emoji `👤`
  - Add `margin-right: 12px` spacing between photo and name

- [X] T008 [US1] Manual testing: Verify photos display correctly
  - Run: `streamlit run app.py`
  - Check: All 11 sessions show circular photos or placeholders
  - Check: Photos are 50px diameter, circular, with border and shadow
  - Check: Photos positioned left of names with proper spacing

#### Group C: Unit Tests (Parallel with Group B)

- [X] T009 [P] [US1] Create test file `tests/ui/test_dashboard.py` if not exists
  - Add imports: `pytest`, `from src.ui.dashboard import _render_speaker_avatar`

- [X] T010 [P] [US1] Write test `test_render_avatar_contains_img_tag()` in `tests/ui/test_dashboard.py`
  - Test: Avatar HTML contains `<img>` tag with correct photo path
  - Assert: `'<img' in html` and `'images/speakers/test.jpg' in html`

- [X] T011 [P] [US1] Write test `test_render_avatar_circular_styling()` in `tests/ui/test_dashboard.py`
  - Test: Avatar HTML contains `border-radius: 50%`
  - Assert: Circular styling present

- [X] T012 [P] [US1] Write test `test_render_avatar_custom_size()` in `tests/ui/test_dashboard.py`
  - Test: Avatar respects custom size parameter
  - Call: `_render_speaker_avatar("test.jpg", "John", size=100)`
  - Assert: `'width: 100px'` and `'height: 100px'` in html

---

## Phase 4: User Story 2 - Handle Missing Photos

**User Story**: As a system administrator, I want the dashboard to gracefully handle missing speaker photos so that users never see broken image icons or errors.

**Acceptance Criteria**:
- ✅ Missing photo files display placeholder avatar with speaker initial
- ✅ No error messages shown to users
- ✅ Placeholder has same dimensions and styling as photos
- ✅ Card layout remains intact when photo is missing

**Independent Test**:
```python
# Manual test: Temporarily rename a photo file
mv images/speakers/nero-un.jpg images/speakers/nero-un.jpg.bak
streamlit run app.py
# Expected: Session shows "N" in gradient circle instead of photo
mv images/speakers/nero-un.jpg.bak images/speakers/nero-un.jpg
```

### Implementation Tasks

- [X] T013 [US2] Add fallback placeholder div in `_render_speaker_avatar()` in `src/ui/dashboard.py`
  - Create container div with `position: relative`
  - Add placeholder div (renders first): gradient circle with speaker initial
  - Background: `linear-gradient(135deg, #667eea 0%, #764ba2 100%)`
  - Display: `flex`, centered initial letter
  - Font size: 25px (50% of avatar size)
  - Reference: `specs/002-speaker-image-rendering/research.md` (R2 section)

- [X] T014 [US2] Add photo `<img>` tag overlaying placeholder in `_render_speaker_avatar()`
  - Position: `absolute`, `z-index: 1` (above placeholder)
  - Add `onerror="this.style.display='none';"` attribute
  - Result: If photo fails to load, it hides and reveals placeholder

- [X] T015 [US2] Implement speaker initial extraction in `_render_speaker_avatar()`
  - Extract first character: `initial = speaker_name[0].upper() if speaker_name else "?"`
  - Use "?" if name is empty

#### Group D: Tests (Parallel)

- [X] T016 [P] [US2] Write test `test_render_avatar_contains_fallback_div()` in `tests/ui/test_dashboard.py`
  - Test: Avatar HTML contains placeholder div with initial
  - Assert: `'<div'` in html and speaker initial present

- [X] T017 [P] [US2] Write test `test_render_avatar_with_empty_name_uses_question_mark()` in `tests/ui/test_dashboard.py`
  - Test: Empty name shows "?" placeholder
  - Call: `_render_speaker_avatar("test.jpg", "")`
  - Assert: `'?' in html`

- [X] T018 [P] [US2] Write test `test_render_avatar_has_onerror_handler()` in `tests/ui/test_dashboard.py`
  - Test: Image has onerror attribute
  - Assert: `'onerror=' in html` and `"this.style.display='none'" in html`

---

## Phase 5: User Story 3 - Responsive Design & Consistency

**User Story**: As a conference attendee on any device, I want speaker photos to display consistently so that the dashboard looks professional on desktop, tablet, and mobile.

**Acceptance Criteria**:
- ✅ Photos maintain 50px size on all screen sizes
- ✅ Circular shape preserved on browser resize
- ✅ Past sessions have reduced opacity (0.6)
- ✅ Upcoming sessions have full opacity (1.0)

**Independent Test**:
```bash
# Manual test: Open dashboard and resize browser window
streamlit run app.py
# Expected: Photos remain circular and properly sized at all window widths
```

### Implementation Tasks

- [X] T019 [US3] Verify responsive layout with browser resize testing
  - Open dashboard in browser
  - Resize window from 1920px to 320px width
  - Verify: Photos maintain circular shape and 50px size
  - Verify: Speaker name wraps properly if needed

- [X] T020 [US3] Write test `test_render_avatar_applies_reduced_opacity_for_past_sessions()` in `tests/ui/test_dashboard.py`
  - Test: Past sessions have opacity 0.6
  - Call: `_render_speaker_avatar("test.jpg", "Jane", is_past=True)`
  - Assert: `'opacity: 0.6' in html`

- [X] T021 [US3] Write test `test_render_avatar_applies_full_opacity_for_upcoming_sessions()` in `tests/ui/test_dashboard.py`
  - Test: Upcoming sessions have opacity 1.0
  - Call: `_render_speaker_avatar("test.jpg", "Jane", is_past=False)`
  - Assert: `'opacity: 1.0' in html`

---

## Phase 6: Polish & Cross-Cutting Concerns

**Goal**: Ensure code quality, documentation, and deployment readiness

### Tasks

- [X] T022 [P] Run all unit tests and verify >80% coverage
  - Command: `pytest tests/ui/test_dashboard.py --cov=src/ui/dashboard --cov-report=term-missing`
  - Expected: All 9 tests pass, coverage >80%

- [X] T023 [P] Update main README.md with speaker photo requirements
  - Add section: "Speaker Photo Requirements"
  - Document: Image location (`images/speakers/`), formats (JPG/PNG/WEBP), size recommendations (<10KB)
  - File: `README.md`

- [X] T024 [P] Verify no browser console errors when loading dashboard
  - Open browser DevTools (F12)
  - Run: `streamlit run app.py`
  - Check Console tab: Should have 0 errors (404s for missing photos are OK)

- [X] T025 Git commit with conventional format
  - Stage: `git add src/ui/dashboard.py tests/ui/test_dashboard.py`
  - Commit: `git commit -m "feat(ui): add circular speaker photo display in dashboard\n\n- Add _render_speaker_avatar() helper function\n- Update _render_session_card() to display photos\n- Implement automatic fallback to speaker initial\n- Add 9 unit tests for avatar rendering\n- Apply reduced opacity for past sessions\n\nCloses #002"`
  - Verify: Constitution-compliant commit message

---

## Dependency Graph

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational) [SKIPPED - No prerequisites]
    ↓
Phase 3 (US1) ────┐
    ↓             │ (independent)
Phase 4 (US2) ────┤
    ↓             │ (independent)
Phase 5 (US3) ────┘
    ↓
Phase 6 (Polish)
```

**Story Dependencies**:
- ✅ US1 (Display Photos) → Blocks US2, US3 (needs core rendering function)
- ✅ US2 (Missing Photos) → Independent after US1
- ✅ US3 (Responsive) → Independent after US1

**Within Phase 3 (US1)**:
```
Group A (Helper Function)
    T003 → T004 → T005
         ↓
    Group B (Integration)
        T006 → T007 → T008

Group C (Tests) [PARALLEL with Group B]
    T009 → T010, T011, T012 [all parallel]
```

---

## Parallel Execution Opportunities

### Within User Story 1 (Phase 3)

**After T005 completes**, these can run in parallel:

**Group B** (Integration):
- T006, T007, T008 (sequential within group)

**Group C** (Tests):
- T009 (setup) → then T010, T011, T012 in parallel

**Estimated Time Savings**: ~15 minutes if tests run concurrently with integration

### Within User Story 2 (Phase 4)

**After T015 completes**, these can run in parallel:

**Group D** (Tests):
- T016, T017, T018 (all parallel)

**Estimated Time Savings**: ~10 minutes

### Within Phase 6 (Polish)

**All tasks can run in parallel**:
- T022 (run tests)
- T023 (update docs)
- T024 (verify console)

**Note**: T025 (git commit) must wait for all others to complete

**Estimated Time Savings**: ~5 minutes

**Total Parallel Time Savings**: ~30 minutes (if executed optimally)

---

## Implementation Strategy

### Recommended Order

**MVP Scope** (Minimum Viable Product):
- ✅ Phase 1: Setup (T001-T002)
- ✅ Phase 3: US1 - Display Photos (T003-T012)
- ✅ Phase 6: Polish - Basic (T022, T025)

**Estimated MVP Time**: 1.5 hours
**MVP Delivers**: Core feature (photos display) with tests

**Incremental Additions**:
1. **Iteration 2**: Add Phase 4 (US2 - Missing Photos) - +30 min
2. **Iteration 3**: Add Phase 5 (US3 - Responsive) - +20 min
3. **Iteration 4**: Complete Phase 6 (Documentation) - +10 min

### Test-Driven Development (TDD) Approach

If following TDD:
1. Write test first (e.g., T010)
2. Run test (should fail)
3. Implement feature (e.g., T003-T005)
4. Run test (should pass)
5. Refactor if needed

**Example TDD Workflow for US1**:
```
T009 (setup test file)
  → T010 (write test for img tag)
  → T003-T005 (implement to make test pass)
  → T011 (write test for circular styling)
  → T004 (enhance implementation)
  ... repeat for each test
```

---

## Task Validation Checklist

**Format Validation**:
- ✅ All tasks have checkbox `- [ ]`
- ✅ All tasks have sequential ID (T001-T025)
- ✅ Parallelizable tasks marked with `[P]`
- ✅ User story tasks labeled `[US1]`, `[US2]`, `[US3]`
- ✅ All tasks have clear file paths or commands
- ✅ All tasks have specific acceptance criteria

**Completeness Validation**:
- ✅ Each user story has independent test criteria
- ✅ Each user story is independently implementable
- ✅ Setup phase validates environment
- ✅ Polish phase includes tests, docs, and commit
- ✅ Dependency graph shows clear order

**Constitution Compliance**:
- ✅ Mandatory testing included (9 unit tests)
- ✅ Tests achieve >80% coverage requirement
- ✅ Conventional commit format enforced (T025)
- ✅ Minimal comments (only function docstrings)
- ✅ Comprehensive error handling (`onerror` attribute)

---

## Execution Tracking

**Progress**: 0 / 25 tasks complete (0%)

**Current Phase**: Phase 1 - Setup

**Next Task**: T001 - Verify branch

**Estimated Time Remaining**: 2-3 hours (full implementation)

---

## Notes

- **No API contracts**: This is a UI-only feature, no backend changes needed
- **No data model changes**: Speaker.photo field already exists
- **No database migrations**: Data loaded from JSON files
- **Image files**: Ensure all photo files exist in `images/speakers/` before testing
- **Browser compatibility**: Tested approach works on Chrome, Firefox, Safari, Edge

---

## Reference Documents

- **Specification**: `specs/002-speaker-image-rendering/spec.md`
- **Implementation Plan**: `specs/002-speaker-image-rendering/plan.md`
- **Research Findings**: `specs/002-speaker-image-rendering/research.md`
- **Developer Guide**: `specs/002-speaker-image-rendering/quickstart.md`
- **Data Model**: `specs/002-speaker-image-rendering/data-model.md`
- **Constitution**: `.specify/memory/constitution.md`

---

**Ready to Start Implementation** ✅

Begin with Phase 1 (Setup) and proceed sequentially through each phase. Use the quickstart guide for detailed code examples and troubleshooting tips.
