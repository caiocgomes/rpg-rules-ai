"""Tests for POST /documents/upload multipart endpoint."""

from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from caprag.api import MAX_UPLOAD_SIZE, app

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_deps():
    with (
        patch("caprag.services.create_ingestion_job") as mock_create_job,
        patch("caprag.api.settings") as mock_settings,
    ):
        mock_settings.sources_dir = "/tmp/test_sources"
        mock_create_job.return_value = "fake-job-id"
        yield {"create_job": mock_create_job}


class TestUploadEndpoint:
    def test_upload_single_file(self, mock_deps, tmp_path):
        with patch("caprag.api.Path") as mock_path_cls:
            mock_dest = MagicMock()
            mock_path_cls.return_value.__truediv__ = MagicMock(return_value=mock_dest)

            resp = client.post(
                "/api/documents/upload",
                files=[("files", ("test.md", b"# Test content", "text/markdown"))],
            )

        assert resp.status_code == 202
        assert resp.json()["job_id"] == "fake-job-id"

    def test_upload_multiple_files(self, mock_deps):
        with patch("caprag.api.Path") as mock_path_cls:
            mock_dest = MagicMock()
            mock_path_cls.return_value.__truediv__ = MagicMock(return_value=mock_dest)

            resp = client.post(
                "/api/documents/upload",
                files=[
                    ("files", ("a.md", b"# A", "text/markdown")),
                    ("files", ("b.md", b"# B", "text/markdown")),
                    ("files", ("c.md", b"# C", "text/markdown")),
                ],
            )

        assert resp.status_code == 202
        mock_deps["create_job"].assert_called_once()
        paths_arg = mock_deps["create_job"].call_args[0][0]
        assert len(paths_arg) == 3

    def test_upload_rejects_non_md(self, mock_deps):
        resp = client.post(
            "/api/documents/upload",
            files=[("files", ("test.txt", b"not markdown", "text/plain"))],
        )
        assert resp.status_code == 400
        assert ".md" in resp.json()["detail"]

    def test_upload_rejects_oversized_file(self, mock_deps):
        big_content = b"x" * (MAX_UPLOAD_SIZE + 1)
        resp = client.post(
            "/api/documents/upload",
            files=[("files", ("huge.md", big_content, "text/markdown"))],
        )
        assert resp.status_code == 413

    def test_upload_with_replace_flag(self, mock_deps):
        with patch("caprag.api.Path") as mock_path_cls:
            mock_dest = MagicMock()
            mock_path_cls.return_value.__truediv__ = MagicMock(return_value=mock_dest)

            resp = client.post(
                "/api/documents/upload?replace=true",
                files=[("files", ("test.md", b"# Test", "text/markdown"))],
            )

        assert resp.status_code == 202
        mock_deps["create_job"].assert_called_once()
        assert mock_deps["create_job"].call_args[1]["replace"] is True
