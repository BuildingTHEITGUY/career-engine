"""Server-side guards so a public host never leaks or burns the K2 key."""

from __future__ import annotations

import re
import time
from collections import deque

from config import Settings

_BEARER = re.compile(r"Bearer\s+\S+", flags=re.IGNORECASE)
_PROCESS_CALLS: deque[float] = deque()


class RateLimitError(Exception):
    """Visitor hit the public usage cap for this session or hour."""


def redact(text: str, secret: str = "") -> str:
    """Strip API keys and bearer tokens from anything shown to a visitor."""
    cleaned = text or ""
    if secret:
        cleaned = cleaned.replace(secret, "[redacted]")
    return _BEARER.sub("Bearer [redacted]", cleaned)


def clip_text(text: str, limit: int) -> str:
    value = (text or "").strip()
    if len(value) <= limit:
        return value
    return value[:limit].rstrip() + "\n\n[truncated for safety]"


def consume_quota(call_times: list[float], settings: Settings, *, now: float | None = None) -> list[float]:
    """Record one K2 call. Raises RateLimitError if the visitor is over cap."""
    if not settings.api_key:
        return call_times

    stamp = now if now is not None else time.time()
    hour_ago = stamp - 3600
    recent = [item for item in call_times if item >= hour_ago]

    if len(call_times) >= settings.max_calls_per_session:
        raise RateLimitError(
            f"This session has used the {settings.max_calls_per_session} analysis cap. "
            "Refresh later or run the sample locally."
        )
    if len(recent) >= settings.max_calls_per_hour:
        raise RateLimitError(
            f"Hourly cap reached ({settings.max_calls_per_hour} K2 calls). Try again in a bit."
        )

    _prune_process(hour_ago)
    if len(_PROCESS_CALLS) >= settings.max_calls_per_hour * 8:
        raise RateLimitError("The public engine is at capacity this hour. Try again shortly.")

    updated = list(call_times)
    updated.append(stamp)
    _PROCESS_CALLS.append(stamp)
    return updated


def _prune_process(hour_ago: float) -> None:
    while _PROCESS_CALLS and _PROCESS_CALLS[0] < hour_ago:
        _PROCESS_CALLS.popleft()
