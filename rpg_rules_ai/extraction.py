"""PDF extraction and markdown post-processing for structured chunking."""

from __future__ import annotations

import re
from pathlib import Path


def extract_pdf(path: Path) -> str:
    """Extract a PDF to markdown using pymupdf4llm.

    Returns markdown text with formatting preserved (bold, italic).
    """
    import pymupdf4llm

    return pymupdf4llm.to_markdown(str(path))


def postprocess_headers(md: str) -> str:
    """Convert bold ALL-CAPS standalone lines to ## headers and italic+bold to ### headers.

    Heuristic tuned for GURPS 4e rulebooks where:
    - Section headers appear as **ALL CAPS TEXT** on a standalone line
    - Sub-section headers appear as ***Mixed Case Text*** (bold+italic)
    """
    lines = md.split("\n")
    result = []

    for line in lines:
        stripped = line.strip()

        # Bold+italic standalone line → ### (sub-section)
        # Matches ***Text*** or **_Text_** patterns
        m_bolditalic = re.match(r"^\*{3}(.+?)\*{3}$", stripped)
        if not m_bolditalic:
            m_bolditalic = re.match(r"^\*{2}_(.+?)_\*{2}$", stripped)
        if m_bolditalic:
            header_text = m_bolditalic.group(1).strip()
            if len(header_text) > 2:
                result.append(f"### {header_text}")
                continue

        # Bold ALL-CAPS standalone line → ## (section)
        m_bold = re.match(r"^\*{2}([A-Z][A-Z0-9\s,;:'\-&/()]+)\*{2}$", stripped)
        if m_bold:
            header_text = m_bold.group(1).strip()
            if len(header_text) > 2 and not _looks_like_page_artifact(header_text):
                result.append(f"## {header_text}")
                continue

        result.append(line)

    return "\n".join(result)


def _looks_like_page_artifact(text: str) -> bool:
    """Check if a bold ALL-CAPS line is likely a page header/footer rather than a real section."""
    # Page number patterns: "COMBAT 99", "99 COMBAT", standalone numbers
    if re.match(r"^\d+$", text.strip()):
        return True
    if re.match(r"^[A-Z\s]+\d+$", text.strip()):
        return True
    if re.match(r"^\d+\s+[A-Z\s]+$", text.strip()):
        return True
    return False


def clean_page_artifacts(md: str) -> str:
    """Remove page numbers, repeated headers/footers from extracted markdown.

    Targets patterns common in GURPS PDF extractions:
    - Standalone page numbers
    - Page header lines (e.g., "GURPS Basic Set" repeated on every page)
    - Horizontal rules that pymupdf4llm inserts at page breaks
    """
    lines = md.split("\n")
    result = []

    for line in lines:
        stripped = line.strip()

        # Skip standalone page numbers
        if re.match(r"^\d{1,4}$", stripped):
            continue

        # Skip page-break horizontal rules (sequences of --- or ___)
        if re.match(r"^[-_]{3,}$", stripped):
            continue

        # Skip lines that are just "page N" or "N"
        if re.match(r"^page\s+\d+$", stripped, re.IGNORECASE):
            continue

        result.append(line)

    return "\n".join(result)
