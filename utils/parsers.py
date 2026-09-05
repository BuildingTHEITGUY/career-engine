"""Robust extraction of structured JSON from LLM text."""

from __future__ import annotations

import json
import re
from typing import Any

from utils.k2_client import strip_reasoning

FENCE = re.compile(r"```(?:json)?\s*(.*?)```", flags=re.IGNORECASE | re.DOTALL)
SCORE_RE = re.compile(r"match[_\s-]*score\s*[:=]\s*['\"]?(\d{1,3})", flags=re.IGNORECASE)
SUMMARY_RE = re.compile(
    r"summary\s*[:=]\s*(['\"])(.+?)\1",
    flags=re.IGNORECASE | re.DOTALL,
)
KEY_AFTER_COMMA = re.compile(r"^[A-Za-z_][A-Za-z0-9_\- ]{0,40}\s*[:=]")


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
        candidates.extend(_object_spans(text))
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            candidates.append(text[start : end + 1])

    seen: set[str] = set()
    last_error = "No JSON object found."
    reports: list[dict[str, Any]] = []
    for candidate in candidates:
        for variant in (candidate, repair_json(candidate)):
            if not variant or variant in seen:
                continue
            seen.add(variant)
            parsed = _try_object(variant)
            if isinstance(parsed, dict):
                if _looks_like_report(parsed):
                    return parsed
                reports.append(parsed)
                continue
            if parsed is not None:
                last_error = "JSON was not an object."
                continue
            try:
                json.loads(variant)
            except json.JSONDecodeError as exc:
                last_error = str(exc)

    salvaged = _salvage_report("\n".join(sources))
    if salvaged:
        return salvaged
    if reports:
        return reports[-1]

    raise ParseError(f"Could not parse K2 Think JSON: {last_error}")


def repair_json(text: str) -> str:
    """Fix the sloppy objects K2 often emits after a think block."""
    cleaned = (text or "").strip().lstrip("\ufeff")
    cleaned = cleaned.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end > start:
        cleaned = cleaned[start : end + 1]
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
    cleaned = re.sub(r"([{\[,]\s*)'([^']+)'(\s*:)", r'\1"\2"\3', cleaned)
    cleaned = re.sub(r":\s*'([^']*)'", r': "\1"', cleaned)
    cleaned = re.sub(r"([{\[,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*=", r'\1"\2":', cleaned)
    cleaned = re.sub(r'([{\[,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', cleaned)
    cleaned = re.sub(
        r'([{\[,]\s*)([A-Za-z_][A-Za-z0-9_]*[ \-][A-Za-z0-9_\- ]*[A-Za-z0-9_])\s*:',
        r'\1"\2":',
        cleaned,
    )
    cleaned = re.sub(r"\bTrue\b", "true", cleaned)
    cleaned = re.sub(r"\bFalse\b", "false", cleaned)
    cleaned = re.sub(r"\bNone\b", "null", cleaned)
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


def _try_object(text: str) -> dict[str, Any] | list[Any] | None:
    for loader in (json.loads, _loads_loose):
        try:
            parsed = loader(text)
        except Exception:
            continue
        if isinstance(parsed, (dict, list)):
            return parsed
    return None


def _looks_like_report(payload: dict[str, Any]) -> bool:
    keys = {str(key).lower().replace(" ", "_").replace("-", "_") for key in payload}
    if keys & {"rewrites", "rewritten", "items", "bullets"}:
        return True
    return "match_score" in keys


def _object_spans(text: str) -> list[str]:
    spans: list[str] = []
    i = 0
    length = len(text)
    while i < length:
        if text[i] != "{":
            i += 1
            continue
        depth = 0
        quote = ""
        escape = False
        for j in range(i, length):
            char = text[j]
            if quote:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == quote:
                    quote = ""
                continue
            if char in {'"', "'"}:
                quote = char
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    spans.append(text[i : j + 1])
                    i = j
                    break
        i += 1
    return spans


def _salvage_report(text: str) -> dict[str, Any] | None:
    score_match = SCORE_RE.search(text or "")
    if not score_match:
        return None
    summary = ""
    summary_match = SUMMARY_RE.search(text)
    if summary_match:
        summary = summary_match.group(2).strip()
    return {
        "match_score": clamp_score(score_match.group(1)),
        "summary": summary or "K2 Think returned a partial score after a messy JSON reply.",
    }


def _loads_loose(text: str) -> Any:
    parser = _LooseParser(text)
    value = parser.parse_value()
    parser.skip()
    return value


class _LooseParser:
    """Accept JS-style / Python-style objects K2 emits instead of strict JSON."""

    def __init__(self, text: str) -> None:
        self.s = (text or "").strip()
        self.n = len(self.s)
        self.i = 0

    def parse_value(self) -> Any:
        self.skip()
        if self.i >= self.n:
            raise ValueError("empty")
        char = self.s[self.i]
        if char == "{":
            return self.parse_object()
        if char == "[":
            return self.parse_array()
        if char in {'"', "'"}:
            return self.parse_string()
        if char.isdigit() or char in "-+":
            return self.parse_number()
        return self.parse_bare()

    def parse_object(self) -> dict[str, Any]:
        self.i += 1
        out: dict[str, Any] = {}
        while True:
            self.skip()
            if self.i >= self.n:
                return out
            if self.s[self.i] == "}":
                self.i += 1
                return out
            key = self.parse_key()
            self.skip()
            if self.i < self.n and self.s[self.i] in ":=":
                self.i += 1
            out[key] = self.parse_value()
            self.skip()
            if self.i < self.n and self.s[self.i] == ",":
                self.i += 1
                continue
            if self.i < self.n and self.s[self.i] == "}":
                self.i += 1
                return out
            if self.i >= self.n:
                return out
            # Next token looks like another key; keep going.
            if self._at_key():
                continue
            raise ValueError("object")

    def parse_array(self) -> list[Any]:
        self.i += 1
        items: list[Any] = []
        while True:
            self.skip()
            if self.i >= self.n:
                return items
            if self.s[self.i] == "]":
                self.i += 1
                return items
            items.append(self.parse_value())
            self.skip()
            if self.i < self.n and self.s[self.i] == ",":
                self.i += 1
                continue
            if self.i < self.n and self.s[self.i] == "]":
                self.i += 1
                return items
            if self.i >= self.n:
                return items
            raise ValueError("array")

    def parse_key(self) -> str:
        self.skip()
        if self.i < self.n and self.s[self.i] in {'"', "'"}:
            return str(self.parse_string())
        start = self.i
        while self.i < self.n and (self.s[self.i].isalnum() or self.s[self.i] in "_- "):
            self.i += 1
        key = self.s[start : self.i].strip()
        if not key:
            raise ValueError("key")
        return key

    def parse_string(self) -> str:
        quote = self.s[self.i]
        self.i += 1
        chars: list[str] = []
        while self.i < self.n:
            char = self.s[self.i]
            self.i += 1
            if char == "\\" and self.i < self.n:
                chars.append(self.s[self.i])
                self.i += 1
                continue
            if char == quote:
                return "".join(chars)
            chars.append(char)
        return "".join(chars)

    def parse_number(self) -> Any:
        start = self.i
        if self.s[self.i] in "-+":
            self.i += 1
        while self.i < self.n and (self.s[self.i].isdigit() or self.s[self.i] in ".eE+-"):
            self.i += 1
        token = self.s[start : self.i]
        if token.isdigit() or (token.startswith("-") and token[1:].isdigit()):
            return int(token)
        return float(token)

    def parse_bare(self) -> Any:
        start = self.i
        while self.i < self.n:
            char = self.s[self.i]
            if char in "}]":
                break
            if char == ",":
                rest = self.s[self.i + 1 :].lstrip()
                if KEY_AFTER_COMMA.match(rest) or rest.startswith("[") or rest.startswith("{") or rest.startswith("]"):
                    break
            self.i += 1
        token = self.s[start : self.i].strip()
        lowered = token.lower()
        if lowered in {"true", "yes"}:
            return True
        if lowered in {"false", "no"}:
            return False
        if lowered in {"null", "none"}:
            return None
        if token.isdigit() or (token.startswith("-") and token[1:].isdigit()):
            return int(token)
        try:
            return float(token)
        except ValueError:
            return token

    def skip(self) -> None:
        while self.i < self.n:
            char = self.s[self.i]
            if char.isspace():
                self.i += 1
                continue
            if self.s.startswith("//", self.i):
                self.i = self.s.find("\n", self.i)
                if self.i < 0:
                    self.i = self.n
                continue
            if self.s.startswith("/*", self.i):
                end = self.s.find("*/", self.i + 2)
                self.i = self.n if end < 0 else end + 2
                continue
            return

    def _at_key(self) -> bool:
        rest = self.s[self.i :]
        return bool(re.match(r"""['\"]?[A-Za-z_]""", rest))
