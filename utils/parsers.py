"""Robust extraction of structured JSON from LLM text."""

from __future__ import annotations

import json
import re
from typing import Any

from utils.k2_client import strip_reasoning

FENCE = re.compile(r"```(?:json)?\s*(.*?)```", flags=re.IGNORECASE | re.DOTALL)


class ParseError(ValueError):
    """The model replied, but the payload was not valid structured JSON."""


def extract_json_object(raw: str) -> dict[str, Any]:
    raw = raw or ""
    stripped = strip_reasoning(raw).strip()
    sources = [item for item in (stripped, raw) if item.strip()]
    if not sources:
        raise ParseError("Empty model output.")

    candidates: list[str] = []
    for text in sources:
        candidates.append(text)
        candidates.extend(match.group(1).strip() for match in FENCE.finditer(text))
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            candidates.append(text[start : end + 1])

    seen: set[str] = set()
    last_error = "No JSON object found."
    for candidate in candidates:
        for variant in (candidate, repair_json(candidate)):
            if not variant or variant in seen:
                continue
            seen.add(variant)
            try:
                parsed = json.loads(variant)
            except json.JSONDecodeError as exc:
                last_error = str(exc)
                continue
            if isinstance(parsed, dict):
                return parsed
            last_error = "JSON was not an object."

    raise ParseError(f"Could not parse K2 Think JSON: {last_error}")


def repair_json(text: str) -> str:
    """Fix the sloppy objects K2 often emits after a think block."""
    cleaned = (text or "").strip()
    cleaned = cleaned.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
    cleaned = re.sub(r"([{\[,]\s*)'([^']+)'(\s*:)", r'\1"\2"\3', cleaned)
    cleaned = re.sub(r":\s*'([^']*)'", r': "\1"', cleaned)
    cleaned = re.sub(r'([{\[,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', cleaned)
    return cleaned


def clamp_score(value: Any, default: int = 0) -> int:
    try:
        score = int(round(float(value)))
    except (TypeError, ValueError):
        return default
    return max(0, min(100, score))


def as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        item = value.strip()
        return [item] if item else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


def as_dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
