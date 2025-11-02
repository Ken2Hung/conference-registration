# Feature Specification: Registration Enhancement with Admin Management

**Feature Branch**: `001-registration-enhancement`
**Created**: 2025-10-28
**Status**: Draft
**Input**: User description: "## bug fix
1. 修正 @dashboard.py中,課程卡片下的button的連結,改至課程卡片本身,點選卡片本身即可進入到 @session_detail.py中
2. @session_detail.py中按下報名會直接累加到額滿,但只需要加1個數量才對

## requirement
1. 報名時要填入姓名、若是已報名者中姓名已有重覆,則pop訊息您已報名,不讓報名。 若是姓名沒重覆,則可報名名額-1。課程報名同時也記錄在 project中的json檔,該json list包含著多個session json object, 同時把報名者的資訊記錄下來。
2. @session_detail.py 要可以顯示已報名的人有誰。
3. @dashboard.py右上角的管理者權限,點選輸入帳號/密碼後,可以進行「新增課程資訊」「編輯課程資訊」"

## Clarifications

### Session 2025-10-28

- Q: How should registrant names be displayed for privacy? → A: Display full names of all registered attendees (complete transparency for community networking)
- Q: How should duplicate name checking handle case sensitivity and whitespace? → A: Normalize before comparison: trim leading/trailing whitespace, case-insensitive (for any Latin characters), preserve internal spacing
- Q: How should concurrent registrations be handled when only 1 slot remains? → A: First-come-first-served: first request succeeds, subsequent requests see "已額滿" message (clear and immediate feedback)
- Q: How long should admin session persist before timeout? → A: Browser session lifetime (remains valid until browser closes or explicit logout)
- Q: Can admin delete sessions with existing registrations? → A: Yes, with confirmation warning showing registrant count and requiring explicit confirmation before deletion

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Named Registration with Duplicate Prevention (Priority: P1)

A conference attendee wants to register for a session by providing their name, ensuring that duplicate registrations are prevented and only legitimate attendees are recorded.

**Why this priority**: This is the core functionality that fixes the current broken registration system. Without name tracking and duplicate prevention, the system allows unlimited registrations and has no record of who registered.

**Independent Test**: Can be fully tested by attempting to register for a session with a name, verifying duplicate prevention when using the same name, and checking that registration count increases by exactly 1 per successful registration.

**Acceptance Scenarios**:

1. **Given** a session with available capacity and user "張三" has not registered, **When** user enters name "張三" and submits registration, **Then** system records registration, decreases available capacity by 1, shows success message, and adds "張三" to the registrants list
2. **Given** user "張三" has already registered for a session, **When** user "張三" attempts to register again (or with variations like " 張三 " with extra spaces), **Then** system displays "您已報名" message and does not change registration count
3. **Given** a session with 1 remaining slot and user "李四" registers, **When** registration completes, **Then** session status changes to "已額滿" and registration button becomes disabled
4. **Given** a session is at capacity, **When** any user attempts to register, **Then** system prevents registration and displays appropriate message
5. **Given** user submits registration with empty name, **When** form is submitted, **Then** system displays validation error and does not process registration

---

### User Story 2 - View Registered Attendees (Priority: P2)

A conference attendee wants to see who else has registered for a session to understand the community and network with other participants.

**Why this priority**: This provides transparency and builds community engagement. It's valuable but the system can function without it, making it secondary to core registration functionality.

**Independent Test**: Can be tested independently by registering multiple users for a session and verifying that all names appear in the attendees list on the session detail page.

**Acceptance Scenarios**:

1. **Given** a session has 3 registered attendees ("張三", "李四", "王五"), **When** user views session detail page, **Then** system displays all 3 names in the registered attendees section
2. **Given** a session has no registered attendees, **When** user views session detail page, **Then** system displays "目前尚無報名者" or similar empty state message
3. **Given** a session has over 20 registered attendees, **When** user views attendees list, **Then** system displays names in a scrollable or paginated format for readability
4. **Given** user just completed registration, **When** page refreshes, **Then** their name immediately appears in the attendees list

---

### User Story 3 - Fix Session Card Navigation (Priority: P2)

A dashboard user wants to click anywhere on a session card to view session details, providing a more intuitive and user-friendly navigation experience.

**Why this priority**: This is a UX improvement that fixes broken navigation. While important for user experience, the system currently has a working button-based navigation, making this a quality-of-life enhancement rather than critical functionality.

**Independent Test**: Can be tested by clicking on different parts of a session card (title, speaker area, tags, card background) and verifying that all clicks navigate to the session detail page.

**Acceptance Scenarios**:

1. **Given** user is on dashboard viewing session cards, **When** user clicks on any part of the session card (title, description, speaker, tags, or background), **Then** system navigates to session detail page for that session
2. **Given** user is hovering over a session card, **When** cursor moves over the card, **Then** visual feedback (cursor change, hover effect) indicates the entire card is clickable
3. **Given** user clicks a session card, **When** navigation occurs, **Then** session detail page displays correct session information matching the clicked card
4. **Given** multiple session cards displayed, **When** user clicks different cards, **Then** each card navigates to its corresponding session detail independently

---

### User Story 4 - Admin Session Management (Priority: P3)

An administrator wants to log in with credentials and manage session content by creating new sessions and editing existing ones, maintaining up-to-date conference information.

**Why this priority**: This enables content management but isn't critical for the initial attendee-facing functionality. The system can operate with manually edited JSON files until admin features are implemented.

**Independent Test**: Can be tested by logging in with admin credentials, creating a new session, editing an existing session, and verifying changes persist and display correctly on the dashboard.

**Acceptance Scenarios**:

1. **Given** user clicks admin button in dashboard header, **When** user enters correct admin username and password, **Then** system grants access to admin panel
2. **Given** user enters incorrect admin credentials, **When** login is attempted, **Then** system displays error message "帳號或密碼錯誤" and denies access
3. **Given** admin is logged in, **When** admin selects "新增課程", **Then** system displays form with all required session fields (title, description, date, time, location, level, tags, capacity, speaker info)
4. **Given** admin fills out new session form with valid data, **When** admin submits form, **Then** system creates new session, saves to JSON storage, and displays on dashboard
5. **Given** admin selects "編輯課程" for an existing session, **When** admin modifies session data and saves, **Then** system updates session data in storage and reflects changes on dashboard and detail pages
6. **Given** admin creates session with invalid data (missing required fields, past date, negative capacity), **When** form is submitted, **Then** system displays validation errors and prevents creation
7. **Given** admin is editing a session with existing registrations, **When** admin attempts to reduce capacity below current registration count, **Then** system displays warning and prevents invalid capacity change
8. **Given** admin selects "刪除課程" for a session with registrants, **When** delete is initiated, **Then** system displays confirmation dialog showing registrant count and requires explicit confirmation
9. **Given** admin confirms deletion of a session, **When** confirmation is submitted, **Then** system permanently deletes session from storage and removes it from dashboard

---

### Edge Cases

- What happens when a user has multiple browser tabs open and attempts to register simultaneously in both tabs?
- What happens when an admin edits a session's date to a past date while users are viewing/registering?
- How does the system behave if JSON file becomes corrupted or unreadable during a registration operation?
- What happens if a user enters extremely long names (100+ characters) or special characters in the name field?
- How does the system handle sessions where the registered count somehow exceeds capacity due to data corruption?

## Requirements *(mandatory)*

### Functional Requirements

#### Registration System

- **FR-001**: System MUST require attendees to provide a name (minimum 1 character, maximum 50 characters) when registering for a session
- **FR-002**: System MUST validate that the provided name is not already in the session's registrants list before allowing registration (duplicate check uses normalized comparison: trim leading/trailing whitespace, case-insensitive for Latin characters, preserve internal spacing)
- **FR-003**: System MUST display "您已報名" message when a duplicate name is detected and prevent the registration
- **FR-004**: System MUST increase the session's registered count by exactly 1 when a new registration succeeds
- **FR-005**: System MUST store registrant information (at minimum: name, registration timestamp) in the session data structure within the JSON file
- **FR-006**: System MUST use file locking mechanism during registration operations to prevent race conditions (first-come-first-served: first successful request acquires slot, concurrent losers receive "已額滿" message)
- **FR-007**: System MUST validate that session capacity has not been reached before accepting a registration
- **FR-008**: System MUST display success message and visual confirmation (e.g., balloons animation) upon successful registration

#### Registrants Display

- **FR-009**: Session detail page MUST display a list of all registered attendees' full names (complete transparency for community networking and engagement)
- **FR-010**: System MUST show an appropriate empty state message when no attendees have registered
- **FR-011**: System MUST display registrants list in chronological order (first registered appears first)
- **FR-012**: System MUST update registrants display immediately after a new registration completes

#### Navigation Fix

- **FR-013**: Dashboard session cards MUST be fully clickable (entire card surface triggers navigation)
- **FR-014**: Clicking any part of a session card MUST navigate to that session's detail page
- **FR-015**: Session cards MUST display visual feedback on hover to indicate clickability
- **FR-016**: Navigation MUST correctly pass session ID to the detail page

#### Admin Authentication

- **FR-017**: Dashboard MUST display an admin access button in the header area (top right corner)
- **FR-018**: System MUST present a login dialog when admin button is clicked, requesting username and password
- **FR-019**: System MUST validate admin credentials against stored credentials (username and password stored in environment variables or configuration file)
- **FR-020**: System MUST display error message "帳號或密碼錯誤" for invalid credentials
- **FR-021**: System MUST grant access to admin panel only after successful authentication
- **FR-022**: Admin session MUST persist for the entire browser session lifetime until explicit logout or browser closes (no inactivity timeout)

#### Admin Session Management

- **FR-023**: Admin panel MUST provide "新增課程" functionality to create new sessions
- **FR-024**: Admin panel MUST provide "編輯課程" functionality to modify existing sessions
- **FR-025**: Admin panel MUST provide "刪除課程" functionality to delete sessions with confirmation warning (show registrant count if any, require explicit confirmation before deletion)
- **FR-026**: New session form MUST collect all required fields: id, title, description, date, time, location, level, tags, learning_outcomes, capacity, speaker (name, photo, bio)
- **FR-027**: System MUST validate all required fields before creating or updating a session
- **FR-028**: System MUST validate that date is in YYYY-MM-DD format and is not in the past (for new sessions)
- **FR-029**: System MUST validate that capacity is a positive integer
- **FR-030**: System MUST validate that level is one of: "初", "中", "高"
- **FR-031**: System MUST generate unique session ID automatically when creating new sessions
- **FR-032**: System MUST prevent admin from setting capacity below current registration count when editing
- **FR-033**: System MUST persist session changes to JSON storage using atomic write operations
- **FR-034**: System MUST clear service cache after creating, editing, or deleting sessions to reflect changes immediately

### Key Entities *(include if feature involves data)*

- **Registrant**: Represents an individual who has registered for a session
  - Name: The attendee's name (string, 1-50 characters)
  - Registration timestamp: When the registration occurred (ISO 8601 format)
  - Relationship: Belongs to exactly one Session

- **Session (enhanced)**: Existing session entity with added registrants tracking
  - Registrants: List of Registrant objects associated with this session
  - Registered count: Derived from length of registrants list (maintains consistency)
  - All existing fields remain unchanged

- **Admin Credentials**: Authentication information for administrative access
  - Username: Admin account identifier
  - Password: Admin account password (stored securely, hashed)
  - Storage: Environment variables or secure configuration file, not in JSON data files

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Attendees can successfully register for a session by providing their name in under 30 seconds from viewing session details
- **SC-002**: Duplicate registration attempts are prevented 100% of the time, with clear feedback to users
- **SC-003**: Registration count increases by exactly 1 per successful registration with zero instances of count corruption
- **SC-004**: Concurrent registration attempts (multiple users registering simultaneously) are handled safely with no data loss or race conditions
- **SC-005**: Users can click anywhere on a session card to navigate, improving navigation success rate to 100% (currently some clicks may miss the button)
- **SC-006**: Attendees can view the complete list of registered participants within 2 seconds of loading session detail page
- **SC-007**: Administrators can create a new session in under 3 minutes from clicking admin button to session appearing on dashboard
- **SC-008**: Administrators can edit an existing session and see changes reflected on dashboard within 5 seconds
- **SC-009**: System handles at least 10 concurrent registration requests for the same session without data corruption
- **SC-010**: Admin authentication prevents unauthorized access with 100% accuracy (no false positives or false negatives)
