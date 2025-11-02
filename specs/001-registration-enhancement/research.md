# Research: Registration Enhancement with Admin Management

**Feature**: 001-registration-enhancement
**Date**: 2025-10-28
**Status**: Complete

## Overview

This document captures research findings and technical decisions for implementing named registration tracking, duplicate prevention, attendee display, card navigation improvements, and admin management functionality in the conference registration system.

## Research Areas

### 1. Name Normalization and Duplicate Detection

**Decision**: Implement string normalization with trim + case-insensitive comparison preserving internal whitespace

**Rationale**:
- Clarification from spec: "trim leading/trailing whitespace, case-insensitive for Latin characters, preserve internal spacing"
- Prevents accidental duplicates from copy-paste errors (e.g., " 張三 " vs "張三")
- Preserves legitimate internal spacing (e.g., "歐陽 明" remains distinct from "歐陽明")
- Simple to implement and test without external dependencies

**Alternatives Considered**:
- **Exact string matching**: Rejected because users may accidentally add spaces
- **Remove all whitespace**: Rejected because it would incorrectly merge distinct names
- **Unicode normalization (NFKC/NFD)**: Rejected as overkill for this use case, adds complexity without clear benefit for Chinese names

**Implementation Approach**:
```python
def normalize_name(name: str) -> str:
    """Normalize name for duplicate checking."""
    return name.strip().lower()
```

---

### 2. Concurrent Registration Handling with File Locking

**Decision**: Use existing `file_lock.py` mechanism with first-come-first-served semantics

**Rationale**:
- Existing codebase already has working file locking implementation in `src/utils/file_lock.py`
- Clarification from spec: "First-come-first-served: first request succeeds, subsequent requests see '已額滿' message"
- File-based locking is sufficient for small-scale concurrent registrations (target: 10 concurrent users)
- No need for external database or distributed locking for this scale

**Alternatives Considered**:
- **Optimistic locking with version numbers**: Rejected as unnecessarily complex for file-based storage
- **Database with transactions**: Rejected to maintain existing JSON storage architecture
- **External locking service (Redis/etcd)**: Rejected as overkill for target scale and introduces new dependencies

**Implementation Approach**:
1. Acquire file lock before reading session data
2. Check capacity and duplicate names within locked section
3. Write updated data with new registrant
4. Release lock
5. Handle timeout/failure → return "已額滿" message to losers in race condition

---

### 3. Admin Authentication and Session Management

**Decision**: Use Streamlit session state for browser-session-lifetime authentication without external auth service

**Rationale**:
- Clarification from spec: "Browser session lifetime (remains valid until browser closes or explicit logout)"
- Streamlit already provides `st.session_state` for persisting data across reruns within same browser session
- Single admin user scenario doesn't require complex role-based access control (RBAC)
- Credentials stored in environment variables (`.env` file) - simple and secure enough for single-admin use case

**Alternatives Considered**:
- **JWT tokens with expiration**: Rejected due to added complexity and no inactivity timeout requirement
- **OAuth2/SSO integration**: Rejected as overkill for single admin use case
- **Session cookies with Flask/FastAPI**: Rejected to avoid adding web framework dependencies alongside Streamlit
- **Database-backed sessions**: Rejected to maintain file-based architecture

**Implementation Approach**:
```python
# In admin_service.py
def authenticate_admin(username: str, password: str) -> bool:
    # Load credentials from environment variables
    # Compare with bcrypt hash or simple comparison for MVP
    # Set st.session_state['admin_authenticated'] = True on success
    pass

# In UI components
if st.session_state.get('admin_authenticated', False):
    # Show admin panel
else:
    # Show login dialog
```

**Security Note**: Passwords will be compared via environment variables. For MVP, plain-text comparison is acceptable given:
- Single admin user
- Local/trusted deployment environment
- Can upgrade to bcrypt hashing in future iteration if needed

---

### 4. Streamlit Card Click Handling

**Decision**: Wrap entire card in invisible Streamlit button with `key` unique to session ID

**Rationale**:
- Existing code already uses button-based navigation (line 440-446 in `dashboard.py`)
- Streamlit buttons can be styled with CSS to be invisible/transparent overlay
- Button `key` parameter ensures each card has unique interaction handler

**Alternatives Considered**:
- **HTML anchor tags with custom click handlers**: Rejected because Streamlit doesn't support custom JavaScript without components
- **Custom Streamlit component**: Rejected as unnecessarily complex for simple click handling
- **st.components with React**: Rejected due to steep learning curve and maintenance burden

**Implementation Approach**:
1. Existing pattern already present (lines 432-447 in `dashboard.py`)
2. Current button is already overlaid on card - just needs CSS adjustment to cover entire card surface
3. Modify CSS to make button cover 100% of card area with transparent background
4. Already working, just need to verify `cursor: pointer` and hover effects

---

### 5. Registrant Data Structure in JSON

**Decision**: Add `registrants` array to each session object in `sessions.json`

**Rationale**:
- Maintains existing JSON structure pattern
- Each registrant stores: `{ "name": str, "registered_at": ISO8601 timestamp }`
- `registered` count derived from `len(registrants)` for consistency
- Supports future extensions (e.g., email, phone) without schema change

**Alternatives Considered**:
- **Separate registrants.json file**: Rejected to avoid join complexity and maintain data locality
- **SQLite database**: Rejected to maintain existing JSON storage architecture
- **registrants as CSV string**: Rejected due to parsing complexity and lack of structure

**Data Model**:
```json
{
  "sessions": [
    {
      "id": "session_001",
      "title": "...",
      "capacity": 100,
      "registered": 3,
      "registrants": [
        {
          "name": "張三",
          "registered_at": "2025-10-28T14:32:10+08:00"
        },
        {
          "name": "李四",
          "registered_at": "2025-10-28T14:35:22+08:00"
        }
      ],
      ...
    }
  ]
}
```

---

### 6. Admin Panel UI Pattern

**Decision**: Modal/sidebar-based admin panel using `st.dialog()` for forms and `st.sidebar` for navigation

**Rationale**:
- Streamlit 1.28.0 supports `st.dialog()` for modal dialogs (good for login, delete confirmation)
- Sidebar can show admin menu when authenticated (`st.session_state.admin_authenticated`)
- Follows existing UI patterns in codebase (modal-like interactions for focused tasks)

**Alternatives Considered**:
- **Separate admin page route**: Rejected because Streamlit doesn't have built-in routing (would need manual page state management)
- **Tabs for admin vs user view**: Rejected to avoid cluttering main UI with admin controls
- **Custom component**: Rejected due to complexity

**Implementation Approach**:
1. Admin button in dashboard header (top-right) triggers login dialog (`st.dialog()`)
2. On successful auth, show sidebar with admin menu: "新增課程", "編輯課程", "登出"
3. Each action opens appropriate form dialog
4. Delete confirmation uses nested dialog with registrant count warning

---

### 7. Session ID Generation for New Sessions

**Decision**: Sequential numbering with zero-padding (`session_001`, `session_002`, ...)

**Rationale**:
- Existing sessions use pattern `session_001` through `session_011`
- Simple to implement: find max existing ID, increment by 1
- Human-readable and sortable

**Alternatives Considered**:
- **UUID**: Rejected due to loss of human readability and sorting
- **Timestamp-based**: Rejected because multiple sessions could be created in same second
- **Title-based slugs**: Rejected due to collision risk and difficulty with Chinese characters

**Implementation Approach**:
```python
def generate_next_session_id(existing_sessions: List[Session]) -> str:
    # Extract numeric parts from all session IDs
    max_num = max([int(s.id.split('_')[1]) for s in existing_sessions], default=0)
    return f"session_{max_num + 1:03d}"
```

---

### 8. Validation Utilities

**Decision**: Create `src/utils/validation.py` module with reusable validators

**Rationale**:
- Multiple validation needs across the feature:
  - Name length (1-50 chars)
  - Date format (YYYY-MM-DD) and not in past
  - Capacity (positive integer)
  - Level enum ("初", "中", "高")
  - Required fields for session creation
- Centralized validation improves testability and reusability

**Implementation Approach**:
```python
# validation.py
from datetime import date
from typing import Tuple

def validate_name(name: str) -> Tuple[bool, str]:
    """Validate registrant name. Returns (is_valid, error_message)."""
    if not name or not name.strip():
        return False, "姓名不可為空"
    if len(name) > 50:
        return False, "姓名長度不可超過 50 字元"
    return True, ""

def validate_session_date(date_str: str) -> Tuple[bool, str]:
    """Validate session date format and not in past."""
    # Parse YYYY-MM-DD format
    # Check >= today
    pass

# ... other validators
```

---

## Summary of Key Decisions

| Area | Decision | Key Reason |
|------|----------|------------|
| Name Normalization | Trim + case-insensitive, preserve internal space | Balances user error tolerance with name accuracy |
| Concurrency | File locking with first-come-first-served | Uses existing mechanism, suitable for scale |
| Admin Auth | Streamlit session state + env variables | Simple, no external dependencies, browser-lifetime |
| Card Click | CSS-styled transparent button overlay | Uses existing Streamlit button pattern |
| Data Structure | Add `registrants` array to session JSON | Maintains data locality, extensible |
| Admin UI | Dialog + sidebar pattern | Native Streamlit components, clean separation |
| Session ID | Sequential `session_NNN` format | Consistent with existing data, human-readable |
| Validation | Centralized utils module | Reusable, testable, follows separation of concerns |

---

## Dependencies and Compatibility

**No new dependencies required**. All research confirms the feature can be implemented using:
- ✅ Streamlit 1.28.0 (existing)
- ✅ python-dateutil 2.8.2 (existing, for date parsing)
- ✅ Python 3.9.6 standard library (dataclasses, json, datetime, pathlib)

**Compatibility Notes**:
- Streamlit `st.dialog()` available in 1.28.0+ ✅
- File locking mechanism already implemented and tested ✅
- All UI patterns compatible with existing CSS styling ✅

---

## Risk Mitigation

**Identified Risks**:
1. **Concurrent registration race conditions**: Mitigated by file locking + proper error handling
2. **Session state loss on browser refresh**: Documented behavior - admin must re-login (acceptable per requirements)
3. **JSON file corruption during write**: Mitigated by existing atomic write + backup mechanism in `storage_service.py`
4. **Name normalization edge cases**: Covered by comprehensive test cases (Chinese, Latin, mixed, special chars)

---

## Next Phase

**Phase 1 Ready**: All technical unknowns resolved. Proceed to:
- Data model design (`data-model.md`)
- Service contracts (internal API signatures)
- UI component specifications
