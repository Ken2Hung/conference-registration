# Implementation Plan: Speaker Image Rendering in Dashboard

**Feature ID**: 002-speaker-image-rendering
**Created**: 2025-10-28
**Status**: Planning
**Spec Reference**: [spec.md](./spec.md)

---

## Technical Context

### Current System Architecture

**Frontend**:
- Framework: Streamlit
- Dashboard Component: `src/ui/dashboard.py`
- Current speaker display: Text-only (`👤 {speaker.name}`)
- Styling: Custom CSS via `st.markdown()` with dark theme

**Backend**:
- Language: Python 3.8+
- Data Source: JSON files (`data/sessions.json`)
- No database - all data from properties/JSON files
- Models: `src/models/speaker.py` (Speaker dataclass), `src/models/session.py` (Session dataclass)

**Data Structure** (from `data/sessions.json`):
```json
{
  "speaker": {
    "name": "Nero Un 阮智軒",
    "photo": "images/speakers/nero-un.jpg",
    "bio": "..."
  }
}
```

**Image Storage**:
- Location: `images/speakers/` directory
- Format: Relative paths from project root (e.g., `images/speakers/nero-un.jpg`)
- Supported formats: JPG, PNG, WEBP
- Current status: Photo paths exist in data, but not displayed in UI

### Technology Stack

**Confirmed Technologies**:
- Frontend: Streamlit (for UI rendering)
- Backend: Python 3.8+
- Data Format: JSON
- Image Processing: PIL/Pillow (already in requirements.txt)

**Display Approach**:
- Decision needed: Streamlit `st.image()` vs HTML `<img>` via `st.markdown()`
- Consideration: HTML approach provides more CSS control for circular styling
- Research needed: Best practice for circular image display in Streamlit

### Integration Points

**Modified Components**:
1. `src/ui/dashboard.py::_render_session_card()` - Add photo rendering logic
2. No backend changes needed (data already contains photo paths)
3. No model changes needed (Speaker.photo field exists)

**New Components**:
1. Image utility function (optional) - Handle missing files and provide placeholder

### Dependencies & Constraints

**Dependencies**:
- Existing: Streamlit, PIL/Pillow, existing Speaker/Session models
- New: None (all required libraries already available)

**Constraints**:
- No database - all data from JSON files
- Image files must exist at paths specified in JSON
- Performance: Dashboard must load within 2 seconds
- Constitution compliance: Mandatory testing, minimal comments, comprehensive error handling

### Open Technical Questions

None - all technical decisions can be made based on existing architecture.

---

## Constitution Compliance Check

**Reference**: [constitution.md](../../.specify/memory/constitution.md) v1.0.0

### Principle I: Minimal Comments
✅ **Compliant** - Code will use self-documenting function names (e.g., `_render_speaker_photo()`, `_get_photo_placeholder()`). Comments only for CSS styling rationale.

### Principle II: Mandatory Testing
✅ **Compliant** - Tests required for:
- Photo rendering with valid path
- Fallback placeholder for missing photo
- Fallback for invalid/empty path
- Integration with session card display

Test files:
- `tests/ui/test_dashboard.py` - Add tests for photo rendering
- `tests/models/test_speaker.py` - Existing validation tests sufficient

### Principle III: Comprehensive Error Handling
✅ **Compliant** - Error handling for:
- Missing image files (try-except with fallback)
- Invalid paths (validation before rendering)
- Malformed image data (PIL error handling)
- No user-facing errors - graceful degradation to placeholder

### Principle IV: Conventional Commits
✅ **Compliant** - Commit format:
- `feat(ui): add circular speaker photo display in dashboard`
- `test(ui): add speaker photo rendering tests`
- `fix(ui): handle missing speaker photo gracefully`

### Principle V: Technology Stack Adherence
✅ **Compliant** - Using approved stack:
- Frontend: Streamlit ✓
- Backend: Python ✓
- Data: JSON files (no DB) ✓
- Testing: pytest ✓

### Quality Standards

**Code Quality**:
- PEP 8 compliance ✓
- Single responsibility functions ✓
- No magic numbers (define CSS constants) ✓

**Performance**:
- Target: Dashboard loads < 2 seconds with 50+ sessions
- Strategy: Efficient image handling, no blocking operations

**Documentation**:
- Update README.md: Document image requirements (formats, location)
- API contracts: N/A (no API changes)
- Quickstart guide: Add image setup instructions

### Gate Evaluation

**Pre-Implementation Gates**:
1. ✅ Spec approved and complete
2. ✅ Constitution compliance verified
3. ✅ Technical approach feasible with existing stack
4. ✅ All dependencies available

**Proceed to Phase 0: Research** ✓

---

## Phase 0: Research & Decisions

### Research Tasks

#### R1: Streamlit Image Display Best Practices

**Question**: What is the best approach for displaying circular images in Streamlit?

**Options**:
1. `st.image()` with custom CSS wrapper
2. HTML `<img>` tag via `st.markdown(unsafe_allow_html=True)`
3. Base64-encoded image in HTML

**Research Focus**:
- Performance implications for 10+ images per page
- Circular styling control (border-radius, shadows)
- Responsive design support
- Caching behavior

#### R2: Missing Image Handling Patterns

**Question**: What's the best fallback strategy for missing speaker photos?

**Options**:
1. Unicode emoji placeholder (👤)
2. Base64-encoded SVG avatar icon
3. Default avatar image file
4. CSS-only circular placeholder

**Research Focus**:
- Visual consistency with design theme
- Performance (no extra file I/O for every missing image)
- Accessibility considerations

#### R3: Image Loading Performance

**Question**: How to ensure efficient image loading without blocking dashboard render?

**Research Focus**:
- Streamlit's image caching behavior
- Lazy loading options
- Image size optimization requirements
- Layout shift prevention

---

## Phase 1: Design & Contracts

### Data Model

**No changes required** - Existing models sufficient:

**Speaker** (`src/models/speaker.py`):
```python
@dataclass
class Speaker:
    name: str
    photo: str  # Relative path from project root
    bio: str
```

**Validation** (already exists):
- Non-empty name, photo, bio
- Photo path validation (non-empty string)

**No new validation needed** - File existence check happens at render time, not model initialization.

---

### API Contracts

**N/A** - This is a UI-only feature. No API endpoints or backend contracts required.

The feature uses existing data from JSON files and existing service layer:
- `src/services/session_service.py::get_past_sessions()`
- `src/services/session_service.py::get_upcoming_sessions()`

---

### Component Architecture

#### Modified Component: `src/ui/dashboard.py`

**Current Structure**:
```
render_dashboard()
  ├── _render_section_title()
  └── _render_session_card(session, is_past)
        └── Currently: HTML with speaker name only
```

**Updated Structure**:
```
render_dashboard()
  ├── _render_section_title()
  ├── _render_session_card(session, is_past)
  │     ├── _render_speaker_photo(photo_path, speaker_name, is_past)
  │     └── HTML layout with photo + name
  └── _get_photo_placeholder_html() [new helper]
```

**New Helper Functions**:

1. `_render_speaker_photo(photo_path: str, speaker_name: str, is_past: bool) -> str`
   - Returns HTML string for speaker photo or placeholder
   - Handles missing file gracefully
   - Applies past session opacity if needed
   - Parameters:
     - `photo_path`: Relative path from project root
     - `speaker_name`: Used for alt text accessibility
     - `is_past`: Whether to apply reduced opacity

2. `_get_photo_placeholder_html(speaker_name: str, is_past: bool) -> str`
   - Returns HTML for placeholder when photo unavailable
   - Consistent dimensions with photo display (50px diameter)
   - Styled to match dark theme

**CSS Constants** (add to module-level):
```python
PHOTO_SIZE = "50px"
PHOTO_BORDER_COLOR = "#2d3748"
PHOTO_SHADOW = "0 2px 8px rgba(0, 0, 0, 0.3)"
PAST_SESSION_OPACITY = "0.6"
```

---

### UI/UX Design

**Speaker Photo Display Specifications**:

**Dimensions**:
- Size: 50px × 50px (circular)
- Border: 2px solid #2d3748
- Shadow: 0 2px 8px rgba(0, 0, 0, 0.3)
- Spacing: 12px right margin from name

**Layout in Session Card**:
```
┌─────────────────────────────────────┐
│ 📅 Date Time          Difficulty    │
│                                     │
│ Session Title                       │
│                                     │
│ [Photo] Speaker Name  <-- NEW      │
│                                     │
│ [Progress Bar]                      │
│ #tag #tag #tag                      │
│                                     │
│ [查看詳情 Button]                    │
└─────────────────────────────────────┐
```

**HTML Structure** (within session card):
```html
<div style="display: flex; align-items: center; margin-bottom: 12px;">
    <img src="{photo_path}"
         alt="{speaker_name}"
         style="width: 50px; height: 50px;
                border-radius: 50%;
                object-fit: cover;
                border: 2px solid #2d3748;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
                margin-right: 12px;
                opacity: {1.0 or 0.6};">
    <span style="color: #cbd5e1; font-size: 14px;">
        {speaker_name}
    </span>
</div>
```

**Placeholder HTML** (for missing photos):
```html
<div style="width: 50px; height: 50px;
            border-radius: 50%;
            background: linear-gradient(135deg, #334155 0%, #1e293b 100%);
            border: 2px solid #2d3748;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
            margin-right: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: {1.0 or 0.6};">
    <span style="font-size: 24px;">👤</span>
</div>
```

**Responsive Behavior**:
- Photo maintains 50px size on all devices
- Layout stacks vertically on very narrow screens (handled by Streamlit's responsive container)

---

### Testing Strategy

**Test Coverage Requirements** (per Constitution: >80% for new features)

#### Unit Tests: `tests/ui/test_dashboard.py`

**Test Cases**:

1. `test_render_speaker_photo_with_valid_path()`
   - GIVEN: Valid image path exists
   - WHEN: `_render_speaker_photo()` called
   - THEN: Returns HTML with `<img>` tag and correct path

2. `test_render_speaker_photo_with_missing_file()`
   - GIVEN: Image path points to non-existent file
   - WHEN: `_render_speaker_photo()` called
   - THEN: Returns placeholder HTML with emoji
   - AND: No exception raised

3. `test_render_speaker_photo_with_empty_path()`
   - GIVEN: Empty string as photo path
   - WHEN: `_render_speaker_photo()` called
   - THEN: Returns placeholder HTML

4. `test_render_speaker_photo_past_session_opacity()`
   - GIVEN: Valid photo path and `is_past=True`
   - WHEN: `_render_speaker_photo()` called
   - THEN: Returns HTML with reduced opacity (0.6)

5. `test_get_photo_placeholder_html_structure()`
   - GIVEN: Speaker name and is_past flag
   - WHEN: `_get_photo_placeholder_html()` called
   - THEN: Returns HTML with circular div and emoji
   - AND: Contains correct dimensions and styling

6. `test_session_card_integrates_photo()`
   - GIVEN: Session object with speaker
   - WHEN: `_render_session_card()` called
   - THEN: Rendered HTML contains speaker photo or placeholder
   - AND: Photo appears before speaker name

#### Integration Tests

**Manual Testing Checklist** (document in test plan):
1. Dashboard loads with all photos displayed
2. Missing photo displays placeholder without errors
3. Past sessions show reduced opacity photos
4. Photos maintain circular shape on browser resize
5. Dashboard loads within 2 seconds with 10+ sessions

**Test Data Setup**:
- Create test image files in `tests/fixtures/images/`
- Update test sessions JSON to reference test images
- Include edge cases: missing files, invalid formats

---

### Error Handling Design

**Error Scenarios & Handling**:

1. **Image file not found**:
   ```python
   try:
       if os.path.exists(photo_path):
           # Render image
       else:
           # Return placeholder
   except Exception:
       # Return placeholder
   ```

2. **Invalid image format**:
   - No explicit validation needed
   - Browser handles rendering
   - If browser fails, image broken icon appears (acceptable)

3. **Empty/None photo path**:
   ```python
   if not photo_path or not photo_path.strip():
       return _get_photo_placeholder_html(speaker_name, is_past)
   ```

4. **File I/O errors**:
   - Wrapped in try-except
   - Falls back to placeholder
   - No logging needed (not critical failure)

**Error Logging**:
- No logging for missing photos (expected scenario, not an error)
- Only log if unexpected exceptions occur during render

---

### Development Workflow

**Implementation Order**:

1. **Phase 1a: Helper Functions**
   - Create `_get_photo_placeholder_html()`
   - Create `_render_speaker_photo()`
   - Add module-level CSS constants

2. **Phase 1b: Integration**
   - Update `_render_session_card()` to use new photo rendering
   - Replace text-only speaker display with photo + name

3. **Phase 1c: Testing**
   - Write unit tests for helper functions
   - Write integration test for session card
   - Manual testing with real dashboard

4. **Phase 1d: Documentation**
   - Update README.md with image requirements
   - Create quickstart section for adding speaker images

**Acceptance Criteria** (before merge):
- ✅ All unit tests pass
- ✅ Manual testing confirms visual design matches spec
- ✅ Constitution compliance verified (testing, error handling, commits)
- ✅ Dashboard loads < 2 seconds
- ✅ No errors in browser console

---

## Phase 2: Task Breakdown

*Task breakdown will be generated in `/speckit.tasks` phase*

---

## Risks & Mitigations

### Technical Risks

**Risk 1: Image Loading Performance**
- Impact: Dashboard load time exceeds 2 seconds
- Likelihood: Low (small images, local files)
- Mitigation: Use Streamlit's caching, optimize image sizes if needed

**Risk 2: Inconsistent Image Sizes**
- Impact: Photos appear distorted or non-circular
- Likelihood: Medium (depends on source image aspect ratios)
- Mitigation: Use `object-fit: cover` CSS to crop to circular shape

**Risk 3: Missing Image Files**
- Impact: Broken image icons shown to users
- Likelihood: Medium (depends on data quality)
- Mitigation: Fallback placeholder tested for all edge cases

### Process Risks

**Risk 1: Test Coverage Below 80%**
- Impact: Constitution violation, merge blocked
- Likelihood: Low
- Mitigation: Write tests first (TDD approach)

---

## Success Metrics

**Technical Metrics**:
1. Dashboard load time: < 2 seconds (target: 1.5 seconds)
2. Test coverage: > 80% for new code
3. Zero errors in browser console
4. All photos display correctly or show placeholder

**User Experience Metrics**:
1. Visual consistency: All photos 50px circular with identical styling
2. Responsive design: Layout works on desktop, tablet, mobile
3. Accessibility: All images have alt text with speaker names

---

## Open Questions & Decisions

### Resolved in Research Phase:
- Will be determined in Phase 0

### Deferred Decisions:
- None

---

## Appendix

### Related Files

**Implementation Files**:
- `src/ui/dashboard.py` (primary modification)
- `data/sessions.json` (data source)
- `images/speakers/*.jpg` (image assets)

**Test Files**:
- `tests/ui/test_dashboard.py` (new tests)
- `tests/fixtures/images/` (test images)

**Documentation Files**:
- `README.md` (setup instructions)
- `specs/002-speaker-image-rendering/quickstart.md` (developer guide)

### References

- [Streamlit Image Documentation](https://docs.streamlit.io/library/api-reference/media/st.image)
- [Streamlit Custom CSS Guide](https://docs.streamlit.io/library/api-reference/utilities/st.markdown)
- Constitution: `/.specify/memory/constitution.md` v1.0.0
- Feature Spec: `./spec.md`
