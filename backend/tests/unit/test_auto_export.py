"""Unit tests for automatic local and Google Drive export service."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.services.auto_export_service import (
    sanitize_filename,
    save_to_local_exports,
    process_post_export,
    upload_to_google_drive,
)


def test_sanitize_filename():
    assert sanitize_filename("my/cool:clip?.mp4") == "my_cool_clip_.mp4"
    assert sanitize_filename("simple_name") == "simple_name.mp4"
    assert sanitize_filename('test"clip".mp4') == "test_clip_.mp4"


def test_save_to_local_exports(tmp_path: Path):
    source_file = tmp_path / "test_clip.mp4"
    source_file.write_bytes(b"fake video content")

    export_dest = tmp_path / "exports"
    with patch.dict(os.environ, {"LOCAL_EXPORT_DIR": str(export_dest)}):
        saved = save_to_local_exports(source_file, "final_clip.mp4")
        assert saved is not None
        assert saved.exists()
        assert saved.read_bytes() == b"fake video content"
        assert saved.name == "final_clip.mp4"


def test_upload_to_google_drive_unconfigured(tmp_path: Path):
    source_file = tmp_path / "clip.mp4"
    source_file.write_bytes(b"data")
    with patch.dict(os.environ, {"GDRIVE_FOLDER_ID": "", "GDRIVE_ACCESS_TOKEN": ""}, clear=True):
        result = upload_to_google_drive(source_file, "clip.mp4")
        assert result is None


def test_process_post_export(tmp_path: Path):
    source_file = tmp_path / "clip.mp4"
    source_file.write_bytes(b"clip bytes")
    export_dest = tmp_path / "my_exports"

    with patch.dict(os.environ, {"LOCAL_EXPORT_DIR": str(export_dest), "GDRIVE_ENABLED": "false"}):
        result = process_post_export(source_file, "clip.mp4")
        assert result["local_path"] is not None
        assert Path(result["local_path"]).exists()
        assert result["gdrive"] is None

