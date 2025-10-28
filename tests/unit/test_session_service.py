"""Unit tests for SessionService."""
import pytest
import json
import os
import tempfile
from src.services.session_service import (
    get_all_sessions,
    get_past_sessions,
    get_upcoming_sessions,
    get_session_by_id,
    register_for_session,
    create_session,
    update_session,
    delete_session,
)
from src.models.session import Session
from src.utils.exceptions import SessionNotFoundError


@pytest.fixture
def temp_sessions_file():
    """Create a temporary sessions.json file for testing."""
    test_data = {
        "sessions": [
            {
                "id": "session_001",
                "title": "過去的議程",
                "description": "這是一個已經過期的議程",
                "date": "2020-01-15",
                "time": "14:00-16:00",
                "location": "線上",
                "level": "初",
                "tags": ["Python"],
                "learning_outcomes": "學習 Python 基礎",
                "capacity": 50,
                "registered": 30,
                "speaker": {
                    "name": "張三",
                    "photo": "images/speakers/zhang-san.jpg",
                    "bio": "資深工程師"
                }
            },
            {
                "id": "session_002",
                "title": "即將到來的議程",
                "description": "這是一個未來的議程",
                "date": "2030-12-01",
                "time": "14:00-16:00",
                "location": "台北",
                "level": "中",
                "tags": ["React"],
                "learning_outcomes": "學習 React 進階技巧",
                "capacity": 100,
                "registered": 50,
                "speaker": {
                    "name": "李四",
                    "photo": "images/speakers/li-si.jpg",
                    "bio": "前端專家"
                }
            },
            {
                "id": "session_003",
                "title": "另一個未來議程",
                "description": "測試用議程",
                "date": "2030-12-15",
                "time": "10:00-12:00",
                "location": "台中",
                "level": "高",
                "tags": ["Docker"],
                "learning_outcomes": "掌握 Docker 容器化",
                "capacity": 80,
                "registered": 80,
                "speaker": {
                    "name": "王五",
                    "photo": "images/speakers/wang-wu.jpg",
                    "bio": "DevOps 工程師"
                }
            }
        ]
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(test_data, f, ensure_ascii=False)
        temp_path = f.name

    yield temp_path

    if os.path.exists(temp_path):
        os.remove(temp_path)


class TestGetAllSessions:
    """Test get_all_sessions function."""

    def test_load_all_sessions(self, temp_sessions_file, monkeypatch):
        """Test loading all sessions from JSON file."""
        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', temp_sessions_file)

        sessions = get_all_sessions()

        assert len(sessions) == 3
        assert all(isinstance(s, Session) for s in sessions)
        assert sessions[0].id == "session_001"
        assert sessions[1].id == "session_002"
        assert sessions[2].id == "session_003"

    def test_parse_session_objects(self, temp_sessions_file, monkeypatch):
        """Test that sessions are parsed into Session dataclass objects."""
        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', temp_sessions_file)

        sessions = get_all_sessions()

        assert sessions[0].title == "過去的議程"
        assert sessions[0].capacity == 50
        assert sessions[0].registered == 30
        assert sessions[0].speaker.name == "張三"

    def test_cache_sessions(self, temp_sessions_file, monkeypatch):
        """Test that sessions are cached to avoid re-reading file."""
        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', temp_sessions_file)

        # First call
        sessions1 = get_all_sessions()
        # Second call should use cache
        sessions2 = get_all_sessions()

        assert sessions1 == sessions2
        assert len(sessions1) == 3


class TestGetPastSessions:
    """Test get_past_sessions function."""

    def test_filter_past_sessions(self, temp_sessions_file, monkeypatch):
        """Test filtering sessions that have already occurred."""
        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', temp_sessions_file)

        past_sessions = get_past_sessions()

        assert len(past_sessions) == 1
        assert past_sessions[0].id == "session_001"
        assert past_sessions[0].is_past()

    def test_sort_descending(self, temp_sessions_file, monkeypatch):
        """Test that past sessions are sorted by date descending (newest first)."""
        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', temp_sessions_file)

        past_sessions = get_past_sessions()

        # Should be sorted by date descending
        if len(past_sessions) > 1:
            for i in range(len(past_sessions) - 1):
                assert past_sessions[i].date >= past_sessions[i + 1].date

    def test_limit_results(self, temp_sessions_file, monkeypatch):
        """Test limiting number of past sessions returned."""
        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', temp_sessions_file)

        past_sessions = get_past_sessions(limit=1)

        assert len(past_sessions) <= 1


class TestGetUpcomingSessions:
    """Test get_upcoming_sessions function."""

    def test_filter_upcoming_sessions(self, temp_sessions_file, monkeypatch):
        """Test filtering sessions that are in the future."""
        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', temp_sessions_file)

        upcoming_sessions = get_upcoming_sessions()

        assert len(upcoming_sessions) == 2
        assert all(s.is_upcoming() for s in upcoming_sessions)

    def test_sort_ascending(self, temp_sessions_file, monkeypatch):
        """Test that upcoming sessions are sorted by date ascending (earliest first)."""
        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', temp_sessions_file)

        upcoming_sessions = get_upcoming_sessions()

        # Should be sorted by date ascending
        for i in range(len(upcoming_sessions) - 1):
            assert upcoming_sessions[i].date <= upcoming_sessions[i + 1].date

    def test_limit_results(self, temp_sessions_file, monkeypatch):
        """Test limiting number of upcoming sessions returned."""
        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', temp_sessions_file)

        upcoming_sessions = get_upcoming_sessions(limit=1)

        assert len(upcoming_sessions) <= 1


class TestGetSessionById:
    """Test get_session_by_id function."""

    def test_find_existing_session(self, temp_sessions_file, monkeypatch):
        """Test finding a session by ID."""
        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', temp_sessions_file)

        session = get_session_by_id("session_002")

        assert session is not None
        assert session.id == "session_002"
        assert session.title == "即將到來的議程"

    def test_return_none_for_missing_session(self, temp_sessions_file, monkeypatch):
        """Test that None is returned for non-existent session ID."""
        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', temp_sessions_file)

        session = get_session_by_id("session_999")

        assert session is None

    def test_invalid_id_format(self, temp_sessions_file, monkeypatch):
        """Test handling of invalid ID format."""
        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', temp_sessions_file)

        session = get_session_by_id("invalid_id")

        assert session is None


class TestRegisterForSession:
    """Test register_for_session function."""

    def test_successful_registration(self, temp_sessions_file, monkeypatch):
        """Test successful registration increments count."""
        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', temp_sessions_file)

        initial_session = get_session_by_id("session_002")
        initial_count = initial_session.registered

        success, message = register_for_session("session_002")

        assert success is True
        assert "成功" in message

        updated_session = get_session_by_id("session_002")
        assert updated_session.registered == initial_count + 1

    def test_registration_when_full(self, temp_sessions_file, monkeypatch):
        """Test registration fails when session is at capacity."""
        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', temp_sessions_file)

        success, message = register_for_session("session_003")

        assert success is False
        assert "已額滿" in message or "額滿" in message

    def test_registration_for_expired_session(self, temp_sessions_file, monkeypatch):
        """Test registration fails for past sessions."""
        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', temp_sessions_file)

        success, message = register_for_session("session_001")

        assert success is False
        assert "已過期" in message or "過期" in message

    def test_registration_nonexistent_session(self, temp_sessions_file, monkeypatch):
        """Test registration fails for non-existent session."""
        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', temp_sessions_file)

        with pytest.raises(SessionNotFoundError):
            register_for_session("session_999")

    def test_file_locking_during_registration(self, temp_sessions_file, monkeypatch):
        """Test that file locking is used during registration."""
        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', temp_sessions_file)

        # This test verifies the registration process doesn't crash
        # Actual file locking behavior is tested in storage_service tests
        success, message = register_for_session("session_002")

        assert success is True


class TestCreateSession:
    """Test create_session function."""

    def test_create_new_session(self, temp_sessions_file, monkeypatch):
        """Test creating a new session."""
        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', temp_sessions_file)

        new_session_data = {
            "title": "新議程",
            "description": "測試建立議程",
            "date": "2030-12-20",
            "time": "14:00-16:00",
            "location": "高雄",
            "level": "初",
            "tags": ["測試"],
            "learning_outcomes": "學習測試",
            "capacity": 50,
            "speaker": {
                "name": "測試講師",
                "photo": "images/speakers/test.jpg",
                "bio": "測試簡介"
            }
        }

        new_id = create_session(new_session_data)

        assert new_id.startswith("session_")

        created_session = get_session_by_id(new_id)
        assert created_session is not None
        assert created_session.title == "新議程"
        assert created_session.registered == 0

    def test_auto_increment_id(self, temp_sessions_file, monkeypatch):
        """Test that session ID is auto-incremented."""
        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', temp_sessions_file)

        new_session_data = {
            "title": "測試 ID",
            "description": "測試",
            "date": "2030-12-20",
            "time": "14:00-16:00",
            "location": "測試",
            "level": "初",
            "tags": ["測試"],
            "learning_outcomes": "測試",
            "capacity": 50,
            "speaker": {
                "name": "測試",
                "photo": "test.jpg",
                "bio": "測試"
            }
        }

        new_id = create_session(new_session_data)

        # Should be session_004 (after session_003)
        assert new_id == "session_004"


class TestUpdateSession:
    """Test update_session function."""

    def test_update_existing_session(self, temp_sessions_file, monkeypatch):
        """Test updating an existing session."""
        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', temp_sessions_file)

        updates = {
            "title": "更新的標題",
            "capacity": 120
        }

        success = update_session("session_002", updates)

        assert success is True

        updated_session = get_session_by_id("session_002")
        assert updated_session.title == "更新的標題"
        assert updated_session.capacity == 120

    def test_update_nonexistent_session(self, temp_sessions_file, monkeypatch):
        """Test updating non-existent session returns False."""
        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', temp_sessions_file)

        updates = {"title": "測試"}

        with pytest.raises(SessionNotFoundError):
            update_session("session_999", updates)

    def test_id_immutability(self, temp_sessions_file, monkeypatch):
        """Test that session ID cannot be changed."""
        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', temp_sessions_file)

        updates = {"id": "session_999"}

        update_session("session_002", updates)

        # ID should remain unchanged
        session = get_session_by_id("session_002")
        assert session.id == "session_002"


class TestDeleteSession:
    """Test delete_session function."""

    def test_delete_existing_session(self, temp_sessions_file, monkeypatch):
        """Test deleting an existing session."""
        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', temp_sessions_file)

        success = delete_session("session_002")

        assert success is True

        deleted_session = get_session_by_id("session_002")
        assert deleted_session is None

    def test_delete_nonexistent_session(self, temp_sessions_file, monkeypatch):
        """Test deleting non-existent session returns False."""
        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', temp_sessions_file)

        success = delete_session("session_999")

        assert success is False

    def test_cache_cleared_after_delete(self, temp_sessions_file, monkeypatch):
        """Test that cache is cleared after deletion."""
        from src.services.session_service import _clear_cache

        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', temp_sessions_file)

        # 清除快取確保讀取正確的檔案
        _clear_cache()

        initial_count = len(get_all_sessions())

        delete_session("session_001")

        new_count = len(get_all_sessions())
        assert new_count == initial_count - 1
