"""
Async transcript loader and viewer components for Streamlit pages.

Provides shared helpers to asynchronously read Whisper transcript files stored
on disk and render them with preview and download controls.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Coroutine, Iterable, List, Optional

import streamlit as st

PREVIEW_CHAR_LIMIT = 4000  # Maximum characters shown inline before truncation


@dataclass
class TranscriptRecord:
    """Container for transcript file metadata and content."""

    path: Path
    filename: str
    content: str
    preview: str
    modified_at: datetime
    size_bytes: int
    error: Optional[str] = None


async def _load_single_transcript(path: Path, preview_chars: int) -> TranscriptRecord:
    """Asynchronously load a single transcript file."""

    def _read_file() -> TranscriptRecord:
        try:
            raw_text = path.read_text(encoding="utf-8")
        except Exception as exc:
            raw_text = ""
            error_msg = f"{type(exc).__name__}: {exc}"
        else:
            error_msg = None

        try:
            stat_result = path.stat()
            modified_at = datetime.fromtimestamp(stat_result.st_mtime)
            size_bytes = stat_result.st_size
        except Exception as stat_exc:
            modified_at = datetime.fromtimestamp(0)
            size_bytes = 0
            error_msg = error_msg or f"{type(stat_exc).__name__}: {stat_exc}"

        preview = raw_text.strip()
        if preview_chars and len(preview) > preview_chars:
            preview = preview[:preview_chars].rstrip() + "…"

        return TranscriptRecord(
            path=path,
            filename=path.name,
            content=raw_text,
            preview=preview,
            modified_at=modified_at,
            size_bytes=size_bytes,
            error=error_msg,
        )

    return await asyncio.to_thread(_read_file)


async def _load_transcripts_async(
    paths: Iterable[Path],
    preview_chars: int,
) -> List[TranscriptRecord]:
    """Load multiple transcript files concurrently."""
    tasks = [_load_single_transcript(path, preview_chars) for path in paths]
    return await asyncio.gather(*tasks)


def _run_async(
    factory: Callable[[], Coroutine[Any, Any, List[TranscriptRecord]]]
) -> List[TranscriptRecord]:
    """Execute coroutine with a fresh event loop when required."""
    try:
        return asyncio.run(factory())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(factory())
        finally:
            loop.close()


def load_transcripts(
    resource_dir: Path,
    *,
    pattern: str = "*.txt",
    limit: int = 10,
    preview_chars: int = PREVIEW_CHAR_LIMIT,
) -> List[TranscriptRecord]:
    """
    Load transcript files within a directory using asyncio-backed IO.

    Args:
        resource_dir: Directory containing transcript text files.
        pattern: Glob pattern used to select transcript files.
        limit: Maximum number of transcripts to return (sorted by modified time).
        preview_chars: Maximum characters retained for inline preview text.
    """
    if not resource_dir.exists() or not resource_dir.is_dir():
        return []

    try:
        candidates = sorted(
            resource_dir.glob(pattern),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
    except FileNotFoundError:
        return []

    if not candidates:
        return []

    selected = candidates[:limit]
    return _run_async(lambda: _load_transcripts_async(selected, preview_chars))


def render_transcript_history(
    *,
    resource_dir: Path,
    heading: str,
    description: Optional[str] = None,
    empty_message: str,
    max_entries: int = 5,
    preview_chars: int = PREVIEW_CHAR_LIMIT,
    key_prefix: Optional[str] = None,
) -> None:
    """
    Render transcript history section with async-loaded Whisper results.
    """
    st.markdown(f"#### {heading}")
    if description:
        st.caption(description)

    transcripts = load_transcripts(
        resource_dir,
        limit=max_entries,
        preview_chars=preview_chars,
    )

    if not transcripts:
        st.info(empty_message)
        return

    for idx, record in enumerate(transcripts, start=1):
        label = (
            f"{record.filename} · "
            f"{record.modified_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        with st.expander(label, expanded=False):
            if record.error:
                st.error(f"無法讀取逐字稿：{record.error}")
                continue

            st.caption(
                f"來源：OpenAI Whisper | 字元數：{len(record.content)} | "
                f"大小：{record.size_bytes / 1024:.1f} KB"
            )

            display_text = record.content
            truncated = False
            if preview_chars and len(display_text) > preview_chars:
                display_text = display_text[:preview_chars].rstrip() + "\n…"
                truncated = True

            text_area_key = (
                f"{key_prefix}_transcript_preview_{idx}"
                if key_prefix
                else f"transcript_preview_{idx}"
            )
            st.text_area(
                "逐字稿預覽",
                value=display_text or "（檔案為空）",
                height=260,
                key=text_area_key,
            )

            if truncated:
                st.caption("已截取部分內容，請下載檔案查看完整逐字稿。")

            download_key = (
                f"{key_prefix}_transcript_download_{idx}"
                if key_prefix
                else f"transcript_download_{idx}"
            )
            st.download_button(
                "下載完整逐字稿 (.txt)",
                data=record.content.encode("utf-8"),
                file_name=record.filename,
                mime="text/plain",
                use_container_width=True,
                key=download_key,
            )
