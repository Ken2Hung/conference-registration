"""Admin data model."""
from dataclasses import dataclass


@dataclass
class Admin:
    """Administrator credentials."""

    username: str
    password: str

    def __post_init__(self):
        """Validate admin data after initialization."""
        if not self.username or len(self.username) < 3:
            raise ValueError("Username must be at least 3 characters")

        if not self.password or len(self.password) < 6:
            raise ValueError("Password must be at least 6 characters")
