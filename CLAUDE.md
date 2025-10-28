# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 必須遵守要點
- 回覆問題一律用中文回覆我
- 寫法需遵遁、參照其他程式的寫法，例如 excel 產生方式、provider 獲取方式、log 方式
- 程式碼中不要使用中文註解，如需註解必須使用英文
- 程式用英文撰寫，但回覆給我的總結或說明用繁體中文
- 修改程式時，應以最小範圍的變更達成目的
- 禁止引用專案未使用的第三方套件
- 撰寫完成後務必進行測試，測試結束後請刪除測試程式碼
- Python 程式碼必須遵循 PEP 8: Style Guide for Python Code

## Project Overview

This is a **Conference Registration System** (議程管理系統) built with Streamlit - a modern conference session management platform with Chinese UI. The application manages conference sessions, speaker information, and attendee registrations using a JSON-based data storage system.

## Development Commands

### Running the Application
```bash
# Activate virtual environment and start
./start.sh

# Or manually
source venv/bin/activate
streamlit run app.py
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=term-missing

# Run specific test types
pytest tests/unit/              # Unit tests
pytest tests/integration/       # Integration tests
pytest -m slow                  # Slow tests
```

### Environment Setup
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt
```

## Architecture

### Three-Layer Architecture
- **UI Layer** (`src/ui/`): Streamlit components for dashboard and session details
- **Service Layer** (`src/services/`): Business logic with caching and file locking
- **Model Layer** (`src/models/`): Data models with validation using dataclasses

### Key Components

**Models**:
- `Session`: Core business entity with status validation and datetime logic
- `Speaker`: Speaker information with photo handling

**Services**:
- `session_service.py`: Session CRUD operations with in-memory caching
- `storage_service.py`: JSON file operations with atomic writes and backup

**UI Components**:
- `dashboard.py`: Two-column layout showing past/upcoming sessions with circular speaker photos
- `session_detail.py`: Individual session view with registration functionality

### Data Flow
1. JSON files in `data/` directory serve as the database
2. Services layer provides caching and thread-safe operations using file locking
3. UI components consume services and manage Streamlit session state
4. Speaker photos have graceful fallback to gradient placeholders with initials

### State Management
Application uses Streamlit's session state for:
- `current_page`: Navigation between "dashboard" and "detail"
- `selected_session_id`: Currently viewed session
- Page transitions trigger `st.rerun()`

## Data Structure

### Session Data (`data/sessions.json`)
```json
{
  "sessions": [
    {
      "id": "session_001",
      "title": "議程標題", 
      "description": "議程描述",
      "date": "2025-11-15",
      "time": "14:00-16:00",
      "location": "線上 Zoom 會議室",
      "level": "中",                    // "初", "中", "高"
      "tags": ["Python", "AI"],
      "learning_outcomes": "學習成果",
      "capacity": 100,
      "registered": 67,
      "speaker": {
        "name": "講者姓名",
        "photo": "images/speakers/speaker-name.jpg",
        "bio": "講者簡介"
      }
    }
  ]
}
```

### Speaker Photos
- **Location**: `images/speakers/` directory
- **Formats**: JPG, PNG, WEBP
- **Size**: < 10KB recommended
- **Fallback**: Automatic gradient placeholders with speaker initials
- **Rendering**: Circular 50px avatars with proper opacity for past sessions

## Core Business Rules

### Session Status Logic
- **Available**: Future date and not full capacity
- **Full**: At capacity regardless of date
- **Expired**: Past date regardless of capacity

### Registration Process
1. Validate session exists and is available
2. Use file locking to prevent race conditions
3. Atomic JSON update with backup creation
4. Clear service cache to reflect changes
5. Return success/failure with user message

### Caching Strategy
- Services maintain in-memory cache of all sessions
- Cache invalidated on any write operation
- Thread-safe file operations using `lock_file()` context manager

## UI Design System

### Theme
- **Background**: Dark gradient (#0f0c29 → #1a1a2e → #16213e)
- **Accent**: Purple gradient (#667eea → #764ba2)
- **Cards**: Semi-transparent with rounded corners
- **Past sessions**: Grayscale filter with reduced opacity

### Component Patterns
- **Session Cards**: Standardized layout with speaker avatar, progress bar, status badge
- **Difficulty Badges**: Color-coded (🔵初級, 🟣中級, 🔴高級)
- **Navigation**: Simple home/admin buttons with session state management

## Testing Strategy

- **139 automated tests** covering all layers
- **Unit tests**: Models, utilities, individual service functions
- **Integration tests**: End-to-end workflows, file operations
- **UI tests**: Streamlit component rendering and interactions
- **Coverage**: Comprehensive coverage with pytest-cov

## File Operations

All data modifications use atomic operations:
1. Create backup of original file
2. Acquire file lock
3. Load, modify, validate data
4. Write to temporary file
5. Atomic rename to replace original
6. Release lock

This ensures data integrity even with concurrent access.

## Active Technologies
- Python 3.9.6 + Streamlit 1.28.0, Pillow 10.1.0 (002-speaker-image-rendering)
- Local file system (speaker photos in `images/` directory) (002-speaker-image-rendering)

## Recent Changes
- 002-speaker-image-rendering: Added Python 3.9.6 + Streamlit 1.28.0, Pillow 10.1.0
