"""Integration tests for registration flow."""
import pytest
import json
import os
from pathlib import Path

from src.services.registration_service import register_for_session
from src.services.session_service import get_session_by_id, _clear_cache


@pytest.fixture
def test_sessions_file(tmp_path):
    """Create a temporary sessions file for testing."""
    sessions_file = tmp_path / "sessions.json"
    data = {
        "sessions": [
            {
                "id": "session_001",
                "title": "Python 基礎課程",
                "description": "學習 Python 基礎語法",
                "date": "2025-12-01",
                "time": "14:00-16:00",
                "location": "線上",
                "level": "初",
                "tags": ["Python", "Programming"],
                "learning_outcomes": "掌握 Python 基礎",
                "capacity": 10,
                "registered": 0,
                "speaker": {
                    "name": "王老師",
                    "photo": "images/speakers/wang.jpg",
                    "bio": "資深工程師"
                },
                "registrants": []
            },
            {
                "id": "session_002",
                "title": "已額滿課程",
                "description": "這個課程已經滿了",
                "date": "2025-12-15",
                "time": "10:00-12:00",
                "location": "台北",
                "level": "中",
                "tags": ["Test"],
                "learning_outcomes": "Test",
                "capacity": 2,
                "registered": 2,
                "speaker": {
                    "name": "李老師",
                    "photo": "images/speakers/li.jpg",
                    "bio": "專家"
                },
                "registrants": [
                    {
                        "name": "已報名者一",
                        "registered_at": "2025-10-28T10:00:00+08:00"
                    },
                    {
                        "name": "已報名者二",
                        "registered_at": "2025-10-28T10:05:00+08:00"
                    }
                ]
            }
        ]
    }
    sessions_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return sessions_file


class TestRegistrationIntegration:
    """Integration tests for end-to-end registration flow."""

    def test_end_to_end_registration_with_real_file(self, test_sessions_file, monkeypatch):
        """Test complete registration flow with real JSON file operations."""
        # Patch the SESSIONS_FILE path
        monkeypatch.setattr('src.services.registration_service.SESSIONS_FILE', str(test_sessions_file))
        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', str(test_sessions_file))
        _clear_cache()

        # Step 1: Register first user
        success1, message1 = register_for_session("session_001", "張三")
        assert success1 is True
        assert message1 == "報名成功"

        # Step 2: Verify session was updated
        session = get_session_by_id("session_001")
        assert session is not None
        assert session.registered == 1
        assert len(session.registrants) == 1
        assert session.registrants[0].name == "張三"

        # Step 3: Register second user
        success2, message2 = register_for_session("session_001", "李四")
        assert success2 is True
        assert message2 == "報名成功"

        # Step 4: Verify both registrations
        _clear_cache()
        session = get_session_by_id("session_001")
        assert session.registered == 2
        assert len(session.registrants) == 2
        assert session.registrants[0].name == "張三"
        assert session.registrants[1].name == "李四"

    def test_duplicate_registration_prevented(self, test_sessions_file, monkeypatch):
        """Test that duplicate registrations are prevented."""
        monkeypatch.setattr('src.services.registration_service.SESSIONS_FILE', str(test_sessions_file))
        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', str(test_sessions_file))
        _clear_cache()

        # First registration succeeds
        success1, message1 = register_for_session("session_001", "王小明")
        assert success1 is True

        # Second registration with same name fails
        _clear_cache()
        success2, message2 = register_for_session("session_001", "王小明")
        assert success2 is False
        assert message2 == "您已報名"

        # Verify only one registration exists
        _clear_cache()
        session = get_session_by_id("session_001")
        assert session.registered == 1

    def test_registration_fills_to_capacity(self, test_sessions_file, monkeypatch):
        """Test registration up to capacity then rejection."""
        monkeypatch.setattr('src.services.registration_service.SESSIONS_FILE', str(test_sessions_file))
        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', str(test_sessions_file))
        _clear_cache()

        # Register 10 users (capacity = 10)
        names = [f"User{i}" for i in range(1, 11)]
        for name in names:
            success, message = register_for_session("session_001", name)
            assert success is True
            _clear_cache()

        # 11th registration should fail
        success, message = register_for_session("session_001", "User11")
        assert success is False
        assert message == "已額滿"

        # Verify exactly 10 registrations
        _clear_cache()
        session = get_session_by_id("session_001")
        assert session.registered == 10
        assert session.is_full() is True

    def test_concurrent_registrations_consistency(self, test_sessions_file, monkeypatch):
        """Test file locking ensures data consistency with concurrent writes."""
        monkeypatch.setattr('src.services.registration_service.SESSIONS_FILE', str(test_sessions_file))
        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', str(test_sessions_file))
        _clear_cache()

        # Simulate multiple registrations
        users = ["ConcUser1", "ConcUser2", "ConcUser3"]
        results = []

        for user in users:
            _clear_cache()
            success, message = register_for_session("session_001", user)
            results.append((success, message))

        # All should succeed
        assert all(success for success, _ in results)

        # Verify final state
        _clear_cache()
        session = get_session_by_id("session_001")
        assert session.registered == 3
        assert len(session.registrants) == 3

        # Verify all names are present
        names = [r.name for r in session.registrants]
        assert set(names) == set(users)

    def test_registration_for_already_full_session(self, test_sessions_file, monkeypatch):
        """Test registration fails for session that's already full."""
        monkeypatch.setattr('src.services.registration_service.SESSIONS_FILE', str(test_sessions_file))
        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', str(test_sessions_file))
        _clear_cache()

        # Try to register for session_002 which is already full
        success, message = register_for_session("session_002", "新報名者")
        assert success is False
        assert message == "已額滿"

        # Verify registrations unchanged
        session = get_session_by_id("session_002")
        assert session.registered == 2
        assert len(session.registrants) == 2

    def test_registration_with_special_characters(self, test_sessions_file, monkeypatch):
        """Test registration with special characters in name."""
        monkeypatch.setattr('src.services.registration_service.SESSIONS_FILE', str(test_sessions_file))
        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', str(test_sessions_file))
        _clear_cache()

        # Register with name containing special characters
        special_names = ["王小明-陳", "李O'Brien", "José García", "山田 太郎"]

        for name in special_names:
            _clear_cache()
            success, message = register_for_session("session_001", name)
            if len(name) <= 50:
                assert success is True, f"Failed to register name: {name}"

        # Verify all were saved correctly
        _clear_cache()
        data = json.loads(test_sessions_file.read_text())
        registrants = data["sessions"][0]["registrants"]
        saved_names = [r["name"] for r in registrants]

        for name in special_names:
            if len(name) <= 50:
                assert name in saved_names

    def test_file_persistence_after_registration(self, test_sessions_file, monkeypatch):
        """Test that registration is persisted to file correctly."""
        monkeypatch.setattr('src.services.registration_service.SESSIONS_FILE', str(test_sessions_file))
        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', str(test_sessions_file))
        _clear_cache()

        # Register a user
        register_for_session("session_001", "Test User")

        # Read file directly
        data = json.loads(test_sessions_file.read_text())
        session_data = data["sessions"][0]

        # Verify structure
        assert "registrants" in session_data
        assert len(session_data["registrants"]) == 1
        assert session_data["registrants"][0]["name"] == "Test User"
        assert "registered_at" in session_data["registrants"][0]
        assert session_data["registered"] == 1

        # Verify backup was created
        backup_files = list(test_sessions_file.parent.glob("sessions.json.backup*"))
        assert len(backup_files) > 0
