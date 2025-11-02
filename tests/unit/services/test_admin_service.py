"""Unit tests for admin_service."""
import pytest
from unittest.mock import patch, MagicMock
import streamlit as st

from src.services.admin_service import (
    authenticate_admin,
    is_admin_authenticated,
    login_admin,
    logout_admin
)


class TestAuthenticateAdmin:
    """Test authenticate_admin function."""

    def test_authenticate_with_correct_credentials(self, monkeypatch):
        """Test authentication succeeds with correct credentials."""
        monkeypatch.setenv("ADMIN_USERNAME", "testadmin")
        monkeypatch.setenv("ADMIN_PASSWORD", "testpass")

        result = authenticate_admin("testadmin", "testpass")
        assert result is True

    def test_authenticate_with_wrong_username(self, monkeypatch):
        """Test authentication fails with wrong username."""
        monkeypatch.setenv("ADMIN_USERNAME", "testadmin")
        monkeypatch.setenv("ADMIN_PASSWORD", "testpass")

        result = authenticate_admin("wronguser", "testpass")
        assert result is False

    def test_authenticate_with_wrong_password(self, monkeypatch):
        """Test authentication fails with wrong password."""
        monkeypatch.setenv("ADMIN_USERNAME", "testadmin")
        monkeypatch.setenv("ADMIN_PASSWORD", "testpass")

        result = authenticate_admin("testadmin", "wrongpass")
        assert result is False

    def test_authenticate_with_empty_credentials(self, monkeypatch):
        """Test authentication fails with empty credentials."""
        monkeypatch.setenv("ADMIN_USERNAME", "testadmin")
        monkeypatch.setenv("ADMIN_PASSWORD", "testpass")

        result = authenticate_admin("", "")
        assert result is False

    def test_authenticate_uses_default_username(self, monkeypatch):
        """Test authentication uses default username if not set."""
        monkeypatch.delenv("ADMIN_USERNAME", raising=False)
        monkeypatch.setenv("ADMIN_PASSWORD", "testpass")

        result = authenticate_admin("admin", "testpass")
        assert result is True


class TestIsAdminAuthenticated:
    """Test is_admin_authenticated function."""

    @patch('src.services.admin_service.st')
    def test_returns_true_when_authenticated(self, mock_st):
        """Test returns True when admin is authenticated."""
        mock_st.session_state.get.return_value = True

        result = is_admin_authenticated()
        assert result is True
        mock_st.session_state.get.assert_called_once_with("admin_authenticated", False)

    @patch('src.services.admin_service.st')
    def test_returns_false_when_not_authenticated(self, mock_st):
        """Test returns False when admin is not authenticated."""
        mock_st.session_state.get.return_value = False

        result = is_admin_authenticated()
        assert result is False

    @patch('src.services.admin_service.st')
    def test_returns_false_when_key_not_exists(self, mock_st):
        """Test returns False when session state key doesn't exist."""
        mock_st.session_state.get.return_value = False

        result = is_admin_authenticated()
        assert result is False


class TestLoginAdmin:
    """Test login_admin function."""

    @patch('src.services.admin_service.authenticate_admin')
    @patch('src.services.admin_service.st')
    def test_login_success(self, mock_st, mock_auth):
        """Test successful login."""
        mock_auth.return_value = True
        mock_st.session_state = {}

        success, message = login_admin("testadmin", "testpass")

        assert success is True
        assert message == "登入成功"
        assert mock_st.session_state["admin_authenticated"] is True

    @patch('src.services.admin_service.authenticate_admin')
    @patch('src.services.admin_service.st')
    def test_login_failure(self, mock_st, mock_auth):
        """Test failed login."""
        mock_auth.return_value = False
        mock_st.session_state = {}

        success, message = login_admin("wronguser", "wrongpass")

        assert success is False
        assert message == "帳號或密碼錯誤"
        assert "admin_authenticated" not in mock_st.session_state


class TestLogoutAdmin:
    """Test logout_admin function."""

    @patch('src.services.admin_service.st')
    def test_logout_clears_session_state(self, mock_st):
        """Test logout clears admin_authenticated from session state."""
        mock_st.session_state = {"admin_authenticated": True}

        logout_admin()

        assert "admin_authenticated" not in mock_st.session_state

    @patch('src.services.admin_service.st')
    def test_logout_when_not_authenticated(self, mock_st):
        """Test logout works even when not authenticated."""
        mock_st.session_state = {}

        # Should not raise exception
        logout_admin()

        assert "admin_authenticated" not in mock_st.session_state
