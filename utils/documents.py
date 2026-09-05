"""CV / JD ingest helpers."""

from __future__ import annotations

import io
import re
from typing import BinaryIO

BULLET_PREFIX = re.compile(r"^\s*(?:[-*•–—]|\d+[.)])\s+")
WEAK_LEAD = re.compile(
    r"^\s*(responsible for|helped|assisted|worked on|participated in|"
    r"involved in|tasked with|handled|duties included|was part of)\b",
    flags=re.IGNORECASE,
)


def normalize_whitespace(text: str) -> str:
    text = (text or "").replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pdf_text(file_obj: BinaryIO) -> str:
    from pypdf import PdfReader

    raw = file_obj.read()
    reader = PdfReader(io.BytesIO(raw))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    text = normalize_whitespace("\n".join(pages))
    if len(text) < 40:
        raise ValueError("Could not extract usable text from that PDF. Paste the CV instead.")
    return text


def split_cv_bullets(cv_text: str) -> list[str]:
    bullets: list[str] = []
    for raw_line in (cv_text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if BULLET_PREFIX.match(line):
            bullets.append(BULLET_PREFIX.sub("", line).strip())
        elif WEAK_LEAD.match(line) and len(line) > 24:
            bullets.append(line)
    return bullets


def detect_weak_bullets(cv_text: str, limit: int = 8) -> list[str]:
    weak: list[str] = []
    for bullet in split_cv_bullets(cv_text):
        if WEAK_LEAD.match(bullet) or _lacks_signal(bullet):
            weak.append(bullet)
        if len(weak) >= limit:
            break
    return weak


def _lacks_signal(bullet: str) -> bool:
    has_digit = any(char.isdigit() for char in bullet)
    has_percent = "%" in bullet
    action_verbs = (
        "built",
        "designed",
        "automated",
        "reduced",
        "increased",
        "led",
        "owned",
        "implemented",
        "delivered",
        "secured",
        "migrated",
        "cut",
        "improved",
    )
    has_verb = any(verb in bullet.lower() for verb in action_verbs)
    return len(bullet) > 28 and not has_digit and not has_percent and not has_verb
