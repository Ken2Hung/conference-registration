"""Unit tests for registration_service."""
import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.services.registration_service import register_for_session
from src.models.session import Session
from src.models.speaker import Speaker
from src.models.registrant import Registrant


@pytest.fixture
def sample_speaker():
    """Create a sample speaker."""
    return Speaker(
        name="Test Speaker",
        photo="images/test.jpg",
        bio="Test bio"
    )


@pytest.fixture
def available_session(sample_speaker):
    """Create an available session."""
    return Session(
        id="session_001",
        title="Test Session",
        description="Test description",
        date="2025-12-01",
        time="14:00-16:00",
        location="Test Location",
        level="初",
        tags=["Test"],
        learning_outcomes="Test outcomes",
        capacity=50,
        registered=0,
        speaker=sample_speaker,
        registrants=[]
    )


@pytest.fixture
def full_session(sample_speaker):
    """Create a full session."""
    registrants = [
        Registrant(name=f"Attendee{i}", registered_at=f"2025-10-28T14:{i:02d}:10+08:00")
        for i in range(50)
    ]
    return Session(
        id="session_002",
        title="Full Session",
        description="Test description",
        date="2025-12-01",
        time="14:00-16:00",
        location="Test Location",
        level="中",
        tags=["Test"],
        learning_outcomes="Test outcomes",
        capacity=50,
        registered=50,
        speaker=sample_speaker,
        registrants=registrants
    )


@pytest.fixture
def past_session(sample_speaker):
    """Create a past session."""
    return Session(
        id="session_003",
        title="Past Session",
        description="Test description",
        date="2020-01-01",
        time="14:00-16:00",
        location="Test Location",
        level="高",
        tags=["Test"],
        learning_outcomes="Test outcomes",
        capacity=50,
        registered=0,
        speaker=sample_speaker,
        registrants=[]
    )


class TestRegisterForSession:
    """Test register_for_session function."""

    def test_successful_registration(self, available_session, tmp_path):
        """Test successful registration with valid name."""
        # Create temporary sessions file
        sessions_file = tmp_path / "sessions.json"
        data = {
            "sessions": [
                {
                    "id": "session_001",
                    "title": "Test Session",
                    "description": "Test description",
                    "date": "2025-12-01",
                    "time": "14:00-16:00",
                    "location": "Test Location",
                    "level": "初",
                    "tags": ["Test"],
                    "learning_outcomes": "Test outcomes",
                    "capacity": 50,
                    "registered": 0,
                    "speaker": {
                        "name": "Test Speaker",
                        "photo": "images/test.jpg",
                        "bio": "Test bio"
                    },
                    "registrants": []
                }
            ]
        }
        sessions_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))

        with patch('src.services.registration_service.SESSIONS_FILE', str(sessions_file)):
            with patch('src.services.registration_service.get_session_by_id', return_value=available_session):
                success, message = register_for_session("session_001", "張三")

        assert success is True
        assert message == "報名成功"

        # Verify file was updated
        updated_data = json.loads(sessions_file.read_text())
        assert len(updated_data["sessions"][0]["registrants"]) == 1
        assert updated_data["sessions"][0]["registrants"][0]["name"] == "張三"
        assert updated_data["sessions"][0]["registered"] == 1

    def test_registration_with_empty_name(self, available_session):
        """Test registration fails with empty name."""
        with patch('src.services.registration_service.get_session_by_id', return_value=available_session):
            success, message = register_for_session("session_001", "")

        assert success is False
        assert message == "姓名不可為空"

    def test_registration_with_too_long_name(self, available_session):
        """Test registration fails with name exceeding 50 characters."""
        long_name = "A" * 51
        with patch('src.services.registration_service.get_session_by_id', return_value=available_session):
            success, message = register_for_session("session_001", long_name)

        assert success is False
        assert message == "姓名長度不可超過 50 字元"

    def test_registration_for_nonexistent_session(self):
        """Test registration fails when session not found."""
        with patch('src.services.registration_service.get_session_by_id', return_value=None):
            success, message = register_for_session("session_999", "張三")

        assert success is False
        assert message == "找不到議程"

    def test_registration_for_full_session(self, full_session):
        """Test registration fails when session is full."""
        with patch('src.services.registration_service.get_session_by_id', return_value=full_session):
            success, message = register_for_session("session_002", "張三")

        assert success is False
        assert message == "已額滿"

    def test_registration_for_past_session(self, past_session):
        """Test registration fails when session has passed."""
        with patch('src.services.registration_service.get_session_by_id', return_value=past_session):
            success, message = register_for_session("session_003", "張三")

        assert success is False
        assert message == "已過期"

    def test_duplicate_registration(self, available_session, tmp_path):
        """Test registration fails for duplicate name."""
        # Add existing registrant
        available_session.registrants = [
            Registrant(name="張三", registered_at="2025-10-28T14:00:00+08:00")
        ]
        available_session.registered = 1

        with patch('src.services.registration_service.get_session_by_id', return_value=available_session):
            success, message = register_for_session("session_001", "張三")

        assert success is False
        assert message == "您已報名"

    def test_duplicate_registration_case_insensitive(self, available_session):
        """Test registration fails for duplicate name (case-insensitive)."""
        available_session.registrants = [
            Registrant(name="John Doe", registered_at="2025-10-28T14:00:00+08:00")
        ]
        available_session.registered = 1

        with patch('src.services.registration_service.get_session_by_id', return_value=available_session):
            success, message = register_for_session("session_001", "JOHN DOE")

        assert success is False
        assert message == "您已報名"

    def test_duplicate_registration_with_whitespace(self, available_session):
        """Test registration fails for duplicate name with extra whitespace."""
        available_session.registrants = [
            Registrant(name="張三", registered_at="2025-10-28T14:00:00+08:00")
        ]
        available_session.registered = 1

        with patch('src.services.registration_service.get_session_by_id', return_value=available_session):
            success, message = register_for_session("session_001", "  張三  ")

        assert success is False
        assert message == "您已報名"

    def test_registration_creates_iso_8601_timestamp(self, available_session, tmp_path):
        """Test registration creates ISO 8601 timestamp."""
        sessions_file = tmp_path / "sessions.json"
        data = {
            "sessions": [
                {
                    "id": "session_001",
                    "title": "Test Session",
                    "description": "Test description",
                    "date": "2025-12-01",
                    "time": "14:00-16:00",
                    "location": "Test Location",
                    "level": "初",
                    "tags": ["Test"],
                    "learning_outcomes": "Test outcomes",
                    "capacity": 50,
                    "registered": 0,
                    "speaker": {
                        "name": "Test Speaker",
                        "photo": "images/test.jpg",
                        "bio": "Test bio"
                    },
                    "registrants": []
                }
            ]
        }
        sessions_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))

        with patch('src.services.registration_service.SESSIONS_FILE', str(sessions_file)):
            with patch('src.services.registration_service.get_session_by_id', return_value=available_session):
                success, message = register_for_session("session_001", "Test User")

        updated_data = json.loads(sessions_file.read_text())
        timestamp = updated_data["sessions"][0]["registrants"][0]["registered_at"]

        # Verify timestamp is valid ISO 8601
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        assert "T" in timestamp  # Has date-time separator
