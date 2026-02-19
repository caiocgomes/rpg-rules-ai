from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass
class IngestionJob:
    """Wraps layered ingestion pipeline in a background thread with thread-safe progress."""

    paths: list[Path]
    replace: bool = False
    _progress: dict = field(default_factory=lambda: {
        "status": "pending",
        "phase": "",
        "phase_completed": 0,
        "phase_total": 0,
        "file_results": [],
        "error": None,
    })
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _thread: threading.Thread | None = field(default=None, repr=False)

    def start(self) -> None:
        self._progress["status"] = "running"
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _on_progress(self, update: dict) -> None:
        with self._lock:
            self._progress.update(update)

    def _run(self) -> None:
        from rpg_rules_ai.pipeline import run_layered_pipeline

        try:
            result = run_layered_pipeline(
                self.paths,
                replace=self.replace,
                on_progress=self._on_progress,
            )
            with self._lock:
                self._progress.update(result)
        except Exception as exc:
            with self._lock:
                self._progress["status"] = "error"
                self._progress["error"] = str(exc)

    def get_progress(self) -> dict:
        with self._lock:
            return dict(self._progress)
