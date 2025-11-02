"""Session data model."""
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Tuple
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
    registrants: List['Registrant'] = field(default_factory=list)

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

        # Validate registrants consistency
        if len(self.registrants) != self.registered:
            raise ValueError(
                f"Registrants count ({len(self.registrants)}) must match "
                f"registered count ({self.registered})"
            )

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

    def can_register(self, name: str) -> Tuple[bool, str]:
        """
        Check if name can register.

        Args:
            name: Attendee name to check

        Returns:
            Tuple of (can_register: bool, error_message: str)
            - (True, "") if registration allowed
            - (False, "已額滿") if session is full
            - (False, "已過期") if session has passed
            - (False, "您已報名") if name is duplicate
        """
        from src.utils.validation import normalize_name

        if self.is_full():
            return False, "已額滿"
        if self.is_past():
            return False, "已過期"

        # Check duplicate using normalized comparison
        normalized = normalize_name(name)
        for reg in self.registrants:
            if normalize_name(reg.name) == normalized:
                return False, "您已報名"

        return True, ""

    def add_registrant(self, registrant: 'Registrant') -> None:
        """
        Add registrant and sync registered count.

        Args:
            registrant: Registrant object to add
        """
        self.registrants.append(registrant)
        self.registered = len(self.registrants)

    def get_registrants_names(self) -> List[str]:
        """
        Get list of registrant names in chronological order.

        Returns:
            List of names (ordered by registration time)
        """
        return [r.name for r in self.registrants]
