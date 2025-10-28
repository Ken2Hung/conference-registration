"""Low-level JSON file I/O operations with locking."""
import json
import os
import shutil
import tempfile
from contextlib import contextmanager
from typing import Any, Dict
import sys

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl


def load_json(file_path: str) -> Dict[str, Any]:
    """
    Load and parse JSON file with UTF-8 encoding.

    Args:
        file_path: Path to JSON file

    Returns:
        dict: Parsed JSON content

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If JSON is malformed
        PermissionError: If file not readable
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except PermissionError:
        raise PermissionError(f"Cannot read file: {file_path}")
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Malformed JSON in {file_path}: {e.msg}",
            e.doc,
            e.pos
        )


def save_json(file_path: str, data: Dict[str, Any], backup: bool = True) -> None:
    """
    Save data to JSON file atomically with UTF-8 encoding.

    Args:
        file_path: Path to JSON file
        data: Dictionary to save
        backup: If True, create backup before overwriting (default True)

    Returns:
        None

    Raises:
        PermissionError: If file not writable
        IOError: If write operation fails
    """
    dir_path = os.path.dirname(file_path)
    if dir_path and not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)

    if backup and os.path.exists(file_path):
        backup_path = f"{file_path}.backup"
        try:
            shutil.copy2(file_path, backup_path)
        except (IOError, PermissionError) as e:
            raise IOError(f"Failed to create backup: {e}")

    temp_fd, temp_path = tempfile.mkstemp(
        dir=dir_path if dir_path else ".",
        prefix=".tmp_",
        suffix=".json"
    )

    try:
        with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())

        if sys.platform == "win32":
            if os.path.exists(file_path):
                os.remove(file_path)
            os.rename(temp_path, file_path)
        else:
            os.rename(temp_path, file_path)

    except Exception as e:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        raise IOError(f"Failed to write file {file_path}: {e}")


@contextmanager
def lock_file(file_path: str):
    """
    Context manager for file locking.

    Args:
        file_path: Path to file to lock

    Yields:
        None

    Usage:
        with lock_file('data/sessions.json'):
            # Critical section - file is locked
            data = load_json('data/sessions.json')
            data['sessions'].append(new_session)
            save_json('data/sessions.json', data)

    Raises:
        TimeoutError: If unable to acquire lock within timeout
        FileNotFoundError: If file doesn't exist
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Cannot lock non-existent file: {file_path}")

    lock_fd = open(file_path, "r+")

    try:
        if sys.platform == "win32":
            try:
                msvcrt.locking(lock_fd.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                raise TimeoutError(f"Could not acquire lock on {file_path}")
        else:
            try:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except (IOError, OSError):
                raise TimeoutError(f"Could not acquire lock on {file_path}")

        yield

    finally:
        if sys.platform == "win32":
            try:
                msvcrt.locking(lock_fd.fileno(), msvcrt.LK_UNLCK, 1)
            except:
                pass
        else:
            try:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
            except:
                pass

        lock_fd.close()
