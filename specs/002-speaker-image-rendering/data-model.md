# Data Model: Speaker Image Rendering

**Feature**: 002-speaker-image-rendering
**Created**: 2025-10-28
**Status**: No Changes Required

---

## Overview

This feature is a **UI-only enhancement** that does not require changes to the existing data model. The necessary data structures already exist in the codebase.

---

## Existing Data Models

### Speaker Model

**Location**: `src/models/speaker.py`

**Definition**:
```python
from dataclasses import dataclass

@dataclass
class Speaker:
    """Speaker information for a session."""

    name: str
    photo: str
    bio: str

    def __post_init__(self):
        """Validate speaker data after initialization."""
        if not self.name or not self.name.strip():
            raise ValueError("Speaker name cannot be empty")

        if not self.photo or not self.photo.strip():
            raise ValueError("Speaker photo path cannot be empty")

        if not self.bio or not self.bio.strip():
            raise ValueError("Speaker bio cannot be empty")
```

**Fields**:
- `name` (str): Speaker's full name
- `photo` (str): Relative path to speaker photo from project root (e.g., `images/speakers/name.jpg`)
- `bio` (str): Speaker biography

**Validation**:
- ✅ All fields are required (non-empty)
- ✅ Photo field contains path string (file existence validated at render time)

**Relationships**:
- Used by `Session` model (one speaker per session)

---

### Session Model

**Location**: `src/models/session.py`

**Relevant Fields**:
```python
@dataclass
class Session:
    id: str
    title: str
    # ... other fields ...
    speaker: Speaker  # Speaker object with photo field
```

**Usage**: Dashboard renders session cards which include speaker information via `session.speaker.photo` and `session.speaker.name`.

---

## Data Source

### JSON File Structure

**Location**: `data/sessions.json`

**Speaker Data Example**:
```json
{
  "sessions": [
    {
      "id": "session_001",
      "title": "AI Guardrails:以 Python 構建企業級 LLM 安全防護策略",
      "speaker": {
        "name": "Nero Un 阮智軒",
        "photo": "images/speakers/nero-un.jpg",
        "bio": "來自澳門的開發者,現職 IBM 顧問。專注於 AI 安全與企業級應用開發..."
      }
    }
  ]
}
```

**Photo Path Convention**:
- Base directory: `images/speakers/`
- Naming: `{speaker-slug}.jpg` (e.g., `nero-un.jpg`, `zhang-zhicheng.jpg`)
- Formats: JPG, PNG, WEBP
- Relative from project root

---

## File System Structure

### Image Assets

```
images/
└── speakers/
    ├── nero-un.jpg
    ├── zhang-zhicheng.jpg
    ├── li-xinyi.jpg
    ├── wang-daming.jpg
    └── ... (more speaker photos)
```

**Requirements**:
- ✅ All photos stored in `images/speakers/` directory
- ✅ Filenames match those referenced in `data/sessions.json`
- ✅ Photos optimized for web (< 10KB each recommended)
- ✅ Dimensions: Any size (CSS will scale to 50px circular)

---

## Data Flow

```
data/sessions.json
        ↓
    JSON Parser
        ↓
src/services/session_service.py
  └── get_past_sessions() / get_upcoming_sessions()
        ↓
    Session objects (with Speaker.photo field)
        ↓
src/ui/dashboard.py
  └── _render_session_card(session)
        ↓
    _render_speaker_avatar(session.speaker.photo, session.speaker.name)
        ↓
    HTML <img> tag or placeholder avatar
        ↓
    Browser renders circular photo
```

---

## Validation Rules

### Existing Validation (Speaker Model)

✅ **At Data Model Level** (`speaker.py`):
- Photo path must be non-empty string
- Validates in `__post_init__()` method

### Runtime Validation (UI Level)

✅ **At Render Time** (`dashboard.py`):
- File existence NOT validated in Python
- Browser's `onerror` event handles missing files
- Fallback placeholder displays if image fails to load

**Rationale**:
- No need for Python file I/O checks (performance overhead)
- Browser efficiently handles missing files via `onerror`
- Graceful degradation without exceptions

---

## No Schema Changes Required

### Why No Changes?

1. **Photo field exists**: `Speaker.photo` already contains image paths
2. **Data format compatible**: Relative paths work with HTML `<img>` tags
3. **Validation sufficient**: Existing validation ensures non-empty paths
4. **UI-only feature**: No backend logic or database changes needed

### What This Feature Adds

**Only UI rendering logic**:
- Helper function to generate photo HTML
- Helper function to generate fallback placeholder
- Updated session card template to include photo

**No data structure changes**:
- ❌ No new fields
- ❌ No new models
- ❌ No database migrations
- ❌ No API changes

---

## Testing Data

### Test Fixtures

**Location**: `tests/fixtures/images/`

**Test Photo Files**:
```
tests/
└── fixtures/
    └── images/
        ├── test-speaker-1.jpg  (valid photo)
        ├── test-speaker-2.png  (valid photo, PNG format)
        └── (missing-photo.jpg intentionally NOT created for fallback testing)
```

**Test Session Data** (`tests/fixtures/test_sessions.json`):
```json
{
  "sessions": [
    {
      "id": "test_001",
      "speaker": {
        "name": "Test Speaker One",
        "photo": "tests/fixtures/images/test-speaker-1.jpg",
        "bio": "Test bio"
      }
    },
    {
      "id": "test_002",
      "speaker": {
        "name": "Missing Photo Speaker",
        "photo": "tests/fixtures/images/missing-photo.jpg",
        "bio": "Test bio for missing photo"
      }
    }
  ]
}
```

---

## Edge Cases & Handling

### 1. Missing Photo File

**Scenario**: JSON contains path `images/speakers/john-doe.jpg`, but file doesn't exist

**Data**: Speaker model still validates (path is non-empty string) ✅

**Rendering**: Browser's `onerror` event triggers, placeholder avatar displays ✅

**User Experience**: Sees speaker initial in gradient circle (graceful degradation) ✅

---

### 2. Invalid Photo Path

**Scenario**: JSON contains empty string `""` or whitespace `"   "`

**Data**: Speaker model validation **FAILS** in `__post_init__()` ❌

**Result**: Data loading error (expected behavior - invalid data)

**Mitigation**: Data validation ensures this never reaches UI

---

### 3. Malformed Image File

**Scenario**: File exists but is corrupted or wrong format

**Data**: Speaker model validates (path exists) ✅

**Rendering**: Browser fails to decode image, `onerror` triggers ✅

**User Experience**: Placeholder avatar displays ✅

---

### 4. Large Image Files

**Scenario**: Photo is 2MB high-resolution image

**Data**: Speaker model validates (path is string) ✅

**Rendering**: Browser loads and downscales (may be slow) ⚠️

**Mitigation**:
- Rely on data quality (photos should be optimized)
- CSS `object-fit: cover` crops and scales efficiently
- Browser caching prevents re-download

**Recommendation**: Document image optimization requirements in quickstart guide

---

## Data Integrity Checklist

✅ **Current Data Quality** (`data/sessions.json`):
- All 11 sessions have valid speaker objects
- All speaker objects have `photo` field with path
- All paths follow convention: `images/speakers/{name}.jpg`

✅ **Photo Files Exist**:
- ✅ `images/speakers/nero-un.jpg`
- ✅ `images/speakers/zhang-zhicheng.jpg`
- ✅ `images/speakers/li-xinyi.jpg`
- ✅ `images/speakers/wang-daming.jpg`
- ✅ `images/speakers/chen-xiaohua.jpg`
- ✅ `images/speakers/lin-yating.jpg`
- ✅ `images/speakers/huang-jianguo.jpg`
- ✅ `images/speakers/zhou-zhiming.jpg`
- ✅ `images/speakers/liu-fangyi.jpg`
- ✅ `images/speakers/wu-chengen.jpg`
- ✅ `images/speakers/zheng-mingzhe.jpg`

**Status**: All data ready for feature implementation ✅

---

## Performance Characteristics

### Data Loading

**Current**:
- JSON file parsed once on dashboard load
- Speaker objects created from JSON data
- Photo paths stored in memory as strings (~50 bytes each)

**Impact of Feature**:
- ❌ No change to data loading
- ❌ No additional memory usage
- ❌ No database queries (none exist)

### Runtime Performance

**Photo Rendering**:
- Photo paths passed directly to HTML (zero processing)
- Browser handles image loading asynchronously
- No Python image processing required

**Memory Usage**:
- Speaker objects: ~500 bytes each (existing)
- Photo HTML strings: ~800 bytes each (new, temporary)
- Total for 10 sessions: ~13KB (negligible)

---

## Conclusion

**Data Model Status**: ✅ **No changes required**

**Existing models fully support this feature**:
- `Speaker.photo` field contains all necessary data
- `Session` model provides speaker relationship
- JSON data source has all required information
- File system structure is already in place

**Implementation can proceed directly to UI layer** with no data model modifications.

---

## References

- **Speaker Model**: `src/models/speaker.py`
- **Session Model**: `src/models/session.py`
- **Data Source**: `data/sessions.json`
- **Service Layer**: `src/services/session_service.py`
- **Feature Spec**: `spec.md`
- **Implementation Plan**: `plan.md`
