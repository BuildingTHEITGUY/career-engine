"""Action-verb rewriter for weak CV bullets."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from config import Settings
from utils.documents import detect_weak_bullets
from utils.k2_client import K2APIError, K2Client
from utils.parsers import ParseError, as_dict_list, as_str_list, extract_json_object
from utils.personas import Persona
from utils.prompts import SYSTEM_REWRITER, rewrite_prompt

STRONG_VERBS = (
    "Automated",
    "Built",
    "Delivered",
    "Implemented",
    "Reduced",
    "Secured",
    "Standardized",
    "Migrated",
)


@dataclass
class RewrittenBullet:
    original: str
    rewritten: str
    why_stronger: str
    verbs_used: list[str] = field(default_factory=list)
    metrics_added: list[str] = field(default_factory=list)


@dataclass
class RewritePack:
    items: list[RewrittenBullet] = field(default_factory=list)
    source: str = "k2"
    warning: str = ""


def rewrite_bullets(
    bullets: list[str],
    cv_text: str,
    jd_text: str,
    persona: Persona,
    settings: Settings,
) -> RewritePack:
    cleaned = [item.strip() for item in bullets if item and item.strip()]
    if not cleaned:
        cleaned = detect_weak_bullets(cv_text)
    if not cleaned:
        return RewritePack(warning="No weak bullets found. Paste 1–8 duty-style lines to rewrite.")

    if not settings.api_key:
        return _heuristic(cleaned, "No K2 API key configured. Showing local rewrite sketches.")

    try:
        client = K2Client(settings)
        raw = client.chat(
            [
                {"role": "system", "content": SYSTEM_REWRITER},
                {"role": "user", "content": rewrite_prompt(cleaned, cv_text, jd_text, persona)},
            ],
            temperature=0.45,
            max_tokens=4096,
        )
        payload = extract_json_object(raw)
        items = _from_payload(payload, cleaned)
        if not items:
            raise ParseError("K2 Think returned no rewrites.")
        return RewritePack(items=items, source="k2")
    except (K2APIError, ParseError) as exc:
        fallback = _heuristic(cleaned, str(exc))
        fallback.source = "local-fallback"
        return fallback


def _from_payload(payload: dict[str, Any], originals: list[str]) -> list[RewrittenBullet]:
    items: list[RewrittenBullet] = []
    rows = as_dict_list(payload.get("rewrites"))
    for index, row in enumerate(rows):
        original = str(row.get("original") or (originals[index] if index < len(originals) else "")).strip()
        rewritten = str(row.get("rewritten") or "").strip()
        if not rewritten:
            continue
        items.append(
            RewrittenBullet(
                original=original or rewritten,
                rewritten=rewritten,
                why_stronger=str(row.get("why_stronger") or "").strip(),
                verbs_used=as_str_list(row.get("verbs_used")),
                metrics_added=as_str_list(row.get("metrics_added")),
            )
        )
    return items


def _heuristic(bullets: list[str], warning: str) -> RewritePack:
    items: list[RewrittenBullet] = []
    for index, bullet in enumerate(bullets):
        verb = STRONG_VERBS[index % len(STRONG_VERBS)]
        stripped = bullet.strip()
        for weak in (
            "Responsible for ",
            "responsible for ",
            "Helped with ",
            "Helped ",
            "helped ",
            "Assisted with ",
            "Assisted ",
            "Worked on ",
            "Participated in ",
            "Involved in ",
            "Tasked with ",
        ):
            if stripped.lower().startswith(weak.lower()):
                stripped = stripped[len(weak) :]
                break
        stripped = stripped[:1].upper() + stripped[1:] if stripped else "the assigned scope"
        rewritten = f"{verb} {stripped} - documented the result with [metric]."
        items.append(
            RewrittenBullet(
                original=bullet,
                rewritten=rewritten.strip(),
                why_stronger="Local sketch only — swaps a duty verb for an achievement frame and a metric placeholder.",
                verbs_used=[verb],
                metrics_added=["[metric]"],
            )
        )
    return RewritePack(items=items, source="local", warning=warning)
