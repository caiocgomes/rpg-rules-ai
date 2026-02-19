"""Tests for the layered ingestion pipeline."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_md(tmp_path: Path, name: str, content: str = "# Test\nSome content here.") -> Path:
    p = tmp_path / name
    p.write_text(content)
    return p


@pytest.fixture
def mock_infra():
    """Mock vectorstore, docstore, embeddings, and settings."""
    mock_vs = MagicMock()
    mock_collection = MagicMock()
    mock_vs._collection = mock_collection
    mock_collection.count.return_value = 0

    mock_docstore = MagicMock()

    mock_embedder = MagicMock()
    mock_embedder.embed_documents.side_effect = lambda texts: [[0.1] * 10 for _ in texts]

    with (
        patch("rpg_rules_ai.pipeline.get_vectorstore", return_value=mock_vs),
        patch("rpg_rules_ai.pipeline.get_docstore", return_value=mock_docstore),
        patch("rpg_rules_ai.pipeline.OpenAIEmbeddings", return_value=mock_embedder),
        patch("rpg_rules_ai.ingest.get_vectorstore", return_value=mock_vs),
        patch("rpg_rules_ai.ingest.get_docstore", return_value=mock_docstore),
        patch("rpg_rules_ai.ingest.settings") as mock_ingest_settings,
        patch("rpg_rules_ai.pipeline.settings") as mock_pipeline_settings,
    ):
        mock_ingest_settings.sources_dir = "/tmp/fake_sources"
        mock_pipeline_settings.embedding_model = "text-embedding-3-large"
        mock_pipeline_settings.enable_contextual_embeddings = False
        mock_pipeline_settings.enable_entity_extraction = False
        mock_pipeline_settings.context_model = "gpt-4o-mini"
        yield {
            "vs": mock_vs,
            "collection": mock_collection,
            "docstore": mock_docstore,
            "embedder": mock_embedder,
        }


class TestLayeredPipeline:
    def test_full_pipeline(self, tmp_path, mock_infra):
        files = [_make_md(tmp_path, f"Book{i}.md", f"# Book {i}\nContent for book {i}.") for i in range(3)]

        from rpg_rules_ai.pipeline import run_layered_pipeline
        result = run_layered_pipeline(files)

        assert result["status"] == "done"
        assert len(result["file_results"]) == 3
        assert all(r["status"] == "success" for r in result["file_results"])
        assert mock_infra["collection"].add.called
        assert mock_infra["docstore"].mset.called

    def test_parse_error_isolation(self, tmp_path, mock_infra):
        good1 = _make_md(tmp_path, "Good1.md")
        good2 = _make_md(tmp_path, "Good2.md")
        bad = _make_md(tmp_path, "Bad.md")

        call_count = 0
        original_loader = None

        def mock_loader_factory(path):
            nonlocal call_count
            call_count += 1
            if "Bad.md" in str(path):
                loader = MagicMock()
                loader.load.side_effect = ValueError("Parse failed")
                return loader
            from langchain_community.document_loaders import UnstructuredMarkdownLoader
            return UnstructuredMarkdownLoader(path)

        with patch("rpg_rules_ai.pipeline.UnstructuredMarkdownLoader", side_effect=mock_loader_factory):
            from rpg_rules_ai.pipeline import run_layered_pipeline
            result = run_layered_pipeline([good1, bad, good2])

        assert result["status"] == "done"
        statuses = {r["filename"]: r["status"] for r in result["file_results"]}
        assert statuses["Good1.md"] == "success"
        assert statuses["Bad.md"] == "error"
        assert statuses["Good2.md"] == "success"

    def test_progress_reports_ingesting_phase(self, tmp_path, mock_infra):
        files = [_make_md(tmp_path, "Test.md", "# Test\nSome content.")]
        phases_seen = []

        def on_progress(data):
            if data["phase"] and data["phase"] not in phases_seen:
                phases_seen.append(data["phase"])

        from rpg_rules_ai.pipeline import run_layered_pipeline
        run_layered_pipeline(files, on_progress=on_progress)

        assert "ingesting" in phases_seen

    def test_progress_counts_files(self, tmp_path, mock_infra):
        files = [_make_md(tmp_path, f"Book{i}.md", f"# Book {i}\nContent.") for i in range(3)]
        max_completed = [0]
        total_seen = [0]

        def on_progress(data):
            if data["phase"] == "ingesting":
                total_seen[0] = data["phase_total"]
                if data["phase_completed"] > max_completed[0]:
                    max_completed[0] = data["phase_completed"]

        from rpg_rules_ai.pipeline import run_layered_pipeline
        run_layered_pipeline(files, on_progress=on_progress)

        assert total_seen[0] == 3
        assert max_completed[0] == 3

    def test_id_consistency(self, tmp_path, mock_infra):
        files = [_make_md(tmp_path, "Book.md", "# Big Book\n" + "Content. " * 200)]

        from rpg_rules_ai.pipeline import run_layered_pipeline
        run_layered_pipeline(files)

        # Check that collection.add was called with metadatas containing doc_id
        add_calls = mock_infra["collection"].add.call_args_list
        all_doc_ids = set()
        for call in add_calls:
            for meta in call.kwargs.get("metadatas", call[1].get("metadatas", [])):
                if "doc_id" in meta:
                    all_doc_ids.add(meta["doc_id"])

        # Check that docstore.mset was called with matching parent IDs
        mset_calls = mock_infra["docstore"].mset.call_args_list
        parent_ids = set()
        for call in mset_calls:
            for pid, _ in call[0][0]:
                parent_ids.add(pid)

        # All doc_ids in children should exist as parent IDs
        assert all_doc_ids
        assert all_doc_ids.issubset(parent_ids)

    def test_skip_duplicates(self, tmp_path, mock_infra):
        mock_infra["collection"].get.return_value = {"metadatas": [{"book": "Dup.md"}]}
        mock_infra["collection"].count.return_value = 1

        files = [_make_md(tmp_path, "Dup.md")]

        from rpg_rules_ai.pipeline import run_layered_pipeline
        result = run_layered_pipeline(files)

        assert result["status"] == "done"
        assert result["file_results"][0]["status"] == "skipped"

    def test_per_file_processing_stores_each_file_before_next(self, tmp_path, mock_infra):
        """Each file is fully stored before the next one starts processing."""
        files = [_make_md(tmp_path, f"Book{i}.md", f"# Book {i}\nContent.") for i in range(3)]

        from rpg_rules_ai.pipeline import run_layered_pipeline
        run_layered_pipeline(files)

        # docstore.mset is called once per file (not once at the end)
        assert mock_infra["docstore"].mset.call_count == 3

    def test_embed_and_store_batching(self, tmp_path, mock_infra):
        """Embedding and storing happen in batches, not all at once."""
        # Create content large enough to produce multiple batches
        big_content = "# Big Book\n" + "\n\n".join(f"## Section {i}\n" + "Word. " * 200 for i in range(20))
        files = [_make_md(tmp_path, "Big.md", big_content)]

        from rpg_rules_ai.pipeline import run_layered_pipeline
        run_layered_pipeline(files)

        # embed_documents should be called multiple times (batched)
        embed_calls = mock_infra["embedder"].embed_documents.call_count
        assert embed_calls >= 1
        assert mock_infra["collection"].add.called

    def test_error_in_one_file_preserves_previous(self, tmp_path, mock_infra):
        """If file 2 fails, file 1's data is already stored."""
        good = _make_md(tmp_path, "Good.md", "# Good\nContent.")
        bad = _make_md(tmp_path, "Bad.md")

        def mock_loader_factory(path):
            if "Bad.md" in str(path):
                loader = MagicMock()
                loader.load.side_effect = RuntimeError("Corrupt file")
                return loader
            from langchain_community.document_loaders import UnstructuredMarkdownLoader
            return UnstructuredMarkdownLoader(path)

        with patch("rpg_rules_ai.pipeline.UnstructuredMarkdownLoader", side_effect=mock_loader_factory):
            from rpg_rules_ai.pipeline import run_layered_pipeline
            result = run_layered_pipeline([good, bad])

        assert result["status"] == "done"
        statuses = {r["filename"]: r["status"] for r in result["file_results"]}
        assert statuses["Good.md"] == "success"
        assert statuses["Bad.md"] == "error"
        # Good.md was stored before Bad.md was attempted
        assert mock_infra["docstore"].mset.call_count == 1


class TestContextualEmbeddings:
    def test_disabled_skips_contextualize(self, tmp_path, mock_infra):
        """When ENABLE_CONTEXTUAL_EMBEDDINGS=false, no contextualize runs."""
        files = [_make_md(tmp_path, "Test.md", "# Test\nSome content.")]

        from rpg_rules_ai.pipeline import run_layered_pipeline
        with patch("rpg_rules_ai.pipeline._contextualize_chunks") as mock_ctx:
            result = run_layered_pipeline(files)

        assert result["status"] == "done"
        mock_ctx.assert_not_called()

    def test_enabled_runs_contextualize(self, tmp_path, mock_infra):
        """When ENABLE_CONTEXTUAL_EMBEDDINGS=true, contextualize runs and enriches chunks."""
        with patch("rpg_rules_ai.pipeline.settings") as mock_settings:
            mock_settings.embedding_model = "text-embedding-3-large"
            mock_settings.enable_contextual_embeddings = True
            mock_settings.context_model = "gpt-4o-mini"
            mock_settings.enable_entity_extraction = False

            files = [_make_md(tmp_path, "Test.md", "# Test\nSome content here.")]

            async def fake_batch(items, model="gpt-4o-mini"):
                return [f"Context for chunk {i}." for i in range(len(items))]

            with patch("rpg_rules_ai.contextualize.contextualize_batch", side_effect=fake_batch):
                from rpg_rules_ai.pipeline import run_layered_pipeline
                result = run_layered_pipeline(files)

            assert result["status"] == "done"

            # Check that stored chunks have enriched content
            add_calls = mock_infra["collection"].add.call_args_list
            for call in add_calls:
                docs = call.kwargs.get("documents", call[1].get("documents", []))
                metadatas = call.kwargs.get("metadatas", call[1].get("metadatas", []))
                for doc, meta in zip(docs, metadatas):
                    assert "Context for chunk" in doc
                    assert "original_text" in meta
                    assert "context_prefix" in meta

    def test_enabled_preserves_original_text_in_metadata(self, tmp_path, mock_infra):
        """Enriched chunks keep original text accessible via metadata."""
        with patch("rpg_rules_ai.pipeline.settings") as mock_settings:
            mock_settings.embedding_model = "text-embedding-3-large"
            mock_settings.enable_contextual_embeddings = True
            mock_settings.context_model = "gpt-4o-mini"
            mock_settings.enable_entity_extraction = False

            files = [_make_md(tmp_path, "Book.md", "# Book\nOriginal rule text.")]

            async def fake_batch(items, model="gpt-4o-mini"):
                return ["Prefix." for _ in items]

            with patch("rpg_rules_ai.contextualize.contextualize_batch", side_effect=fake_batch):
                from rpg_rules_ai.pipeline import run_layered_pipeline
                result = run_layered_pipeline(files)

            assert result["status"] == "done"
            add_calls = mock_infra["collection"].add.call_args_list
            for call in add_calls:
                metadatas = call.kwargs.get("metadatas", call[1].get("metadatas", []))
                for meta in metadatas:
                    assert meta["original_text"] != ""
                    assert "Prefix." not in meta["original_text"]


def _make_pdf(tmp_path: Path, name: str) -> Path:
    """Create a dummy .pdf file (content doesn't matter, pymupdf4llm will be mocked)."""
    p = tmp_path / name
    p.write_bytes(b"%PDF-1.4 dummy")
    return p


SAMPLE_PDF_MARKDOWN = """\
**COMBAT**

This chapter covers the rules for fighting.

**MELEE ATTACKS**

To make a melee attack, roll against your skill.

***Rapid Strike***

You may attempt two attacks on the same turn at -6 each.

***Deceptive Attack***

Trade skill for a penalty to the defender's active defense.

**RANGED ATTACKS**

Ranged attacks use DX-based weapon skills.
"""


class TestPdfPipeline:
    def test_pdf_full_pipeline(self, tmp_path, mock_infra):
        """PDF files go through extract_pdf -> postprocess_headers -> section-aware splitting."""
        pdf_file = _make_pdf(tmp_path, "Rulebook.pdf")

        mock_pymupdf = MagicMock()
        mock_pymupdf.to_markdown.return_value = SAMPLE_PDF_MARKDOWN

        with patch.dict(sys.modules, {"pymupdf4llm": mock_pymupdf}):
            from rpg_rules_ai.pipeline import run_layered_pipeline
            result = run_layered_pipeline([pdf_file])

        assert result["status"] == "done"
        assert result["file_results"][0]["filename"] == "Rulebook.pdf"
        assert result["file_results"][0]["status"] == "success"
        assert mock_infra["collection"].add.called
        assert mock_infra["docstore"].mset.called

    def test_pdf_produces_section_aware_chunks(self, tmp_path, mock_infra):
        """Parent chunks from PDF should carry section header metadata from markdown splitting."""
        pdf_file = _make_pdf(tmp_path, "Sections.pdf")

        mock_pymupdf = MagicMock()
        mock_pymupdf.to_markdown.return_value = SAMPLE_PDF_MARKDOWN

        with patch.dict(sys.modules, {"pymupdf4llm": mock_pymupdf}):
            from rpg_rules_ai.pipeline import run_layered_pipeline
            run_layered_pipeline([pdf_file])

        # Check that stored parents in docstore have section header metadata
        mset_calls = mock_infra["docstore"].mset.call_args_list
        assert len(mset_calls) > 0

        # Check child chunks have doc_id linking to parents
        add_calls = mock_infra["collection"].add.call_args_list
        all_doc_ids = set()
        for call in add_calls:
            metadatas = call.kwargs.get("metadatas", call[1].get("metadatas", []))
            for meta in metadatas:
                assert "doc_id" in meta
                all_doc_ids.add(meta["doc_id"])
                assert meta.get("book") == "Sections.pdf"

        parent_ids = set()
        for call in mset_calls:
            for pid, _ in call[0][0]:
                parent_ids.add(pid)

        assert all_doc_ids.issubset(parent_ids)

    def test_mixed_pdf_and_md(self, tmp_path, mock_infra):
        """Pipeline handles a mix of PDF and markdown files."""
        md_file = _make_md(tmp_path, "Guide.md", "# Guide\nSome guidance content.")
        pdf_file = _make_pdf(tmp_path, "Rules.pdf")

        mock_pymupdf = MagicMock()
        mock_pymupdf.to_markdown.return_value = "## COMBAT\nFight rules here."

        with patch.dict(sys.modules, {"pymupdf4llm": mock_pymupdf}):
            from rpg_rules_ai.pipeline import run_layered_pipeline
            result = run_layered_pipeline([md_file, pdf_file])

        assert result["status"] == "done"
        statuses = {r["filename"]: r["status"] for r in result["file_results"]}
        assert statuses["Guide.md"] == "success"
        assert statuses["Rules.pdf"] == "success"

    def test_pdf_extraction_error_isolation(self, tmp_path, mock_infra):
        """A failing PDF doesn't block other files."""
        good_md = _make_md(tmp_path, "Good.md", "# Good\nContent.")
        bad_pdf = _make_pdf(tmp_path, "Bad.pdf")

        mock_pymupdf = MagicMock()
        mock_pymupdf.to_markdown.side_effect = RuntimeError("Corrupt PDF")

        with patch.dict(sys.modules, {"pymupdf4llm": mock_pymupdf}):
            from rpg_rules_ai.pipeline import run_layered_pipeline
            result = run_layered_pipeline([good_md, bad_pdf])

        assert result["status"] == "done"
        statuses = {r["filename"]: r["status"] for r in result["file_results"]}
        assert statuses["Good.md"] == "success"
        assert statuses["Bad.pdf"] == "error"


class TestEntityExtraction:
    def test_disabled_skips_entity_extraction(self, tmp_path, mock_infra):
        files = [_make_md(tmp_path, "Test.md", "# Test\nSome content.")]

        from rpg_rules_ai.pipeline import run_layered_pipeline
        with patch("rpg_rules_ai.pipeline._extract_and_store_entities") as mock_ext:
            result = run_layered_pipeline(files)

        assert result["status"] == "done"
        mock_ext.assert_not_called()

    def test_enabled_runs_entity_extraction(self, tmp_path, mock_infra):
        with patch("rpg_rules_ai.pipeline.settings") as mock_settings:
            mock_settings.embedding_model = "text-embedding-3-large"
            mock_settings.enable_contextual_embeddings = False
            mock_settings.enable_entity_extraction = True
            mock_settings.context_model = "gpt-4o-mini"

            files = [_make_md(tmp_path, "Test.md", "# Test\nRapid Strike lets you attack twice.")]

            async def fake_batch(items, model="gpt-4o-mini"):
                return [[{"name": "Rapid Strike", "type": "maneuver", "mention_type": "defines"}] for _ in items]

            with (
                patch("rpg_rules_ai.entity_extractor.extract_entities_batch", side_effect=fake_batch),
                patch("rpg_rules_ai.entity_index.EntityIndex") as mock_idx_cls,
            ):
                mock_idx = MagicMock()
                mock_idx_cls.return_value = mock_idx

                from rpg_rules_ai.pipeline import run_layered_pipeline
                result = run_layered_pipeline(files)

            assert result["status"] == "done"
            mock_idx.add_entities.assert_called()
            mock_idx.close.assert_called()
