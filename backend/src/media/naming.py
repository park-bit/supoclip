"""Naming helpers for exported and downloaded clips."""

import re
from typing import Optional


def sanitize_title_for_filename(title: Optional[str], max_chars: int = 150) -> str:
    """Sanitize video title for cross-platform filenames and Google Drive."""
    if not title:
        return "video"

    cleaned = title.strip()
    if cleaned.lower().endswith(".mp4"):
        cleaned = cleaned[:-4].strip()

    # Replace common path or separator characters with a space or dash
    cleaned = re.sub(r"[/\\|:]", " - ", cleaned)
    # Remove filesystem-illegal characters and control characters
    cleaned = re.sub(r'[\x00-\x1f\x7f*?"<>~#%&{}`@!$+=]', "", cleaned)
    # Collapse multiple spaces or dashes
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"-{2,}", "-", cleaned)
    cleaned = cleaned.strip(" .-_")

    if not cleaned:
        return "video"

    return cleaned[:max_chars].rstrip(" .-_")


def format_clip_filename(
    video_title: Optional[str],
    clip_number: int | str,
    preset: Optional[str] = None,
    ext: str = ".mp4",
) -> str:
    """Format clip filename as <ytvideoname>_<clip-number>[_<preset>].mp4"""
    clean_title = sanitize_title_for_filename(video_title)

    try:
        num = int(clip_number)
    except (ValueError, TypeError):
        num = str(clip_number).strip() or "1"

    base = f"{clean_title}_{num}"

    if preset and preset.lower() not in ("original", "none", ""):
        clean_preset = re.sub(r"[^a-zA-Z0-9_-]", "", preset.lower())
        if clean_preset:
            base = f"{base}_{clean_preset}"

    if not ext.startswith("."):
        ext = f".{ext}"

    return f"{base}{ext}"
