"""Utilities for preparing HTML snippets before rendering in Streamlit."""
from textwrap import dedent


def html_block(template: str) -> str:
    """
    Normalize multi-line HTML so Streamlit doesn't treat it as Markdown code.

    Streamlit's Markdown renderer interprets lines with >=4 leading spaces as
    code blocks. We dedent and strip leading whitespace on each line to avoid
    that while keeping the markup intact.
    """
    lines = dedent(template).splitlines()
    return "\n".join(line.lstrip() for line in lines).strip()

