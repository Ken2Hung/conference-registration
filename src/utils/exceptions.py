"""Custom exception classes."""


class SessionNotFoundError(Exception):
    """Raised when session ID doesn't exist."""
    pass


class ValidationError(Exception):
    """Raised when data fails validation."""
    pass


class FileWriteError(Exception):
    """Raised when unable to write to JSON file."""
    pass


class AuthenticationError(Exception):
    """Raised when login credentials invalid."""
    pass
