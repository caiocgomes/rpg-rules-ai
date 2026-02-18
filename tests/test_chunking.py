"""Tests for section-aware chunking module."""

from unittest.mock import patch

from langchain_core.documents import Document

from caprag.chunking import (
    split_into_sections,
    split_parents_into_children,
    split_sections_into_parents,
)


class TestSplitIntoSections:
    def test_splits_by_h2(self):
        md = "Intro text\n## COMBAT\nCombat rules here\n## MAGIC\nMagic rules here"
        sections = split_into_sections(md)
        assert len(sections) >= 2
        texts = [s.page_content for s in sections]
        assert any("COMBAT" in t for t in texts)
        assert any("MAGIC" in t for t in texts)

    def test_splits_by_h3(self):
        md = "## COMBAT\n### Rapid Strike\nStrike rules\n### Deceptive Attack\nDeception rules"
        sections = split_into_sections(md)
        assert len(sections) >= 2

    def test_empty_input(self):
        sections = split_into_sections("")
        assert isinstance(sections, list)

    def test_no_headers(self):
        md = "Just plain text without any headers at all."
        sections = split_into_sections(md)
        assert len(sections) >= 1
        assert "plain text" in sections[0].page_content


class TestSplitSectionsIntoParents:
    @patch("caprag.chunking.settings")
    def test_small_sections_stay_whole(self, mock_settings):
        mock_settings.parent_chunk_max = 4000
        mock_settings.parent_chunk_overlap = 500

        sections = [
            Document(page_content="Short section " * 10, metadata={"h2": "COMBAT"}),
        ]
        parents = split_sections_into_parents(sections, max_size=4000)
        assert len(parents) == 1
        assert parents[0].page_content == sections[0].page_content

    @patch("caprag.chunking.settings")
    def test_large_sections_get_split(self, mock_settings):
        mock_settings.parent_chunk_max = 100
        mock_settings.parent_chunk_overlap = 20

        big_text = "Word " * 200  # ~1000 chars
        sections = [Document(page_content=big_text, metadata={"h2": "BIG"})]
        parents = split_sections_into_parents(sections, max_size=100)
        assert len(parents) > 1
        for p in parents:
            assert "h2" in p.metadata

    @patch("caprag.chunking.settings")
    def test_mixed_sizes(self, mock_settings):
        mock_settings.parent_chunk_max = 500
        mock_settings.parent_chunk_overlap = 50

        small = Document(page_content="Short.", metadata={"h2": "A"})
        big = Document(page_content="Word " * 200, metadata={"h2": "B"})
        parents = split_sections_into_parents([small, big], max_size=500)
        assert len(parents) >= 3  # 1 small + 2+ big splits


class TestSplitParentsIntoChildren:
    @patch("caprag.chunking.settings")
    def test_children_have_doc_id(self, mock_settings):
        mock_settings.child_chunk_size = 50
        mock_settings.child_chunk_overlap = 10

        parents = [
            Document(page_content="Word " * 50, metadata={"book": "Test.md"}),
        ]
        children, parent_map = split_parents_into_children(parents)

        assert len(children) > 0
        assert len(parent_map) == 1

        parent_id = list(parent_map.keys())[0]
        for child in children:
            assert child.metadata["doc_id"] == parent_id
            assert child.metadata["book"] == "Test.md"

    @patch("caprag.chunking.settings")
    def test_id_consistency(self, mock_settings):
        mock_settings.child_chunk_size = 50
        mock_settings.child_chunk_overlap = 10

        parents = [
            Document(page_content="Word " * 30, metadata={}),
            Document(page_content="Other " * 30, metadata={}),
        ]
        children, parent_map = split_parents_into_children(parents)

        child_parent_ids = {c.metadata["doc_id"] for c in children}
        assert child_parent_ids.issubset(set(parent_map.keys()))

    @patch("caprag.chunking.settings")
    def test_multiple_parents(self, mock_settings):
        mock_settings.child_chunk_size = 50
        mock_settings.child_chunk_overlap = 10

        parents = [
            Document(page_content="AAA " * 30, metadata={"h2": "A"}),
            Document(page_content="BBB " * 30, metadata={"h2": "B"}),
        ]
        children, parent_map = split_parents_into_children(parents)

        assert len(parent_map) == 2
        assert len(children) >= 2
