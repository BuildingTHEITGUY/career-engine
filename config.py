"""Runtime settings for Building THE IT GUY: Career Engine."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

APP_NAME = "Building THE IT GUY: Career Engine"
APP_TAGLINE = "ATS optimizer and job-fit comparator for students and IT professionals."
DEFAULT_API_BASE = "https://api.k2think.ai/v1"
DEFAULT_MODEL = "MBZUAI-IFM/K2-Think-v2"
DEFAULT_REASONING_EFFORT = "medium"
VALID_REASONING_EFFORTS = ("low", "medium", "high")


def _first(*values: str | None) -> str:
    for value in values:
        if value and value.strip():
            return value.strip()
    return ""


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    api_key: str
    api_base: str
    model: str
    reasoning_effort: str
    timeout: int
    max_retries: int
    max_calls_per_session: int = 8
    max_calls_per_hour: int = 20
    max_input_chars: int = 20000

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    @property
    def chat_url(self) -> str:
        return f"{self.api_base.rstrip('/')}/chat/completions"


def _secret(name: str) -> str:
    """Read a Streamlit Cloud / local secrets value without leaking errors to the UI."""
    try:
        import streamlit as st
    except Exception:
        return ""
    try:
        value = st.secrets[name]
        if value is not None and str(value).strip():
            return str(value).strip()
    except Exception:
        pass
    return ""


def get_settings() -> Settings:
    effort = _first(os.getenv("K2_REASONING_EFFORT"), _secret("K2_REASONING_EFFORT"), DEFAULT_REASONING_EFFORT).lower()
    if effort not in VALID_REASONING_EFFORTS:
        effort = DEFAULT_REASONING_EFFORT

    return Settings(
        api_key=_first(_secret("K2_API_KEY"), os.getenv("K2_API_KEY"), os.getenv("K2THINK_API_KEY")),
        api_base=_first(_secret("K2_API_BASE"), os.getenv("K2_API_BASE"), DEFAULT_API_BASE),
        model=_first(_secret("K2_MODEL"), os.getenv("K2_MODEL"), DEFAULT_MODEL),
        reasoning_effort=effort,
        timeout=_int_env("K2_TIMEOUT", 120),
        max_retries=_int_env("K2_MAX_RETRIES", 3),
        max_calls_per_session=_int_env("K2_MAX_CALLS_PER_SESSION", 8),
        max_calls_per_hour=_int_env("K2_MAX_CALLS_PER_HOUR", 20),
        max_input_chars=_int_env("K2_MAX_INPUT_CHARS", 20000),
    )


def override_settings(*, api_key: str | None = None, reasoning_effort: str | None = None) -> Settings:
    """Return settings with optional UI overrides. Does not mutate the cache."""
    base = get_settings()
    effort = (reasoning_effort or base.reasoning_effort).lower()
    if effort not in VALID_REASONING_EFFORTS:
        effort = base.reasoning_effort
    return Settings(
        api_key=_first(api_key, base.api_key),
        api_base=base.api_base,
        model=base.model,
        reasoning_effort=effort,
        timeout=base.timeout,
        max_retries=base.max_retries,
        max_calls_per_session=base.max_calls_per_session,
        max_calls_per_hour=base.max_calls_per_hour,
        max_input_chars=base.max_input_chars,
    )
