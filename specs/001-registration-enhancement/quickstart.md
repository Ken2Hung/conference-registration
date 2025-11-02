# Quickstart: Registration Enhancement Implementation

**Feature**: 001-registration-enhancement
**Branch**: `001-registration-enhancement`
**Date**: 2025-10-28

## Overview

This quickstart guide provides a step-by-step implementation roadmap for the registration enhancement feature. Follow this sequence to build the feature incrementally with testable milestones at each stage.

---

## Prerequisites

✅ Branch `001-registration-enhancement` checked out
✅ Virtual environment activated (`source venv/bin/activate`)
✅ All dependencies installed (`pip install -r requirements.txt`)
✅ Tests passing (`pytest` shows 139 tests passing)
✅ Application running (`streamlit run app.py`)

---

## Implementation Sequence

### Phase 1: Data Models (Foundation)

**Goal**: Establish data structures without modifying existing functionality.

**Steps**:

1. **Create `Registrant` model** (`src/models/registrant.py`)
   - Define dataclass with `name` and `registered_at` fields
   - Add validation in `__post_init__`
   - Write unit tests (`tests/unit/models/test_registrant.py`)
   - Run tests: `pytest tests/unit/models/test_registrant.py -v`

2. **Enhance `Session` model** (`src/models/session.py`)
   - Add `registrants: List[Registrant] = field(default_factory=list)` field
   - Add `can_register(name: str) -> Tuple[bool, str]` method
   - Add `add_registrant(registrant: Registrant) -> None` method
   - Add `get_registrants_names() -> List[str]` method
   - Update `__post_init__` validation for registrants consistency
   - Write unit tests for new methods
   - Run tests: `pytest tests/unit/models/test_session.py -v`

**Milestone**: All model tests passing, no existing functionality broken.

---

### Phase 2: Validation Utilities

**Goal**: Create reusable validation functions.

**Steps**:

1. **Create `validation.py`** (`src/utils/validation.py`)
   - Implement `validate_name(name: str) -> Tuple[bool, str]`
   - Implement `normalize_name(name: str) -> str`
   - Implement `validate_session_date(date_str: str, allow_past: bool) -> Tuple[bool, str]`
   - Implement `validate_capacity(capacity: int, current_registered: int) -> Tuple[bool, str]`
   - Implement `validate_level(level: str) -> Tuple[bool, str]`

2. **Write unit tests** (`tests/unit/utils/test_validation.py`)
   - Test each validator with valid and invalid inputs
   - Test edge cases (empty strings, special characters, Chinese characters)
   - Run tests: `pytest tests/unit/utils/test_validation.py -v`

**Milestone**: All validation tests passing, utilities ready for use in services.

---

### Phase 3: Service Layer - Registration

**Goal**: Implement registration business logic.

**Steps**:

1. **Create `registration_service.py`** (`src/services/registration_service.py`)
   - Implement `register_for_session(session_id: str, attendee_name: str) -> Tuple[bool, str]`
   - Use file locking from `src/utils/file_lock.py`
   - Use validation from `src/utils/validation.py`
   - Add proper error handling and logging

2. **Write unit tests** (`tests/unit/services/test_registration_service.py`)
   - Mock file I/O and locking
   - Test success path
   - Test error paths (duplicate, full, expired, not found)
   - Run tests: `pytest tests/unit/services/test_registration_service.py -v`

3. **Write integration test** (`tests/integration/test_registration.py`)
   - Test with real JSON file operations
   - Test concurrent registrations
   - Run tests: `pytest tests/integration/test_registration.py -v`

**Milestone**: Registration logic implemented and tested, ready for UI integration.

---

### Phase 4: UI - Registration Form & Attendee List

**Goal**: Add registration form and display registered attendees.

**Steps**:

1. **Enhance `session_detail.py`** (`src/ui/session_detail.py`)
   - Add registration form UI (name input field)
   - Call `registration_service.register_for_session()` on submit
   - Display success/error messages
   - Add attendee list section (display `session.get_registrants_names()`)
   - Add empty state message ("目前尚無報名者")
   - Update CSS for form and list styling

2. **Manual Testing**:
   - Start app: `streamlit run app.py`
   - Navigate to a session detail page
   - Test registration with valid name → should succeed
   - Test duplicate registration → should show "您已報名"
   - Test registration on full session → should show "已額滿"
   - Verify attendee list displays names correctly

**Milestone**: Registration form working, attendee list displays correctly.

---

### Phase 5: UI - Fix Card Navigation

**Goal**: Make entire session card clickable.

**Steps**:

1. **Modify `dashboard.py`** (`src/ui/dashboard.py`)
   - Adjust CSS to make button overlay cover 100% of card area
   - Ensure hover effects work across entire card
   - Verify `cursor: pointer` applies to whole card

2. **Manual Testing**:
   - Click different parts of session card (title, speaker, tags, background)
   - Verify all clicks navigate to session detail page
   - Verify hover effects show card is clickable

**Milestone**: Card navigation intuitive and working across entire card surface.

---

### Phase 6: Admin Service & Authentication

**Goal**: Implement admin authentication.

**Steps**:

1. **Create `.env` file** (root directory, add to `.gitignore`)
   ```bash
   ADMIN_USERNAME=admin
   ADMIN_PASSWORD=your_secure_password_here
   ```

2. **Create `admin_service.py`** (`src/services/admin_service.py`)
   - Implement `authenticate_admin(username: str, password: str) -> bool`
   - Implement `is_admin_authenticated() -> bool`
   - Implement `logout_admin() -> None`

3. **Write unit tests** (`tests/unit/services/test_admin_service.py`)
   - Test authentication with correct/incorrect credentials
   - Test session state management
   - Run tests: `pytest tests/unit/services/test_admin_service.py -v`

**Milestone**: Admin authentication logic working.

---

### Phase 7: Session Service - Admin CRUD

**Goal**: Add admin session management methods.

**Steps**:

1. **Enhance `session_service.py`** (`src/services/session_service.py`)
   - Implement `create_session(...)` with auto ID generation
   - Implement `update_session(session_id: str, updates: dict)`
   - Implement `delete_session(session_id: str) -> Tuple[bool, str, int]`
   - Add helper: `generate_next_session_id(sessions: List[Session]) -> str`

2. **Write unit tests** (`tests/unit/services/test_session_service.py`)
   - Test create with valid/invalid data
   - Test update with partial updates
   - Test update capacity validation (cannot go below registered count)
   - Test delete and registrant count return
   - Run tests: `pytest tests/unit/services/ -v`

3. **Write integration test** (`tests/integration/test_admin_workflow.py`)
   - Test complete admin workflow: create → update → delete
   - Run tests: `pytest tests/integration/test_admin_workflow.py -v`

**Milestone**: Admin CRUD operations implemented and tested.

---

### Phase 8: UI - Admin Panel

**Goal**: Build admin UI for session management.

**Steps**:

1. **Add admin button to `dashboard.py`**
   - Add "管理者登入" button in header (top-right corner)
   - Show/hide based on `st.session_state.admin_authenticated`

2. **Create `admin_panel.py`** (`src/ui/admin_panel.py`)
   - Implement login dialog using `st.dialog()`
   - Implement session creation form
   - Implement session edit form (load existing data)
   - Implement delete confirmation dialog (show registrant count)
   - Add logout button in sidebar

3. **Integrate admin panel in `app.py`**
   - Check `st.session_state.admin_authenticated`
   - Show admin sidebar menu when authenticated
   - Route to appropriate admin actions

4. **Manual Testing**:
   - Click admin button → login dialog appears
   - Enter correct credentials → admin menu shows in sidebar
   - Test "新增課程" → form appears → submit → session created → appears on dashboard
   - Test "編輯課程" → select session → form loads data → modify → save → changes reflect
   - Test "刪除課程" → select session with registrants → confirmation shows count → confirm → session deleted
   - Test logout → admin menu disappears

**Milestone**: Admin panel fully functional.

---

### Phase 9: End-to-End Testing

**Goal**: Verify complete feature works end-to-end.

**Test Scenarios**:

1. **Registration Flow** (P1):
   - Open app as attendee
   - Navigate to available session
   - Register with name "測試者一" → Success
   - Try to register again with " 測試者一 " (extra spaces) → "您已報名"
   - Verify name appears in attendee list
   - Verify registration count increased by 1

2. **Attendee List Display** (P2):
   - Navigate to session with 3+ registrants
   - Verify all names displayed in chronological order
   - Navigate to session with 0 registrants
   - Verify empty state message shows

3. **Card Navigation** (P2):
   - Click session card title → navigates to detail
   - Click session card speaker area → navigates to detail
   - Click session card tags → navigates to detail
   - Click session card background → navigates to detail

4. **Admin Workflow** (P3):
   - Login as admin
   - Create new session with all fields
   - Verify session appears on dashboard
   - Edit session (change title, date)
   - Verify changes reflected
   - Attempt to reduce capacity below registered count → error shown
   - Delete session without registrants → success
   - Delete session with registrants → confirmation shows count → confirm → deleted

5. **Concurrent Registration**:
   - Open app in 2 browser tabs
   - Navigate both to same session with 1 remaining slot
   - Submit registration simultaneously in both tabs
   - Verify: one succeeds, other shows "已額滿"
   - Verify: registration count is exactly 1 (not 2)

**Milestone**: All test scenarios pass, feature ready for production.

---

### Phase 10: Cleanup & Documentation

**Goal**: Finalize implementation.

**Steps**:

1. **Run full test suite**:
   ```bash
   pytest --cov=src --cov-report=term-missing
   ```
   - Verify coverage remains high
   - Verify all new code is tested

2. **Code cleanup**:
   - Remove debug print statements
   - Remove test data/sessions created during manual testing
   - Ensure Chinese error messages are consistent
   - Verify PEP 8 compliance: `flake8 src/`

3. **Update documentation**:
   - Update `CLAUDE.md` with new features (if needed)
   - Ensure `.env` is in `.gitignore`
   - Document admin credentials setup in README (if needed)

4. **Final verification**:
   - Start fresh: `streamlit run app.py`
   - Verify no errors in console
   - Quick smoke test of all features

**Milestone**: Feature complete, tested, and ready for deployment.

---

## Development Tips

### Quick Commands

```bash
# Run specific test file
pytest tests/unit/models/test_registrant.py -v

# Run all tests with coverage
pytest --cov=src --cov-report=html
open htmlcov/index.html

# Run only integration tests
pytest tests/integration/ -v

# Run app with auto-reload
streamlit run app.py --server.runOnSave true

# Check PEP 8 compliance
flake8 src/ --max-line-length=100
```

### Debugging Tips

1. **Registration not working**:
   - Check file lock timeout (increase if needed)
   - Verify JSON file permissions
   - Check console for error messages

2. **Duplicate detection not working**:
   - Verify `normalize_name()` logic
   - Print normalized names for comparison
   - Check case-insensitive comparison

3. **Admin auth not persisting**:
   - Verify `st.session_state` is being used correctly
   - Check if session state is being cleared accidentally
   - Test in incognito window (clear session)

4. **Streamlit rerun issues**:
   - Ensure `st.rerun()` is called after state changes
   - Check for infinite rerun loops
   - Use `st.write()` to debug state values

---

## Rollback Plan

If issues arise in production:

1. **Revert to previous commit**:
   ```bash
   git checkout master
   ```

2. **Data migration** (if needed):
   - Sessions with `registrants` field remain compatible with old code
   - Old code reads `registered` count (ignores `registrants` array)
   - No data loss on rollback

---

## Next Steps After Implementation

After completing this feature:

1. Run `/speckit.tasks` to generate detailed task breakdown for implementation
2. Consider implementing follow-up enhancements:
   - Email notifications for registrations
   - Registration cancellation feature
   - Export registrant list to CSV/Excel
   - Admin operation audit log
   - Password reset functionality

---

## Support & Resources

- **Spec**: [spec.md](spec.md)
- **Research**: [research.md](research.md)
- **Data Model**: [data-model.md](data-model.md)
- **Service Contracts**: [contracts/service-contracts.md](contracts/service-contracts.md)
- **Implementation Plan**: [plan.md](plan.md)
- **CLAUDE.md**: Project guidelines and conventions

For questions or issues during implementation, refer to these documents first.
