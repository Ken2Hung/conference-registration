# Tasks: Registration Enhancement with Admin Management

**Input**: Design documents from `/specs/001-registration-enhancement/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/service-contracts.md, quickstart.md

**Tests**: Test tasks are included based on existing project test coverage requirements (pytest with 139 tests).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

This is a single-project Streamlit application with three-layer architecture:
- **Models**: `src/models/`
- **Services**: `src/services/`
- **UI**: `src/ui/`
- **Utils**: `src/utils/`
- **Tests**: `tests/unit/`, `tests/integration/`
- **Data**: `data/sessions.json`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Environment setup and configuration

- [ ] T001 Create `.env` file in repository root with ADMIN_USERNAME and ADMIN_PASSWORD (add to .gitignore if not already present)
- [ ] T002 Verify Python 3.9.6 environment and all dependencies installed (Streamlit 1.28.0, python-dateutil 2.8.2, Pillow 10.1.0, pytest 7.4.3)
- [ ] T003 Run existing test suite to ensure baseline: `pytest --cov=src --cov-report=term-missing` (should show 139 tests passing)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core utilities and data models that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 [P] Create Registrant dataclass in src/models/registrant.py (name, registered_at fields with validation)
- [ ] T005 [P] Create validation utilities module in src/utils/validation.py (validate_name, normalize_name, validate_session_date, validate_capacity, validate_level functions)
- [ ] T006 Enhance Session model in src/models/session.py (add registrants field, can_register method, add_registrant method, get_registrants_names method)
- [ ] T007 [P] Write unit tests for Registrant model in tests/unit/models/test_registrant.py
- [ ] T008 [P] Write unit tests for validation utilities in tests/unit/utils/test_validation.py
- [ ] T009 Write unit tests for enhanced Session model methods in tests/unit/models/test_session.py (verify new methods: can_register, add_registrant, get_registrants_names)
- [ ] T010 Run foundational tests to verify models and utilities: `pytest tests/unit/models/ tests/unit/utils/ -v`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Named Registration with Duplicate Prevention (Priority: P1) 🎯 MVP

**Goal**: Enable attendees to register for sessions with their name, preventing duplicates and tracking registrations correctly (+1 count per registration)

**Independent Test**: Can be fully tested by attempting to register for a session with a name, verifying duplicate prevention when using the same name (with whitespace variations), and checking that registration count increases by exactly 1 per successful registration. System should display "您已報名" for duplicates, "已額滿" when full, and "報名成功" with balloons on success.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T011 [P] [US1] Write unit tests for registration_service in tests/unit/services/test_registration_service.py (test register_for_session with success, duplicate, full, expired, not found scenarios)
- [ ] T012 [P] [US1] Write integration test for registration flow in tests/integration/test_registration.py (test end-to-end registration with real JSON file operations and concurrent registrations)

### Implementation for User Story 1

- [ ] T013 [US1] Create registration_service.py in src/services/registration_service.py (implement register_for_session function using file locking, validation, and duplicate checking)
- [ ] T014 [US1] Enhance session_service.py to add get_session_registrants method in src/services/session_service.py (return list of registrants for a session)
- [ ] T015 [US1] Update session_detail.py to add registration form UI in src/ui/session_detail.py (add name input field, call registration_service, display success/error messages with appropriate Chinese text)
- [ ] T016 [US1] Add registration form CSS styling to session_detail.py in src/ui/session_detail.py (style input field, button, and messages to match existing design system)
- [ ] T017 [US1] Run User Story 1 tests: `pytest tests/unit/services/test_registration_service.py tests/integration/test_registration.py -v`
- [ ] T018 [US1] Manual testing: Start app, navigate to session detail, test registration with valid name → should succeed, test duplicate registration → should show "您已報名", test registration on full session → should show "已額滿"

**Checkpoint**: At this point, User Story 1 should be fully functional - attendees can register with names, duplicates are prevented, and count increases correctly by 1

---

## Phase 4: User Story 2 - View Registered Attendees (Priority: P2)

**Goal**: Display list of all registered attendees on session detail page for transparency and community engagement

**Independent Test**: Can be tested independently by registering multiple users for a session and verifying that all names appear in the attendees list in chronological order. Empty state message should show when no registrants exist.

### Implementation for User Story 2

- [ ] T019 [P] [US2] Add registrants list display section to session_detail.py in src/ui/session_detail.py (call get_session_registrants, display names in chronological order, show "目前尚無報名者" for empty state)
- [ ] T020 [US2] Add CSS styling for attendees list in src/ui/session_detail.py (style list container, individual name items, empty state message, scrollable layout for 20+ attendees)
- [ ] T021 [US2] Ensure page updates immediately after registration completes in src/ui/session_detail.py (verify st.rerun() triggers after successful registration to show new name)
- [ ] T022 [US2] Manual testing: Register 3-5 users for a session, verify all names display in chronological order, verify empty state shows for sessions with 0 registrants, verify registrant's name appears immediately after registration

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - registration works (US1) and attendee list displays correctly (US2)

---

## Phase 5: User Story 3 - Fix Session Card Navigation (Priority: P2)

**Goal**: Make entire session card clickable for improved UX, not just the button underneath

**Independent Test**: Can be tested by clicking on different parts of a session card (title, speaker area, tags, card background) and verifying that all clicks navigate to the session detail page with correct session information.

### Implementation for User Story 3

- [ ] T023 [US3] Modify CSS in dashboard.py to make button overlay cover 100% of card area in src/ui/dashboard.py (adjust `.session-card-wrapper > div[data-testid="stButton"] button` CSS to cover entire card with transparent background)
- [ ] T024 [US3] Verify hover effects work across entire card surface in src/ui/dashboard.py (ensure `cursor: pointer` applies to whole card, hover transform works on card wrapper)
- [ ] T025 [US3] Manual testing: Click different parts of session card (title, speaker, tags, background) → all should navigate to detail page, hover anywhere on card → should show visual feedback

**Checkpoint**: All card clicks now work intuitively - entire card surface is clickable

---

## Phase 6: User Story 4 - Admin Session Management (Priority: P3)

**Goal**: Enable admin to log in and manage sessions (create, edit, delete) with proper authentication and validation

**Independent Test**: Can be tested by logging in with admin credentials, creating a new session, editing an existing session, and deleting a session (with confirmation for sessions with registrants). All changes should persist and display correctly on dashboard.

### Tests for User Story 4

- [ ] T026 [P] [US4] Write unit tests for admin_service in tests/unit/services/test_admin_service.py (test authenticate_admin with correct/incorrect credentials, test session state management)
- [ ] T027 [P] [US4] Write unit tests for session_service admin methods in tests/unit/services/test_session_service.py (test create_session, update_session, delete_session with various scenarios)
- [ ] T028 [P] [US4] Write integration test for admin workflow in tests/integration/test_admin_workflow.py (test complete admin workflow: login → create → update → delete)

### Implementation for User Story 4

- [ ] T029 [P] [US4] Create admin_service.py in src/services/admin_service.py (implement authenticate_admin, is_admin_authenticated, logout_admin functions using Streamlit session state and .env credentials)
- [ ] T030 [P] [US4] Enhance session_service.py to add admin CRUD methods in src/services/session_service.py (implement create_session, update_session, delete_session, generate_next_session_id methods)
- [ ] T031 [US4] Create admin_panel.py UI component in src/ui/admin_panel.py (implement login dialog, session creation form, session edit form, delete confirmation dialog)
- [ ] T032 [US4] Add admin button to dashboard header in src/ui/dashboard.py (add "管理者登入" button in top-right corner, show/hide based on admin_authenticated state)
- [ ] T033 [US4] Integrate admin panel with app.py in app.py (check admin_authenticated state, show sidebar menu when authenticated, route to appropriate admin actions)
- [ ] T034 [US4] Add CSS styling for admin UI components in src/ui/admin_panel.py (style login dialog, forms, delete confirmation, sidebar menu)
- [ ] T035 [US4] Run User Story 4 tests: `pytest tests/unit/services/test_admin_service.py tests/unit/services/test_session_service.py tests/integration/test_admin_workflow.py -v`
- [ ] T036 [US4] Manual testing: Click admin button → login dialog appears, enter correct credentials → admin menu shows, test "新增課程" → form appears → submit → session created, test "編輯課程" → form loads → modify → save → changes reflect, test "刪除課程" with registrants → confirmation shows count → confirm → session deleted

**Checkpoint**: All user stories are now complete - registration (US1), attendee list (US2), card navigation (US3), and admin management (US4) all working independently

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T037 [P] Run full test suite with coverage: `pytest --cov=src --cov-report=html` (verify coverage remains high, all new code tested)
- [ ] T038 [P] Code cleanup: Remove debug print statements, remove test data created during manual testing, verify Chinese error messages consistent
- [ ] T039 [P] PEP 8 compliance check: `flake8 src/ --max-line-length=100` (fix any style violations)
- [ ] T040 Update CLAUDE.md documentation if needed in CLAUDE.md (document new features: registration with names, attendee list, admin panel)
- [ ] T041 Final smoke test: Start fresh app `streamlit run app.py`, verify no console errors, quick test of all 4 user stories
- [ ] T042 Update agent context: Run `.specify/scripts/bash/update-agent-context.sh claude` to ensure context includes new features

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phases 3-6)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (US1 → US2/US3 → US4)
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1) - Registration**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2) - Attendee List**: Can start after Foundational (Phase 2) - Uses US1's registration data but independently testable
- **User Story 3 (P2) - Card Navigation**: Can start after Foundational (Phase 2) - Completely independent of other stories (pure UI fix)
- **User Story 4 (P3) - Admin Panel**: Can start after Foundational (Phase 2) - Independent of other stories (different user role)

### Within Each User Story

- Tests MUST be written and FAIL before implementation (T011-T012 before T013-T018 for US1)
- Models before services (already done in Foundational)
- Services before UI (T013-T014 before T015 for US1)
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

**Setup (Phase 1)**: All 3 tasks can run sequentially (quick environment checks)

**Foundational (Phase 2)**:
- T004 (Registrant), T005 (validation utils) can run in parallel
- T007 (Registrant tests), T008 (validation tests) can run in parallel after T004-T005
- T006 (Session enhancement) depends on T004 (needs Registrant class)

**User Story 1 (Phase 3)**:
- T011 (unit tests), T012 (integration test) can run in parallel
- T013 (registration service), T014 (session service method) can run sequentially (T014 may need T013)

**User Story 2 (Phase 4)**:
- T019 (add list display), T020 (CSS styling) can be done together (same file)

**User Story 3 (Phase 5)**:
- T023 (CSS fix), T024 (hover verification) can be done together (same file)

**User Story 4 (Phase 6)**:
- T026 (admin tests), T027 (session service tests), T028 (integration test) can run in parallel
- T029 (admin service), T030 (session service methods) can run in parallel
- T031-T034 (UI work) are sequential (build on each other)

**Polish (Phase 7)**:
- T037 (tests), T038 (cleanup), T039 (PEP 8) can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Write unit tests for registration_service in tests/unit/services/test_registration_service.py"
Task: "Write integration test for registration flow in tests/integration/test_registration.py"

# After tests written and failing, implement services:
Task: "Create registration_service.py in src/services/registration_service.py"
# Can potentially run in parallel with:
Task: "Enhance session_service.py to add get_session_registrants method"
```

## Parallel Example: User Story 4

```bash
# Launch all tests for User Story 4 together:
Task: "Write unit tests for admin_service in tests/unit/services/test_admin_service.py"
Task: "Write unit tests for session_service admin methods in tests/unit/services/test_session_service.py"
Task: "Write integration test for admin workflow in tests/integration/test_admin_workflow.py"

# After tests written, implement services in parallel:
Task: "Create admin_service.py in src/services/admin_service.py"
Task: "Enhance session_service.py to add admin CRUD methods in src/services/session_service.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003) → 環境準備完成
2. Complete Phase 2: Foundational (T004-T010) → **CRITICAL - blocks all stories** → 基礎模型和工具完成
3. Complete Phase 3: User Story 1 (T011-T018) → 具名報名與防重複完成
4. **STOP and VALIDATE**: Test User Story 1 independently → 獨立測試 US1
5. Deploy/demo if ready → 可展示 MVP (最小可行產品)

**MVP 價值**: 使用者可以用姓名報名課程，系統防止重複報名，報名數正確增加 +1

### Incremental Delivery

1. Complete Setup + Foundational (Phases 1-2) → Foundation ready → 基礎就緒
2. Add User Story 1 (Phase 3) → Test independently → Deploy/Demo → **MVP 上線！** (具名報名)
3. Add User Story 2 (Phase 4) → Test independently → Deploy/Demo → **v1.1 上線** (顯示報名者)
4. Add User Story 3 (Phase 5) → Test independently → Deploy/Demo → **v1.2 上線** (卡片點擊改善)
5. Add User Story 4 (Phase 6) → Test independently → Deploy/Demo → **v1.3 上線** (管理員功能)
6. Each story adds value without breaking previous stories → 每個故事獨立增加價值

### Parallel Team Strategy

With multiple developers:

1. **Team completes Setup + Foundational together** (Phases 1-2)
2. **Once Foundational is done:**
   - Developer A: User Story 1 (T011-T018) - Core registration
   - Developer B: User Story 3 (T023-T025) - Card navigation (completely independent)
   - Developer C: Start User Story 4 tests (T026-T028)
3. **After US1 completes:**
   - Developer A: User Story 2 (T019-T022) - Attendee list (builds on US1 data)
   - Developer B: User Story 4 implementation (T029-T036) - Admin panel
4. Stories complete and integrate independently

---

## Task Summary

**Total Tasks**: 42

**Task Count per Phase**:
- Phase 1 (Setup): 3 tasks
- Phase 2 (Foundational): 7 tasks
- Phase 3 (US1 - Registration): 8 tasks (2 tests + 6 implementation)
- Phase 4 (US2 - Attendee List): 4 tasks
- Phase 5 (US3 - Card Navigation): 3 tasks
- Phase 6 (US4 - Admin Panel): 11 tasks (3 tests + 8 implementation)
- Phase 7 (Polish): 6 tasks

**Parallel Opportunities Identified**: 15 tasks marked [P]

**Independent Test Criteria**:
- **US1**: Register with name, verify duplicate prevention, check +1 count → "您已報名", "已額滿", "報名成功" messages
- **US2**: View attendee list with multiple names, verify chronological order, verify empty state
- **US3**: Click anywhere on card, verify navigation to correct detail page
- **US4**: Admin login, create session, edit session, delete session with confirmation

**Suggested MVP Scope**: **Phases 1-3 only** (Setup + Foundational + US1) = 18 tasks
- Delivers core value: Named registration with duplicate prevention
- Fixes broken registration system
- Independently testable and deployable
- Can add US2-US4 incrementally later

---

## Notes

- **[P] tasks** = different files, no dependencies, can run in parallel
- **[Story] label** (US1-US4) maps task to specific user story for traceability
- Each user story should be independently completable and testable
- **Tests first**: Verify tests fail before implementing (T011-T012 before T013-T018)
- Commit after each task or logical group of tasks
- Stop at any checkpoint to validate story independently
- **Chinese text**: All user-facing messages in Chinese (error messages, UI labels)
- **PEP 8**: All Python code follows style guide (English code/comments only)
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence

---

## Format Validation ✅

All tasks follow the required checklist format:
- ✅ All tasks start with `- [ ]` checkbox
- ✅ All tasks have sequential Task ID (T001-T042)
- ✅ Setup/Foundational/Polish tasks have NO story label (correct)
- ✅ User Story tasks have [US1], [US2], [US3], or [US4] label (correct)
- ✅ Parallelizable tasks marked with [P] (15 tasks identified)
- ✅ All tasks include clear description with exact file path
- ✅ Task organization follows user story structure (Phases 3-6)
