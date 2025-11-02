"""
Standalone Streamlit page entry point for the transcription UI.

The heavy lifting lives in `src.ui.transcription_widget`. This module simply
renders the widget with the default configuration used by the dedicated page.
"""

from pathlib import Path

from src.ui.transcription_widget import render_transcription_widget


def render_transcription_page() -> None:
    """Render the standalone transcription page."""
    render_transcription_widget(
        prefix="transcription",
        resource_dir=Path("resource"),
        show_header=True,
    )


__all__ = ["render_transcription_page"]
