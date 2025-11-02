"""Tests for new validation utilities (name, session_date, capacity, level)."""
import pytest
from datetime import datetime, timedelta
from src.utils.validation import (
    validate_name,
    normalize_name,
    validate_session_date,
    validate_capacity,
    validate_level
)


class TestValidateName:
    """Tests for validate_name function."""

    def test_valid_name(self):
        """Valid name should pass validation."""
        is_valid, message = validate_name("張三")
        assert is_valid is True
        assert message == ""

    def test_empty_name(self):
        """Empty name should fail validation."""
        is_valid, message = validate_name("")
        assert is_valid is False
        assert message == "姓名不可為空"

    def test_whitespace_only_name(self):
        """Whitespace-only name should fail validation."""
        is_valid, message = validate_name("   ")
        assert is_valid is False
        assert message == "姓名不可為空"

    def test_name_exactly_50_chars(self):
        """Name with 50 characters should pass validation."""
        name_50_chars = "A" * 50
        is_valid, message = validate_name(name_50_chars)
        assert is_valid is True
        assert message == ""

    def test_name_exceeds_50_chars(self):
        """Name longer than 50 characters should fail validation."""
        long_name = "A" * 51
        is_valid, message = validate_name(long_name)
        assert is_valid is False
        assert message == "姓名長度不可超過 50 字元"


class TestNormalizeName:
    """Tests for normalize_name function."""

    def test_trim_leading_whitespace(self):
        """Should trim leading whitespace."""
        assert normalize_name("  張三") == "張三"

    def test_trim_trailing_whitespace(self):
        """Should trim trailing whitespace."""
        assert normalize_name("張三  ") == "張三"

    def test_trim_both_whitespaces(self):
        """Should trim both leading and trailing whitespace."""
        assert normalize_name("  張三  ") == "張三"

    def test_preserve_internal_spacing(self):
        """Should preserve internal spacing."""
        assert normalize_name("John Doe") == "john doe"

    def test_lowercase_latin_chars(self):
        """Should convert Latin characters to lowercase."""
        assert normalize_name("JOHN DOE") == "john doe"

    def test_chinese_chars_unchanged(self):
        """Chinese characters should remain unchanged."""
        assert normalize_name("張三") == "張三"

    def test_mixed_language_normalization(self):
        """Should handle mixed language names correctly."""
        assert normalize_name(" John 王 ") == "john 王"


class TestValidateSessionDate:
    """Tests for validate_session_date function."""

    def test_valid_future_date(self):
        """Future date should pass validation."""
        future_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        is_valid, message = validate_session_date(future_date)
        assert is_valid is True
        assert message == ""

    def test_past_date_not_allowed_by_default(self):
        """Past date should fail validation by default."""
        past_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        is_valid, message = validate_session_date(past_date)
        assert is_valid is False
        assert message == "日期不可為過去"

    def test_past_date_allowed_with_flag(self):
        """Past date should pass validation when allow_past=True."""
        past_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        is_valid, message = validate_session_date(past_date, allow_past=True)
        assert is_valid is True
        assert message == ""

    def test_invalid_date_format(self):
        """Invalid date format should fail validation."""
        is_valid, message = validate_session_date("2025/10/28")
        assert is_valid is False
        assert message == "日期格式錯誤"

    def test_malformed_date_value(self):
        """Malformed date value should fail validation."""
        is_valid, message = validate_session_date("2025-13-32")
        assert is_valid is False
        assert message == "日期格式錯誤"

    def test_non_string_date(self):
        """Non-string date should fail validation."""
        is_valid, message = validate_session_date(20251028)
        assert is_valid is False
        assert message == "日期格式錯誤"


class TestValidateCapacity:
    """Tests for validate_capacity function."""

    def test_valid_capacity_no_registrations(self):
        """Valid capacity with no registrations should pass."""
        is_valid, message = validate_capacity(100)
        assert is_valid is True
        assert message == ""

    def test_valid_capacity_with_registrations(self):
        """Valid capacity higher than registrations should pass."""
        is_valid, message = validate_capacity(100, current_registered=50)
        assert is_valid is True
        assert message == ""

    def test_capacity_equals_registered(self):
        """Capacity equal to registered count should pass."""
        is_valid, message = validate_capacity(100, current_registered=100)
        assert is_valid is True
        assert message == ""

    def test_capacity_below_registered(self):
        """Capacity lower than registered count should fail."""
        is_valid, message = validate_capacity(50, current_registered=100)
        assert is_valid is False
        assert message == "容量不可低於目前已報名人數"

    def test_zero_capacity(self):
        """Zero capacity should fail validation."""
        is_valid, message = validate_capacity(0)
        assert is_valid is False
        assert message == "容量必須為正整數"

    def test_negative_capacity(self):
        """Negative capacity should fail validation."""
        is_valid, message = validate_capacity(-10)
        assert is_valid is False
        assert message == "容量必須為正整數"

    def test_non_integer_capacity(self):
        """Non-integer capacity should fail validation."""
        is_valid, message = validate_capacity(100.5)
        assert is_valid is False
        assert message == "容量必須為正整數"


class TestValidateLevel:
    """Tests for validate_level function."""

    def test_valid_level_beginner(self):
        """Level '初' should pass validation."""
        is_valid, message = validate_level("初")
        assert is_valid is True
        assert message == ""

    def test_valid_level_intermediate(self):
        """Level '中' should pass validation."""
        is_valid, message = validate_level("中")
        assert is_valid is True
        assert message == ""

    def test_valid_level_advanced(self):
        """Level '高' should pass validation."""
        is_valid, message = validate_level("高")
        assert is_valid is True
        assert message == ""

    def test_invalid_level_english(self):
        """English level should fail validation."""
        is_valid, message = validate_level("beginner")
        assert is_valid is False
        assert message == "難度必須為「初」、「中」或「高」"

    def test_invalid_level_empty(self):
        """Empty level should fail validation."""
        is_valid, message = validate_level("")
        assert is_valid is False
        assert message == "難度必須為「初」、「中」或「高」"

    def test_invalid_level_mixed(self):
        """Mixed or invalid level should fail validation."""
        is_valid, message = validate_level("初級")
        assert is_valid is False
        assert message == "難度必須為「初」、「中」或「高」"
