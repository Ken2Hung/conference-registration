"""Registration service for handling session registrations."""
import logging
from datetime import datetime
from typing import Tuple

from src.models.registrant import Registrant
from src.models.session import Session
from src.services.session_service import (
    get_session_by_id,
    SESSIONS_FILE
)
from src.services.storage_service import load_json, save_json, lock_file
from src.utils.validation import validate_name

logger = logging.getLogger(__name__)


def register_for_session(session_id: str, attendee_name: str) -> Tuple[bool, str]:
    """
    Register an attendee for a session.

    Args:
        session_id: Session to register for
        attendee_name: Attendee's name

    Returns:
        Tuple of (success: bool, message: str)
        - (True, "報名成功") on success
        - (False, "找不到議程") if session not found
        - (False, error_message) on validation or business rule failure

    Behavior:
        - Validates name
        - Checks session availability (not full, not past, not duplicate)
        - Uses file locking for thread-safe registration
        - Records registration with ISO 8601 timestamp
        - Clears session service cache
    """
    # Validate name
    is_valid, error_msg = validate_name(attendee_name)
    if not is_valid:
        return False, error_msg

    # Get session
    session = get_session_by_id(session_id)
    if session is None:
        return False, "找不到議程"

    # Check if can register
    can_register, error_msg = session.can_register(attendee_name)
    if not can_register:
        return False, error_msg

    # Perform registration with file lock
    try:
        with lock_file(SESSIONS_FILE):
            # Reload data from file to get latest state
            data = load_json(SESSIONS_FILE)
            sessions = data.get("sessions", [])

            # Find and update the session
            session_updated = False
            for session_data in sessions:
                if session_data["id"] == session_id:
                    # Create registrant with current timestamp
                    registrant_data = {
                        "name": attendee_name,
                        "registered_at": datetime.now().astimezone().isoformat()
                    }

                    # Add to registrants array
                    if "registrants" not in session_data:
                        session_data["registrants"] = []
                    session_data["registrants"].append(registrant_data)

                    # Sync registered count
                    session_data["registered"] = len(session_data["registrants"])

                    session_updated = True
                    break

            if not session_updated:
                return False, "找不到議程"

            # Save back to file
            save_json(SESSIONS_FILE, data, backup=True)

            # Clear cache to force reload
            from src.services.session_service import _clear_cache
            _clear_cache()

            return True, "報名成功"

    except IOError as e:
        logger.error(f"File operation failed during registration: {e}")
        return False, "系統錯誤，請稍後再試"
    except Exception as e:
        logger.error(f"Unexpected error during registration: {e}")
        return False, "發生未預期的錯誤"


def remove_registrant(session_id: str, registrant_index: int) -> Tuple[bool, str]:
    """Remove a registrant from a session by index."""
    if registrant_index < 0:
        return False, "找不到報名紀錄"

    session = get_session_by_id(session_id)
    if session is None:
        return False, "找不到議程"

    try:
        with lock_file(SESSIONS_FILE):
            data = load_json(SESSIONS_FILE)
            sessions = data.get("sessions", [])

            for session_data in sessions:
                if session_data.get("id") == session_id:
                    registrants = session_data.get("registrants", [])

                    if registrant_index >= len(registrants):
                        return False, "找不到報名紀錄"

                    removed = registrants.pop(registrant_index)
                    session_data["registered"] = len(registrants)

                    save_json(SESSIONS_FILE, data, backup=True)

                    from src.services.session_service import _clear_cache
                    _clear_cache()

                    removed_name = removed.get("name", "報名者")
                    return True, f"已移除 {removed_name}"

            return False, "找不到議程"

    except IOError as e:  # pragma: no cover - filesystem errors rare in tests
        logger.error(f"File operation failed during registrant removal: {e}")
        return False, "系統錯誤，請稍後再試"
    except Exception as e:  # pragma: no cover - defensive logging
        logger.error(f"Unexpected error during registrant removal: {e}")
        return False, "發生未預期的錯誤"
