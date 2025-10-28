"""Integration tests for dashboard display flow."""
import pytest
import json
import os
import tempfile


@pytest.fixture
def mock_sessions_data():
    """Create mock sessions data for testing."""
    return {
        "sessions": [
            # Past sessions
            {
                "id": "session_001",
                "title": "過去議程 1",
                "description": "已結束",
                "date": "2020-01-01",
                "time": "14:00-16:00",
                "location": "台北",
                "level": "初",
                "tags": ["Python"],
                "learning_outcomes": "學習基礎",
                "capacity": 50,
                "registered": 30,
                "speaker": {
                    "name": "講師 A",
                    "photo": "images/speakers/a.jpg",
                    "bio": "專家"
                }
            },
            {
                "id": "session_002",
                "title": "過去議程 2",
                "description": "已結束",
                "date": "2020-02-01",
                "time": "10:00-12:00",
                "location": "台中",
                "level": "中",
                "tags": ["React"],
                "learning_outcomes": "學習進階",
                "capacity": 80,
                "registered": 60,
                "speaker": {
                    "name": "講師 B",
                    "photo": "images/speakers/b.jpg",
                    "bio": "前端專家"
                }
            },
            # Upcoming sessions
            {
                "id": "session_003",
                "title": "未來議程 1",
                "description": "即將開始",
                "date": "2030-11-01",
                "time": "14:00-16:00",
                "location": "高雄",
                "level": "高",
                "tags": ["Docker"],
                "learning_outcomes": "容器化技術",
                "capacity": 100,
                "registered": 45,
                "speaker": {
                    "name": "講師 C",
                    "photo": "images/speakers/c.jpg",
                    "bio": "DevOps"
                }
            },
            {
                "id": "session_004",
                "title": "未來議程 2",
                "description": "即將開始",
                "date": "2030-12-01",
                "time": "09:00-11:00",
                "location": "新竹",
                "level": "初",
                "tags": ["Kubernetes"],
                "learning_outcomes": "K8s 管理",
                "capacity": 60,
                "registered": 20,
                "speaker": {
                    "name": "講師 D",
                    "photo": "images/speakers/d.jpg",
                    "bio": "雲端專家"
                }
            }
        ]
    }


@pytest.fixture
def temp_test_file(mock_sessions_data):
    """Create temporary sessions file for integration testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(mock_sessions_data, f, ensure_ascii=False)
        temp_path = f.name

    yield temp_path

    if os.path.exists(temp_path):
        os.remove(temp_path)


class TestDashboardFlow:
    """Integration tests for complete dashboard display flow."""

    def test_load_and_display_sessions(self, temp_test_file, monkeypatch):
        """Test complete flow: load → filter → display."""
        from src.services.session_service import get_all_sessions, get_past_sessions, get_upcoming_sessions, _clear_cache

        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', temp_test_file)
        _clear_cache()

        # Step 1: Load all sessions
        all_sessions = get_all_sessions()
        assert len(all_sessions) == 4

        # Step 2: Filter past sessions
        past_sessions = get_past_sessions(limit=5)
        assert len(past_sessions) == 2
        assert all(s.is_past() for s in past_sessions)

        # Step 3: Filter upcoming sessions
        upcoming_sessions = get_upcoming_sessions(limit=5)
        assert len(upcoming_sessions) == 2
        assert all(s.is_upcoming() for s in upcoming_sessions)

        # Step 4: Verify correct ordering
        assert past_sessions[0].date >= past_sessions[1].date  # Descending
        assert upcoming_sessions[0].date <= upcoming_sessions[1].date  # Ascending

    def test_dashboard_shows_correct_sessions(self, temp_test_file, monkeypatch):
        """Test that dashboard shows 5 past and 5 upcoming sessions."""
        from src.services.session_service import get_past_sessions, get_upcoming_sessions

        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', temp_test_file)

        past_sessions = get_past_sessions(limit=5)
        upcoming_sessions = get_upcoming_sessions(limit=5)

        # Should show up to 5 of each (we have 2 past and 2 upcoming)
        assert len(past_sessions) <= 5
        assert len(upcoming_sessions) <= 5

        # Verify visual differentiation is possible
        for session in past_sessions:
            assert session.status() == "expired"

        for session in upcoming_sessions:
            assert session.status() in ["available", "full"]

    def test_session_information_complete(self, temp_test_file, monkeypatch):
        """Test that all session information is available for display."""
        from src.services.session_service import get_upcoming_sessions

        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', temp_test_file)

        sessions = get_upcoming_sessions(limit=1)
        session = sessions[0]

        # Verify all display fields are present
        assert session.title
        assert session.date
        assert session.time
        assert session.speaker.name
        assert session.level in ["初", "中", "高"]
        assert session.capacity > 0
        assert session.registered >= 0
        assert len(session.tags) > 0

    def test_chronological_ordering(self, temp_test_file, monkeypatch):
        """Test that sessions are displayed in correct chronological order."""
        from src.services.session_service import get_past_sessions, get_upcoming_sessions

        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', temp_test_file)

        # Past sessions should be newest first (descending)
        past_sessions = get_past_sessions()
        for i in range(len(past_sessions) - 1):
            assert past_sessions[i].date >= past_sessions[i + 1].date

        # Upcoming sessions should be earliest first (ascending)
        upcoming_sessions = get_upcoming_sessions()
        for i in range(len(upcoming_sessions) - 1):
            assert upcoming_sessions[i].date <= upcoming_sessions[i + 1].date

    def test_empty_dashboard_handling(self, monkeypatch):
        """Test dashboard behavior with no sessions."""
        # Create empty sessions file
        empty_data = {"sessions": []}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(empty_data, f, ensure_ascii=False)
            temp_path = f.name

        try:
            from src.services.session_service import get_past_sessions, get_upcoming_sessions, _clear_cache

            monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', temp_path)
            _clear_cache()

            past_sessions = get_past_sessions()
            upcoming_sessions = get_upcoming_sessions()

            assert len(past_sessions) == 0
            assert len(upcoming_sessions) == 0

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
