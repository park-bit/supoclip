from pathlib import Path
import json
import pytest

from src.media.transcription import (
    format_transcript_for_analysis,
    load_cached_transcript_data,
    AnalysisWord,
    _to_analysis_word,
)


def test_analysis_word_normalization():
    # Int milliseconds
    w1 = _to_analysis_word({"text": "hello", "start": 1000, "end": 2000, "speaker": "A"})
    assert w1.text == "hello"
    assert w1.start == 1000
    assert w1.end == 2000
    assert w1.speaker == "A"

    # Float seconds
    w2 = _to_analysis_word({"word": "world", "start": 2.5, "end": 3.0})
    assert w2.text == "world"
    assert w2.start == 2500
    assert w2.end == 3000


def test_format_transcript_splits_single_long_utterance():
    # Simulate a single-speaker video where AssemblyAI produces 1 utterance with 100 words
    words = []
    for i in range(100):
        words.append({
            "text": f"word{i}" + ("." if i % 10 == 9 else ""),
            "start": i * 1000,
            "end": (i + 1) * 1000,
            "speaker": "A",
        })

    transcript_dict = {
        "utterances": [
            {
                "text": " ".join(w["text"] for w in words),
                "start": 0,
                "end": 100000,
                "speaker": "A",
                "words": words,
            }
        ],
        "words": words,
    }

    lines = format_transcript_for_analysis(transcript_dict)
    # Must produce multiple granular lines rather than 1 giant line
    assert len(lines) > 5
    assert all("[" in line and "]" in line for line in lines)
    # First line should start at 00:00
    assert lines[0].startswith("[00:00")


def test_load_cached_transcript_data_returns_dict_without_mutation(tmp_path: Path):
    cache_path = tmp_path / "video.transcript_cache.json"
    cache_data = {
        "version": 1,
        "utterances": [{"text": "Hello world", "start": 0, "end": 1000, "words": []}],
        "words": [],
        "text": "Hello world",
    }
    with open(cache_path, "w") as f:
        json.dump(cache_data, f)

    video_path = tmp_path / "video.mp4"
    loaded = load_cached_transcript_data(video_path)
    assert loaded is not None
    assert loaded["text"] == "Hello world"
