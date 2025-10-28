# Quickstart: Speaker Image Rendering

**Feature**: 002-speaker-image-rendering
**For**: Developers implementing circular speaker photos in dashboard
**Time to Implement**: ~2-3 hours

---

## Overview

This guide walks you through implementing circular speaker profile photos in the Streamlit dashboard. You'll add visual speaker identification to session cards with automatic fallback for missing images.

**What You'll Build**:
- Circular speaker photos (50px diameter) next to speaker names
- Automatic fallback to speaker initial in gradient circle
- Consistent styling matching dark theme
- Graceful error handling for missing files

---

## Prerequisites

**Required Knowledge**:
- ✅ Python 3.8+ basics
- ✅ Streamlit fundamentals
- ✅ HTML/CSS basics
- ✅ Git workflow

**Environment**:
- ✅ Project cloned and dependencies installed (`pip install -r requirements.txt`)
- ✅ Streamlit dashboard runs successfully (`streamlit run app.py`)
- ✅ Branch: `002-speaker-image-rendering` (create if needed: `git checkout -b 002-speaker-image-rendering`)

**Files You'll Modify**:
- `src/ui/dashboard.py` (primary modification)
- `tests/ui/test_dashboard.py` (add tests)

---

## Step 1: Understand Current Implementation

### Current Dashboard Structure

**File**: `src/ui/dashboard.py`

**Current Speaker Display** (line ~70):
```python
<div style="color: #cbd5e1; font-size: 14px; margin-bottom: 12px;">
    👤 {session.speaker.name}
</div>
```

**What's Missing**:
- No photo display
- Only emoji icon + name text

### Data Already Available

**Session Data** (`data/sessions.json`):
```json
{
  "speaker": {
    "name": "Nero Un 阮智軒",
    "photo": "images/speakers/nero-un.jpg",
    "bio": "..."
  }
}
```

**Speaker Model** (`src/models/speaker.py`):
```python
@dataclass
class Speaker:
    name: str
    photo: str  # ← This field exists!
    bio: str
```

**Key Insight**: Photo paths are already in the data - you just need to render them!

---

## Step 2: Add Helper Functions

### 2a. Add Speaker Avatar Renderer

**Location**: `src/ui/dashboard.py` (add near top, after imports)

**Code**:
```python
def _render_speaker_avatar(
    photo_path: str,
    speaker_name: str,
    size: int = 50,
    is_past: bool = False
) -> str:
    """
    Render speaker avatar with automatic fallback to initial.

    Args:
        photo_path: Relative path to photo from project root
        speaker_name: Speaker name (for alt text and initial)
        size: Avatar diameter in pixels
        is_past: Apply reduced opacity for past sessions

    Returns:
        HTML string for avatar (photo or placeholder)
    """
    initial = speaker_name[0].upper() if speaker_name else "?"
    opacity = "0.6" if is_past else "1.0"

    return f"""
    <div style="
        display: inline-block;
        position: relative;
        width: {size}px;
        height: {size}px;
        vertical-align: middle;
        margin-right: 12px;
    ">
        <!-- Fallback placeholder (renders first) -->
        <div style="
            width: {size}px;
            height: {size}px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: 2px solid #2d3748;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: {int(size * 0.5)}px;
            font-weight: 600;
            color: #ffffff;
            opacity: {opacity};
            position: absolute;
            top: 0;
            left: 0;
        ">
            {initial}
        </div>

        <!-- Actual photo (overlays placeholder if loads successfully) -->
        <img
            src="{photo_path}"
            alt="{speaker_name}"
            style="
                width: {size}px;
                height: {size}px;
                border-radius: 50%;
                object-fit: cover;
                border: 2px solid #2d3748;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
                opacity: {opacity};
                position: absolute;
                top: 0;
                left: 0;
                z-index: 1;
            "
            onerror="this.style.display='none';"
        />
    </div>
    """
```

**How It Works**:
1. Creates container div with fixed dimensions
2. Renders placeholder with speaker initial
3. Overlays actual photo on top (higher z-index)
4. If photo fails to load, `onerror` hides it, revealing placeholder

---

### 2b. Test the Helper Function (Optional but Recommended)

**Quick Test in Python REPL**:
```python
>>> from src.ui.dashboard import _render_speaker_avatar
>>> html = _render_speaker_avatar("images/speakers/test.jpg", "John Doe")
>>> print(html)
# Should output HTML with <div> and <img>
```

---

## Step 3: Update Session Card Rendering

### 3a. Modify `_render_session_card()`

**Location**: `src/ui/dashboard.py::_render_session_card()` (around line 18)

**Find This Section** (around line 69-71):
```python
<div style="color: #cbd5e1; font-size: 14px; margin-bottom: 12px;">
    👤 {session.speaker.name}
</div>
```

**Replace With**:
```python
# Generate speaker avatar HTML
avatar_html = _render_speaker_avatar(
    session.speaker.photo,
    session.speaker.name,
    size=50,
    is_past=is_past
)

# Update the markdown to include avatar
st.markdown(f"""
<div style="
    {container_style}
    padding: 20px;
    border-radius: 12px;
    border: 1px solid #2d3748;
    margin-bottom: 16px;
">
    <!-- ... existing date/time section ... -->

    <div style="color: #f1f5f9; font-size: 18px; font-weight: 600; margin-bottom: 8px;">
        {session.title}
    </div>

    <div style="color: #cbd5e1; font-size: 14px; margin-bottom: 12px; display: flex; align-items: center;">
        {avatar_html}
        <span>{session.speaker.name}</span>
    </div>

    <!-- ... rest of card ... -->
</div>
""", unsafe_allow_html=True)
```

**Key Changes**:
1. ✅ Call `_render_speaker_avatar()` before the card HTML
2. ✅ Change speaker div to `display: flex; align-items: center;`
3. ✅ Insert `{avatar_html}` before `{session.speaker.name}`
4. ✅ Remove emoji `👤` (replaced by photo/avatar)

---

### 3b. Complete Modified Function

**Full Updated `_render_session_card()`**:
```python
def _render_session_card(session: Session, is_past: bool = False):
    """
    渲染單一議程卡片。

    Args:
        session: 議程物件
        is_past: 是否為過去的議程
    """
    # 設定容器樣式
    if is_past:
        container_style = """
            background-color: #1a1a2e;
            opacity: 0.7;
            filter: grayscale(20%);
        """
    else:
        container_style = """
            background-color: #16213e;
        """

    # 狀態標籤
    status = session.status()
    status_labels = {
        "available": "🟢 可報名",
        "full": "🔴 已額滿",
        "expired": "⏰ 已過期"
    }
    status_label = status_labels.get(status, "")

    # 計算報名百分比
    registration_pct = session.registration_percentage()

    # 生成講師頭像 HTML
    avatar_html = _render_speaker_avatar(
        session.speaker.photo,
        session.speaker.name,
        size=50,
        is_past=is_past
    )

    # 使用 container 建立卡片
    with st.container():
        st.markdown(f"""
        <div style="
            {container_style}
            padding: 20px;
            border-radius: 12px;
            border: 1px solid #2d3748;
            margin-bottom: 16px;
        ">
            <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
                <span style="color: #94a3b8; font-size: 14px;">📅 {session.date} {session.time}</span>
                <span style="color: #94a3b8; font-size: 12px;">{_get_difficulty_badge(session.level)}</span>
            </div>

            <div style="color: #f1f5f9; font-size: 18px; font-weight: 600; margin-bottom: 8px;">
                {session.title}
            </div>

            <div style="color: #cbd5e1; font-size: 14px; margin-bottom: 12px; display: flex; align-items: center;">
                {avatar_html}
                <span>{session.speaker.name}</span>
            </div>

            <div style="margin-bottom: 8px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span style="color: #94a3b8; font-size: 13px;">{status_label}</span>
                    <span style="color: #94a3b8; font-size: 13px;">{session.registered}/{session.capacity} 人</span>
                </div>
                <div style="width: 100%; height: 6px; background: #334155; border-radius: 3px; overflow: hidden;">
                    <div style="width: {registration_pct}%; height: 100%; background: linear-gradient(90deg, #06b6d4, #8b5cf6);"></div>
                </div>
            </div>

            <div style="display: flex; flex-wrap: wrap; gap: 6px; margin-top: 12px;">
                {"".join([f'<span style="background: #334155; color: #94a3b8; padding: 3px 10px; border-radius: 10px; font-size: 12px;">#{tag}</span>' for tag in session.tags])}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 查看詳情按鈕
        if st.button(f"查看詳情 »", key=f"view_{session.id}", use_container_width=True):
            st.session_state.selected_session_id = session.id
            st.session_state.current_page = "detail"
            st.rerun()
```

---

## Step 4: Manual Testing

### 4a. Run the Dashboard

```bash
# From project root
streamlit run app.py
```

### 4b. Visual Verification Checklist

Open dashboard and check:

- [ ] **Past Sessions** (left column):
  - [ ] Circular speaker photos displayed (or initials if photo missing)
  - [ ] Photos have reduced opacity (grayed out effect)
  - [ ] Photos positioned left of speaker names
  - [ ] Consistent 50px size

- [ ] **Upcoming Sessions** (right column):
  - [ ] Circular speaker photos displayed
  - [ ] Photos at full opacity (bright)
  - [ ] Border and shadow visible
  - [ ] Name aligned vertically with photo

- [ ] **Edge Cases**:
  - [ ] Missing photo shows initial in gradient circle
  - [ ] No broken image icons
  - [ ] No console errors (check browser DevTools)

### 4c. Browser Console Check

**Open DevTools** (F12 or Cmd+Opt+I):
1. Go to **Console** tab
2. Look for errors related to images
3. Should see NO errors (404s are OK - handled by fallback)

---

## Step 5: Add Unit Tests

### 5a. Create Test File

**Location**: `tests/ui/test_dashboard.py`

**Add These Tests**:
```python
"""Tests for dashboard UI components."""
import pytest
from src.ui.dashboard import _render_speaker_avatar


class TestSpeakerAvatarRendering:
    """Tests for speaker avatar rendering with fallback."""

    def test_render_avatar_contains_img_tag(self):
        """Avatar HTML should contain img tag with photo path."""
        html = _render_speaker_avatar("images/speakers/test.jpg", "John Doe")

        assert '<img' in html
        assert 'images/speakers/test.jpg' in html
        assert 'alt="John Doe"' in html

    def test_render_avatar_contains_fallback_div(self):
        """Avatar HTML should contain fallback div with initial."""
        html = _render_speaker_avatar("images/test.jpg", "John Doe")

        assert '<div' in html
        assert 'J' in html  # Speaker initial

    def test_render_avatar_with_empty_name_uses_question_mark(self):
        """Empty speaker name should use '?' as initial."""
        html = _render_speaker_avatar("images/test.jpg", "")

        assert '?' in html

    def test_render_avatar_applies_reduced_opacity_for_past_sessions(self):
        """Past sessions should have opacity 0.6."""
        html = _render_speaker_avatar("images/test.jpg", "Jane", is_past=True)

        assert 'opacity: 0.6' in html

    def test_render_avatar_applies_full_opacity_for_upcoming_sessions(self):
        """Upcoming sessions should have opacity 1.0."""
        html = _render_speaker_avatar("images/test.jpg", "Jane", is_past=False)

        assert 'opacity: 1.0' in html

    def test_render_avatar_custom_size(self):
        """Avatar should respect custom size parameter."""
        html = _render_speaker_avatar("images/test.jpg", "John", size=100)

        assert 'width: 100px' in html
        assert 'height: 100px' in html

    def test_render_avatar_has_onerror_handler(self):
        """Image should have onerror handler for missing files."""
        html = _render_speaker_avatar("images/test.jpg", "John")

        assert 'onerror=' in html
        assert "this.style.display='none'" in html

    def test_render_avatar_circular_styling(self):
        """Avatar should have circular border-radius."""
        html = _render_speaker_avatar("images/test.jpg", "John")

        assert 'border-radius: 50%' in html

    def test_render_avatar_has_gradient_background(self):
        """Fallback should have gradient background."""
        html = _render_speaker_avatar("images/test.jpg", "John")

        assert 'linear-gradient' in html
        assert '#667eea' in html
        assert '#764ba2' in html
```

### 5b. Run Tests

```bash
# Run all tests
pytest tests/ui/test_dashboard.py

# Run with coverage
pytest tests/ui/test_dashboard.py --cov=src/ui/dashboard --cov-report=term-missing

# Expected output:
# ✅ 9 tests passed
# ✅ Coverage > 80%
```

---

## Step 6: Verify Constitution Compliance

### Checklist

- [x] **Minimal Comments**: Function docstrings only, no inline comments
- [x] **Mandatory Testing**: 9 unit tests added (>80% coverage)
- [x] **Error Handling**: `onerror` handles missing files gracefully
- [x] **Conventional Commits**: Ready for `feat(ui): add circular speaker photos in dashboard`
- [x] **Tech Stack**: Streamlit + Python only (no new dependencies)

---

## Step 7: Commit Your Changes

### 7a. Stage Changes

```bash
git add src/ui/dashboard.py
git add tests/ui/test_dashboard.py
```

### 7b. Commit with Conventional Format

```bash
git commit -m "feat(ui): add circular speaker photo display in dashboard

- Add _render_speaker_avatar() helper function
- Update _render_session_card() to display photos
- Implement automatic fallback to speaker initial
- Add 9 unit tests for avatar rendering
- Apply reduced opacity for past sessions

Closes #002"
```

---

## Troubleshooting

### Photos Not Displaying

**Symptom**: All speakers show initials instead of photos

**Diagnosis**:
```bash
# Check if image files exist
ls -la images/speakers/

# Verify photo paths in data
cat data/sessions.json | grep "photo"
```

**Fix**:
- Ensure `images/speakers/` directory exists
- Verify filenames match those in `data/sessions.json`
- Check file permissions (`chmod 644 images/speakers/*.jpg`)

---

### Broken Layout

**Symptom**: Photos overlap or misalign with names

**Diagnosis**:
- Open browser DevTools > Elements tab
- Inspect speaker div styling

**Fix**:
- Verify `display: flex; align-items: center;` on parent div
- Check `vertical-align: middle;` on avatar container
- Ensure `margin-right: 12px;` for spacing

---

### Tests Failing

**Symptom**: `pytest` shows failures

**Diagnosis**:
```bash
# Run tests with verbose output
pytest tests/ui/test_dashboard.py -v

# Check specific failing test
pytest tests/ui/test_dashboard.py::TestSpeakerAvatarRendering::test_name -v
```

**Fix**:
- Read assertion error carefully
- Verify function signature matches test expectations
- Check for typos in HTML generation

---

## Performance Optimization (Optional)

### If Dashboard Loads Slowly (>2 seconds)

**Add Pagination**:
```python
# In render_dashboard()
def render_dashboard():
    # ... existing code ...

    # Limit sessions per page
    page_size = 10
    past_sessions = get_past_sessions(limit=page_size)
    upcoming_sessions = get_upcoming_sessions(limit=page_size)

    # ... rest of function ...
```

**Optimize Images**:
```bash
# Install image optimization tool
brew install imagemagick  # macOS
# or
sudo apt install imagemagick  # Linux

# Resize and optimize all speaker photos
cd images/speakers/
for img in *.jpg; do
    convert "$img" -resize 100x100^ -gravity center -extent 100x100 -quality 85 "optimized_$img"
done
```

---

## Next Steps

### After Implementation Complete

1. ✅ Manual testing passed
2. ✅ All unit tests passing
3. ✅ Git commit created
4. ✅ Constitution compliance verified

**Ready for**:
- Code review (create PR if working with team)
- Merge to main branch
- Deploy to production

### Optional Enhancements (Future)

- Add photo hover effect (zoom or border highlight)
- Implement lazy loading for large session lists
- Add photo upload feature in admin panel
- Generate speaker initials dynamically from full name

---

## Reference Files

**Implementation**:
- `src/ui/dashboard.py` - Main implementation
- `src/models/speaker.py` - Data model
- `data/sessions.json` - Data source

**Documentation**:
- `specs/002-speaker-image-rendering/spec.md` - Feature specification
- `specs/002-speaker-image-rendering/plan.md` - Technical plan
- `specs/002-speaker-image-rendering/research.md` - Research findings

**Testing**:
- `tests/ui/test_dashboard.py` - Unit tests
- `tests/fixtures/images/` - Test image files

---

## Questions or Issues?

**Common Questions**:

**Q: Can I use PNG instead of JPG for photos?**
A: Yes! `object-fit: cover` works with JPG, PNG, and WEBP.

**Q: What if speaker has multi-word name?**
A: Initial uses first character: "John Doe" → "J"

**Q: How to change avatar size?**
A: Pass `size` parameter: `_render_speaker_avatar(path, name, size=60)`

**Q: Can I customize the gradient colors?**
A: Yes! Edit the `linear-gradient(135deg, #667eea 0%, #764ba2 100%)` values in `_render_speaker_avatar()`.

---

**Happy Coding!** 🎉

You've successfully implemented circular speaker photos in the dashboard. This feature improves visual hierarchy and helps attendees quickly identify speakers.
