import json
import pytest
from src.services.video_service import VideoService


def test_build_fallback_segment_has_fallback_marker():
    seg = VideoService._build_fallback_segment(100.0, "sample text", 30)
    assert seg["hook_type"] == "fallback"
    assert "AI analysis did not identify" in seg["reasoning"]
    assert seg["virality_score"] == 0
    assert seg["start_time"] == "00:00"


def test_fallback_segment_detected():
    fallback_seg = VideoService._build_fallback_segment(60.0, "test", 30)
    normal_seg = {
        "start_time": "01:00",
        "end_time": "01:30",
        "text": "Great punchline here",
        "hook_type": "punchline",
        "virality_score": 85,
    }

    # Verify helper identification
    def is_fallback(segments):
        return bool(segments) and all(
            s.get("hook_type") == "fallback"
            or "AI analysis did not identify" in str(s.get("reasoning", ""))
            for s in segments
            if isinstance(s, dict)
        )

    assert is_fallback([fallback_seg]) is True
    assert is_fallback([fallback_seg, normal_seg]) is False
    assert is_fallback([normal_seg]) is False
    assert is_fallback([]) is False
