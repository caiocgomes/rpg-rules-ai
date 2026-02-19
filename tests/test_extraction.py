"""Tests for PDF extraction and markdown post-processing."""

from unittest.mock import patch

from rpg_rules_ai.extraction import clean_page_artifacts, postprocess_headers


class TestPostprocessHeaders:
    def test_bold_allcaps_becomes_h2(self):
        md = "Some text\n**COMBAT**\nMore text"
        result = postprocess_headers(md)
        assert "## COMBAT" in result
        assert "**COMBAT**" not in result

    def test_bold_allcaps_with_spaces(self):
        md = "**RAPID STRIKE**"
        result = postprocess_headers(md)
        assert "## RAPID STRIKE" in result

    def test_bold_allcaps_with_special_chars(self):
        md = "**ADVANTAGES AND DISADVANTAGES**"
        result = postprocess_headers(md)
        assert "## ADVANTAGES AND DISADVANTAGES" in result

    def test_bold_mixed_case_not_promoted(self):
        md = "**Rapid Strike**"
        result = postprocess_headers(md)
        assert "**Rapid Strike**" in result
        assert "##" not in result

    def test_bold_italic_becomes_h3(self):
        md = "***Rapid Strike***"
        result = postprocess_headers(md)
        assert "### Rapid Strike" in result
        assert "***" not in result

    def test_bold_italic_alt_syntax(self):
        md = "**_Deceptive Attack_**"
        result = postprocess_headers(md)
        assert "### Deceptive Attack" in result

    def test_page_artifact_not_promoted(self):
        md = "**COMBAT 99**"
        result = postprocess_headers(md)
        assert "##" not in result

    def test_page_number_artifact_not_promoted(self):
        md = "**99 COMBAT**"
        result = postprocess_headers(md)
        assert "##" not in result

    def test_short_bold_not_promoted(self):
        md = "**OK**"
        result = postprocess_headers(md)
        # "OK" is only 2 chars, should not become header
        assert "##" not in result

    def test_inline_bold_not_promoted(self):
        md = "This has **BOLD** inline text"
        result = postprocess_headers(md)
        # Not standalone, should not become header
        assert "##" not in result
        assert "**BOLD**" in result

    def test_preserves_existing_headers(self):
        md = "## Existing Header\nSome text"
        result = postprocess_headers(md)
        assert "## Existing Header" in result

    def test_multiple_headers(self):
        md = "**COMBAT**\nSome text\n***Rapid Strike***\nMore text\n**MAGIC**"
        result = postprocess_headers(md)
        assert "## COMBAT" in result
        assert "### Rapid Strike" in result
        assert "## MAGIC" in result


class TestCleanPageArtifacts:
    def test_removes_standalone_page_numbers(self):
        md = "Some text\n42\nMore text"
        result = clean_page_artifacts(md)
        assert "\n42\n" not in result
        assert "Some text" in result
        assert "More text" in result

    def test_removes_horizontal_rules(self):
        md = "Text above\n---\nText below"
        result = clean_page_artifacts(md)
        assert "---" not in result

    def test_removes_page_prefix(self):
        md = "Text\npage 42\nMore"
        result = clean_page_artifacts(md)
        assert "page 42" not in result

    def test_preserves_normal_numbers_in_text(self):
        md = "Roll 3d6 for damage"
        result = clean_page_artifacts(md)
        assert "Roll 3d6 for damage" in result

    def test_preserves_content(self):
        md = "## COMBAT\n\nRapid Strike allows two attacks at -6 each."
        result = clean_page_artifacts(md)
        assert "## COMBAT" in result
        assert "Rapid Strike allows two attacks at -6 each." in result


class TestExtractPdf:
    @patch.dict("sys.modules", {"pymupdf4llm": __import__("unittest.mock", fromlist=["MagicMock"]).MagicMock()})
    def test_calls_pymupdf4llm(self):
        import sys
        from pathlib import Path

        mock_pymupdf = sys.modules["pymupdf4llm"]
        mock_pymupdf.to_markdown.return_value = "# Title\nContent"

        from rpg_rules_ai.extraction import extract_pdf

        result = extract_pdf(Path("/fake/book.pdf"))

        mock_pymupdf.to_markdown.assert_called_once_with("/fake/book.pdf")
        assert result == "# Title\nContent"
