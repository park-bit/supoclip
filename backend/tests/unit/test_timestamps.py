import sys
if sys.platform == "win32" and "fcntl" not in sys.modules:
    import unittest.mock
    sys.modules["fcntl"] = unittest.mock.MagicMock()

import asyncio
import math
from unittest.mock import AsyncMock, patch
import pytest
from fastapi import HTTPException

from src.youtube_source import parse_clock
from src.youtube_utils import YouTubeDownloader
from src.api.routes.tasks import _preflight_youtube_source


def test_parse_clock():
    assert parse_clock("01:30:00") == 5400.0
    assert parse_clock("1:30:00") == 5400.0
    assert parse_clock("15:30") == 930.0
    assert parse_clock("0:45") == 45.0
    assert parse_clock("90") == 90.0
    assert parse_clock(90) == 90.0
    assert parse_clock(90.5) == 90.5
    assert parse_clock(0) == 0.0
    assert parse_clock("00:00:00") == 0.0
    assert parse_clock(None) is None
    assert parse_clock("") is None
    assert parse_clock("invalid") is None
    assert parse_clock(True) is None


def test_download_options_with_timestamp_range(tmp_path):
    downloader = YouTubeDownloader(temp_dir=tmp_path)
    opts = downloader.get_optimal_download_options(
        "test_video_id",
        max_height=1080,
        start_time=3600.0,
        end_time=5400.0,
    )
    assert "test_video_id_3600_5400" in opts["outtmpl"]
    assert "download_ranges" in opts
    assert opts.get("force_keyframes_at_cuts") is True

    # Test the range function
    ranges = opts["download_ranges"]({"duration": 86400}, None)
    assert ranges == [{"start_time": 3600.0, "end_time": 5400.0}]


@pytest.mark.asyncio
async def test_preflight_allows_short_range_from_24hr_stream():
    # 24-hour video (86400 seconds)
    mock_metadata = {"duration": 86400.0, "title": "24 Hour Live Stream"}
    with patch("src.api.routes.tasks.async_get_youtube_video_info", AsyncMock(return_value=mock_metadata)):
        # Plan limit is 2 hours (7200s), range is 30 mins (3600s to 5400s = 1800s)
        metadata = await _preflight_youtube_source(
            "https://www.youtube.com/watch?v=mock24hr",
            duration_limit=7200,
            start_seconds=3600.0,
            end_seconds=5400.0,
        )
        assert metadata["duration"] == 1800.0
        assert metadata["clip_start_time"] == 3600.0
        assert metadata["clip_end_time"] == 5400.0


@pytest.mark.asyncio
async def test_preflight_rejects_selected_range_exceeding_plan_limit():
    mock_metadata = {"duration": 86400.0, "title": "24 Hour Live Stream"}
    with patch("src.api.routes.tasks.async_get_youtube_video_info", AsyncMock(return_value=mock_metadata)):
        # Plan limit is 1 hour (3600s), range is 2 hours (7200s)
        with pytest.raises(HTTPException) as exc_info:
            await _preflight_youtube_source(
                "https://www.youtube.com/watch?v=mock24hr",
                duration_limit=3600,
                start_seconds=0.0,
                end_seconds=7200.0,
            )
        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["code"] == "VIDEO_TOO_LONG"
        assert "The selected timestamp range" in exc_info.value.detail["message"]


@pytest.mark.asyncio
async def test_preflight_rejects_invalid_timestamp_range():
    mock_metadata = {"duration": 1800.0, "title": "30 Min Video"}
    with patch("src.api.routes.tasks.async_get_youtube_video_info", AsyncMock(return_value=mock_metadata)):
        # Start beyond duration
        with pytest.raises(HTTPException) as exc_info:
            await _preflight_youtube_source(
                "https://www.youtube.com/watch?v=mock",
                duration_limit=7200,
                start_seconds=2000.0,
                end_seconds=2500.0,
            )
        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["code"] == "INVALID_TIMESTAMP_RANGE"

        # End before start
        with pytest.raises(HTTPException) as exc_info:
            await _preflight_youtube_source(
                "https://www.youtube.com/watch?v=mock",
                duration_limit=7200,
                start_seconds=500.0,
                end_seconds=400.0,
            )
        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["code"] == "INVALID_TIMESTAMP_RANGE"
