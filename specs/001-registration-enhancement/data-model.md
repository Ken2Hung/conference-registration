# Data Model: Registration Enhancement

**Feature**: 001-registration-enhancement
**Date**: 2025-10-28

## Overview

This document defines the data models for the registration enhancement feature. The models extend the existing three-layer architecture (Model/Service/UI) and maintain backward compatibility with the current JSON storage format.

## Core Entities

### 1. Registrant (NEW)

Represents an individual who has registered for a conference session.

**File**: `src/models/registrant.py`

**Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `name` | `str` | 1-50 chars, non-empty after strip | Attendee's full name |
| `registered_at` | `str` | ISO 8601 format | Registration timestamp (e.g., "2025-10-28T14:32:10+08:00") |

**Validation Rules**:
- Name must not be empty after `strip()`
- Name length: 1 ≤ len(name) ≤ 50
- `registered_at` must be valid ISO 8601 timestamp
- Timezone-aware timestamp preferred (include offset like `+08:00`)

**Python Dataclass**:
```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Registrant:
    """Individual who registered for a session."""
    name: str
    registered_at: str  # ISO 8601 format

    def __post_init__(self):
        """Validate registrant data."""
        if not self.name or not self.name.strip():
            raise ValueError("Name cannot be empty")
        if len(self.name) > 50:
            raise ValueError("Name cannot exceed 50 characters")
        # Validate ISO 8601 format
        try:
            datetime.fromisoformat(self.registered_at.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError(f"Invalid timestamp format: {self.registered_at}")
```

**JSON Representation**:
```json
{
  "name": "張三",
  "registered_at": "2025-10-28T14:32:10+08:00"
}
```

---

### 2. Session (ENHANCED)

Enhanced existing `Session` model to include registrants tracking.

**File**: `src/models/session.py` (modify existing)

**New Field**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `registrants` | `List[Registrant]` | Optional, defaults to [] | List of registered attendees |

**Enhanced Methods**:
- `can_register(name: str) -> Tuple[bool, str]`: Check if name can register (not duplicate, capacity available)
- `add_registrant(registrant: Registrant) -> None`: Add registrant and sync `registered` count
- `get_registrants_names() -> List[str]`: Return list of names in chronological order

**Modified Validation**:
- `registered` count must equal `len(registrants)` for consistency
- Both fields should be kept in sync

**Python Dataclass Enhancement**:
```python
@dataclass
class Session:
    # ... existing fields ...
    registrants: List[Registrant] = field(default_factory=list)  # NEW

    def __post_init__(self):
        # ... existing validation ...

        # NEW: Validate registrants consistency
        if len(self.registrants) != self.registered:
            raise ValueError(
                f"Registrants count ({len(self.registrants)}) must match "
                f"registered count ({self.registered})"
            )

    def can_register(self, name: str) -> Tuple[bool, str]:
        """Check if name can register. Returns (can_register, error_message)."""
        from src.utils.validation import normalize_name

        if self.is_full():
            return False, "已額滿"
        if self.is_past():
            return False, "已過期"

        # Check duplicate using normalized comparison
        normalized = normalize_name(name)
        for reg in self.registrants:
            if normalize_name(reg.name) == normalized:
                return False, "您已報名"

        return True, ""

    def add_registrant(self, registrant: Registrant) -> None:
        """Add registrant and sync registered count."""
        self.registrants.append(registrant)
        self.registered = len(self.registrants)

    def get_registrants_names() -> List[str]:
        """Get list of registrant names in chronological order."""
        return [r.name for r in self.registrants]
```

**JSON Representation (Enhanced)**:
```json
{
  "id": "session_001",
  "title": "AI Guardrails:以 Python 構建企業級 LLM 安全防護策略",
  "description": "...",
  "date": "2025-11-15",
  "time": "14:00-16:00",
  "location": "線上 Zoom 會議室",
  "level": "中",
  "tags": ["Python", "LLM", "AI Safety"],
  "learning_outcomes": "...",
  "capacity": 100,
  "registered": 3,
  "speaker": { ... },
  "registrants": [
    {
      "name": "張三",
      "registered_at": "2025-10-28T14:32:10+08:00"
    },
    {
      "name": "李四",
      "registered_at": "2025-10-28T14:35:22+08:00"
    },
    {
      "name": "王五",
      "registered_at": "2025-10-28T15:01:05+08:00"
    }
  ]
}
```

---

### 3. AdminCredentials (NEW - Configuration Only)

Admin authentication credentials stored in environment variables, not a Python dataclass.

**Storage**: `.env` file (not committed to git)

**Fields**:
```bash
ADMIN_USERNAME=admin
ADMIN_PASSWORD=secure_password_here
```

**Access Pattern**:
```python
import os

def get_admin_credentials() -> Tuple[str, str]:
    """Load admin credentials from environment."""
    username = os.getenv("ADMIN_USERNAME", "admin")
    password = os.getenv("ADMIN_PASSWORD", "")
    return username, password
```

**Security Notes**:
- Passwords stored in plain text for MVP (acceptable for single-admin, trusted deployment)
- Future enhancement: Use bcrypt for password hashing
- `.env` file must be in `.gitignore`

---

## Data Relationships

```
Session 1---* Registrant
   |
   |-- 1 Speaker
```

- **Session → Registrant**: One-to-many (one session has many registrants)
- **Session → Speaker**: One-to-one (one session has one speaker)
- **Registrant**: Independent entity (no references to other entities)

---

## Data Validation Summary

### Registrant Validation
- ✅ Name non-empty after trim
- ✅ Name length 1-50 characters
- ✅ `registered_at` valid ISO 8601 timestamp

### Session Validation (Enhanced)
- ✅ All existing validations (ID format, title, capacity, etc.)
- ✅ NEW: `len(registrants) == registered` (consistency check)
- ✅ NEW: Cannot add registrant if full or expired
- ✅ NEW: Cannot have duplicate normalized names

---

## State Transitions

### Session Status State Machine

```
┌─────────────┐
│  available  │ ◄── Initial state (not full, not past)
└─────────────┘
       │
       ├──► (capacity reached) ──► ┌──────┐
       │                            │ full │
       │                            └──────┘
       │
       └──► (date passed) ──────► ┌──────────┐
                                   │ expired  │
                                   └──────────┘
```

**Status Determination** (no change from existing logic):
1. If `is_past()` → `"expired"`
2. Else if `is_full()` → `"full"`
3. Else → `"available"`

### Registration Lifecycle

```
┌──────────────┐
│ Not          │
│ Registered   │
└──────────────┘
       │
       │ (submit name)
       ▼
┌──────────────┐
│ Validate:    │
│ - Not full   │
│ - Not expired│
│ - Not dup    │
└──────────────┘
       │
       ├──► (validation fails) ──► [Show error]
       │
       └──► (validation passes)
              │
              ▼
       ┌──────────────┐
       │ Add to       │
       │ registrants  │
       │ array        │
       └──────────────┘
              │
              ▼
       ┌──────────────┐
       │ Sync         │
       │ registered   │
       │ count        │
       └──────────────┘
              │
              ▼
       ┌──────────────┐
       │ Persist to   │
       │ JSON file    │
       └──────────────┘
              │
              ▼
       ┌──────────────┐
       │ Registered   │
       └──────────────┘
```

---

## Data Migration

### Backward Compatibility

Existing `sessions.json` files without `registrants` field remain valid:
- Missing `registrants` field defaults to empty array `[]`
- `registered` count of 0 matches empty registrants array
- No data migration script needed for existing sessions

### Forward Compatibility

Once `registrants` field is added:
- Older code reading `registered` count still works
- `registered` count is authoritative until registrants field is populated
- Future writes should maintain both fields in sync

---

## Indexing and Performance

**Current Scale**: 11 sessions, ~100 registrations per session max

**Performance Considerations**:
- Linear search for duplicate name check: O(n) where n ≤ 1000 registrants per session → acceptable
- No indexing needed at current scale
- File locking ensures thread-safe concurrent access

**Future Optimization** (if scale increases to 1000+ sessions or 10k+ registrations):
- Consider SQLite for indexed lookups
- Add in-memory cache for session data
- Use database transactions instead of file locking

---

## Testing Data Models

### Unit Test Coverage

**Registrant Model** (`tests/unit/models/test_registrant.py`):
- ✅ Valid creation with proper fields
- ✅ Validation: empty name rejected
- ✅ Validation: name >50 chars rejected
- ✅ Validation: invalid timestamp format rejected
- ✅ ISO 8601 parsing with timezone

**Session Model Enhancements** (`tests/unit/models/test_session.py`):
- ✅ `can_register()` returns true for valid name
- ✅ `can_register()` rejects duplicate (case-insensitive)
- ✅ `can_register()` rejects when full
- ✅ `can_register()` rejects when expired
- ✅ `add_registrant()` syncs count
- ✅ `get_registrants_names()` returns chronological order
- ✅ Validation: registrants count mismatch raises error

---

## Summary

**New Models**: 1 (`Registrant`)
**Enhanced Models**: 1 (`Session`)
**Configuration**: Admin credentials in `.env`

**Key Design Decisions**:
1. ✅ Registrants stored inline with session (data locality)
2. ✅ `registered` count derived from `len(registrants)` (single source of truth)
3. ✅ Normalized name comparison for duplicates (case-insensitive, trim spaces)
4. ✅ ISO 8601 timestamps for timezone-aware registration tracking
5. ✅ Backward compatible with existing JSON data (default empty array)
