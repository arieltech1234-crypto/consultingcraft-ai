"""Small testable helpers shared by the Streamlit UI."""

from __future__ import annotations

import re
from pathlib import Path


ALLOWED_UPLOAD_EXTENSIONS = {".docx", ".pdf", ".png", ".jpg", ".jpeg"}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024


def validate_upload(filename: str, content: bytes) -> None:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_UPLOAD_EXTENSIONS:
        raise ValueError(f"{filename}: unsupported file type.")
    if not content:
        raise ValueError(f"{filename}: file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError(f"{filename}: file exceeds the 8 MB limit.")


def meaningful_lines(text: str) -> list[str]:
    noise_keywords = (
        "how to use",
        "chronological index",
        "source bank",
        "this document",
        "items without",
        "ordered from",
        "grouped by",
        "repeated source",
        "life stage",
        "current/intended",
    )
    result = []
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip(" •\t")
        lowered = line.lower()
        if len(line) < 18 or any(noise in lowered for noise in noise_keywords):
            continue
        if re.fullmatch(r"\d+\.", line):
            continue
        result.append(line)
    return result


def build_contact_line(profile: dict) -> str:
    ordered = [
        profile.get("email", ""),
        profile.get("phone", ""),
        profile.get("location", ""),
        profile.get("linkedin", ""),
    ]
    return " | ".join(value.strip() for value in ordered if value and value.strip())


def safe_download_stem(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", name.strip()).strip("_")
    return cleaned or "candidate"
