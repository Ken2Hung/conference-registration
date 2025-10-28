# Feature Specification: Speaker Image Rendering in Dashboard

**Feature ID**: 002-speaker-image-rendering
**Created**: 2025-10-28
**Status**: Draft
**Priority**: Medium

---

## Summary

Enable the conference session dashboard to display speaker information with properly rendered circular profile images, replacing the current text-only display. This enhancement improves visual appeal and provides immediate speaker recognition for conference attendees browsing sessions.

---

## Background & Context

The current dashboard displays session information including speaker names as text (`👤 {speaker.name}`), but does not display speaker profile photos despite the `Speaker` model containing a `photo` field with the image path. The screenshot shows the desired end-state where speaker photos are displayed as circular thumbnails next to speaker names in the session cards.

This feature addresses the gap between available data (speaker photos in the data model) and the current UI presentation, improving the visual hierarchy and making the dashboard more engaging.

---

## User Scenarios & Testing

### Primary User Flow

1. User opens the conference session dashboard
2. Dashboard loads and displays session cards in two columns (past and upcoming sessions)
3. Each session card shows:
   - Session metadata (date, time, difficulty level)
   - Session title
   - **Speaker photo as a circular thumbnail** (new)
   - Speaker name
   - Registration status and progress bar
   - Topic tags
4. User can visually identify speakers by their photos while browsing sessions
5. Photos render consistently across all session cards with proper styling

### Edge Cases

- **Missing photo file**: If speaker photo file doesn't exist at the specified path, display a placeholder avatar icon instead of breaking the UI
- **Invalid photo path**: Handle empty or malformed photo paths gracefully with fallback placeholder
- **Large photo files**: Ensure photos are displayed efficiently without impacting page load performance
- **Different image formats**: Support common formats (JPG, PNG, WEBP) used in speaker photos

### Acceptance Scenarios

**Scenario 1: Display speaker photo in session card**
- GIVEN a session with a valid speaker photo path
- WHEN the dashboard renders the session card
- THEN the speaker photo appears as a circular thumbnail next to the speaker name
- AND the photo has consistent size and styling across all cards

**Scenario 2: Handle missing photo gracefully**
- GIVEN a session where the speaker photo file is missing
- WHEN the dashboard renders the session card
- THEN a placeholder avatar icon is displayed instead of the photo
- AND no error is shown to the user
- AND the card layout remains intact

**Scenario 3: Maintain responsive layout**
- GIVEN multiple session cards displayed in the dashboard
- WHEN the browser window is resized
- THEN speaker photos maintain their circular shape and size
- AND the overall card layout remains responsive

---

## Functional Requirements

### Core Requirements

1. **Photo Display**
   - Display speaker photos as circular thumbnails in session cards
   - Photo size: approximately 48-60 pixels in diameter for optimal balance
   - Photos must maintain circular shape with proper cropping
   - Photos positioned to the left of the speaker name

2. **Photo Styling**
   - Circular border with subtle shadow for depth
   - Consistent styling matching the dashboard's dark theme
   - Border color matching the card design system (#2d3748 or similar)
   - Smooth edges with appropriate border-radius

3. **Fallback Handling**
   - Display placeholder avatar icon when photo is unavailable
   - Placeholder uses same dimensions as photo display
   - Placeholder styling consistent with overall design
   - No error messages shown to users for missing photos

4. **Layout Integration**
   - Photo and name displayed on the same line
   - Proper spacing between photo and speaker name (8-12 pixels)
   - Layout works for both "past sessions" (grayed out) and "upcoming sessions"
   - Photo visibility maintained in both states (past sessions may have reduced opacity)

5. **Performance**
   - Photos load without blocking card rendering
   - Efficient image handling for multiple cards (10+ sessions)
   - No visible layout shift as images load

### Data Requirements

- Use existing `Speaker.photo` field which contains the file path to speaker image
- Support relative paths from project root (e.g., `images/speakers/john-doe.jpg`)
- Support common image formats: JPG, PNG, WEBP

---

## Success Criteria

1. **Visual Quality**: All session cards display speaker photos as circular thumbnails with consistent styling, matching the design shown in the reference screenshot
2. **User Experience**: Dashboard loads within 2 seconds with all photos rendered, providing immediate visual identification of speakers
3. **Reliability**: System handles missing or invalid photo paths without errors, displaying placeholder icons in 100% of edge cases
4. **Visual Consistency**: Photo size, shape, and styling are identical across all session cards (both past and upcoming)
5. **Responsive Design**: Photos maintain proper proportions and layout when viewed on different screen sizes (desktop, tablet, mobile)

---

## Key Entities

### Modified Components

**Session Card Display** (in `src/ui/dashboard.py::_render_session_card`)
- Current: Displays speaker name with emoji icon (`👤 {speaker.name}`)
- Updated: Displays circular speaker photo thumbnail + speaker name

**Speaker Data** (in `src/models/speaker.py::Speaker`)
- Already contains: `photo` field with image path
- Usage: Photo path will be used to load and display speaker image

---

## Scope & Boundaries

### In Scope

- Rendering speaker photos in dashboard session cards
- Circular image styling and layout
- Fallback placeholder for missing photos
- Support for common image formats
- Responsive photo display

### Out of Scope

- Photo upload or management features
- Photo editing or cropping tools
- Speaker profile photo updates
- Photo optimization or compression
- Session detail page photo display (separate from dashboard)
- Admin panel for managing speaker photos

---

## Assumptions & Dependencies

### Assumptions

1. Speaker photo files are stored in the `images/` directory with paths stored in `Speaker.photo`
2. Photo files are reasonably sized (< 1MB each) and optimized for web display
3. All speaker records have a photo path defined (may point to missing file)
4. The current dark theme design system should be maintained
5. Streamlit's `st.image()` component or HTML `<img>` tags via `st.markdown()` can be used for display

### Dependencies

- Existing `Speaker` model with `photo` field
- Existing `Session` model with `speaker` relationship
- Streamlit framework for rendering
- Image files in the project directory
- PIL/Pillow library (already in requirements) for potential image handling

---

## Open Questions

None - all requirements are sufficiently specified for implementation.

---

## Notes

- The reference screenshot shows a polished design with circular speaker photos, which should serve as the visual target
- The current implementation already loads speaker data, so this is primarily a UI enhancement
- Consider using Streamlit's `st.image()` with custom CSS styling, or HTML/CSS via `st.markdown()` for precise control
- The grayed-out effect for past sessions should also apply to speaker photos (reduced opacity)
