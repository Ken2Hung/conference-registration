"""Integration tests for session registration flow."""
import pytest
import json
import os
import tempfile


@pytest.fixture
def registration_test_data():
    """Create test data for registration flow."""
    return {
        "sessions": [
            {
                "id": "session_001",
                "title": "測試議程",
                "description": "這是測試議程描述",
                "date": "2030-12-01",
                "time": "14:00-16:00",
                "location": "台北國際會議中心",
                "level": "中",
                "tags": ["Python", "測試"],
                "learning_outcomes": "學習如何進行報名測試",
                "capacity": 50,
                "registered": 25,
                "speaker": {
                    "name": "測試講師",
                    "photo": "images/speakers/test.jpg",
                    "bio": "專業測試講師，擁有豐富的測試經驗"
                }
            },
            {
                "id": "session_002",
                "title": "已額滿議程",
                "description": "此議程已額滿",
                "date": "2030-12-15",
                "time": "10:00-12:00",
                "location": "線上",
                "level": "高",
                "tags": ["進階"],
                "learning_outcomes": "測試額滿狀態",
                "capacity": 100,
                "registered": 100,
                "speaker": {
                    "name": "高級講師",
                    "photo": "images/speakers/advanced.jpg",
                    "bio": "高級講師"
                }
            }
        ]
    }


@pytest.fixture
def temp_registration_file(registration_test_data):
    """Create temporary file for registration testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(registration_test_data, f, ensure_ascii=False)
        temp_path = f.name

    yield temp_path

    if os.path.exists(temp_path):
        os.remove(temp_path)


class TestRegistrationFlow:
    """Integration tests for complete registration flow."""

    def test_view_session_details(self, temp_registration_file, monkeypatch):
        """Test viewing session details."""
        from src.services.session_service import get_session_by_id, _clear_cache

        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', temp_registration_file)
        _clear_cache()

        # Step 1: 取得議程詳情
        session = get_session_by_id("session_001")

        # Step 2: 驗證所有欄位都存在
        assert session is not None
        assert session.title == "測試議程"
        assert session.description == "這是測試議程描述"
        assert session.date == "2030-12-01"
        assert session.time == "14:00-16:00"
        assert session.location == "台北國際會議中心"
        assert session.level == "中"
        assert session.tags == ["Python", "測試"]
        assert session.learning_outcomes == "學習如何進行報名測試"
        assert session.capacity == 50
        assert session.registered == 25

        # Step 3: 驗證講師資訊
        assert session.speaker.name == "測試講師"
        assert session.speaker.photo == "images/speakers/test.jpg"
        assert session.speaker.bio == "專業測試講師，擁有豐富的測試經驗"

        # Step 4: 驗證計算屬性
        assert session.is_upcoming() is True
        assert session.is_full() is False
        assert session.status() == "available"
        assert session.registration_percentage() == 50.0

    def test_successful_registration_flow(self, temp_registration_file, monkeypatch):
        """Test complete registration flow: view → register → verify."""
        from src.services.session_service import get_session_by_id, register_for_session, _clear_cache

        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', temp_registration_file)
        _clear_cache()

        # Step 1: 查看議程詳情
        session_before = get_session_by_id("session_001")
        initial_count = session_before.registered

        # Step 2: 進行報名
        success, message = register_for_session("session_001")

        # Step 3: 驗證報名成功
        assert success is True
        assert "成功" in message

        # Step 4: 重新查看議程，驗證人數增加
        session_after = get_session_by_id("session_001")
        assert session_after.registered == initial_count + 1

        # Step 5: 驗證百分比更新
        expected_pct = (initial_count + 1) / session_before.capacity * 100
        assert session_after.registration_percentage() == expected_pct

    def test_registration_for_full_session(self, temp_registration_file, monkeypatch):
        """Test registration fails for full sessions."""
        from src.services.session_service import get_session_by_id, register_for_session, _clear_cache

        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', temp_registration_file)
        _clear_cache()

        # Step 1: 查看已額滿的議程
        session = get_session_by_id("session_002")
        assert session.is_full() is True
        assert session.status() == "full"

        # Step 2: 嘗試報名
        success, message = register_for_session("session_002")

        # Step 3: 驗證報名失敗
        assert success is False
        assert "額滿" in message

        # Step 4: 驗證人數沒有變化
        session_after = get_session_by_id("session_002")
        assert session_after.registered == session.registered

    def test_ui_state_updates(self, temp_registration_file, monkeypatch):
        """Test that UI state is properly updated after registration."""
        from src.services.session_service import get_session_by_id, register_for_session, _clear_cache

        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', temp_registration_file)
        _clear_cache()

        session_id = "session_001"

        # Step 1: 初始狀態
        session = get_session_by_id(session_id)
        initial_status = session.status()
        initial_pct = session.registration_percentage()

        # Step 2: 報名
        register_for_session(session_id)

        # Step 3: 驗證 UI 相關資料更新
        updated_session = get_session_by_id(session_id)

        # 報名人數應增加
        assert updated_session.registered > session.registered

        # 百分比應增加
        assert updated_session.registration_percentage() > initial_pct

        # 如果未額滿，狀態應仍為 available
        if updated_session.registered < updated_session.capacity:
            assert updated_session.status() == "available"

    def test_multiple_registrations(self, temp_registration_file, monkeypatch):
        """Test multiple sequential registrations."""
        from src.services.session_service import get_session_by_id, register_for_session, _clear_cache

        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', temp_registration_file)
        _clear_cache()

        session_id = "session_001"
        initial_session = get_session_by_id(session_id)
        initial_count = initial_session.registered

        # 進行 3 次報名
        for i in range(3):
            success, message = register_for_session(session_id)
            assert success is True

        # 驗證人數增加 3 人
        final_session = get_session_by_id(session_id)
        assert final_session.registered == initial_count + 3

    def test_session_not_found(self, temp_registration_file, monkeypatch):
        """Test handling of non-existent session."""
        from src.services.session_service import get_session_by_id, _clear_cache

        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', temp_registration_file)
        _clear_cache()

        # 嘗試查看不存在的議程
        session = get_session_by_id("session_999")

        # 應回傳 None
        assert session is None

    def test_registration_persistence(self, temp_registration_file, monkeypatch):
        """Test that registration data persists to file."""
        from src.services.session_service import register_for_session, _clear_cache
        from src.services.storage_service import load_json

        monkeypatch.setattr('src.services.session_service.SESSIONS_FILE', temp_registration_file)
        _clear_cache()

        # 進行報名
        register_for_session("session_001")

        # 直接從檔案讀取驗證資料已儲存
        data = load_json(temp_registration_file)
        session_data = next((s for s in data["sessions"] if s["id"] == "session_001"), None)

        assert session_data is not None
        assert session_data["registered"] == 26  # 原本 25 + 1
