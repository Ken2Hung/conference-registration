"""Session data model."""
import re
from dataclasses import dataclass
from datetime import datetime
from typing import List
from src.models.speaker import Speaker


@dataclass
class Session:
    """Conference session with registration information."""

    id: str
    title: str
    description: str
    date: str
    time: str
    location: str
    level: str
    tags: List[str]
    learning_outcomes: str
    capacity: int
    registered: int
    speaker: Speaker

    def __post_init__(self):
        """Validate session data after initialization."""
        if not self.id or not self.id.strip():
            raise ValueError("Session ID cannot be empty")

        if not re.match(r"^session_\d{3}$", self.id):
            raise ValueError(f"Session ID must match format 'session_XXX': {self.id}")

        if not self.title or not self.title.strip():
            raise ValueError("Title cannot be empty")

        if not self.description or not self.description.strip():
            raise ValueError("Description cannot be empty")

        if self.level not in ["初", "中", "高"]:
            raise ValueError(f"Level must be one of ['初', '中', '高'], got: {self.level}")

        if self.capacity <= 0:
            raise ValueError("Capacity must be positive")

        if self.registered < 0:
            raise ValueError("Registered count cannot be negative")

        if self.registered > self.capacity:
            raise ValueError(f"Registered count ({self.registered}) cannot exceed capacity ({self.capacity})")

    def is_full(self) -> bool:
        """Check if session is at capacity."""
        return self.registered >= self.capacity

    def is_past(self) -> bool:
        """Check if session date/time has passed."""
        try:
            start_time_str = self.time.split("-")[0].strip()
            session_datetime = datetime.strptime(
                f"{self.date} {start_time_str}",
                "%Y-%m-%d %H:%M"
            )
            return session_datetime < datetime.now()
        except (ValueError, IndexError):
            return False

    def is_upcoming(self) -> bool:
        """Check if session is in the future."""
        return not self.is_past()

    def status(self) -> str:
        """
        Get session status.

        Returns:
            'expired' if past, 'full' if at capacity, 'available' otherwise
        """
        if self.is_past():
            return "expired"
        elif self.is_full():
            return "full"
        else:
            return "available"

    def registration_percentage(self) -> float:
        """Calculate registration percentage (0-100)."""
        if self.capacity == 0:
            return 0.0
        return (self.registered / self.capacity) * 100.0
