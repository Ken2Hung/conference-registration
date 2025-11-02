"""Unit tests for Session model."""
import pytest
from datetime import datetime
from src.models.session import Session
from src.models.speaker import Speaker
from src.models.registrant import Registrant


@pytest.fixture
def sample_speaker():
    """Create a sample speaker for testing."""
    return Speaker(
        name="張志成",
        photo="images/speakers/zhang-zhicheng.jpg",
        bio="資深全端工程師,擅長 Python 與 React 開發"
    )


@pytest.fixture
def sample_session(sample_speaker):
    """Create a sample session for testing."""
    return Session(
        id="session_001",
        title="Python 網頁爬蟲入門",
        description="網頁爬蟲是數據收集的重要技能",
        date="2025-12-01",
        time="14:00-16:00",
        location="台北國際會議中心 201 室",
        level="初",
        tags=["Python", "Web Scraping"],
        learning_outcomes="掌握 Requests 與 BeautifulSoup 用法",
        capacity=50,
        registered=0,
        speaker=sample_speaker,
        registrants=[]
    )


@pytest.fixture
def past_session(sample_speaker):
    """Create a past session for testing."""
    return Session(
        id="session_002",
        title="過去的議程",
        description="這是一個已經過期的議程",
        date="2020-01-01",
        time="10:00-12:00",
        location="線上",
        level="中",
        tags=["Test"],
        learning_outcomes="測試過去議程",
        capacity=100,
        registered=0,
        speaker=sample_speaker,
        registrants=[]
    )


class TestSessionValidation:
    """Test Session model validation."""

    def test_create_valid_session(self, sample_session):
        """Test creating a valid session."""
        assert sample_session.id == "session_001"
        assert sample_session.title == "Python 網頁爬蟲入門"
        assert sample_session.capacity == 50
        assert sample_session.registered == 0

    def test_empty_id_raises_error(self, sample_speaker):
        """Test that empty ID raises ValueError."""
        with pytest.raises(ValueError, match="Session ID cannot be empty"):
            Session(
                id="",
                title="Test",
                description="Test",
                date="2025-12-01",
                time="14:00-16:00",
                location="Test",
                level="初",
                tags=["Test"],
                learning_outcomes="Test",
                capacity=50,
                registered=0,
                speaker=sample_speaker
            )

    def test_invalid_id_format_raises_error(self, sample_speaker):
        """Test that invalid ID format raises ValueError."""
        with pytest.raises(ValueError, match="Session ID must match format"):
            Session(
                id="invalid_id",
                title="Test",
                description="Test",
                date="2025-12-01",
                time="14:00-16:00",
                location="Test",
                level="初",
                tags=["Test"],
                learning_outcomes="Test",
                capacity=50,
                registered=0,
                speaker=sample_speaker
            )

    def test_empty_title_raises_error(self, sample_speaker):
        """Test that empty title raises ValueError."""
        with pytest.raises(ValueError, match="Title cannot be empty"):
            Session(
                id="session_001",
                title="",
                description="Test",
                date="2025-12-01",
                time="14:00-16:00",
                location="Test",
                level="初",
                tags=["Test"],
                learning_outcomes="Test",
                capacity=50,
                registered=0,
                speaker=sample_speaker
            )

    def test_invalid_level_raises_error(self, sample_speaker):
        """Test that invalid difficulty level raises ValueError."""
        with pytest.raises(ValueError, match="Level must be one of"):
            Session(
                id="session_001",
                title="Test",
                description="Test",
                date="2025-12-01",
                time="14:00-16:00",
                location="Test",
                level="無效",
                tags=["Test"],
                learning_outcomes="Test",
                capacity=50,
                registered=0,
                speaker=sample_speaker
            )

    def test_negative_capacity_raises_error(self, sample_speaker):
        """Test that negative capacity raises ValueError."""
        with pytest.raises(ValueError, match="Capacity must be positive"):
            Session(
                id="session_001",
                title="Test",
                description="Test",
                date="2025-12-01",
                time="14:00-16:00",
                location="Test",
                level="初",
                tags=["Test"],
                learning_outcomes="Test",
                capacity=-10,
                registered=0,
                speaker=sample_speaker
            )

    def test_negative_registered_raises_error(self, sample_speaker):
        """Test that negative registered count raises ValueError."""
        with pytest.raises(ValueError, match="Registered count cannot be negative"):
            Session(
                id="session_001",
                title="Test",
                description="Test",
                date="2025-12-01",
                time="14:00-16:00",
                location="Test",
                level="初",
                tags=["Test"],
                learning_outcomes="Test",
                capacity=50,
                registered=-5,
                speaker=sample_speaker
            )

    def test_registered_exceeds_capacity_raises_error(self, sample_speaker):
        """Test that registered > capacity raises ValueError."""
        with pytest.raises(ValueError, match="Registered count .* cannot exceed capacity"):
            Session(
                id="session_001",
                title="Test",
                description="Test",
                date="2025-12-01",
                time="14:00-16:00",
                location="Test",
                level="初",
                tags=["Test"],
                learning_outcomes="Test",
                capacity=50,
                registered=60,
                speaker=sample_speaker
            )


class TestSessionProperties:
    """Test Session model computed properties."""

    def test_is_full_when_at_capacity(self, sample_session):
        """Test is_full returns True when session is at capacity."""
        sample_session.registered = sample_session.capacity
        assert sample_session.is_full() is True

    def test_is_full_when_below_capacity(self, sample_session):
        """Test is_full returns False when session has space."""
        sample_session.registered = 25
        sample_session.capacity = 50
        assert sample_session.is_full() is False

    def test_is_past_for_old_session(self, past_session):
        """Test is_past returns True for sessions in the past."""
        assert past_session.is_past() is True

    def test_is_past_for_future_session(self, sample_session):
        """Test is_past returns False for future sessions."""
        assert sample_session.is_past() is False

    def test_is_upcoming_for_future_session(self, sample_session):
        """Test is_upcoming returns True for future sessions."""
        assert sample_session.is_upcoming() is True

    def test_is_upcoming_for_past_session(self, past_session):
        """Test is_upcoming returns False for past sessions."""
        assert past_session.is_upcoming() is False

    def test_status_available(self, sample_session):
        """Test status returns 'available' for open sessions."""
        sample_session.registered = 10
        sample_session.capacity = 50
        assert sample_session.status() == "available"

    def test_status_full(self, sample_session):
        """Test status returns 'full' when at capacity."""
        sample_session.registered = sample_session.capacity
        assert sample_session.status() == "full"

    def test_status_expired(self, past_session):
        """Test status returns 'expired' for past sessions."""
        assert past_session.status() == "expired"

    def test_registration_percentage_half_full(self, sample_session):
        """Test registration_percentage calculation."""
        sample_session.registered = 25
        sample_session.capacity = 50
        assert sample_session.registration_percentage() == 50.0

    def test_registration_percentage_full(self, sample_session):
        """Test registration_percentage at 100%."""
        sample_session.registered = sample_session.capacity
        assert sample_session.registration_percentage() == 100.0

    def test_registration_percentage_empty(self, sample_session):
        """Test registration_percentage at 0%."""
        sample_session.registered = 0
        assert sample_session.registration_percentage() == 0.0

    def test_registration_percentage_zero_capacity(self, sample_speaker):
        """Test registration_percentage returns 0 for zero capacity."""
        session = Session(
            id="session_999",
            title="Test",
            description="Test",
            date="2025-12-01",
            time="14:00-16:00",
            location="Test",
            level="初",
            tags=["Test"],
            learning_outcomes="Test",
            capacity=1,
            registered=0,
            speaker=sample_speaker
        )
        session.capacity = 0
        assert session.registration_percentage() == 0.0


class TestSessionEnhancements:
    """Test enhanced Session model methods for registration."""

    def test_registrants_consistency_validation(self, sample_speaker):
        """Test that registrants count must match registered count."""
        with pytest.raises(ValueError, match="Registrants count .* must match registered count"):
            Session(
                id="session_001",
                title="Test",
                description="Test",
                date="2025-12-01",
                time="14:00-16:00",
                location="Test",
                level="初",
                tags=["Test"],
                learning_outcomes="Test",
                capacity=50,
                registered=2,
                speaker=sample_speaker,
                registrants=[
                    Registrant(name="張三", registered_at="2025-10-28T14:32:10+08:00")
                ]
            )

    def test_can_register_available_session(self, sample_session):
        """Test can_register returns True for available session."""
        can_register, message = sample_session.can_register("新報名者")
        assert can_register is True
        assert message == ""

    def test_can_register_duplicate_name(self, sample_session):
        """Test can_register rejects duplicate name."""
        sample_session.registrants = [
            Registrant(name="張三", registered_at="2025-10-28T14:32:10+08:00")
        ]
        sample_session.registered = 1

        can_register, message = sample_session.can_register("張三")
        assert can_register is False
        assert message == "您已報名"

    def test_can_register_duplicate_case_insensitive(self, sample_session):
        """Test can_register rejects duplicate name (case-insensitive)."""
        sample_session.registrants = [
            Registrant(name="John Doe", registered_at="2025-10-28T14:32:10+08:00")
        ]
        sample_session.registered = 1

        can_register, message = sample_session.can_register("JOHN DOE")
        assert can_register is False
        assert message == "您已報名"

    def test_can_register_duplicate_with_whitespace(self, sample_session):
        """Test can_register rejects duplicate name with extra whitespace."""
        sample_session.registrants = [
            Registrant(name="張三", registered_at="2025-10-28T14:32:10+08:00")
        ]
        sample_session.registered = 1

        can_register, message = sample_session.can_register("  張三  ")
        assert can_register is False
        assert message == "您已報名"

    def test_can_register_full_session(self, sample_session):
        """Test can_register rejects when session is full."""
        sample_session.registered = sample_session.capacity
        sample_session.registrants = []

        can_register, message = sample_session.can_register("新報名者")
        assert can_register is False
        assert message == "已額滿"

    def test_can_register_past_session(self, past_session):
        """Test can_register rejects when session has passed."""
        can_register, message = past_session.can_register("新報名者")
        assert can_register is False
        assert message == "已過期"

    def test_add_registrant(self, sample_session):
        """Test add_registrant adds to list and syncs count."""
        initial_count = sample_session.registered
        registrant = Registrant(name="張三", registered_at="2025-10-28T14:32:10+08:00")

        sample_session.add_registrant(registrant)

        assert len(sample_session.registrants) == initial_count + 1
        assert sample_session.registered == initial_count + 1
        assert sample_session.registrants[-1].name == "張三"

    def test_add_multiple_registrants(self, sample_session):
        """Test adding multiple registrants."""
        registrant1 = Registrant(name="張三", registered_at="2025-10-28T14:32:10+08:00")
        registrant2 = Registrant(name="李四", registered_at="2025-10-28T14:35:22+08:00")

        sample_session.add_registrant(registrant1)
        sample_session.add_registrant(registrant2)

        assert len(sample_session.registrants) == 2
        assert sample_session.registered == 2

    def test_get_registrants_names(self, sample_session):
        """Test get_registrants_names returns list of names."""
        sample_session.registrants = [
            Registrant(name="張三", registered_at="2025-10-28T14:32:10+08:00"),
            Registrant(name="李四", registered_at="2025-10-28T14:35:22+08:00"),
            Registrant(name="王五", registered_at="2025-10-28T15:01:05+08:00")
        ]
        sample_session.registered = 3

        names = sample_session.get_registrants_names()

        assert names == ["張三", "李四", "王五"]

    def test_get_registrants_names_empty(self, sample_session):
        """Test get_registrants_names returns empty list when no registrants."""
        sample_session.registrants = []
        sample_session.registered = 0

        names = sample_session.get_registrants_names()

        assert names == []
