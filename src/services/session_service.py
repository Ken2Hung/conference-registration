"""Session management service with caching."""
import os
from typing import List, Optional, Dict, Any, Tuple
from src.models.session import Session
from src.models.speaker import Speaker
from src.models.registrant import Registrant
from src.services.storage_service import load_json, save_json, lock_file
from src.utils.exceptions import SessionNotFoundError
from src.utils.validation import validate_session

# 資料檔案路徑
SESSIONS_FILE = "data/sessions.json"

# 快取變數
_sessions_cache: Optional[List[Session]] = None


def _clear_cache():
    """清除議程快取。"""
    global _sessions_cache
    _sessions_cache = None


def get_all_sessions() -> List[Session]:
    """
    載入所有議程。

    Returns:
        List[Session]: 所有議程列表

    Raises:
        FileNotFoundError: 如果資料檔案不存在
        json.JSONDecodeError: 如果 JSON 格式錯誤
    """
    global _sessions_cache

    if _sessions_cache is not None:
        return _sessions_cache

    data = load_json(SESSIONS_FILE)
    sessions = []

    for session_data in data.get("sessions", []):
        speaker_data = session_data.get("speaker", {})
        speaker = Speaker(
            name=speaker_data["name"],
            photo=speaker_data["photo"],
            bio=speaker_data["bio"]
        )

        # Parse registrants (defaults to empty list for backward compatibility)
        registrants_data = session_data.get("registrants", [])
        registrants = [
            Registrant(
                name=reg["name"],
                registered_at=reg["registered_at"]
            )
            for reg in registrants_data
        ]

        session = Session(
            id=session_data["id"],
            title=session_data["title"],
            description=session_data["description"],
            date=session_data["date"],
            time=session_data["time"],
            location=session_data["location"],
            level=session_data["level"],
            tags=session_data["tags"],
            learning_outcomes=session_data["learning_outcomes"],
            capacity=session_data["capacity"],
            registered=session_data["registered"],
            speaker=speaker,
            registrants=registrants,
            registration_start_date=session_data.get("registration_start_date")
        )

        sessions.append(session)

    _sessions_cache = sessions
    return sessions


def get_past_sessions(limit: int = 5) -> List[Session]:
    """
    取得過去的議程。

    Args:
        limit: 最多回傳幾筆（預設 5）

    Returns:
        List[Session]: 過去的議程列表，按日期降序排列（最新的在前）
    """
    all_sessions = get_all_sessions()
    past_sessions = [s for s in all_sessions if s.is_past()]

    # 按日期降序排序（最新的在前）
    past_sessions.sort(key=lambda s: s.date, reverse=True)

    return past_sessions[:limit]


def get_upcoming_sessions(limit: int = 5) -> List[Session]:
    """
    取得即將到來的議程。

    Args:
        limit: 最多回傳幾筆（預設 5）

    Returns:
        List[Session]: 未來的議程列表，按日期升序排列（最早的在前）
    """
    all_sessions = get_all_sessions()
    upcoming_sessions = [s for s in all_sessions if s.is_upcoming()]

    # 按日期升序排序（最早的在前）
    upcoming_sessions.sort(key=lambda s: s.date)

    return upcoming_sessions[:limit]


def get_session_by_id(session_id: str) -> Optional[Session]:
    """
    根據 ID 取得議程。

    Args:
        session_id: 議程 ID

    Returns:
        Session: 找到的議程，若不存在則回傳 None
    """
    all_sessions = get_all_sessions()

    for session in all_sessions:
        if session.id == session_id:
            return session

    return None


def register_for_session(session_id: str) -> Tuple[bool, str]:
    """
    為議程報名。

    Args:
        session_id: 議程 ID

    Returns:
        Tuple[bool, str]: (成功與否, 訊息)

    Raises:
        SessionNotFoundError: 如果議程不存在
    """
    session = get_session_by_id(session_id)

    if session is None:
        raise SessionNotFoundError(f"找不到議程: {session_id}")

    # 檢查議程是否已過期
    if session.is_past():
        return False, "此議程已過期，無法報名"

    # 檢查是否已額滿
    if session.is_full():
        return False, "此議程已額滿，無法報名"

    # 使用檔案鎖定確保資料一致性
    with lock_file(SESSIONS_FILE):
        data = load_json(SESSIONS_FILE)

        # 找到對應的議程並增加報名人數
        for session_data in data["sessions"]:
            if session_data["id"] == session_id:
                # 再次檢查容量（防止競爭條件）
                if session_data["registered"] >= session_data["capacity"]:
                    return False, "此議程已額滿，無法報名"

                session_data["registered"] += 1
                break

        # 儲存更新後的資料
        save_json(SESSIONS_FILE, data, backup=True)

    # 清除快取以載入最新資料
    _clear_cache()

    return True, "報名成功！"


def create_session(session_data: Dict[str, Any]) -> str:
    """
    建立新議程。

    Args:
        session_data: 議程資料字典（不含 id 和 registered）

    Returns:
        str: 新建立的議程 ID

    Raises:
        ValueError: 如果資料驗證失敗
    """
    # 載入現有議程
    data = load_json(SESSIONS_FILE)
    sessions = data.get("sessions", [])

    # 產生新的 ID（找出最大編號並加 1）
    max_id = 0
    for session in sessions:
        session_id = session.get("id", "")
        if session_id.startswith("session_"):
            try:
                num = int(session_id.split("_")[1])
                max_id = max(max_id, num)
            except (IndexError, ValueError):
                pass

    new_id = f"session_{max_id + 1:03d}"

    # 建立完整的議程資料
    complete_session_data = {
        "id": new_id,
        "registered": 0,
        **session_data
    }

    # 驗證議程資料
    validate_session(complete_session_data)

    # 新增到列表
    sessions.append(complete_session_data)
    data["sessions"] = sessions

    # 儲存檔案
    with lock_file(SESSIONS_FILE):
        save_json(SESSIONS_FILE, data, backup=True)

    # 清除快取
    _clear_cache()

    return new_id


def update_session(session_id: str, updates: Dict[str, Any]) -> bool:
    """
    更新議程資訊。

    Args:
        session_id: 議程 ID
        updates: 要更新的欄位字典

    Returns:
        bool: 更新是否成功

    Raises:
        SessionNotFoundError: 如果議程不存在
    """
    with lock_file(SESSIONS_FILE):
        data = load_json(SESSIONS_FILE)
        sessions = data.get("sessions", [])

        # 找到對應的議程
        session_found = False
        for session_data in sessions:
            if session_data["id"] == session_id:
                session_found = True

                # 更新欄位（不允許更改 ID）
                for key, value in updates.items():
                    if key != "id":  # ID 不可變更
                        session_data[key] = value

                # 驗證更新後的議程
                validate_session(session_data)

                break

        if not session_found:
            raise SessionNotFoundError(f"找不到議程: {session_id}")

        # 儲存更新
        save_json(SESSIONS_FILE, data, backup=True)

    # 清除快取
    _clear_cache()

    return True


def delete_session(session_id: str) -> bool:
    """
    刪除議程。

    Args:
        session_id: 議程 ID

    Returns:
        bool: 刪除是否成功
    """
    with lock_file(SESSIONS_FILE):
        data = load_json(SESSIONS_FILE)
        sessions = data.get("sessions", [])

        # 過濾掉要刪除的議程
        original_count = len(sessions)
        sessions = [s for s in sessions if s.get("id") != session_id]
        new_count = len(sessions)

        # 如果數量沒有改變，表示找不到該議程
        if original_count == new_count:
            return False

        data["sessions"] = sessions

        # 儲存更新
        save_json(SESSIONS_FILE, data, backup=True)

    # 清除快取
    _clear_cache()

    return True

def get_session_registrants(session_id: str) -> List[Registrant]:
    """
    Get list of registrants for a session.

    Args:
        session_id: Session identifier

    Returns:
        List of Registrant objects (ordered by registration time)
        Empty list if session not found or has no registrants
    """
    session = get_session_by_id(session_id)
    if session is None:
        return []

    return session.registrants
