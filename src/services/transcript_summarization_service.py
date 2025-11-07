"""
Transcript summarization service for generating course summaries.

This module provides:
- Reading the latest transcript files
- Generating AI-powered summaries using OpenAI GPT-5-mini
- Saving summary results to disk
- Multi-stage summarization for long transcripts (chunking + final synthesis)
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List

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


def chunk_transcript(transcript_text: str, chunk_size: int = 50000) -> List[str]:
    """
    Split transcript into chunks of approximately equal size.

    Args:
        transcript_text: Full transcript text
        chunk_size: Maximum characters per chunk

    Returns:
        List of text chunks
    """
    if len(transcript_text) <= chunk_size:
        return [transcript_text]

    chunks = []
    current_pos = 0

    while current_pos < len(transcript_text):
        # Calculate end position for this chunk
        end_pos = min(current_pos + chunk_size, len(transcript_text))

        # Try to find a natural break point (paragraph or sentence)
        if end_pos < len(transcript_text):
            # Look for paragraph break first
            paragraph_break = transcript_text.rfind("\n\n", current_pos, end_pos)
            if paragraph_break > current_pos:
                end_pos = paragraph_break + 2
            else:
                # Look for sentence break
                sentence_break = transcript_text.rfind("。", current_pos, end_pos)
                if sentence_break == -1:
                    sentence_break = transcript_text.rfind(".", current_pos, end_pos)
                if sentence_break > current_pos:
                    end_pos = sentence_break + 1

        chunks.append(transcript_text[current_pos:end_pos])
        current_pos = end_pos

    print(f"[Summary] Split transcript into {len(chunks)} chunks")
    for i, chunk in enumerate(chunks):
        print(f"[Summary]   Chunk {i+1}: {len(chunk)} chars")

    return chunks


def summarize_chunk(
    chunk_text: str,
    chunk_index: int,
    total_chunks: int,
    api_key: str
) -> Tuple[bool, str]:
    """
    Generate a summary for a single transcript chunk.

    Args:
        chunk_text: Text chunk to summarize
        chunk_index: Index of this chunk (0-based)
        total_chunks: Total number of chunks
        api_key: OpenAI API key

    Returns:
        Tuple of (success: bool, summary: str)
    """
    try:
        client = OpenAI(api_key=api_key)

        system_prompt = """你是一位專業的課程內容摘要助手。
你的任務是為課程逐字稿的一個片段生成簡潔的摘要。

請專注於：
1. 記錄這一部分討論的主要議題
2. 提取關鍵的技術概念、工具或方法
3. 保留重要的觀點和結論

使用條列式格式，以繁體中文撰寫。摘要應簡潔明瞭，但保留足夠細節以便後續合併。"""

        user_prompt = f"""這是課程逐字稿的第 {chunk_index + 1} 部分（共 {total_chunks} 部分）。

請為以下內容生成摘要：

{chunk_text}

---

請以條列式格式總結這一部分的重點內容。"""

        print(f"[Summary] Summarizing chunk {chunk_index + 1}/{total_chunks}...")

        response = client.chat.completions.create(
            model="gpt-5-mini-2025-08-07",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_completion_tokens=2000,
            timeout=120
        )

        if not response.choices or len(response.choices) == 0:
            return False, f"Chunk {chunk_index + 1} 總結失敗：API 無回應"

        chunk_summary = response.choices[0].message.content

        if not chunk_summary or not chunk_summary.strip():
            return False, f"Chunk {chunk_index + 1} 總結為空"

        print(f"[Summary] Chunk {chunk_index + 1} summarized ({len(chunk_summary)} chars)")
        return True, chunk_summary.strip()

    except Exception as e:
        print(f"[Summary] Error summarizing chunk {chunk_index + 1}: {str(e)}")
        return False, f"Chunk {chunk_index + 1} 總結失敗: {str(e)}"


def generate_summary(
    transcript_text: str,
    session_title: Optional[str] = None,
    session_description: Optional[str] = None,
    session_learning_outcomes: Optional[str] = None
) -> Tuple[bool, str, dict]:
    """
    Generate a course summary from transcript text using OpenAI GPT-5-mini.

    For long transcripts, uses a multi-stage approach:
    1. Split transcript into chunks
    2. Summarize each chunk separately
    3. Synthesize all chunk summaries into final structured summary

    Args:
        transcript_text: Full transcript content to summarize
        session_title: Session title for context
        session_description: Session description for context
        session_learning_outcomes: Session learning outcomes for context

    Returns:
        Tuple of (success: bool, result: str, metadata: dict)
        If success, result contains the summary markdown
        If failure, result contains error message
        metadata contains: {"is_multi_stage": bool, "num_chunks": int}
    """
    if not transcript_text or not transcript_text.strip():
        print("[Summary] Error: Transcript text is empty")
        return False, "逐字稿內容為空，無法生成總結", {}

    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[Summary] Error: OPENAI_API_KEY not set")
        return False, "未設定 OPENAI_API_KEY，請檢查 .env 檔案設定", {}

    original_length = len(transcript_text)
    print(f"[Summary] Starting summary generation (transcript length: {original_length} chars)")

    # Determine if we need multi-stage summarization
    # Use chunking for transcripts > 40k chars to ensure quality
    CHUNK_THRESHOLD = 40000
    CHUNK_SIZE = 50000

    if original_length <= CHUNK_THRESHOLD:
        print("[Summary] Using single-stage summarization")
        success, result = _generate_single_summary(
            transcript_text,
            session_title,
            session_description,
            session_learning_outcomes,
            api_key
        )
        metadata = {"is_multi_stage": False, "num_chunks": 1}
        return success, result, metadata
    else:
        print("[Summary] Using multi-stage summarization (chunking)")
        chunks = chunk_transcript(transcript_text, chunk_size=CHUNK_SIZE)
        success, result = _generate_multi_stage_summary(
            transcript_text,
            session_title,
            session_description,
            session_learning_outcomes,
            api_key,
            chunk_size=CHUNK_SIZE
        )
        metadata = {"is_multi_stage": True, "num_chunks": len(chunks)}
        return success, result, metadata


def _generate_single_summary(
    transcript_text: str,
    session_title: Optional[str],
    session_description: Optional[str],
    session_learning_outcomes: Optional[str],
    api_key: str
) -> Tuple[bool, str]:
    """
    Generate summary for a transcript in a single API call.

    Args:
        transcript_text: Transcript text (should be under 40k chars)
        session_title: Session title for context
        session_description: Session description for context
        session_learning_outcomes: Session learning outcomes for context
        api_key: OpenAI API key

    Returns:
        Tuple of (success: bool, summary: str)
    """

    try:
        client = OpenAI(api_key=api_key)

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

        print("[Summary] Calling OpenAI API...")

        # Call OpenAI Chat API with GPT-5-mini
        # Note: GPT-5 models do not support temperature, top_p, or logprobs parameters
        # Increase max_completion_tokens to ensure enough space for full summary
        response = client.chat.completions.create(
            model="gpt-5-mini-2025-08-07",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_completion_tokens=4000,
            timeout=120
        )

        print(f"[Summary] API call completed. Response ID: {response.id}")
        print(f"[Summary] Response has {len(response.choices)} choice(s)")

        if not response.choices or len(response.choices) == 0:
            print("[Summary] Error: No choices in API response")
            return False, "API 返回格式錯誤：沒有回應選項"

        choice = response.choices[0]
        print(f"[Summary] Choice finish_reason: {choice.finish_reason}")

        # Check finish_reason for issues
        if choice.finish_reason == "length":
            print("[Summary] Warning: Response was truncated due to length limit")
            # Check if we got any content despite truncation
            if not choice.message.content or len(choice.message.content.strip()) == 0:
                return False, "逐字稿過長，API 無法生成總結。請縮短逐字稿內容後重試。"

        message_content = choice.message.content

        print(f"[Summary] Message content type: {type(message_content)}")
        print(f"[Summary] Message content is None: {message_content is None}")

        if message_content is not None:
            print(f"[Summary] Raw content length: {len(message_content)}")
            if len(message_content) > 0:
                print(f"[Summary] Content preview (first 200 chars): {repr(message_content[:200])}")

        if message_content is None:
            print("[Summary] Error: Message content is None")
            return False, "API 返回空白內容（content 為 None）"

        summary = message_content.strip()

        if not summary:
            print(f"[Summary] Error: Summary is empty after strip (original length: {len(message_content)})")
            print(f"[Summary] Original content repr: {repr(message_content)}")
            return False, "API 返回空白總結（內容為空字串或僅包含空白字元）"

        print(f"[Summary] Successfully generated summary ({len(summary)} chars)")
        return True, summary

    except openai.AuthenticationError as e:
        print(f"[Summary] Authentication error: {str(e)}")
        return False, f"OpenAI API 認證失敗：{str(e)}"
    except openai.RateLimitError as e:
        print(f"[Summary] Rate limit error: {str(e)}")
        return False, f"API 速率限制：{str(e)}"
    except openai.APIConnectionError as e:
        print(f"[Summary] Connection error: {str(e)}")
        return False, f"無法連接到 OpenAI API：{str(e)}"
    except openai.APIError as e:
        print(f"[Summary] API error: {str(e)}")
        return False, f"OpenAI API 錯誤：{str(e)}"
    except Exception as e:
        print(f"[Summary] Unexpected error: {str(e)}")
        return False, f"生成總結時發生錯誤：{str(e)}"


def _generate_multi_stage_summary(
    transcript_text: str,
    session_title: Optional[str],
    session_description: Optional[str],
    session_learning_outcomes: Optional[str],
    api_key: str,
    chunk_size: int = 50000
) -> Tuple[bool, str]:
    """
    Generate summary using multi-stage approach (chunk + synthesize).

    Args:
        transcript_text: Full transcript text
        session_title: Session title for context
        session_description: Session description for context
        session_learning_outcomes: Session learning outcomes for context
        api_key: OpenAI API key
        chunk_size: Maximum characters per chunk

    Returns:
        Tuple of (success: bool, summary: str)
    """
    print(f"[Summary] Multi-stage summarization: {len(transcript_text)} chars")

    # Step 1: Split into chunks
    chunks = chunk_transcript(transcript_text, chunk_size=chunk_size)

    # Step 2: Summarize each chunk
    chunk_summaries = []
    for i, chunk in enumerate(chunks):
        success, chunk_summary = summarize_chunk(chunk, i, len(chunks), api_key)
        if not success:
            return False, f"分段總結失敗：{chunk_summary}"
        chunk_summaries.append(chunk_summary)

    print(f"[Summary] All {len(chunk_summaries)} chunks summarized successfully")

    # Step 3: Combine chunk summaries
    combined_summaries = "\n\n---\n\n".join([
        f"## 第 {i+1} 部分摘要\n\n{summary}"
        for i, summary in enumerate(chunk_summaries)
    ])

    print(f"[Summary] Combined summaries length: {len(combined_summaries)} chars")

    # Step 4: Synthesize final summary from all chunk summaries
    try:
        client = OpenAI(api_key=api_key)

        system_prompt = """你是一位專業的課程總結助手。
你將收到一份課程逐字稿的多個部分摘要。請將這些摘要整合成一份結構化的完整課程總結。

總結必須包含以下四個部分：

1. **議程重點**：列出本次課程討論的主要議題和核心內容
2. **技術新知**：整理課程中提到的技術知識點、工具、框架或方法論
3. **結論**：總結課程的關鍵收穫和重點洞察
4. **進一步學習**：建議學員可以深入研究的方向和自我學習要點

請整合所有部分的內容，使用繁體中文，並以清晰的 Markdown 格式組織。每個部分使用二級標題（##），並用條列式呈現要點。
不要遺漏任何重要信息，確保總結涵蓋課程的完整內容。"""

        # Build context section
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

        user_prompt = f"""請將以下課程的多個部分摘要整合成一份完整的結構化總結：

{context_section}## 各部分摘要

{combined_summaries}

---

請依照指定格式生成包含「議程重點」、「技術新知」、「結論」、「進一步學習」四個部分的完整總結。
請整合所有部分的內容，確保總結涵蓋課程的完整內容，不要遺漏重要信息。"""

        print("[Summary] Generating final synthesis...")

        response = client.chat.completions.create(
            model="gpt-5-mini-2025-08-07",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_completion_tokens=4000,
            timeout=120
        )

        if not response.choices or len(response.choices) == 0:
            return False, "最終總結失敗：API 無回應"

        final_summary = response.choices[0].message.content

        if not final_summary or not final_summary.strip():
            return False, "最終總結為空"

        print(f"[Summary] Final summary generated ({len(final_summary)} chars)")
        return True, final_summary.strip()

    except Exception as e:
        print(f"[Summary] Error in final synthesis: {str(e)}")
        return False, f"最終總結失敗：{str(e)}"


def save_summary(
    resource_dir: Path,
    summary_text: str,
    transcript_filename: str,
    is_multi_stage: bool = False,
    num_chunks: int = 1
) -> Tuple[bool, str, Optional[Path]]:
    """
    Save summary to disk with timestamp.

    Args:
        resource_dir: Directory to save summary file
        summary_text: Summary content to save
        transcript_filename: Original transcript filename (for reference)
        is_multi_stage: Whether multi-stage summarization was used
        num_chunks: Number of chunks processed (if multi-stage)

    Returns:
        Tuple of (success: bool, message: str, path: Optional[Path])
    """
    try:
        resource_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        summary_filename = f"summary-{timestamp}.md"
        summary_path = resource_dir / summary_filename

        # Create header with metadata
        method_info = f"多階段總結（{num_chunks} 個片段）" if is_multi_stage else "單階段總結"

        header = f"""# 課程總結

> 生成時間：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
> 來源逐字稿：{transcript_filename}
> 生成模型：OpenAI GPT-5-mini (gpt-5-mini-2025-08-07)
> 處理方式：{method_info}

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
    success, result, metadata = generate_summary(
        transcript_text,
        session_title=session_title,
        session_description=session_description,
        session_learning_outcomes=session_learning_outcomes
    )
    if not success:
        return False, result, None

    summary_text = result

    # Step 4: Save summary with metadata
    success, message, summary_path = save_summary(
        resource_dir,
        summary_text,
        transcript_path.name,
        is_multi_stage=metadata.get("is_multi_stage", False),
        num_chunks=metadata.get("num_chunks", 1)
    )

    if not success:
        return False, message, None

    return True, message, summary_path
