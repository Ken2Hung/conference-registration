"""Low-level JSON file I/O operations with locking."""
import json
import os
import shutil
import tempfile
import time
from contextlib import contextmanager
from typing import Any, Dict
import sys

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl


def load_json(file_path: str, retry_count: int = 3, retry_delay: float = 0.1) -> Dict[str, Any]:
    """
    Load and parse JSON file with UTF-8 encoding.

    Args:
        file_path: Path to JSON file
        retry_count: Number of retry attempts for permission errors (default: 3)
        retry_delay: Delay in seconds between retries (default: 0.1)

    Returns:
        dict: Parsed JSON content

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If JSON is malformed
        PermissionError: If file not readable after retries
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    last_error = None
    for attempt in range(retry_count):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except PermissionError as e:
            last_error = e
            if attempt < retry_count - 1:
                time.sleep(retry_delay)
                continue
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Malformed JSON in {file_path}: {e.msg}",
                e.doc,
                e.pos
            )
    
    raise PermissionError(f"Cannot read file after {retry_count} attempts: {file_path}")


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

        # Windows requires more careful file replacement
        if sys.platform == "win32":
            retry_count = 3
            for attempt in range(retry_count):
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    os.rename(temp_path, file_path)
                    break
                except PermissionError:
                    if attempt < retry_count - 1:
                        time.sleep(0.1)
                        continue
                    raise
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
def lock_file(file_path: str, timeout: float = 5.0):
    """
    Context manager for file locking with retry mechanism.

    Args:
        file_path: Path to file to lock
        timeout: Maximum seconds to wait for lock acquisition (default: 5.0)

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

    # For Windows, use a lock file approach to avoid file handle conflicts
    if sys.platform == "win32":
        lock_file_path = f"{file_path}.lock"
        start_time = time.time()
        lock_fd = None
        
        while True:
            try:
                # Try to create an exclusive lock file
                lock_fd = os.open(
                    lock_file_path,
                    os.O_CREAT | os.O_EXCL | os.O_RDWR
                )
                break
            except FileExistsError:
                # Lock file exists, wait and retry
                if time.time() - start_time > timeout:
                    raise TimeoutError(f"Could not acquire lock on {file_path} within {timeout}s")
                time.sleep(0.05)
        
        try:
            yield
        finally:
            if lock_fd is not None:
                try:
                    os.close(lock_fd)
                except:
                    pass
            try:
                os.remove(lock_file_path)
            except:
                pass
    else:
        # Unix/Linux file locking
        lock_fd = open(file_path, "r+")
        try:
            start_time = time.time()
            while True:
                try:
                    fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except (IOError, OSError):
                    if time.time() - start_time > timeout:
                        raise TimeoutError(f"Could not acquire lock on {file_path} within {timeout}s")
                    time.sleep(0.05)

            yield

        finally:
            try:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
            except:
                pass
            lock_fd.close()
