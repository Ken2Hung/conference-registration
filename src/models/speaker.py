"""Speaker data model."""
from dataclasses import dataclass


@dataclass
class Speaker:
    """Speaker information for a session."""

    name: str
    photo: str
    bio: str

    def __post_init__(self):
        """Validate speaker data after initialization."""
        if not self.name or not self.name.strip():
            raise ValueError("Speaker name cannot be empty")

        if not self.photo or not self.photo.strip():
            raise ValueError("Speaker photo path cannot be empty")

        if not self.bio or not self.bio.strip():
            raise ValueError("Speaker bio cannot be empty")
