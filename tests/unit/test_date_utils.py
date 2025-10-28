"""Unit tests for date utilities."""
import pytest
from datetime import datetime
from src.utils.date_utils import (
    parse_date,
    parse_time,
    compare_to_now,
    is_past_datetime
)


class TestParseDate:
    """Test date parsing."""

    def test_parse_valid_date(self):
        """Test parsing valid YYYY-MM-DD date."""
        result = parse_date("2025-12-01")
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 12
        assert result.day == 1

    def test_parse_date_with_leading_zeros(self):
        """Test parsing date with leading zeros."""
        result = parse_date("2025-01-05")
        assert result.month == 1
        assert result.day == 5

    def test_parse_invalid_format_raises_error(self):
        """Test invalid date format raises ValueError."""
        with pytest.raises(ValueError):
            parse_date("12/01/2025")

    def test_parse_invalid_date_value_raises_error(self):
        """Test invalid date value raises ValueError."""
        with pytest.raises(ValueError):
            parse_date("2025-13-01")


class TestParseTime:
    """Test time range parsing."""

    def test_parse_valid_time_range(self):
        """Test parsing valid HH:MM-HH:MM time range."""
        start_time, end_time = parse_time("14:00-16:00")
        assert start_time.hour == 14
        assert start_time.minute == 0
        assert end_time.hour == 16
        assert end_time.minute == 0

    def test_parse_time_with_spaces(self):
        """Test parsing time range with spaces."""
        start_time, end_time = parse_time("14:00 - 16:00")
        assert start_time.hour == 14
        assert end_time.hour == 16

    def test_parse_time_with_minutes(self):
        """Test parsing time range with non-zero minutes."""
        start_time, end_time = parse_time("14:30-16:45")
        assert start_time.minute == 30
        assert end_time.minute == 45

    def test_parse_invalid_format_raises_error(self):
        """Test invalid time format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid time format"):
            parse_time("2pm-4pm")

    def test_parse_missing_dash_raises_error(self):
        """Test missing dash raises ValueError."""
        with pytest.raises(ValueError, match="Invalid time format"):
            parse_time("14:00")

    def test_parse_invalid_hour_raises_error(self):
        """Test invalid hour value raises ValueError."""
        with pytest.raises(ValueError, match="Invalid time format"):
            parse_time("25:00-26:00")


class TestIsPastDatetime:
    """Test checking if datetime is in the past."""

    def test_past_datetime_returns_true(self):
        """Test past datetime returns True."""
        result = is_past_datetime("2020-01-01", "10:00-12:00")
        assert result is True

    def test_future_datetime_returns_false(self):
        """Test future datetime returns False."""
        result = is_past_datetime("2030-12-31", "23:00-23:59")
        assert result is False

    def test_uses_start_time(self):
        """Test that function uses start time of range."""
        result = is_past_datetime("2020-01-01", "10:00-23:59")
        assert result is True

    def test_invalid_date_returns_false(self):
        """Test invalid date returns False (graceful handling)."""
        result = is_past_datetime("invalid-date", "10:00-12:00")
        assert result is False

    def test_invalid_time_returns_false(self):
        """Test invalid time returns False (graceful handling)."""
        result = is_past_datetime("2025-12-01", "invalid-time")
        assert result is False

    def test_malformed_time_range_returns_false(self):
        """Test malformed time range returns False."""
        result = is_past_datetime("2025-12-01", "10:00")
        assert result is False


class TestCompareToNow:
    """Test comparing datetime to current time."""

    def test_compare_past_to_now(self):
        """Test comparing past datetime to now."""
        result = compare_to_now("2020-01-01", "10:00-12:00")
        assert result is True

    def test_compare_future_to_now(self):
        """Test comparing future datetime to now."""
        result = compare_to_now("2030-12-31", "23:00-23:59")
        assert result is False

    def test_compare_delegates_to_is_past_datetime(self):
        """Test that compare_to_now delegates to is_past_datetime."""
        past_result = compare_to_now("2020-01-01", "10:00-12:00")
        direct_result = is_past_datetime("2020-01-01", "10:00-12:00")
        assert past_result == direct_result

        future_result = compare_to_now("2030-12-31", "23:00-23:59")
        direct_future_result = is_past_datetime("2030-12-31", "23:00-23:59")
        assert future_result == direct_future_result


class TestEdgeCases:
    """Test edge cases for date utilities."""

    def test_parse_date_leap_year(self):
        """Test parsing leap year date."""
        result = parse_date("2024-02-29")
        assert result.month == 2
        assert result.day == 29

    def test_parse_date_non_leap_year_invalid(self):
        """Test parsing Feb 29 in non-leap year raises error."""
        with pytest.raises(ValueError):
            parse_date("2025-02-29")

    def test_parse_time_midnight(self):
        """Test parsing midnight time."""
        start_time, end_time = parse_time("00:00-01:00")
        assert start_time.hour == 0
        assert start_time.minute == 0

    def test_parse_time_before_midnight(self):
        """Test parsing time before midnight."""
        start_time, end_time = parse_time("23:00-23:59")
        assert start_time.hour == 23
        assert end_time.minute == 59

    def test_is_past_datetime_edge_of_day(self):
        """Test is_past_datetime with edge of day times."""
        past_result = is_past_datetime("2020-12-31", "23:59-23:59")
        assert past_result is True

    def test_date_with_utf8_raises_error(self):
        """Test date with Chinese characters raises error."""
        with pytest.raises(ValueError):
            parse_date("二〇二五-十二-〇一")
