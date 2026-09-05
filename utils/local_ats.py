"""Deterministic ATS overlap so the app stays useful without the LLM."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from utils.personas import Persona

TOKEN = re.compile(r"[a-z0-9][a-z0-9+.#/-]{1,}")
WEAK_PHRASES = (
    "responsible for",
    "helped with",
    "worked on",
    "participated in",
    "involved in",
    "tasked with",
    "duties included",
    "various tasks",
    "team player",
    "hard working",
)


@dataclass
class LocalATSResult:
    score: int
    overlap: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    weak_phrases: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower())


def _phrases_in(text: str, lexicon: tuple[str, ...]) -> list[str]:
    haystack = _normalize(text)
    found: list[str] = []
    for phrase in lexicon:
        if phrase in haystack and phrase not in found:
            found.append(phrase)
    return found


def score_local_ats(cv_text: str, jd_text: str, persona: Persona) -> LocalATSResult:
    cv = _normalize(cv_text)
    jd = _normalize(jd_text)
    if not cv or not jd:
        return LocalATSResult(score=0, notes=["Paste both a CV and a job description."])

    jd_terms = _phrases_in(jd, persona.lexicon)
    if not jd_terms:
        jd_tokens = {token for token in TOKEN.findall(jd) if len(token) > 3}
        cv_tokens = set(TOKEN.findall(cv))
        overlap = sorted(jd_tokens & cv_tokens)[:24]
        missing = sorted(jd_tokens - cv_tokens)[:18]
        ratio = len(overlap) / max(1, len(overlap) + len(missing))
        score = int(round(ratio * 100))
    else:
        overlap = [term for term in jd_terms if term in cv]
        missing = [term for term in jd_terms if term not in cv]
        ratio = len(overlap) / max(1, len(jd_terms))
        score = int(round(ratio * 100))

    weak = [phrase for phrase in WEAK_PHRASES if phrase in cv]
    notes: list[str] = []
    if len(cv) < 400:
        notes.append("CV is short — ATS parsers may under-index your experience.")
        score = max(0, score - 8)
    if weak:
        notes.append("Weak duty verbs detected. Rewrite them into achievements.")
        score = max(0, score - min(12, 3 * len(weak)))
    if missing:
        notes.append("Mirror missing JD terms only where they are truthful.")

    return LocalATSResult(
        score=max(0, min(100, score)),
        overlap=overlap[:20],
        missing=missing[:20],
        weak_phrases=weak,
        notes=notes,
    )
