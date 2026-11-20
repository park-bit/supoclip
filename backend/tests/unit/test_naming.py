"""Tests for clip naming helper."""

import pytest
from src.media.naming import sanitize_title_for_filename, format_clip_filename


def test_sanitize_title_for_filename():
    assert sanitize_title_for_filename("Italy Summer Ya Idli Sambar?") == "Italy Summer Ya Idli Sambar"
    assert sanitize_title_for_filename("idli sambar vs vadapav") == "idli sambar vs vadapav"
    assert sanitize_title_for_filename("A/B: Test | Video") == "A - B - Test - Video"
    assert sanitize_title_for_filename("Uploaded.mp4") == "Uploaded"
    assert sanitize_title_for_filename(None) == "video"
    assert sanitize_title_for_filename("") == "video"
    assert sanitize_title_for_filename("???") == "video"


def test_format_clip_filename():
    assert format_clip_filename("Italy Summer Ya Idli Sambar?", 1) == "Italy Summer Ya Idli Sambar_1.mp4"
    assert format_clip_filename("idli sambar vs vadapav", 1) == "idli sambar vs vadapav_1.mp4"
    assert format_clip_filename("Even the Student Council Has Its Limits", 6) == "Even the Student Council Has Its Limits_6.mp4"
    assert format_clip_filename("Puore Bollywood Ne Attendance Lagayi", 2, preset="tiktok") == "Puore Bollywood Ne Attendance Lagayi_2_tiktok.mp4"
    assert format_clip_filename(None, 3) == "video_3.mp4"
    assert format_clip_filename("Podcast", 4, preset="original") == "Podcast_4.mp4"
