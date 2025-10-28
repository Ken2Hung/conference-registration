"""Tests for dashboard UI components."""
import pytest
from src.ui.dashboard import _render_speaker_avatar


class TestSpeakerAvatarRendering:
    """Tests for speaker avatar rendering with fallback."""

    def test_render_avatar_contains_img_tag(self):
        """Avatar HTML should contain img tag with photo path."""
        html = _render_speaker_avatar("images/speakers/test.jpg", "John Doe")

        assert '<img' in html
        assert 'images/speakers/test.jpg' in html
        assert 'alt="John Doe"' in html

    def test_render_avatar_contains_fallback_div(self):
        """Avatar HTML should contain fallback div with initial."""
        html = _render_speaker_avatar("images/test.jpg", "John Doe")

        assert '<div' in html
        assert 'J' in html  # Speaker initial

    def test_render_avatar_with_empty_name_uses_question_mark(self):
        """Empty speaker name should use '?' as initial."""
        html = _render_speaker_avatar("images/test.jpg", "")

        assert '?' in html

    def test_render_avatar_applies_reduced_opacity_for_past_sessions(self):
        """Past sessions should have opacity 0.6."""
        html = _render_speaker_avatar("images/test.jpg", "Jane", is_past=True)

        assert 'opacity: 0.6' in html

    def test_render_avatar_applies_full_opacity_for_upcoming_sessions(self):
        """Upcoming sessions should have opacity 1.0."""
        html = _render_speaker_avatar("images/test.jpg", "Jane", is_past=False)

        assert 'opacity: 1.0' in html

    def test_render_avatar_custom_size(self):
        """Avatar should respect custom size parameter."""
        html = _render_speaker_avatar("images/test.jpg", "John", size=100)

        assert 'width: 100px' in html
        assert 'height: 100px' in html

    def test_render_avatar_has_onerror_handler(self):
        """Image should have onerror handler for missing files."""
        html = _render_speaker_avatar("images/test.jpg", "John")

        assert 'onerror=' in html
        assert "this.style.display='none'" in html

    def test_render_avatar_circular_styling(self):
        """Avatar should have circular border-radius."""
        html = _render_speaker_avatar("images/test.jpg", "John")

        assert 'border-radius: 50%' in html

    def test_render_avatar_has_gradient_background(self):
        """Fallback should have gradient background."""
        html = _render_speaker_avatar("images/test.jpg", "John")

        assert 'linear-gradient' in html
        assert '#667eea' in html
        assert '#764ba2' in html
