"""Unit tests for validation utilities."""
import pytest
from src.utils.validation import (
    validate_session,
    validate_speaker,
    validate_date_format,
    validate_time_format
)


class TestValidateDateFormat:
    """Test date format validation."""

    def test_valid_date(self):
        """Test valid YYYY-MM-DD date."""
        assert validate_date_format("2025-12-01") is True

    def test_invalid_format_raises_error(self):
        """Test invalid date format raises ValueError."""
        with pytest.raises(ValueError, match="must be in YYYY-MM-DD format"):
            validate_date_format("12/01/2025")

    def test_invalid_date_value_raises_error(self):
        """Test invalid date value raises ValueError."""
        with pytest.raises(ValueError, match="Invalid date value"):
            validate_date_format("2025-13-01")

    def test_non_string_raises_error(self):
        """Test non-string input raises ValueError."""
        with pytest.raises(ValueError, match="Date must be a string"):
            validate_date_format(20251201)


class TestValidateTimeFormat:
    """Test time format validation."""

    def test_valid_time_range(self):
        """Test valid HH:MM-HH:MM time range."""
        assert validate_time_format("14:00-16:00") is True

    def test_invalid_format_raises_error(self):
        """Test invalid time format raises ValueError."""
        with pytest.raises(ValueError, match="must be in HH:MM-HH:MM format"):
            validate_time_format("2pm-4pm")

    def test_start_after_end_raises_error(self):
        """Test start time after end time raises ValueError."""
        with pytest.raises(ValueError, match="Start time must be before end time"):
            validate_time_format("16:00-14:00")

    def test_start_equals_end_raises_error(self):
        """Test start time equals end time raises ValueError."""
        with pytest.raises(ValueError, match="Start time must be before end time"):
            validate_time_format("14:00-14:00")

    def test_invalid_hour_raises_error(self):
        """Test invalid hour value raises ValueError."""
        with pytest.raises(ValueError, match="Invalid time value"):
            validate_time_format("25:00-26:00")

    def test_non_string_raises_error(self):
        """Test non-string input raises ValueError."""
        with pytest.raises(ValueError, match="Time must be a string"):
            validate_time_format(1400)


class TestValidateSpeaker:
    """Test speaker validation."""

    def test_valid_speaker(self):
        """Test valid speaker data."""
        speaker_data = {
            "name": "張志成",
            "photo": "images/speakers/zhang-zhicheng.jpg",
            "bio": "資深全端工程師,擅長 Python 與 React 開發"
        }
        assert validate_speaker(speaker_data) is True

    def test_valid_speaker_with_url(self):
        """Test valid speaker with HTTP photo URL."""
        speaker_data = {
            "name": "李欣怡",
            "photo": "https://example.com/speakers/li-xinyi.jpg",
            "bio": "前端技術專家"
        }
        assert validate_speaker(speaker_data) is True

    def test_missing_name_raises_error(self):
        """Test missing name raises ValueError."""
        speaker_data = {
            "photo": "images/speakers/test.jpg",
            "bio": "Test bio"
        }
        with pytest.raises(ValueError, match="Missing required speaker field: name"):
            validate_speaker(speaker_data)

    def test_empty_name_raises_error(self):
        """Test empty name raises ValueError."""
        speaker_data = {
            "name": "",
            "photo": "images/speakers/test.jpg",
            "bio": "Test bio"
        }
        with pytest.raises(ValueError, match="Speaker name cannot be empty"):
            validate_speaker(speaker_data)

    def test_missing_photo_raises_error(self):
        """Test missing photo raises ValueError."""
        speaker_data = {
            "name": "Test Speaker",
            "bio": "Test bio"
        }
        with pytest.raises(ValueError, match="Missing required speaker field: photo"):
            validate_speaker(speaker_data)

    def test_invalid_photo_format_raises_error(self):
        """Test invalid photo format raises ValueError."""
        speaker_data = {
            "name": "Test Speaker",
            "photo": "invalid.txt",
            "bio": "Test bio"
        }
        with pytest.raises(ValueError, match="Invalid photo path format"):
            validate_speaker(speaker_data)

    def test_missing_bio_raises_error(self):
        """Test missing bio raises ValueError."""
        speaker_data = {
            "name": "Test Speaker",
            "photo": "images/speakers/test.jpg"
        }
        with pytest.raises(ValueError, match="Missing required speaker field: bio"):
            validate_speaker(speaker_data)

    def test_non_dict_raises_error(self):
        """Test non-dictionary input raises ValueError."""
        with pytest.raises(ValueError, match="Speaker data must be a dictionary"):
            validate_speaker("not a dict")


class TestValidateSession:
    """Test session validation."""

    @pytest.fixture
    def valid_session_data(self):
        """Create valid session data for testing."""
        return {
            "id": "session_001",
            "title": "Python 網頁爬蟲入門",
            "description": "網頁爬蟲是數據收集的重要技能",
            "date": "2025-12-01",
            "time": "14:00-16:00",
            "location": "台北國際會議中心 201 室",
            "level": "初",
            "tags": ["Python", "Web Scraping"],
            "learning_outcomes": "掌握 Requests 與 BeautifulSoup 用法",
            "capacity": 50,
            "registered": 25,
            "speaker": {
                "name": "張志成",
                "photo": "images/speakers/zhang-zhicheng.jpg",
                "bio": "資深全端工程師"
            }
        }

    def test_valid_session(self, valid_session_data):
        """Test valid session data."""
        assert validate_session(valid_session_data) is True

    def test_missing_required_field_raises_error(self, valid_session_data):
        """Test missing required field raises ValueError."""
        del valid_session_data["title"]
        with pytest.raises(ValueError, match="Missing required field: title"):
            validate_session(valid_session_data)

    def test_invalid_session_id_format_raises_error(self, valid_session_data):
        """Test invalid session ID format raises ValueError."""
        valid_session_data["id"] = "invalid_id"
        with pytest.raises(ValueError, match="Invalid session ID format"):
            validate_session(valid_session_data)

    def test_empty_title_raises_error(self, valid_session_data):
        """Test empty title raises ValueError."""
        valid_session_data["title"] = ""
        with pytest.raises(ValueError, match="Title cannot be empty"):
            validate_session(valid_session_data)

    def test_invalid_date_format_raises_error(self, valid_session_data):
        """Test invalid date format raises ValueError."""
        valid_session_data["date"] = "12/01/2025"
        with pytest.raises(ValueError, match="must be in YYYY-MM-DD format"):
            validate_session(valid_session_data)

    def test_invalid_time_format_raises_error(self, valid_session_data):
        """Test invalid time format raises ValueError."""
        valid_session_data["time"] = "2pm-4pm"
        with pytest.raises(ValueError, match="must be in HH:MM-HH:MM format"):
            validate_session(valid_session_data)

    def test_invalid_level_raises_error(self, valid_session_data):
        """Test invalid difficulty level raises ValueError."""
        valid_session_data["level"] = "無效"
        with pytest.raises(ValueError, match="Level must be one of"):
            validate_session(valid_session_data)

    def test_empty_tags_raises_error(self, valid_session_data):
        """Test empty tags list raises ValueError."""
        valid_session_data["tags"] = []
        with pytest.raises(ValueError, match="Tags must be a non-empty list"):
            validate_session(valid_session_data)

    def test_non_list_tags_raises_error(self, valid_session_data):
        """Test non-list tags raises ValueError."""
        valid_session_data["tags"] = "Python"
        with pytest.raises(ValueError, match="Tags must be a non-empty list"):
            validate_session(valid_session_data)

    def test_empty_tag_raises_error(self, valid_session_data):
        """Test empty tag in list raises ValueError."""
        valid_session_data["tags"] = ["Python", ""]
        with pytest.raises(ValueError, match="All tags must be non-empty strings"):
            validate_session(valid_session_data)

    def test_negative_capacity_raises_error(self, valid_session_data):
        """Test negative capacity raises ValueError."""
        valid_session_data["capacity"] = -10
        with pytest.raises(ValueError, match="Capacity must be a positive integer"):
            validate_session(valid_session_data)

    def test_zero_capacity_raises_error(self, valid_session_data):
        """Test zero capacity raises ValueError."""
        valid_session_data["capacity"] = 0
        with pytest.raises(ValueError, match="Capacity must be a positive integer"):
            validate_session(valid_session_data)

    def test_negative_registered_raises_error(self, valid_session_data):
        """Test negative registered count raises ValueError."""
        valid_session_data["registered"] = -5
        with pytest.raises(ValueError, match="Registered count must be a non-negative integer"):
            validate_session(valid_session_data)

    def test_registered_exceeds_capacity_raises_error(self, valid_session_data):
        """Test registered > capacity raises ValueError."""
        valid_session_data["registered"] = 60
        valid_session_data["capacity"] = 50
        with pytest.raises(ValueError, match="Registered count .* cannot exceed capacity"):
            validate_session(valid_session_data)

    def test_invalid_speaker_raises_error(self, valid_session_data):
        """Test invalid speaker data raises ValueError."""
        valid_session_data["speaker"]["name"] = ""
        with pytest.raises(ValueError, match="Speaker name cannot be empty"):
            validate_session(valid_session_data)

    def test_non_dict_raises_error(self):
        """Test non-dictionary input raises ValueError."""
        with pytest.raises(ValueError, match="Session data must be a dictionary"):
            validate_session("not a dict")

    def test_edge_case_capacity_one(self, valid_session_data):
        """Test edge case with capacity of 1."""
        valid_session_data["capacity"] = 1
        valid_session_data["registered"] = 0
        assert validate_session(valid_session_data) is True

    def test_edge_case_large_capacity(self, valid_session_data):
        """Test edge case with large capacity."""
        valid_session_data["capacity"] = 10000
        valid_session_data["registered"] = 5000
        assert validate_session(valid_session_data) is True

    def test_utf8_chinese_characters(self, valid_session_data):
        """Test UTF-8 Chinese characters are handled correctly."""
        valid_session_data["title"] = "中文標題測試"
        valid_session_data["description"] = "這是中文描述"
        assert validate_session(valid_session_data) is True
