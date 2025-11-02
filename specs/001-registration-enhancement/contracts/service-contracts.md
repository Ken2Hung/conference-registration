# Service Layer Contracts

**Feature**: 001-registration-enhancement
**Date**: 2025-10-28

## Overview

This document defines the service layer API contracts (internal Python function signatures) for the registration enhancement feature. These are not REST/GraphQL APIs but internal service method interfaces that the UI layer will call.

---

## 1. Registration Service

**File**: `src/services/registration_service.py` (NEW)

### register_for_session()

Register an attendee for a session with duplicate checking and concurrency control.

**Signature**:
```python
def register_for_session(
    session_id: str,
    attendee_name: str
) -> Tuple[bool, str]:
    """
    Register attendee for a session.

    Args:
        session_id: Session identifier (e.g., "session_001")
        attendee_name: Attendee's full name

    Returns:
        Tuple of (success: bool, message: str)
        - (True, "報名成功") on success
        - (False, "您已報名") if duplicate name
        - (False, "已額滿") if capacity reached or race condition
        - (False, "已過期") if session expired
        - (False, "找不到議程：{session_id}") if session not found
        - (False, "姓名不可為空") if name validation fails

    Raises:
        IOError: If file operations fail (lock timeout, write error)
    ```

**Behavior**:
1. Load session data with file lock
2. Validate session exists
3. Validate attendee name (use `validation.validate_name()`)
4. Check session status (not full, not expired)
5. Check duplicate using normalized name comparison
6. Add registrant with current timestamp
7. Persist to JSON
8. Clear service cache
9. Release lock

**Thread Safety**: Uses file locking mechanism from `src/utils/file_lock.py`

---

## 2. Session Service (ENHANCED)

**File**: `src/services/session_service.py` (modify existing)

### Existing Methods (No Changes)
- `get_all_sessions() -> List[Session]`
- `get_session_by_id(session_id: str) -> Optional[Session]`

### New/Enhanced Methods

#### get_session_registrants()

Get list of registrants for a session.

**Signature**:
```python
def get_session_registrants(session_id: str) -> List[Registrant]:
    """
    Get all registrants for a session in chronological order.

    Args:
        session_id: Session identifier

    Returns:
        List of Registrant objects (ordered by registration time)
        Empty list if session not found or has no registrants

    Raises:
        None (returns empty list on error)
    ```

#### create_session()

Create a new session (admin functionality).

**Signature**:
```python
def create_session(
    title: str,
    description: str,
    date: str,
    time: str,
    location: str,
    level: str,
    tags: List[str],
    learning_outcomes: str,
    capacity: int,
    speaker_name: str,
    speaker_photo: str,
    speaker_bio: str
) -> Tuple[bool, str, Optional[str]]:
    """
    Create a new session.

    Args:
        All session fields (excluding id and registrants)

    Returns:
        Tuple of (success: bool, message: str, session_id: Optional[str])
        - (True, "建立成功", "session_012") on success
        - (False, "驗證失敗：{reason}", None) on validation error
        - (False, "儲存失敗：{reason}", None) on I/O error

    Behavior:
        - Generates next session ID automatically
        - Validates all fields
        - Persists to JSON with file lock
        - Clears service cache
    ```

#### update_session()

Update an existing session (admin functionality).

**Signature**:
```python
def update_session(
    session_id: str,
    updates: dict
) -> Tuple[bool, str]:
    """
    Update an existing session.

    Args:
        session_id: Session to update
        updates: Dictionary of fields to update (partial updates allowed)

    Returns:
        Tuple of (success: bool, message: str)
        - (True, "更新成功") on success
        - (False, "找不到議程") if session not found
        - (False, "驗證失敗：{reason}") on validation error
        - (False, "不可將容量設定為低於已報名人數") if capacity < registered

    Behavior:
        - Validates updated fields
        - Prevents capacity reduction below registered count
        - Persists changes with file lock
        - Clears service cache
    ```

#### delete_session()

Delete a session (admin functionality).

**Signature**:
```python
def delete_session(session_id: str) -> Tuple[bool, str, int]:
    """
    Delete a session.

    Args:
        session_id: Session to delete

    Returns:
        Tuple of (success: bool, message: str, registrants_count: int)
        - (True, "刪除成功", N) on success
        - (False, "找不到議程", 0) if session not found

    Behavior:
        - Returns registrants count for confirmation dialog
        - Removes session from JSON with file lock
        - Clears service cache

    Note:
        UI layer should confirm deletion before calling this method
        when registrants_count > 0
    ```

---

## 3. Admin Service

**File**: `src/services/admin_service.py` (NEW)

### authenticate_admin()

Authenticate admin user.

**Signature**:
```python
def authenticate_admin(username: str, password: str) -> bool:
    """
    Authenticate admin credentials.

    Args:
        username: Admin username
        password: Admin password

    Returns:
        True if credentials valid, False otherwise

    Behavior:
        - Loads credentials from environment variables
        - Compares with provided values
        - For MVP: plain-text comparison
        - Future: use bcrypt for hashing

    Security:
        - No timing attack protection (acceptable for MVP)
        - Single admin user only
    ```

### is_admin_authenticated()

Check if current session is authenticated.

**Signature**:
```python
def is_admin_authenticated() -> bool:
    """
    Check if admin is authenticated in current session.

    Returns:
        True if st.session_state['admin_authenticated'] is True

    Behavior:
        - Reads from Streamlit session state
        - Returns False if key doesn't exist
    ```

### logout_admin()

Log out admin user.

**Signature**:
```python
def logout_admin() -> None:
    """
    Log out admin user.

    Behavior:
        - Clears st.session_state['admin_authenticated']
        - May clear other admin-related session state
    ```

---

## 4. Validation Utilities

**File**: `src/utils/validation.py` (NEW)

### validate_name()

**Signature**:
```python
def validate_name(name: str) -> Tuple[bool, str]:
    """
    Validate attendee name.

    Args:
        name: Name to validate

    Returns:
        Tuple of (is_valid: bool, error_message: str)
        - (True, "") if valid
        - (False, "姓名不可為空") if empty
        - (False, "姓名長度不可超過 50 字元") if too long
    ```

### normalize_name()

**Signature**:
```python
def normalize_name(name: str) -> str:
    """
    Normalize name for duplicate comparison.

    Args:
        name: Name to normalize

    Returns:
        Normalized name (trimmed, lowercased)

    Behavior:
        - Trims leading/trailing whitespace
        - Converts to lowercase (for Latin chars)
        - Preserves internal spacing
        - Example: " 張三 " → "張三", "John Doe" → "john doe"
    ```

### validate_session_date()

**Signature**:
```python
def validate_session_date(date_str: str, allow_past: bool = False) -> Tuple[bool, str]:
    """
    Validate session date.

    Args:
        date_str: Date in YYYY-MM-DD format
        allow_past: If True, past dates are allowed (for editing existing sessions)

    Returns:
        Tuple of (is_valid: bool, error_message: str)
        - (True, "") if valid
        - (False, "日期格式錯誤") if format invalid
        - (False, "日期不可為過去") if date < today and allow_past=False
    ```

### validate_capacity()

**Signature**:
```python
def validate_capacity(capacity: int, current_registered: int = 0) -> Tuple[bool, str]:
    """
    Validate session capacity.

    Args:
        capacity: Desired capacity
        current_registered: Current registration count (for updates)

    Returns:
        Tuple of (is_valid: bool, error_message: str)
        - (True, "") if valid
        - (False, "容量必須為正整數") if capacity <= 0
        - (False, "容量不可低於目前已報名人數") if capacity < current_registered
    ```

### validate_level()

**Signature**:
```python
def validate_level(level: str) -> Tuple[bool, str]:
    """
    Validate session level.

    Args:
        level: Level to validate

    Returns:
        Tuple of (is_valid: bool, error_message: str)
        - (True, "") if valid ("初", "中", or "高")
        - (False, "難度必須為「初」、「中」或「高」") if invalid
    ```

---

## Error Handling Strategy

### Service Layer Error Handling

**Pattern**: Services return `Tuple[bool, str]` for operations that can fail
- `bool`: Success indicator
- `str`: User-friendly message (Chinese text for UI display)

**Exceptions**:
- Services should catch and log internal errors
- Only raise exceptions for catastrophic failures (file system errors, data corruption)
- UI layer catches exceptions and shows generic error message

### Example Error Flow

```python
# Service layer
def register_for_session(session_id: str, name: str) -> Tuple[bool, str]:
    try:
        # ... validation ...
        if duplicate:
            return False, "您已報名"
        # ... registration logic ...
        return True, "報名成功"
    except IOError as e:
        logger.error(f"File operation failed: {e}")
        return False, "系統錯誤，請稍後再試"
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False, "發生未預期的錯誤"

# UI layer
success, message = register_for_session(session_id, name)
if success:
    st.success(message)
    st.balloons()
else:
    st.error(message)
```

---

## Concurrency Control

### File Locking Pattern

All write operations must use the existing file locking mechanism:

```python
from src.utils.file_lock import lock_file

def some_write_operation():
    with lock_file(SESSION_FILE_PATH, timeout=5.0):
        # Read current data
        data = load_json()
        # Modify data
        data['sessions'].append(new_session)
        # Write atomically
        save_json(data)
    # Lock released automatically
```

**Timeout Handling**:
- Default timeout: 5 seconds
- If lock not acquired → return `(False, "系統忙碌中，請稍後再試")`

---

## Cache Invalidation

### Pattern

All write operations must clear the service cache:

```python
# After successful write
_session_cache.clear()  # or whatever cache invalidation method exists
```

**Affected Operations**:
- ✅ `register_for_session()` - clears cache after adding registrant
- ✅ `create_session()` - clears cache after creating session
- ✅ `update_session()` - clears cache after updating session
- ✅ `delete_session()` - clears cache after deleting session

---

## Testing Contracts

### Service Layer Tests

**Contract Tests** (`tests/contract/`):
- Verify function signatures match contracts
- Test return types and error codes
- Validate error message formats

**Unit Tests** (`tests/unit/services/`):
- Test each service method independently
- Mock file I/O and locking
- Test all error paths

**Integration Tests** (`tests/integration/`):
- Test service methods with real file operations
- Test concurrent registration scenarios
- Test admin workflow end-to-end

---

## Summary

**New Services**: 2 (`registration_service.py`, `admin_service.py`)
**Enhanced Services**: 1 (`session_service.py`)
**New Utilities**: 1 (`validation.py`)

**Total New Methods**: 13
**Total Enhanced Methods**: 4

**Key Design Patterns**:
- ✅ Return tuples `(bool, str)` for operations with user feedback
- ✅ File locking for all write operations
- ✅ Cache invalidation after writes
- ✅ Chinese error messages for UI display
- ✅ Validation separated into utility module for reusability
