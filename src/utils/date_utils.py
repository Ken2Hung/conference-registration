"""Date and time utility functions."""
from datetime import datetime
from typing import Tuple


def parse_date(date_str: str) -> datetime:
    """
    Parse date string in YYYY-MM-DD format.

    Args:
        date_str: Date string (e.g., "2025-11-15")

    Returns:
        datetime object

    Raises:
        ValueError: If date format is invalid
    """
    return datetime.strptime(date_str, "%Y-%m-%d")


def parse_time(time_str: str) -> Tuple[datetime, datetime]:
    """
    Parse time range string in HH:MM-HH:MM format.

    Args:
        time_str: Time range string (e.g., "14:00-16:00")

    Returns:
        Tuple of (start_time, end_time) as datetime.time objects

    Raises:
        ValueError: If time format is invalid
    """
    try:
        start_str, end_str = time_str.split("-")
        start_time = datetime.strptime(start_str.strip(), "%H:%M").time()
        end_time = datetime.strptime(end_str.strip(), "%H:%M").time()
        return (start_time, end_time)
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Invalid time format: {time_str}") from e


def compare_to_now(date_str: str, time_str: str) -> bool:
    """
    Compare session date/time to current date/time.

    Args:
        date_str: Date in YYYY-MM-DD format
        time_str: Time range in HH:MM-HH:MM format

    Returns:
        True if session start time is in the past, False otherwise
    """
    return is_past_datetime(date_str, time_str)


def is_past_datetime(date_str: str, time_str: str) -> bool:
    """
    Check if session date/time has passed.

    Args:
        date_str: Date in YYYY-MM-DD format
        time_str: Time range in HH:MM-HH:MM format (uses start time)

    Returns:
        True if start datetime is before now, False otherwise
    """
    try:
        start_time_str = time_str.split("-")[0].strip()
        session_datetime = datetime.strptime(
            f"{date_str} {start_time_str}",
            "%Y-%m-%d %H:%M"
        )
        return session_datetime < datetime.now()
    except (ValueError, IndexError):
        return False
