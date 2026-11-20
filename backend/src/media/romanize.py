"""Romanization / transliteration of Devanagari Hindi text to Romanized Hindi (Hinglish).

Produces readable, natural Latin-script Hindi captions (e.g. 'मेरा नाम पार्थ है'
-> 'mera naam parth hai') so that standard Latin video fonts (TikTokSans, Poppins,
THEBOLDFONT, BebasNeue, etc.) render captions without missing glyph boxes or broken
conjuncts, and match the standard short-form creator style.
"""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEVANAGARI_RANGE = re.compile(r"[\u0900-\u097F]")

VOWELS = {
    "अ": "a",
    "आ": "aa",
    "इ": "i",
    "ई": "ee",
    "उ": "u",
    "ऊ": "oo",
    "ऋ": "ri",
    "ए": "e",
    "ऐ": "ai",
    "ओ": "o",
    "औ": "au",
    "अं": "an",
    "अः": "ah",
    "ऑ": "o",
}

MATRAS = {
    "ा": "aa",
    "ि": "i",
    "ी": "i",
    "ु": "u",
    "ू": "u",
    "ृ": "ri",
    "े": "e",
    "ै": "ai",
    "ो": "o",
    "ौ": "au",
    "ॉ": "o",
}

CONSONANTS = {
    "क": "k",
    "ख": "kh",
    "ग": "g",
    "घ": "gh",
    "ङ": "ng",
    "च": "ch",
    "छ": "chh",
    "ज": "j",
    "झ": "jh",
    "ञ": "ny",
    "ट": "t",
    "ठ": "th",
    "ड": "d",
    "ढ": "dh",
    "ण": "n",
    "त": "t",
    "थ": "th",
    "द": "d",
    "ध": "dh",
    "न": "n",
    "प": "p",
    "फ": "f",
    "ब": "b",
    "भ": "bh",
    "म": "m",
    "य": "y",
    "र": "r",
    "ल": "l",
    "व": "v",
    "श": "sh",
    "ष": "sh",
    "स": "s",
    "ह": "h",
    "क़": "q",
    "ख़": "kh",
    "ग़": "gh",
    "ज़": "z",
    "ड़": "d",
    "ढ़": "dh",
    "फ़": "f",
}

VIRAMA = "्"
ANUSVARA = "ं"
CHANDRABINDU = "ँ"
VISARGA = "ः"
NUKTA = "़"

CONJUNCTS = {
    "क्ष": "ksh",
    "त्र": "tr",
    "ज्ञ": "gy",
    "श्र": "shr",
}

# High-frequency conversational Hindi / Hinglish vocabulary
HINDI_DICTIONARY: Dict[str, str] = {
    # Pronouns & Possessives
    "मेरा": "mera",
    "मेरी": "meri",
    "मेरे": "mere",
    "तेरा": "tera",
    "तेरी": "teri",
    "तेरे": "tere",
    "उसका": "uska",
    "उसकी": "uski",
    "उसके": "uske",
    "इसका": "iska",
    "इसकी": "iski",
    "इसके": "iske",
    "हमारा": "hamara",
    "हमारी": "hamari",
    "हमारे": "hamare",
    "तुम्हारा": "tumhara",
    "तुम्हारी": "tumhari",
    "तुम्हारे": "tumhare",
    "आपका": "aapka",
    "आपकी": "aapki",
    "आपके": "aapke",
    "हम": "hum",
    "तुम": "tum",
    "आप": "aap",
    "मैं": "main",
    "मुझ": "mujh",
    "तुझ": "tujh",
    "मुझे": "mujhe",
    "तुम्हें": "tumhein",
    "हमें": "humein",
    "उन्हें": "unhein",
    "उसे": "use",
    "इसे": "ise",
    "खुद": "khud",
    "अपना": "apna",
    "अपनी": "apni",
    "अपने": "apne",
    "यह": "yeh",
    "वह": "woh",
    "ये": "ye",
    "वे": "woh",
    # Verbs / Auxiliaries
    "है": "hai",
    "हैं": "hain",
    "हो": "ho",
    "हूँ": "hoon",
    "हूं": "hoon",
    "था": "tha",
    "थी": "thi",
    "थे": "the",
    "करेंगे": "karenge",
    "करूंगा": "karunga",
    "करूंगी": "karungi",
    "करता": "karta",
    "करती": "karti",
    "करते": "karte",
    "करना": "karna",
    "कर": "kar",
    "किया": "kiya",
    "करें": "karein",
    "बताएं": "batayein",
    "देखें": "dekhein",
    "जानें": "jaanein",
    "रहें": "rahein",
    "लें": "lein",
    "दें": "dein",
    "सकता": "sakta",
    "सकती": "sakti",
    "सकते": "sakte",
    "होगा": "hoga",
    "होगी": "hogi",
    "होंगे": "honge",
    "होता": "hota",
    "होती": "hoti",
    "होते": "hote",
    "होना": "hona",
    "जाना": "jaana",
    "जा": "jaa",
    "गया": "gaya",
    "गई": "gayi",
    "गए": "gaye",
    "आना": "aana",
    "आ": "aa",
    "आया": "aaya",
    "आई": "aayi",
    "आए": "aaye",
    "देखना": "dekhna",
    "देखो": "dekho",
    "देखा": "dekha",
    "सुनना": "sunna",
    "सुनो": "suno",
    "सुना": "suna",
    "बोलना": "bolna",
    "बोलो": "bolo",
    "बोला": "bola",
    "कहना": "kahna",
    "कहा": "kaha",
    "रहना": "rahna",
    "रहा": "raha",
    "रही": "rahi",
    "रहे": "rahe",
    # Questions
    "क्या": "kya",
    "क्यों": "kyun",
    "कैसे": "kaise",
    "कहाँ": "kahan",
    "कहा": "kaha",
    "कब": "kab",
    "कौन": "kaun",
    "कितना": "kitna",
    "कितनी": "kitni",
    "कितने": "kitne",
    # Connectors & Adverbs
    "और": "aur",
    "या": "ya",
    "भी": "bhi",
    "तो": "to",
    "में": "mein",
    "पर": "par",
    "से": "se",
    "को": "ko",
    "का": "ka",
    "की": "ki",
    "के": "ke",
    "ने": "ne",
    "तक": "tak",
    "नहीं": "nahi",
    "नही": "nahi",
    "हाँ": "haan",
    "हां": "haan",
    "ना": "na",
    "मत": "mat",
    "अगर": "agar",
    "लेकिन": "lekin",
    "मगर": "magar",
    "क्योंकि": "kyunki",
    "इसलिए": "isliye",
    "तब": "tab",
    "जब": "jab",
    "अब": "ab",
    "यहाँ": "yahan",
    "यहाँ": "yahan",
    "वहाँ": "wahan",
    "यहाँ": "yahan",
    "वहां": "wahan",
    "जहाँ": "jahan",
    "बहुत": "bahut",
    "ज़्यादा": "zyada",
    "कम": "kam",
    "थोड़ा": "thoda",
    "थोड़ी": "thodi",
    "काफी": "kaafi",
    "सिर्फ": "sirf",
    "बस": "bas",
    "शायद": "shayad",
    # Nouns & Common Words
    "नाम": "naam",
    "काम": "kaam",
    "दाम": "daam",
    "बात": "baat",
    "रात": "raat",
    "दिन": "din",
    "आज": "aaj",
    "कल": "kal",
    "समय": "samay",
    "वक्त": "waqt",
    "साल": "saal",
    "महीना": "mahina",
    "लोग": "log",
    "सब": "sab",
    "सबको": "sabko",
    "दोस्त": "dost",
    "दोस्तों": "doston",
    "भाई": "bhai",
    "यार": "yaar",
    "बेटा": "beta",
    "घर": "ghar",
    "गाड़ी": "gaadi",
    "पैसा": "paisa",
    "पैसे": "paise",
    "दुनिया": "duniya",
    "ज़िन्दगी": "zindagi",
    "जिंदगी": "zindagi",
    "नमस्ते": "namaste",
    "धन्यवाद": "dhanyawad",
    "शुक्रिया": "shukriya",
    "स्वागत": "swagat",
    "अच्छा": "achha",
    "अच्छी": "achhi",
    "अच्छे": "achhe",
    "बुरा": "bura",
    "बुरी": "buri",
    "बुरे": "bure",
    "बड़ा": "bada",
    "बड़ी": "badi",
    "बड़े": "bade",
    "छोटा": "chhota",
    "छोटी": "chhoti",
    "छोटे": "chhote",
    "नया": "naya",
    "नई": "nayi",
    "नए": "naye",
    "पहला": "pehla",
    "पहली": "pehli",
    "पहले": "pehle",
    "दूसरा": "doosra",
    "तीसरा": "teesra",
    "सही": "sahi",
    "गलत": "galat",
    "सच": "sach",
    "झूठ": "jhooth",
    # Creator / Social / Digital terms
    "यूट्यूब": "YouTube",
    "इंस्टाग्राम": "Instagram",
    "फेसबुक": "Facebook",
    "ट्विटर": "Twitter",
    "व्हाट्सएप": "WhatsApp",
    "वीडियो": "video",
    "ऑडियो": "audio",
    "चैनल": "channel",
    "सब्सक्राइब": "subscribe",
    "सब्सक्राइबर्स": "subscribers",
    "लाइक": "like",
    "कमेंट": "comment",
    "शेयर": "share",
    "फॉलो": "follow",
    "फॉलोअर्स": "followers",
    "व्यूज": "views",
    "व्यूज़": "views",
    "पोस्ट": "post",
    "स्टोरी": "story",
    "रील": "reel",
    "रील्स": "reels",
    "शॉर्ट्स": "shorts",
    "लिंक": "link",
    "बायो": "bio",
    "कंटेंट": "content",
    "क्रिएटर": "creator",
    "इन्फ्लुएंसर": "influencer",
    "वायरल": "viral",
    "ट्रेंडिंग": "trending",
    "ट्रेंड": "trend",
    "नोटिफिकेशन": "notification",
    "बेल": "bell",
    "आइकन": "icon",
    "क्लिक": "click",
    "डाउनलोड": "download",
    "अपलोड": "upload",
    "फोटो": "photo",
    # Tech, Computing & Internet
    "कंप्यूटर": "computer",
    "लैपटॉप": "laptop",
    "मोबाइल": "mobile",
    "फोन": "phone",
    "स्क्रीन": "screen",
    "कैमरा": "camera",
    "माइक": "mic",
    "इंटरनेट": "internet",
    "वेबसाइट": "website",
    "ऐप": "app",
    "एप": "app",
    "सॉफ्टवेयर": "software",
    "सिस्टम": "system",
    "डेटा": "data",
    "सर्वर": "server",
    "क्लाउड": "cloud",
    "कोडिंग": "coding",
    "कोड": "code",
    "प्रोग्रामिंग": "programming",
    "डेवलपर": "developer",
    "मशीन": "machine",
    "लर्निंग": "learning",
    "आर्टिफिशियल": "artificial",
    "इंटेलिजेंस": "intelligence",
    "टूल": "tool",
    "टूल्स": "tools",
    "प्लेटफॉर्म": "platform",
    "पासवर्ड": "password",
    "अकाउंट": "account",
    "अपडेट": "update",
    "फीचर": "feature",
    "फीचर्स": "features",
    "बटन": "button",
    "ऑनलाइन": "online",
    "ऑफलाइन": "offline",
    "एडिट": "edit",
    "एडिटिंग": "editing",
    # Career, Business & Finance
    "जॉब": "job",
    "करियर": "career",
    "इंटरव्यू": "interview",
    "सैलरी": "salary",
    "ऑफिस": "office",
    "कंपनी": "company",
    "बिजनेस": "business",
    "स्टार्टअप": "startup",
    "मार्केटिंग": "marketing",
    "सेल्स": "sales",
    "क्लाइंट": "client",
    "क्लाइंट्स": "clients",
    "मीटिंग": "meeting",
    "कॉल": "call",
    "प्रोजेक्ट": "project",
    "टीम": "team",
    "बॉस": "boss",
    "वर्क": "work",
    "मनी": "money",
    "प्रॉफिट": "profit",
    "मार्केट": "market",
    # Conversational English loanwords
    "प्रॉब्लम": "problem",
    "सॉल्यूशन": "solution",
    "आईडिया": "idea",
    "प्लान": "plan",
    "फोकस": "focus",
    "गोल": "goal",
    "गोल्स": "goals",
    "रिजल्ट": "result",
    "सक्सेस": "success",
    "फेल": "fail",
    "चांस": "chance",
    "ऑप्शन": "option",
    "पॉइंट": "point",
    "पॉइंट्स": "points",
    "रीजन": "reason",
    "क्वेश्चन": "question",
    "आंसर": "answer",
    "डिटेल": "detail",
    "एग्जांपल": "example",
    "सीक्रेट": "secret",
    "ट्रिक": "trick",
    "टिप": "tip",
    "टिप्स": "tips",
    "लेवल": "level",
    "स्टेप": "step",
    "स्टेप्स": "steps",
    "प्रैक्टिस": "practice",
    "एक्सपीरियंस": "experience",
    "नॉलेज": "knowledge",
    "स्किल": "skill",
    "स्किल्स": "skills",
    "टाइम": "time",
    "लाइफ": "life",
    "गाइज": "guys",
    "गाइज़": "guys",
    "ब्रो": "bro",
    "ड्यूड": "dude",
    "फ्रेंड": "friend",
    "फ्रेंड्स": "friends",
    "थैंक्स": "thanks",
    "सॉरी": "sorry",
    "प्लीज": "please",
    "प्लिज": "please",
    "ओके": "okay",
    "हेलो": "hello",
    "हाय": "hi",
    "बाय": "bye",
    "सिंपल": "simple",
    "इजी": "easy",
    "हार्ड": "hard",
    "फास्ट": "fast",
    "स्लो": "slow",
    "बेस्ट": "best",
    "परफेक्ट": "perfect",
    "सुपर": "super",
    "क्रेजी": "crazy",
    "कूल": "cool",
    "अमेजिंग": "amazing",
    "इंटरेस्टिंग": "interesting",
    "इम्पॉर्टेंट": "important",
    "एक्चुअली": "actually",
    "बेसिकली": "basically",
    "लिटरली": "literally",
    "डेफिनेटली": "definitely",
    "ऑब्वियसली": "obviously",
    "नॉर्मल": "normal",
    "कॉमन": "common",
    "स्पेशली": "specially",
    "सीरियस": "serious",
    "रियल": "real",
    "फेक": "fake",
    "डायरेक्ट": "direct",
    "स्मार्ट": "smart",
    "क्लियर": "clear",
    "स्टार्ट": "start",
    "स्टॉप": "stop",
    "रेडी": "ready",
    "चेक": "check",
    "ट्राई": "try",
    "टेस्ट": "test",
    "चेंज": "change",
    "हेल्प": "help",
    "सपोर्ट": "support",
    "स्कूल": "school",
    "कॉलेज": "college",
    "दिल्ली": "dilli",
    "भारत": "bharat",
    "इंडिया": "india",
    "हिंदी": "hindi",
    "हिन्दी": "hindi",
    "पार्थ": "parth",
    # Indian Foods & Dishes
    "इडली": "idli",
    "सांभर": "sambar",
    "सांबर": "sambar",
    "वड़ा": "vada",
    "पाव": "pav",
    "वड़ापाव": "vadapav",
    "दोसा": "dosa",
    "डोसा": "dosa",
    "चटनी": "chutney",
    "बिरयानी": "biryani",
    "रोटी": "roti",
    "चाय": "chai",
    "समोसा": "samosa",
    "छोले": "chhole",
    "भटूरे": "bhature",
    "पनीर": "paneer",
    "दाल": "dal",
    "चावल": "chawal",
    "सब्जी": "sabzi",
    "पराठा": "paratha",
    # Conversational & Verbal Inflections
    "सफलता": "safalta",
    "बातचीत": "baatcheet",
    "मुश्किल": "mushkil",
    "आसान": "aasan",
    "फायदा": "faayda",
    "नुकसान": "nuksan",
    "फिल्म": "film",
    "दोस्त": "dost",
    "दोस्तों": "doston",
    "भाइयों": "bhaiyon",
    "लोगों": "logon",
    "बातों": "baaton",
    "चीजों": "cheezon",
    "समझते": "samajhte",
    "समझता": "samajhta",
    "समझती": "samajhti",
    "समझना": "samajhna",
    "करते": "karte",
    "रहते": "rehte",
    "चलते": "chalte",
    "बोलते": "bolte",
    "देखते": "dekhte",
    "सुनते": "sunte",
    "जानते": "jaante",
    "लगता": "lagta",
    "लगती": "lagti",
    "लगते": "lagte",
    "बनता": "banta",
    "चाहता": "chahta",
    "सकते": "sakte",
    "सकता": "sakta",
    "सकती": "sakti",
}


_SCHWA_CONSONANTS = r"(?:kh|gh|chh|ch|jh|th|dh|ph|bh|sh|ny|ng|[bcdfghjklmnpqrstvwxyz])"
_SCHWA_VOWELS = r"[aeiou]"


def _apply_schwa_deletion(roman: str) -> str:
    """Drop inherent schwa 'a' according to Hindi phonological rules."""
    if not roman:
        return ""
    # 1. Verbal & nominal inflectional suffixes:
    # -ate -> -te, -ata -> -ta, -ati -> -ti, -ato -> -to, -ake -> -ke, -ane -> -ne, -ana -> -na, -ani -> -ni, -akar -> -kar
    roman = re.sub(rf"({_SCHWA_CONSONANTS})a(te|ta|ti|to|ke|ne|na|ni|kar)\b", r"\1\2", roman)
    # 2. Abstract noun/adjective suffixes: -ta (safal-a-ta -> safalta)
    roman = re.sub(rf"({_SCHWA_CONSONANTS})a(ta|pan|baaz|daar)\b", r"\1\2", roman)
    # 3. VC_CV schwa drop for internal syllables in words of 3+ syllables (e.g. la-da-ka -> ladka)
    roman = re.sub(rf"({_SCHWA_VOWELS}{_SCHWA_CONSONANTS})a({_SCHWA_CONSONANTS}{_SCHWA_VOWELS})", r"\1\2", roman)
    # 4. Natural Hinglish convention: trailing long 'aa' in words of 4+ chars becomes 'a'
    if len(roman) > 3 and roman.endswith("aa"):
        roman = roman[:-1]
    if roman == "paav":
        roman = "pav"
    return roman


def contains_devanagari(text: str) -> bool:
    """Return True if text contains any Devanagari character."""
    if not text:
        return False
    return bool(DEVANAGARI_RANGE.search(text))


def _romanize_core(core: str) -> str:
    """Transliterate a purely Devanagari string to Romanized phonetic Hindi."""
    if core in HINDI_DICTIONARY:
        return HINDI_DICTIONARY[core]

    chars = list(core)
    n = len(chars)
    res: List[str] = []
    i = 0

    while i < n:
        ch = chars[i]

        # Check two-character nukta sequence (e.g. क + ़ -> क़)
        if i + 1 < n and chars[i + 1] == NUKTA:
            comb = ch + NUKTA
            if comb in CONSONANTS:
                ch = comb
                i += 1

        # Check conjuncts (e.g. क्ष, त्र, ज्ञ, श्र)
        if i + 2 < n and ch in ("क", "त", "ज", "श") and chars[i + 1] == VIRAMA:
            conj_pair = ch + chars[i + 2]
            if conj_pair in CONJUNCTS:
                res.append(CONJUNCTS[conj_pair])
                i += 3
                continue

        if ch in VOWELS:
            res.append(VOWELS[ch])
        elif ch in CONSONANTS:
            base = CONSONANTS[ch]
            next_ch = chars[i + 1] if i + 1 < n else None

            if next_ch == VIRAMA:
                # Consonant followed by halant: no inherent vowel
                res.append(base)
                i += 1
            elif next_ch in MATRAS:
                res.append(base + MATRAS[next_ch])
                i += 1
            elif next_ch in (ANUSVARA, CHANDRABINDU):
                res.append(base + "an")
                i += 1
            else:
                # Inherent vowel rule:
                # Hindi applies schwa-deletion at word-end.
                is_last = (i == n - 1)
                if is_last:
                    res.append(base)
                else:
                    res.append(base + "a")
        elif ch in MATRAS:
            res.append(MATRAS[ch])
        elif ch in (ANUSVARA, CHANDRABINDU):
            res.append("n")
        elif ch == VISARGA:
            res.append("h")
        elif ch == VIRAMA:
            pass
        else:
            res.append(ch)

        i += 1

    out = "".join(res)
    # Apply standard Hindi schwa deletion & phonetic tuning
    return _apply_schwa_deletion(out)


_GROQ_TRANSLATION_CACHE: Dict[str, str] = {}
_GROQ_WORD_CACHE: Dict[str, str] = {}
DEVANAGARI_FULL_STOPS = re.compile(r"[\u0964\u0965]+")

PHONETIC_ASR_REPLACEMENTS = [
    # Common speech-to-text phonetic hallucinations for Indian foods and terms
    (re.compile(r"\bitaly\s+summer\b", re.IGNORECASE), "Idli Sambar"),
    (re.compile(r"\bitaly(?=\s+(?:ya|or|aur|sambar|vadapav|vada|on\s+one\s+side|on\s+the\s+side|khao|khaana|dosa))\b", re.IGNORECASE), "Idli"),
    (re.compile(r"\b(ya|or|aur|sambar|dosa)\s+italy\b", re.IGNORECASE), r"\1 Idli"),
    (re.compile(r"\b(idli|sambar|ya|or|dosa)\s+what\s+about\b", re.IGNORECASE), r"\1 Vada Pav"),
    (re.compile(r"\bwhat\s+about(?=\s+(?:ya|or|idli|sambar|on\s+the\s+side|khao|khaana|dosa))\b", re.IGNORECASE), "Vada Pav"),
    (re.compile(r"\bwater\s+power\b", re.IGNORECASE), "Vada Pav"),
    (re.compile(r"\bwhat\s+a\s+pow\b", re.IGNORECASE), "Vada Pav"),
]


def correct_phonetic_asr_mishearings(text: str) -> str:
    """Pre-correct obvious phonetic ASR mishearings of Indian food and terms."""
    if not text:
        return ""
    res = str(text)
    for pat, repl in PHONETIC_ASR_REPLACEMENTS:
        res = pat.sub(repl, res)
    return res


HINGLISH_WORDS = frozenset({
    "kya", "kyun", "kyu", "kaise", "kaisa", "kaisi", "kahan", "kaha", "kab", "kisko", "kise",
    "yeh", "ye", "woh", "wo", "hai", "hain", "ho", "hoon", "hun", "tha", "thi", "the",
    "mein", "me", "se", "ko", "ka", "ki", "ke", "par", "pe", "aur", "nahi", "nhi", "na",
    "toh", "to", "ab", "jab", "tab", "hum", "humein", "tum", "tumhe", "aap", "aapko",
    "bhai", "yaar", "log", "logon", "baat", "baaten", "baatein", "karo", "karna", "karne",
    "kar", "raha", "rahe", "rahi", "diya", "de", "le", "liya", "kuch", "bohot", "bahut",
    "accha", "achha", "acha", "acchi", "achhi", "ek", "do", "teen", "char", "donon", "dono",
    "sab", "sabhi", "sirji", "aisa", "aisi", "aise", "waise", "waisa", "dekho", "dekh",
    "suno", "sun", "bolo", "bol", "bolte", "chahiye", "hoga", "hogi", "honge", "hota", "hoti",
    "hote", "bhi", "sirf", "lekin", "magar", "kyunki", "isliye", "matlab", "shuru", "khatam",
    "bich", "beech", "sambar", "vadapav", "vada", "pav", "idli", "dosa", "roti", "paise", "paisa",
    "chutney", "biryani", "chai", "paneer", "dal", "samosa", "chhole", "bhature", "paratha",
    "chawal", "sabzi", "safalta", "namaste", "shukriya", "dhanyawad", "zindagi", "duniya", "desh",
    "bharat", "batao", "bataiye", "samajh", "aaya", "aayi", "gaya", "gayi", "karte", "karti",
    "karta", "rakho", "paas", "dur", "andar", "bahar", "uper", "niche", "peeche", "aage",
})


def is_hindi_or_hinglish_text(text: str) -> bool:
    """Return True if text contains Devanagari or notable Hinglish vocabulary."""
    if not text:
        return False
    if DEVANAGARI_RANGE.search(str(text)):
        return True
    corrected = correct_phonetic_asr_mishearings(str(text))
    if corrected != str(text):
        return True
    tokens = [t for t in re.findall(r"[a-zA-Z]+", corrected.lower()) if t != "the"]
    matches = sum(1 for t in tokens if t in HINGLISH_WORDS)
    return matches >= 2


def strip_devanagari_full_stops(text: str) -> str:
    """Remove Hindi / Devanagari full stops (। and ॥) and normalize spacing."""
    if not text:
        return ""
    cleaned = DEVANAGARI_FULL_STOPS.sub("", str(text))
    return re.sub(r"[ \t]+", " ", cleaned).strip()


def _get_groq_credentials() -> tuple[Optional[str], str]:
    key = os.getenv("GROQ_API_KEY")
    model = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
    if not key:
        try:
            from ..config import get_config
            c = get_config()
            key = getattr(c, "groq_api_key", None)
            model = getattr(c, "groq_model", model)
        except Exception:
            pass
    if not key:
        for env_path in (
            Path(__file__).resolve().parents[2] / ".env",
            Path(__file__).resolve().parents[3] / ".env",
        ):
            if env_path.exists():
                try:
                    for line in env_path.read_text(encoding="utf-8").splitlines():
                        if line.startswith("GROQ_API_KEY=") and not key:
                            key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        elif line.startswith("GROQ_MODEL=") and not model:
                            model = line.split("=", 1)[1].strip().strip('"').strip("'")
                except Exception:
                    pass
    return key, model or "qwen/qwen3.8-27b"


def _split_into_sentences(text: str) -> List[str]:
    """Split text into sentences or manageable sentence-sized clauses."""
    if not text:
        return []
    raw_parts = re.split(r"(?<=[.!?\u0964\u0965])\s+", text.strip())
    parts: List[str] = []
    for part in raw_parts:
        part = part.strip()
        if not part:
            continue
        words = part.split()
        if len(words) > 35:
            for i in range(0, len(words), 25):
                chunk = " ".join(words[i : i + 25])
                if chunk:
                    parts.append(chunk)
        else:
            parts.append(part)
    return parts if parts else [text.strip()]


def translate_sentences_with_groq(
    sentences: List[str],
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    force_all: bool = False,
) -> List[str]:
    """Translate and romanize Hindi/Hinglish sentences using Groq LLM.

    Verifies sentence coherence and natural grammar, keeping English terms in
    correct English spelling (e.g. debentures, stock market, LinkedIn, finance),
    and correcting phonetic speech-to-text mishearings (e.g. 'Italy summer' -> 'Idli Sambar',
    'what about' -> 'Vadapav').
    """
    if not sentences:
        return []

    needed_indices: List[int] = []
    needed_sentences: List[str] = []
    results: List[Optional[str]] = [None] * len(sentences)

    for i, s in enumerate(sentences):
        cleaned = correct_phonetic_asr_mishearings(str(s).strip())
        if not force_all and not contains_devanagari(cleaned):
            results[i] = cleaned
        elif cleaned in _GROQ_TRANSLATION_CACHE:
            results[i] = _GROQ_TRANSLATION_CACHE[cleaned]
        else:
            needed_indices.append(i)
            needed_sentences.append(cleaned)

    if not needed_sentences:
        return [r if r is not None else "" for r in results]

    key, default_model = _get_groq_credentials()
    use_key = api_key or key
    use_model = model or default_model

    if not use_key:
        for idx, s in zip(needed_indices, needed_sentences):
            results[idx] = _rule_based_romanize_text(s)
        return [r if r is not None else "" for r in results]

    # Create batches bounded by both sentence count and word count
    batches: List[tuple[List[str], List[int]]] = []
    curr_chunk: List[str] = []
    curr_indices: List[int] = []
    curr_words = 0

    for idx, s in zip(needed_indices, needed_sentences):
        w_count = len(s.split())
        if curr_chunk and (len(curr_chunk) >= 5 or (curr_words + w_count) > 150):
            batches.append((curr_chunk, curr_indices))
            curr_chunk = []
            curr_indices = []
            curr_words = 0
        curr_chunk.append(s)
        curr_indices.append(idx)
        curr_words += w_count
    if curr_chunk:
        batches.append((curr_chunk, curr_indices))

    for chunk_sentences, chunk_indices in batches:
        prompt = (
            "You are an expert audio transcript and subtitle editor for Indian Hindi and Hinglish content.\n"
            "The input sentences are ASR (speech-to-text) transcripts that often contain phonetic mishearings "
            "where speech recognition mishears Indian foods, Hindi phrases, or names as nonsensical English words.\n"
            "Examples:\n"
            "- 'Italy summer' or 'Italy' -> 'Idli Sambar' / 'Idli'\n"
            "- 'what about' -> 'Vada Pav' / 'Vadapav'\n"
            "- other phonetic distortions of Hindi/Hinglish speech\n\n"
            "Your task:\n"
            "1. Fix all phonetic transcription errors, misheard Indian foods/places/names, and nonsensical words so the sentences make complete, coherent sense in context.\n"
            "2. If the text is in Hindi/Hinglish, write it in natural conversational Romanized Hindi (Hinglish with Latin alphabet).\n"
            "3. Keep legitimate English terms in proper English spelling (e.g. shot taking, filmmaking, fundamental question, debentures, LinkedIn, finance).\n"
            "4. Do NOT output any Devanagari script or Devanagari full stops (। or ॥).\n"
            "Return a JSON object with a single key 'translations' containing the list of translated/corrected strings."
        )
        user_content = "Sentences to translate/correct:\n" + "\n".join(
            f"{j + 1}. {s}" for j, s in enumerate(chunk_sentences)
        )

        success = False
        for attempt in range(3):
            try:
                req = urllib.request.Request(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {use_key}",
                        "Content-Type": "application/json",
                        "User-Agent": "Mozilla/5.0",
                    },
                    data=json.dumps({
                        "model": use_model,
                        "messages": [
                            {"role": "system", "content": prompt},
                            {"role": "user", "content": user_content},
                        ],
                        "response_format": {"type": "json_object"},
                        "max_tokens": 500,
                        "temperature": 0.1,
                    }).encode("utf-8"),
                )
                with urllib.request.urlopen(req, timeout=20) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                    content = payload["choices"][0]["message"]["content"]
                    parsed = json.loads(content)
                    trans_list = parsed.get("translations", [])

                    for j, trans in enumerate(trans_list):
                        if j < len(chunk_indices):
                            clean_trans = strip_devanagari_full_stops(trans)
                            orig_s = chunk_sentences[j]
                            _GROQ_TRANSLATION_CACHE[orig_s] = clean_trans
                            results[chunk_indices[j]] = clean_trans

                            orig_tokens = orig_s.split()
                            trans_tokens = clean_trans.split()
                            if len(orig_tokens) == len(trans_tokens):
                                for o_tok, t_tok in zip(orig_tokens, trans_tokens):
                                    c_o = re.sub(r"^[^\w]+|[^\w]+$", "", o_tok)
                                    c_t = re.sub(r"^[^\w]+|[^\w]+$", "", t_tok)
                                    if c_o and c_t:
                                        _GROQ_WORD_CACHE[c_o] = c_t
                    success = True
                    import time
                    time.sleep(0.3)
                    break
            except urllib.error.HTTPError as http_err:
                if http_err.code == 429 and attempt < 2:
                    import time
                    retry_after = 5.0
                    try:
                        retry_after = float(http_err.headers.get("retry-after", 5.0))
                    except Exception:
                        pass
                    time.sleep(min(12.0, max(2.0, retry_after)))
                    continue
                logger.warning("Groq sentence translation failed (%s), using fallback", http_err)
                break
            except Exception as exc:
                logger.warning("Groq sentence translation failed, using fallback: %s", exc)
                break

        if not success:
            for j in range(len(chunk_indices)):
                idx = chunk_indices[j]
                if results[idx] is None:
                    results[idx] = strip_devanagari_full_stops(_rule_based_romanize_text(chunk_sentences[j]))

    for idx, s in zip(needed_indices, needed_sentences):
        if results[idx] is None:
            results[idx] = strip_devanagari_full_stops(_rule_based_romanize_text(s))

    return [r if r is not None else "" for r in results]


def align_words(
    orig_words: List[Dict[str, Any]],
    translated_text: str,
    utt_start: float,
    utt_end: float,
) -> List[Dict[str, Any]]:
    """Align word timestamps to translated text tokens."""
    new_tokens = [
        w for raw_w in re.split(r"\s+", translated_text.strip())
        for w in [strip_devanagari_full_stops(raw_w)]
        if w
    ]
    if not new_tokens:
        return [
            w for w in orig_words
            if strip_devanagari_full_stops(str(w.get("text", "")))
        ]

    if len(new_tokens) == len(orig_words):
        aligned = []
        for orig, new_t in zip(orig_words, new_tokens):
            w = dict(orig)
            w["text"] = new_t
            aligned.append(w)
        return aligned

    start_bound = orig_words[0].get("start", utt_start) if orig_words else utt_start
    end_bound = orig_words[-1].get("end", utt_end) if orig_words else utt_end
    is_ms = isinstance(start_bound, (int, float)) and (start_bound > 100 or end_bound > 100 or utt_end > 100)

    duration = max(0.1, float(end_bound) - float(start_bound))
    total_chars = sum(len(w) for w in new_tokens) or len(new_tokens)
    aligned = []
    current_time = float(start_bound)
    for i, t in enumerate(new_tokens):
        token_duration = (len(t) / total_chars) * duration
        w_start = current_time
        w_end = min(float(end_bound), current_time + token_duration)
        orig_ref = orig_words[min(i, len(orig_words) - 1)] if orig_words else {}
        w_dict: Dict[str, Any] = {
            "text": t,
            "start": int(round(w_start)) if is_ms else round(w_start, 3),
            "end": int(round(w_end)) if is_ms else round(w_end, 3),
        }
        if "speaker" in orig_ref:
            w_dict["speaker"] = orig_ref["speaker"]
        if "confidence" in orig_ref:
            w_dict["confidence"] = orig_ref["confidence"]
        aligned.append(w_dict)
        current_time += token_duration
    return aligned


def _rule_based_romanize_word(word: str) -> str:
    """Fallback rule-based romanization of a single word."""
    word = strip_devanagari_full_stops(word)
    if not word or not contains_devanagari(word):
        return word

    match = re.match(r"^([^\u0900-\u097F]*)([\u0900-\u097F]+)([^\u0900-\u097F]*)$", word)
    if not match:
        res = []
        token = ""
        for ch in word:
            if "\u0900" <= ch <= "\u097F":
                token += ch
            else:
                if token:
                    res.append(_romanize_core(token))
                    token = ""
                res.append(ch)
        if token:
            res.append(_romanize_core(token))
        return "".join(res)

    prefix, core, suffix = match.groups()
    romanized = _romanize_core(core)
    return prefix + romanized + suffix


def _rule_based_romanize_text(text: str) -> str:
    """Fallback rule-based romanization of text tokens."""
    text = strip_devanagari_full_stops(text)
    if not text or not contains_devanagari(text):
        return text

    tokens = re.split(r"(\s+)", text)
    result = []
    for token in tokens:
        if token.isspace() or not token:
            result.append(token)
        else:
            cleaned_tok = strip_devanagari_full_stops(token)
            if cleaned_tok:
                result.append(_rule_based_romanize_word(cleaned_tok))
    return "".join(result)


def romanize_word(word: str) -> str:
    """Romanize a single word, preserving surrounding punctuation."""
    word = strip_devanagari_full_stops(word)
    if not word or not contains_devanagari(word):
        return word

    cleaned = word.strip()
    if cleaned in _GROQ_WORD_CACHE:
        return _GROQ_WORD_CACHE[cleaned]
    if cleaned in _GROQ_TRANSLATION_CACHE:
        return _GROQ_TRANSLATION_CACHE[cleaned]

    return _rule_based_romanize_word(word)


def romanize_text(text: str) -> str:
    """Romanize all Devanagari text in a block, using Groq when available."""
    text = strip_devanagari_full_stops(text)
    if not text or not contains_devanagari(text):
        return text

    cleaned = text.strip()
    if cleaned in _GROQ_TRANSLATION_CACHE:
        return _GROQ_TRANSLATION_CACHE[cleaned]

    key, model = _get_groq_credentials()
    if key:
        try:
            translated = translate_sentences_with_groq([cleaned], api_key=key, model=model)
            if translated and translated[0]:
                return strip_devanagari_full_stops(translated[0])
        except Exception as exc:
            logger.warning("Groq text romanize failed: %s", exc)

    return _rule_based_romanize_text(text)


def romanize_transcript_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Romanize and verify all Hindi/Hinglish text in a transcript cache data dictionary.

    Uses Groq LLM to convert Hindi/Hinglish utterances into natural, verified
    Romanized English while keeping word-level timestamps synchronized for captions,
    and correcting phonetic speech-to-text mishearings (e.g. 'Italy summer' -> 'Idli Sambar').
    """
    if not isinstance(data, dict):
        return data

    utterances = data.get("utterances") or []
    if utterances:
        all_text = " ".join(str(u.get("text", "")) for u in utterances if isinstance(u, dict))
        all_text_corrected = correct_phonetic_asr_mishearings(all_text)
        lang_code = str(data.get("language_code") or "").lower()
        is_hindi = lang_code in {"hi", "hin", "hindi"} or is_hindi_or_hinglish_text(all_text_corrected)

        if is_hindi:
            valid_utts = [u for u in utterances if isinstance(u, dict) and u.get("text")]
            for u in valid_utts:
                raw_text = correct_phonetic_asr_mishearings(str(u.get("text", "")).strip())
                if not raw_text:
                    continue
                sents = _split_into_sentences(raw_text)
                translated_sents = translate_sentences_with_groq(sents, force_all=True)
                clean_trans = strip_devanagari_full_stops(" ".join(translated_sents))
                u["text"] = clean_trans
                u_words = u.get("words") or []
                u_start = float(u.get("start", 0))
                u_end = float(u.get("end", u_start + 1.0))
                if u_words:
                    u["words"] = align_words(u_words, clean_trans, u_start, u_end)
        else:
            dev_utts = [
                u for u in utterances
                if isinstance(u, dict) and contains_devanagari(u.get("text", ""))
            ]
            for u in dev_utts:
                raw_text = correct_phonetic_asr_mishearings(str(u.get("text", "")).strip())
                if not raw_text:
                    continue
                sents = _split_into_sentences(raw_text)
                translated_sents = translate_sentences_with_groq(sents)
                clean_trans = strip_devanagari_full_stops(" ".join(translated_sents))
                u["text"] = clean_trans
                u_words = u.get("words") or []
                u_start = float(u.get("start", 0))
                u_end = float(u.get("end", u_start + 1.0))
                if u_words:
                    u["words"] = align_words(u_words, clean_trans, u_start, u_end)

        all_aligned_words = []
        has_aligned_words = False
        for u in utterances:
            if isinstance(u, dict) and u.get("words"):
                for w in u["words"]:
                    w_text = strip_devanagari_full_stops(str(w.get("text", "")))
                    if w_text:
                        w["text"] = w_text
                        all_aligned_words.append(w)
                has_aligned_words = True

        if has_aligned_words and all_aligned_words:
            data["words"] = all_aligned_words

        data["text"] = strip_devanagari_full_stops(
            " ".join(
                str(u.get("text", "")) for u in utterances
                if isinstance(u, dict) and u.get("text")
            )
        )
    else:
        cleaned_words = []
        for word in data.get("words") or []:
            if isinstance(word, dict) and "text" in word:
                w_text = strip_devanagari_full_stops(romanize_word(str(word["text"])))
                if w_text:
                    word["text"] = w_text
                    cleaned_words.append(word)
            else:
                cleaned_words.append(word)
        data["words"] = cleaned_words

        main_text = data.get("text", "")
        if main_text:
            data["text"] = strip_devanagari_full_stops(romanize_text(main_text))

    return data

