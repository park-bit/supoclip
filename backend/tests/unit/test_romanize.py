"""Unit tests for Devanagari Hindi romanization."""

import pytest
from src.media.romanize import (
    contains_devanagari,
    romanize_word,
    romanize_text,
    romanize_transcript_data,
)


def test_contains_devanagari():
    assert contains_devanagari("मेरा नाम पार्थ है") is True
    assert contains_devanagari("Hello world") is False
    assert contains_devanagari("Video 123 !@#") is False
    assert contains_devanagari("") is False
    assert contains_devanagari("Mix: नमस्ते friend") is True


def test_romanize_user_exact_example():
    # User requirement: "mera naam parth hai"
    result = romanize_text("मेरा नाम पार्थ है")
    assert result.lower().rstrip(".") == "mera naam parth hai"


def test_romanize_common_phrases():
    cases = {
        "आप कैसे हो भाई?": "aap kaise ho bhai?",
        "आज हम बात करेंगे": "aaj hum baat karenge",
        "क्या चल रहा है दोस्त": "kya chal raha hai dost",
        "नमस्ते दोस्तों": "namaste doston",
        "चैनल को सब्सक्राइब करें": "channel ko subscribe karein",
    }
    for hindi, expected in cases.items():
        assert romanize_text(hindi).lower().rstrip("?.").strip() == expected.lower().rstrip("?.").strip()

    accha_result = romanize_text("यह बहुत अच्छा है").lower().rstrip("?.").strip()
    assert "accha" in accha_result or "achha" in accha_result


def test_romanize_leaves_english_intact():
    english_text = "This is a 100% English sentence with punctuation: wow!"
    assert romanize_text(english_text) == english_text


def test_romanize_mixed_hinglish():
    mixed = "mera नाम Parth hai aur ye mera YouTube channel है"
    expected = "mera naam parth hai aur ye mera youtube channel hai"
    assert romanize_text(mixed).lower().rstrip(".") == expected

    devanagari_mixed = "हेलो गाइज, एक्चुअली यह प्रॉब्लम बहुत कॉमन है अगर आप स्टार्टअप या बिजनेस स्टार्ट कर रहे हो"
    assert "guys" in romanize_text(devanagari_mixed).lower()
    assert "problem" in romanize_text(devanagari_mixed).lower()


def test_romanize_transcript_data():
    cache_data = {
        "version": 1,
        "words": [
            {"text": "मेरा", "start": 100, "end": 400},
            {"text": "नाम", "start": 410, "end": 700},
            {"text": "पार्थ", "start": 710, "end": 1000},
            {"text": "है", "start": 1010, "end": 1300},
            {"text": "bro", "start": 1310, "end": 1500},
        ],
        "utterances": [
            {
                "text": "मेरा नाम पार्थ है bro",
                "start": 100,
                "end": 1500,
                "words": [
                    {"text": "मेरा", "start": 100, "end": 400},
                    {"text": "नाम", "start": 410, "end": 700},
                    {"text": "पार्थ", "start": 710, "end": 1000},
                    {"text": "है", "start": 1010, "end": 1300},
                    {"text": "bro", "start": 1310, "end": 1500},
                ],
            }
        ],
        "text": "मेरा नाम पार्थ है bro",
    }

    result = romanize_transcript_data(cache_data)

    assert [w["text"].lower().rstrip(".,") for w in result["words"]] == ["mera", "naam", "parth", "hai", "bro"]
    assert result["text"].lower().rstrip(".,") == "mera naam parth hai, bro" or "mera naam parth hai bro" in result["text"].lower()
    assert [w["text"].lower().rstrip(".,") for w in result["utterances"][0]["words"]] == ["mera", "naam", "parth", "hai", "bro"]
    # Check timings are preserved
    assert result["words"][0]["start"] == 100
    assert result["words"][0]["end"] == 400


def test_strip_devanagari_full_stops():
    from src.media.romanize import strip_devanagari_full_stops

    assert strip_devanagari_full_stops("नमस्ते दोस्तों। आज हम बात करेंगे॥") == "नमस्ते दोस्तों आज हम बात करेंगे"
    assert strip_devanagari_full_stops("।") == ""
    assert strip_devanagari_full_stops("॥") == ""
    assert strip_devanagari_full_stops("करेंगे।") == "करेंगे"

    # In full romanized sentences and words
    assert "।" not in romanize_text("नमस्ते दोस्तों। आज बात करेंगे॥")
    assert "॥" not in romanize_text("नमस्ते दोस्तों। आज बात करेंगे॥")
    assert romanize_word("करेंगे।") == "karenge"
    assert romanize_word("।") == ""
    assert romanize_word("॥") == ""


def test_is_hindi_or_hinglish_detection():
    from src.media.romanize import is_hindi_or_hinglish_text

    hinglish = "kya barhiya creative baaten ho rahi hain donon ke bich mein? Italy, Italy summer, or what about?"
    assert is_hindi_or_hinglish_text(hinglish) is True

    pure_english = "Today we are building an autonomous software engineering workflow with Next.js and Python."
    assert is_hindi_or_hinglish_text(pure_english) is False


