"""
Transcript summarization service for generating course summaries.

This module provides:
- Reading the latest transcript files
- Generating AI-powered summaries using OpenAI GPT-5-mini
- Saving summary results to disk
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from openai import OpenAI
import openai


def get_latest_transcript(resource_dir: Path) -> Optional[Path]:
    """
    Get the most recent transcript file from the resource directory.

    Args:
        resource_dir: Directory containing transcript files

    Returns:
        Path to the latest transcript file, or None if no transcripts found
    """
    if not resource_dir.exists() or not resource_dir.is_dir():
        return None

    try:
        transcript_files = sorted(
            resource_dir.glob("*-transcript.txt"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        if transcript_files:
            return transcript_files[0]
        return None
    except Exception as e:
        print(f"[Summary] Error finding transcript files: {e}")
        return None


def generate_summary(
    transcript_text: str,
    session_title: Optional[str] = None,
    session_description: Optional[str] = None,
    session_learning_outcomes: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Generate a course summary from transcript text using OpenAI GPT-5-mini.

    Args:
        transcript_text: Full transcript content to summarize
        session_title: Session title for context
        session_description: Session description for context
        session_learning_outcomes: Session learning outcomes for context

    Returns:
        Tuple of (success: bool, result: str)
        If success, result contains the summary markdown
        If failure, result contains error message
    """
    if not transcript_text or not transcript_text.strip():
        return False, "逐字稿內容為空，無法生成總結"

    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return False, "未設定 OPENAI_API_KEY，無法生成總結"

    try:
        client = OpenAI()

        # Construct prompt for summarization
        system_prompt = """你是一位專業的課程總結助手。請根據提供的課程逐字稿，生成一份結構化的課程總結。

總結必須包含以下四個部分：

1. **議程重點**：列出本次課程討論的主要議題和核心內容
2. **技術新知**：整理課程中提到的技術知識點、工具、框架或方法論
3. **結論**：總結課程的關鍵收穫和重點洞察
4. **進一步學習**：建議學員可以深入研究的方向和自我學習要點

請使用繁體中文，並以清晰的 Markdown 格式組織內容。每個部分使用二級標題（##），並用條列式呈現要點。"""

        # Build context section with session information
        context_parts = []

        if session_title:
            context_parts.append(f"**議程標題**：{session_title}")

        if session_description:
            context_parts.append(f"**議程敘述**：{session_description}")

        if session_learning_outcomes:
            context_parts.append(f"**學習重點**：{session_learning_outcomes}")

        context_section = ""
        if context_parts:
            context_section = "## 課程資訊\n\n" + "\n\n".join(context_parts) + "\n\n---\n\n"

        user_prompt = f"""請為以下課程生成總結：

{context_section}## 課程逐字稿

{transcript_text}

---

請依照指定格式生成包含「議程重點」、「技術新知」、「結論」、「進一步學習」四個部分的總結。請參考上述課程資訊，並結合逐字稿內容進行總結。"""

        # Call OpenAI Chat API with GPT-5-mini
        # Note: GPT-5 models do not support temperature, top_p, or logprobs parameters
        response = client.chat.completions.create(
            model="gpt-5-mini-2025-08-07",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_completion_tokens=2000,
            timeout=120
        )

        summary = response.choices[0].message.content.strip()

        if not summary:
            return False, "API 返回空白總結"

        return True, summary

    except openai.AuthenticationError as e:
        return False, f"OpenAI API 認證失敗：{str(e)}"
    except openai.RateLimitError as e:
        return False, f"API 速率限制：{str(e)}"
    except openai.APIConnectionError as e:
        return False, f"無法連接到 OpenAI API：{str(e)}"
    except openai.APIError as e:
        return False, f"OpenAI API 錯誤：{str(e)}"
    except Exception as e:
        return False, f"生成總結時發生錯誤：{str(e)}"


def save_summary(
    resource_dir: Path,
    summary_text: str,
    transcript_filename: str
) -> Tuple[bool, str, Optional[Path]]:
    """
    Save summary to disk with timestamp.

    Args:
        resource_dir: Directory to save summary file
        summary_text: Summary content to save
        transcript_filename: Original transcript filename (for reference)

    Returns:
        Tuple of (success: bool, message: str, path: Optional[Path])
    """
    try:
        resource_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        summary_filename = f"summary-{timestamp}.md"
        summary_path = resource_dir / summary_filename

        # Create header with metadata
        header = f"""# 課程總結

> 生成時間：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
> 來源逐字稿：{transcript_filename}
> 生成模型：OpenAI GPT-5-mini (gpt-5-mini-2025-08-07)

---

"""

        full_content = header + summary_text

        summary_path.write_text(full_content, encoding="utf-8")

        return True, f"總結已保存至 {summary_filename}", summary_path

    except Exception as e:
        return False, f"保存總結時發生錯誤：{str(e)}", None


def summarize_latest_transcript(
    resource_dir: Path,
    session_title: Optional[str] = None,
    session_description: Optional[str] = None,
    session_learning_outcomes: Optional[str] = None
) -> Tuple[bool, str, Optional[Path]]:
    """
    Complete workflow: find latest transcript, generate summary, and save.

    Args:
        resource_dir: Directory containing transcript files
        session_title: Session title for context
        session_description: Session description for context
        session_learning_outcomes: Session learning outcomes for context

    Returns:
        Tuple of (success: bool, message: str, summary_path: Optional[Path])
    """
    # Step 1: Find latest transcript
    transcript_path = get_latest_transcript(resource_dir)
    if not transcript_path:
        return False, "找不到任何逐字稿檔案", None

    # Step 2: Read transcript content
    try:
        transcript_text = transcript_path.read_text(encoding="utf-8")
    except Exception as e:
        return False, f"讀取逐字稿時發生錯誤：{str(e)}", None

    # Step 3: Generate summary with session context
    success, result = generate_summary(
        transcript_text,
        session_title=session_title,
        session_description=session_description,
        session_learning_outcomes=session_learning_outcomes
    )
    if not success:
        return False, result, None

    summary_text = result

    # Step 4: Save summary
    success, message, summary_path = save_summary(
        resource_dir,
        summary_text,
        transcript_path.name
    )

    if not success:
        return False, message, None

    return True, message, summary_path
