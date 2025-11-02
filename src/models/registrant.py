"""Registrant data model for conference registration."""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Registrant:
    """Individual who registered for a session."""

    name: str
    registered_at: str  # ISO 8601 format

    def __post_init__(self):
        """Validate registrant data."""
        # Validate name
        if not self.name or not self.name.strip():
            raise ValueError("Name cannot be empty")
        if len(self.name) > 50:
            raise ValueError("Name cannot exceed 50 characters")

        # Validate ISO 8601 timestamp format
        try:
            datetime.fromisoformat(self.registered_at.replace('Z', '+00:00'))
        except ValueError as e:
            raise ValueError(f"Invalid timestamp format: {self.registered_at}") from e
