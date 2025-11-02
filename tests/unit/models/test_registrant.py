"""Tests for Registrant model."""
import pytest
from datetime import datetime
from src.models.registrant import Registrant


class TestRegistrantValidation:
    """Tests for registrant data validation."""

    def test_create_valid_registrant(self):
        """Valid registrant should be created successfully."""
        registrant = Registrant(
            name="張三",
            registered_at="2025-10-28T14:32:10+08:00"
        )
        assert registrant.name == "張三"
        assert registrant.registered_at == "2025-10-28T14:32:10+08:00"

    def test_empty_name_raises_error(self):
        """Empty name should raise ValueError."""
        with pytest.raises(ValueError, match="Name cannot be empty"):
            Registrant(
                name="",
                registered_at="2025-10-28T14:32:10+08:00"
            )

    def test_whitespace_only_name_raises_error(self):
        """Whitespace-only name should raise ValueError."""
        with pytest.raises(ValueError, match="Name cannot be empty"):
            Registrant(
                name="   ",
                registered_at="2025-10-28T14:32:10+08:00"
            )

    def test_name_exceeds_50_chars_raises_error(self):
        """Name longer than 50 characters should raise ValueError."""
        long_name = "A" * 51
        with pytest.raises(ValueError, match="Name cannot exceed 50 characters"):
            Registrant(
                name=long_name,
                registered_at="2025-10-28T14:32:10+08:00"
            )

    def test_name_exactly_50_chars_accepted(self):
        """Name with exactly 50 characters should be accepted."""
        name_50_chars = "A" * 50
        registrant = Registrant(
            name=name_50_chars,
            registered_at="2025-10-28T14:32:10+08:00"
        )
        assert registrant.name == name_50_chars

    def test_invalid_timestamp_format_raises_error(self):
        """Invalid ISO 8601 timestamp should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid timestamp format"):
            Registrant(
                name="張三",
                registered_at="28/10/2025 14:32:10"
            )

    def test_iso_8601_with_z_suffix(self):
        """ISO 8601 timestamp with Z suffix should be accepted."""
        registrant = Registrant(
            name="John Doe",
            registered_at="2025-10-28T06:32:10Z"
        )
        assert registrant.registered_at == "2025-10-28T06:32:10Z"

    def test_iso_8601_without_timezone(self):
        """ISO 8601 timestamp without timezone should be accepted."""
        registrant = Registrant(
            name="Jane Doe",
            registered_at="2025-10-28T14:32:10"
        )
        assert registrant.registered_at == "2025-10-28T14:32:10"

    def test_chinese_name_accepted(self):
        """Chinese characters in name should be accepted."""
        registrant = Registrant(
            name="王小明",
            registered_at="2025-10-28T14:32:10+08:00"
        )
        assert registrant.name == "王小明"

    def test_mixed_language_name_accepted(self):
        """Mixed language name should be accepted."""
        registrant = Registrant(
            name="John 王",
            registered_at="2025-10-28T14:32:10+08:00"
        )
        assert registrant.name == "John 王"
