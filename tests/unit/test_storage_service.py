"""Unit tests for StorageService."""
import pytest
import json
import os
import tempfile
from pathlib import Path
from src.services.storage_service import load_json, save_json, lock_file


@pytest.fixture
def temp_json_file():
    """Create a temporary JSON file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        test_data = {"test": "data", "number": 42}
        json.dump(test_data, f, ensure_ascii=False)
        temp_path = f.name

    yield temp_path

    if os.path.exists(temp_path):
        os.remove(temp_path)

    backup_path = f"{temp_path}.backup"
    if os.path.exists(backup_path):
        os.remove(backup_path)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_path = tempfile.mkdtemp()
    yield temp_path

    import shutil
    if os.path.exists(temp_path):
        shutil.rmtree(temp_path)


class TestLoadJson:
    """Test load_json function."""

    def test_load_valid_json(self, temp_json_file):
        """Test loading valid JSON file."""
        data = load_json(temp_json_file)
        assert data["test"] == "data"
        assert data["number"] == 42

    def test_load_json_with_utf8(self, temp_dir):
        """Test loading JSON with UTF-8 Chinese characters."""
        file_path = os.path.join(temp_dir, "chinese.json")
        test_data = {"title": "中文標題", "description": "這是測試"}

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, ensure_ascii=False)

        data = load_json(file_path)
        assert data["title"] == "中文標題"
        assert data["description"] == "這是測試"

    def test_load_nonexistent_file_raises_error(self):
        """Test loading non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="File not found"):
            load_json("/nonexistent/path/file.json")

    def test_load_malformed_json_raises_error(self, temp_dir):
        """Test loading malformed JSON raises JSONDecodeError."""
        file_path = os.path.join(temp_dir, "malformed.json")

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("{invalid json")

        with pytest.raises(json.JSONDecodeError):
            load_json(file_path)

    def test_load_empty_file_raises_error(self, temp_dir):
        """Test loading empty file raises JSONDecodeError."""
        file_path = os.path.join(temp_dir, "empty.json")

        with open(file_path, 'w', encoding='utf-8') as f:
            pass

        with pytest.raises(json.JSONDecodeError):
            load_json(file_path)


class TestSaveJson:
    """Test save_json function."""

    def test_save_valid_json(self, temp_dir):
        """Test saving valid JSON data."""
        file_path = os.path.join(temp_dir, "test.json")
        test_data = {"key": "value", "number": 123}

        save_json(file_path, test_data, backup=False)

        assert os.path.exists(file_path)

        with open(file_path, 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)

        assert loaded_data == test_data

    def test_save_json_with_utf8(self, temp_dir):
        """Test saving JSON with UTF-8 Chinese characters."""
        file_path = os.path.join(temp_dir, "chinese.json")
        test_data = {"title": "中文標題", "tags": ["Python", "測試"]}

        save_json(file_path, test_data, backup=False)

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        assert "中文標題" in content
        assert "測試" in content

    def test_save_creates_directory(self, temp_dir):
        """Test save_json creates parent directory if needed."""
        file_path = os.path.join(temp_dir, "subdir", "test.json")
        test_data = {"test": "data"}

        save_json(file_path, test_data, backup=False)

        assert os.path.exists(file_path)

    def test_save_with_backup(self, temp_dir):
        """Test save_json creates backup when enabled."""
        file_path = os.path.join(temp_dir, "test.json")
        backup_path = f"{file_path}.backup"

        original_data = {"version": 1}
        save_json(file_path, original_data, backup=False)

        updated_data = {"version": 2}
        save_json(file_path, updated_data, backup=True)

        assert os.path.exists(backup_path)

        with open(backup_path, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)

        assert backup_data["version"] == 1

    def test_save_without_backup(self, temp_dir):
        """Test save_json does not create backup when disabled."""
        file_path = os.path.join(temp_dir, "test.json")
        backup_path = f"{file_path}.backup"

        original_data = {"version": 1}
        save_json(file_path, original_data, backup=False)

        updated_data = {"version": 2}
        save_json(file_path, updated_data, backup=False)

        assert not os.path.exists(backup_path)

    def test_save_overwrites_existing_file(self, temp_dir):
        """Test save_json overwrites existing file."""
        file_path = os.path.join(temp_dir, "test.json")

        save_json(file_path, {"version": 1}, backup=False)
        save_json(file_path, {"version": 2}, backup=False)

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert data["version"] == 2

    def test_save_json_formatted_with_indent(self, temp_dir):
        """Test save_json formats JSON with indentation."""
        file_path = os.path.join(temp_dir, "test.json")
        test_data = {"key": "value"}

        save_json(file_path, test_data, backup=False)

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        assert "\n" in content
        assert "  " in content


class TestLockFile:
    """Test lock_file context manager."""

    def test_lock_file_basic(self, temp_json_file):
        """Test basic file locking."""
        with lock_file(temp_json_file):
            data = load_json(temp_json_file)
            assert "test" in data

    def test_lock_file_releases_lock(self, temp_json_file):
        """Test lock is released after context exits."""
        with lock_file(temp_json_file):
            pass

        with lock_file(temp_json_file):
            pass

    def test_lock_nonexistent_file_raises_error(self):
        """Test locking non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Cannot lock non-existent file"):
            with lock_file("/nonexistent/file.json"):
                pass

    def test_lock_protects_critical_section(self, temp_dir):
        """Test lock protects critical section during read-modify-write."""
        file_path = os.path.join(temp_dir, "counter.json")
        save_json(file_path, {"count": 0}, backup=False)

        with lock_file(file_path):
            data = load_json(file_path)
            data["count"] += 1
            save_json(file_path, data, backup=False)

        final_data = load_json(file_path)
        assert final_data["count"] == 1


class TestIntegration:
    """Integration tests for storage operations."""

    def test_full_workflow(self, temp_dir):
        """Test complete workflow: create, read, update, backup."""
        file_path = os.path.join(temp_dir, "sessions.json")

        initial_data = {
            "sessions": [
                {"id": "session_001", "title": "Test Session", "capacity": 50}
            ]
        }
        save_json(file_path, initial_data, backup=False)

        loaded_data = load_json(file_path)
        assert len(loaded_data["sessions"]) == 1

        loaded_data["sessions"].append(
            {"id": "session_002", "title": "Another Session", "capacity": 30}
        )
        save_json(file_path, loaded_data, backup=True)

        updated_data = load_json(file_path)
        assert len(updated_data["sessions"]) == 2

        backup_path = f"{file_path}.backup"
        backup_data = load_json(backup_path)
        assert len(backup_data["sessions"]) == 1

    def test_utf8_round_trip(self, temp_dir):
        """Test UTF-8 data survives save and load."""
        file_path = os.path.join(temp_dir, "chinese.json")

        original_data = {
            "sessions": [
                {
                    "id": "session_001",
                    "title": "Python 網頁爬蟲入門",
                    "description": "學習使用 Python 進行網頁爬蟲",
                    "tags": ["Python", "爬蟲", "數據"]
                }
            ]
        }

        save_json(file_path, original_data, backup=False)
        loaded_data = load_json(file_path)

        assert loaded_data["sessions"][0]["title"] == "Python 網頁爬蟲入門"
        assert "爬蟲" in loaded_data["sessions"][0]["tags"]

    def test_concurrent_write_protection(self, temp_dir):
        """Test file locking prevents corruption during concurrent access."""
        file_path = os.path.join(temp_dir, "shared.json")
        save_json(file_path, {"value": 0}, backup=False)

        with lock_file(file_path):
            data = load_json(file_path)
            data["value"] = 100
            save_json(file_path, data, backup=False)

        final_data = load_json(file_path)
        assert final_data["value"] == 100
