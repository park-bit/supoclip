"""Tests for Hindi / Hinglish audio transcript recognition, romanization and ASR correction."""

import pytest
from src.media.romanize import (
    _rule_based_romanize_text,
    _rule_based_romanize_word,
    correct_phonetic_asr_mishearings,
    is_hindi_or_hinglish_text,
    strip_devanagari_full_stops,
    translate_sentences_with_groq,
    align_words,
    romanize_transcript_data,
)


def test_rule_based_schwa_deletion_and_consonants():
    """Verify standard Hindi schwa deletion and natural Hinglish spelling."""
    samples = {
        "वड़ा पाव": "vada pav",
        "इडली": "idli",
        "सांभर": "sambar",
        "करके": "karke",
        "समझते": "samajhte",
        "सफलता": "safalta",
        "लड़का": "ladka",
        "गाड़ी": "gaadi",
        "थोड़ा": "thoda",
        "बड़ा": "bada",
        "फिल्म": "film",
        "बातचीत": "baatcheet",
        "मुश्किल": "mushkil",
        "लगता": "lagta",
        "जानते": "jaante",
    }
    for devanagari, expected in samples.items():
        actual = _rule_based_romanize_text(devanagari)
        assert actual.lower() == expected.lower(), f"Expected {expected}, got {actual} for {devanagari}"


def test_phonetic_asr_mishearings_correction():
    """Verify common English ASR phonetic mishearings of Indian food and terms are corrected."""
    text = "It's a very fundamental question. Italy, Italy summer, or what about? You have Italy on one side, what about on the side"
    corrected = correct_phonetic_asr_mishearings(text)
    assert "Idli Sambar" in corrected
    assert "Vada Pav" in corrected
    assert "Italy summer" not in corrected.lower()


def test_devanagari_full_stops_removal():
    """Verify Devanagari full stops (danda । and double danda ॥) are removed cleanly."""
    text = "नमस्ते दोस्तों। आज का वीडियो बहुत खास है॥"
    cleaned = strip_devanagari_full_stops(text)
    assert "।" not in cleaned
    assert "॥" not in cleaned
    assert "नमस्ते दोस्तों" in cleaned


def test_is_hindi_or_hinglish_detection():
    """Verify language detection catches both Devanagari and conversational Hinglish."""
    assert is_hindi_or_hinglish_text("नमस्ते दोस्तों") is True
    assert is_hindi_or_hinglish_text("kya baat kar rahe ho yaar") is True
    assert is_hindi_or_hinglish_text("yeh to vadapav aur idli sambar hai") is True
    assert is_hindi_or_hinglish_text("Italy summer or what about") is True
    assert is_hindi_or_hinglish_text("The quick brown fox jumps over the lazy dog.") is False


def test_align_words_timestamp_scale():
    """Verify word alignment preserves millisecond scale without distorting integer timings."""
    orig_words = [
        {"text": "Italy", "start": 120, "end": 450, "speaker": "A"},
        {"text": "summer", "start": 460, "end": 900, "speaker": "A"},
    ]
    aligned = align_words(orig_words, "Idli Sambar", 120, 900)
    assert len(aligned) == 2
    assert aligned[0]["text"] == "Idli"
    assert aligned[1]["text"] == "Sambar"
    assert isinstance(aligned[0]["start"], int)
    assert isinstance(aligned[1]["end"], int)
    assert aligned[0]["start"] == 120


def test_romanize_transcript_data_e2e():
    """Verify end-to-end transcript data romanization with ASR phonetic corrections."""
    data = {
        "language_code": "en",
        "utterances": [
            {
                "text": "Italy, Italy summer, or what about?",
                "start": 100,
                "end": 2000,
                "speaker": "A",
                "words": [
                    {"text": "Italy,", "start": 100, "end": 400},
                    {"text": "Italy", "start": 410, "end": 700},
                    {"text": "summer,", "start": 710, "end": 1200},
                    {"text": "or", "start": 1210, "end": 1400},
                    {"text": "what", "start": 1410, "end": 1700},
                    {"text": "about?", "start": 1710, "end": 2000},
                ],
            }
        ],
        "words": [],
        "text": "Italy, Italy summer, or what about?",
    }
    processed = romanize_transcript_data(data)
    result_text = processed["text"].lower()
    assert "sambar" in result_text or "vadapav" in result_text or "vada pav" in result_text
    assert len(processed["words"]) > 0
