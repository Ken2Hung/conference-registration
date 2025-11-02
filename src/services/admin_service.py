"""Admin service for authentication and session state management."""
import os
from pathlib import Path
from threading import Lock
import streamlit as st
from typing import Tuple


_ENV_LOADED = False
_ENV_LOCK = Lock()


def _load_admin_env() -> None:
    """Load admin credentials from .env file if present."""
    global _ENV_LOADED

    if _ENV_LOADED:
        return

    with _ENV_LOCK:
        if _ENV_LOADED:
            return

        env_path = Path(".env")
        if env_path.exists():
            for raw_line in env_path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue

                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"\'')

                if key in {"ADMIN_USERNAME", "ADMIN_PASSWORD"} and key not in os.environ:
                    os.environ[key] = value

        _ENV_LOADED = True


def authenticate_admin(username: str, password: str) -> bool:
    """
    Authenticate admin credentials.

    Args:
        username: Admin username
        password: Admin password

    Returns:
        True if credentials valid, False otherwise

    Behavior:
        - Loads credentials from environment variables
        - Compares with provided values
        - For MVP: plain-text comparison
        - Future: use bcrypt for hashing

    Security:
        - No timing attack protection (acceptable for MVP)
        - Single admin user only
    """
    _load_admin_env()

    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "")

    return username == admin_username and password == admin_password


def is_admin_authenticated() -> bool:
    """
    Check if admin is authenticated in current session.

    Returns:
        True if st.session_state['admin_authenticated'] is True

    Behavior:
        - Reads from Streamlit session state
        - Returns False if key doesn't exist
    """
    return st.session_state.get("admin_authenticated", False)


def login_admin(username: str, password: str) -> Tuple[bool, str]:
    """
    Log in admin user.

    Args:
        username: Admin username
        password: Admin password

    Returns:
        Tuple of (success: bool, message: str)
        - (True, "登入成功") on success
        - (False, "帳號或密碼錯誤") on failure
    """
    if authenticate_admin(username, password):
        st.session_state["admin_authenticated"] = True
        return True, "登入成功"
    else:
        return False, "帳號或密碼錯誤"


def logout_admin() -> None:
    """
    Log out admin user.

    Behavior:
        - Clears st.session_state['admin_authenticated']
        - May clear other admin-related session state
    """
    if "admin_authenticated" in st.session_state:
        del st.session_state["admin_authenticated"]
