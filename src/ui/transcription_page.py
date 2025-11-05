"""
Standalone Streamlit page entry point for the transcription UI.

The heavy lifting lives in `src.ui.transcription_widget`. This module simply
renders the widget with the default configuration used by the dedicated page.
"""

from pathlib import Path

from src.ui.transcription_widget import render_transcription_widget
from src.ui.transcript_history import render_transcript_history


def render_transcription_page() -> None:
    """Render the standalone transcription page."""
    resource_dir = Path("resource")

    render_transcription_widget(
        prefix="transcription",
        resource_dir=resource_dir,
        show_header=True,
    )

    render_transcript_history(
        resource_dir=resource_dir,
        heading="🗂️ 歷史逐字稿",
        description="以下內容由即時轉錄，使用非同步方式載入以避免阻塞頁面。",
        empty_message="尚未產生任何逐字稿。開始錄音後，最新的 轉錄會顯示於此。",
        max_entries=8,
        key_prefix="transcription_page",
    )


__all__ = ["render_transcription_page"]
