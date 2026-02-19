from __future__ import annotations

import os
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from rpg_rules_ai.ingestion_job import IngestionJob


class TestIngestionJobInit:
    def test_defaults(self, tmp_path: Path):
        p = tmp_path / "a.md"
        p.touch()
        job = IngestionJob(paths=[p])

        progress = job.get_progress()
        assert progress["status"] == "pending"
        assert progress["phase"] == ""
        assert progress["file_results"] == []
        assert progress["error"] is None
        assert job._thread is None

    def test_replace_flag(self, tmp_path: Path):
        p = tmp_path / "b.md"
        p.touch()
        job = IngestionJob(paths=[p], replace=True)
        assert job.replace is True


class TestGetProgress:
    def test_pending_state(self, tmp_path: Path):
        job = IngestionJob(paths=[tmp_path / "x.md"])
        progress = job.get_progress()
        assert progress["status"] == "pending"
        assert progress["phase"] == ""
        assert progress["phase_completed"] == 0
        assert progress["phase_total"] == 0

    def test_progress_returns_copy(self, tmp_path: Path):
        job = IngestionJob(paths=[tmp_path / "x.md"])
        p1 = job.get_progress()
        p1["status"] = "modified"
        p2 = job.get_progress()
        assert p2["status"] == "pending"


class TestRun:
    @patch("rpg_rules_ai.pipeline.run_layered_pipeline")
    def test_successful_run(self, mock_pipeline: MagicMock, tmp_path: Path):
        p1 = tmp_path / "a.md"
        p1.touch()
        job = IngestionJob(paths=[p1])

        mock_pipeline.return_value = {
            "status": "done",
            "phase": "storing",
            "phase_completed": 10,
            "phase_total": 10,
            "file_results": [{"filename": "a.md", "status": "success", "error_message": None}],
            "error": None,
        }

        job._run()

        progress = job.get_progress()
        assert progress["status"] == "done"
        assert len(progress["file_results"]) == 1
        mock_pipeline.assert_called_once()

    @patch("rpg_rules_ai.pipeline.run_layered_pipeline")
    def test_run_with_replace(self, mock_pipeline: MagicMock, tmp_path: Path):
        p1 = tmp_path / "a.md"
        p1.touch()
        job = IngestionJob(paths=[p1], replace=True)
        mock_pipeline.return_value = {"status": "done", "phase": "", "phase_completed": 0, "phase_total": 0, "file_results": [], "error": None}

        job._run()

        _, kwargs = mock_pipeline.call_args
        assert kwargs["replace"] is True

    @patch("rpg_rules_ai.pipeline.run_layered_pipeline")
    def test_run_exception_sets_error(self, mock_pipeline: MagicMock, tmp_path: Path):
        p1 = tmp_path / "a.md"
        p1.touch()
        job = IngestionJob(paths=[p1])
        mock_pipeline.side_effect = RuntimeError("disk full")

        job._run()

        progress = job.get_progress()
        assert progress["status"] == "error"
        assert progress["error"] == "disk full"


class TestStart:
    @patch("rpg_rules_ai.pipeline.run_layered_pipeline")
    def test_start_launches_thread(self, mock_pipeline: MagicMock, tmp_path: Path):
        p1 = tmp_path / "a.md"
        p1.touch()
        mock_pipeline.return_value = {"status": "done", "phase": "", "phase_completed": 0, "phase_total": 0, "file_results": [], "error": None}

        job = IngestionJob(paths=[p1])
        job.start()
        job._thread.join(timeout=5)

        assert job.get_progress()["status"] == "done"
        assert not job._thread.is_alive()

    @patch("rpg_rules_ai.pipeline.run_layered_pipeline")
    def test_start_thread_is_daemon(self, mock_pipeline: MagicMock, tmp_path: Path):
        p1 = tmp_path / "a.md"
        p1.touch()
        mock_pipeline.return_value = {"status": "done", "phase": "", "phase_completed": 0, "phase_total": 0, "file_results": [], "error": None}

        job = IngestionJob(paths=[p1])
        job.start()
        assert job._thread.daemon is True
        job._thread.join(timeout=5)

    @patch("rpg_rules_ai.pipeline.run_layered_pipeline")
    def test_start_error_in_thread(self, mock_pipeline: MagicMock, tmp_path: Path):
        p1 = tmp_path / "a.md"
        p1.touch()
        mock_pipeline.side_effect = ValueError("bad data")

        job = IngestionJob(paths=[p1])
        job.start()
        job._thread.join(timeout=5)

        progress = job.get_progress()
        assert progress["status"] == "error"
        assert progress["error"] == "bad data"


class TestThreadSafety:
    @patch("rpg_rules_ai.pipeline.run_layered_pipeline")
    def test_concurrent_progress_reads(self, mock_pipeline: MagicMock, tmp_path: Path):
        paths = [tmp_path / f"{i}.md" for i in range(5)]
        for p in paths:
            p.touch()

        barrier = threading.Barrier(2, timeout=5)

        def fake_pipeline(paths, replace=False, on_progress=None):
            if on_progress:
                on_progress({"status": "running", "phase": "embedding", "phase_completed": 5, "phase_total": 10, "file_results": [], "error": None})
            barrier.wait()
            return {"status": "done", "phase": "storing", "phase_completed": 10, "phase_total": 10, "file_results": [], "error": None}

        mock_pipeline.side_effect = fake_pipeline

        job = IngestionJob(paths=paths)
        snapshots: list[dict] = []

        def reader():
            barrier.wait()
            for _ in range(10):
                snapshots.append(job.get_progress())

        reader_thread = threading.Thread(target=reader)
        reader_thread.start()

        job.start()
        job._thread.join(timeout=5)
        reader_thread.join(timeout=5)

        assert len(snapshots) == 10
        for snap in snapshots:
            assert "status" in snap
            assert "phase" in snap
