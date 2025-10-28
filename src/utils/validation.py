"""Data validation utilities."""
import re
from datetime import datetime
from typing import Any, Dict, List


def validate_session(session_data: Dict[str, Any]) -> bool:
    """
    Validate session data dictionary against all rules.

    Args:
        session_data: Dictionary containing session fields

    Returns:
        True if valid

    Raises:
        ValueError: If validation fails with detailed message
    """
    if not isinstance(session_data, dict):
        raise ValueError("Session data must be a dictionary")

    required_fields = [
        "id", "title", "description", "date", "time",
        "location", "level", "tags", "learning_outcomes",
        "capacity", "registered", "speaker"
    ]

    for field in required_fields:
        if field not in session_data:
            raise ValueError(f"Missing required field: {field}")

    if not re.match(r"^session_\d{3}$", session_data["id"]):
        raise ValueError(f"Invalid session ID format: {session_data['id']}")

    if not session_data["title"] or not session_data["title"].strip():
        raise ValueError("Title cannot be empty")

    if not session_data["description"] or not session_data["description"].strip():
        raise ValueError("Description cannot be empty")

    validate_date_format(session_data["date"])
    validate_time_format(session_data["time"])

    if not session_data["location"] or not session_data["location"].strip():
        raise ValueError("Location cannot be empty")

    valid_levels = ["初", "中", "高"]
    if session_data["level"] not in valid_levels:
        raise ValueError(f"Level must be one of {valid_levels}")

    if not isinstance(session_data["tags"], list) or len(session_data["tags"]) == 0:
        raise ValueError("Tags must be a non-empty list")

    for tag in session_data["tags"]:
        if not isinstance(tag, str) or not tag.strip():
            raise ValueError("All tags must be non-empty strings")

    if not session_data["learning_outcomes"] or not session_data["learning_outcomes"].strip():
        raise ValueError("Learning outcomes cannot be empty")

    capacity = session_data["capacity"]
    if not isinstance(capacity, int) or capacity <= 0:
        raise ValueError("Capacity must be a positive integer")

    registered = session_data["registered"]
    if not isinstance(registered, int) or registered < 0:
        raise ValueError("Registered count must be a non-negative integer")

    if registered > capacity:
        raise ValueError(f"Registered count ({registered}) cannot exceed capacity ({capacity})")

    validate_speaker(session_data["speaker"])

    return True


def validate_speaker(speaker_data: Dict[str, Any]) -> bool:
    """
    Validate speaker data dictionary.

    Args:
        speaker_data: Dictionary containing speaker fields

    Returns:
        True if valid

    Raises:
        ValueError: If validation fails with detailed message
    """
    if not isinstance(speaker_data, dict):
        raise ValueError("Speaker data must be a dictionary")

    required_fields = ["name", "photo", "bio"]

    for field in required_fields:
        if field not in speaker_data:
            raise ValueError(f"Missing required speaker field: {field}")

    if not speaker_data["name"] or not speaker_data["name"].strip():
        raise ValueError("Speaker name cannot be empty")

    if not speaker_data["photo"] or not speaker_data["photo"].strip():
        raise ValueError("Speaker photo path cannot be empty")

    photo_path = speaker_data["photo"]
    if not (photo_path.endswith(('.jpg', '.jpeg', '.png', '.gif')) or
            photo_path.startswith('http://') or
            photo_path.startswith('https://')):
        raise ValueError(f"Invalid photo path format: {photo_path}")

    if not speaker_data["bio"] or not speaker_data["bio"].strip():
        raise ValueError("Speaker bio cannot be empty")

    return True


def validate_date_format(date_str: str) -> bool:
    """
    Validate date string in YYYY-MM-DD format.

    Args:
        date_str: Date string to validate

    Returns:
        True if valid

    Raises:
        ValueError: If date format is invalid
    """
    if not isinstance(date_str, str):
        raise ValueError("Date must be a string")

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        raise ValueError(f"Date must be in YYYY-MM-DD format: {date_str}")

    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as e:
        raise ValueError(f"Invalid date value: {date_str} - {str(e)}")

    return True


def validate_time_format(time_str: str) -> bool:
    """
    Validate time range string in HH:MM-HH:MM format.

    Args:
        time_str: Time range string to validate

    Returns:
        True if valid

    Raises:
        ValueError: If time format is invalid
    """
    if not isinstance(time_str, str):
        raise ValueError("Time must be a string")

    if not re.match(r"^\d{2}:\d{2}-\d{2}:\d{2}$", time_str):
        raise ValueError(f"Time must be in HH:MM-HH:MM format: {time_str}")

    try:
        parts = time_str.split("-")
        if len(parts) != 2:
            raise ValueError(f"Time range must have start and end times: {time_str}")

        start_str = parts[0].strip()
        end_str = parts[1].strip()

        start_time = datetime.strptime(start_str, "%H:%M")
        end_time = datetime.strptime(end_str, "%H:%M")

        if start_time >= end_time:
            raise ValueError(f"Start time must be before end time: {time_str}")

    except ValueError as e:
        if "does not match format" in str(e):
            raise ValueError(f"Invalid time value: {time_str}")
        raise

    return True
