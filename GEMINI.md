# GEMINI.md


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

This project is a modern conference registration system built with Python and Streamlit. It provides a web-based interface for managing and viewing conference sessions. The application features a dark-themed UI, session browsing, speaker information with photo display, and real-time registration management.

The backend is written in Python, and the frontend is rendered using Streamlit. The data is stored in JSON files located in the `data` directory. The project is well-structured with separate directories for models, services, UI components, and tests.

## Building and Running

### Prerequisites

*   Python 3.8+
*   pip

### Installation

1.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

### Running the Application

To run the application, use the following command:

```bash
streamlit run app.py --logger.level=debug
```

The application will be available at `http://localhost:8501`.

### Testing

The project uses `pytest` for testing. To run the tests, use the following command:

```bash
pytest
```

You can also run specific tests or check for test coverage:

```bash
# Run tests in a specific file
pytest tests/unit/test_session_service.py

# Run tests with coverage report
pytest --cov=src --cov-report=term-missing
```

## Development Conventions

### Code Style

The project follows the PEP 8 style guide for Python code. It emphasizes clean, readable code with minimal comments, preferring self-documenting code.

### Testing

All new features and bug fixes should be accompanied by unit tests. The project uses `pytest` for testing and `pytest-cov` for measuring test coverage.

### Data Management

The conference data is stored in `data/sessions.json`. The admin credentials are in `data/config.json`. The `src/services/storage_service.py` module provides functions for reading and writing JSON data, including file locking to prevent race conditions.

### UI Components

The UI is built with Streamlit and is organized into components in the `src/ui` directory. The application uses a lot of custom CSS to achieve its modern look and feel. The main UI components are:

*   `dashboard.py`: Renders the main dashboard with session cards.
*   `session_detail.py`: Renders the detailed view of a session.
*   `admin_panel.py`: Provides an interface for managing sessions.

### Real-time Transcription

The project includes a real-time transcription feature, which uses `streamlit-webrtc` and `openai` to transcribe audio from the microphone in real-time. This feature can be accessed from the "Transcription" page.
