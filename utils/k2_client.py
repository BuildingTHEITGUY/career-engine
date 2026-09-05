"""OpenAI-compatible client for the K2 Think v2 API."""

from __future__ import annotations

import logging
import re
import time
from typing import Any

import requests

from config import Settings
from utils.security import redact

logger = logging.getLogger(__name__)

THINK_BLOCK = re.compile(
    r"(<think>.*?</think>|<reasoning>.*?</reasoning>|◁think▷.*?◁/think▷)",
    flags=re.IGNORECASE | re.DOTALL,
)


class K2APIError(Exception):
    """Raised when the K2 Think API cannot complete a request."""

    def __init__(self, message: str, *, status_code: int | None = None, retryable: bool = False) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


def strip_reasoning(text: str) -> str:
    """Remove K2 Think chain-of-thought wrappers so callers get the final answer."""
    cleaned = THINK_BLOCK.sub("", text or "")
    return cleaned.strip()


def _is_retryable(status_code: int | None) -> bool:
    return status_code in {408, 409, 425, 429, 500, 502, 503, 504}


class K2Client:
    def __init__(self, settings: Settings) -> None:
        if not settings.api_key:
            raise K2APIError(
                "Missing K2 API key. Add K2_API_KEY to your local .env file "
                "or to Streamlit / Hugging Face secrets. Do not commit the key."
            )
        self.settings = settings

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self.settings.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        last_error = "Unknown K2 API error"
        attempts = max(1, self.settings.max_retries)
        for attempt in range(1, attempts + 1):
            try:
                response = requests.post(
                    self.settings.chat_url,
                    headers={
                        "Accept": "application/json",
                        "Authorization": f"Bearer {self.settings.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=self.settings.timeout,
                )
            except requests.Timeout as exc:
                last_error = f"K2 Think timed out after {self.settings.timeout}s."
                if attempt < attempts:
                    self._backoff(attempt)
                    continue
                raise K2APIError(last_error, retryable=True) from exc
            except requests.RequestException as exc:
                last_error = redact(f"Could not reach the K2 Think API: {exc}", self.settings.api_key)
                if attempt < attempts:
                    self._backoff(attempt)
                    continue
                raise K2APIError(last_error, retryable=True) from exc

            if 200 <= response.status_code < 300:
                return self._extract_content(response.json())

            last_error = self._format_http_error(response)
            if _is_retryable(response.status_code) and attempt < attempts:
                logger.warning("K2 API retryable error (%s): %s", response.status_code, last_error)
                self._backoff(attempt)
                continue
            raise K2APIError(last_error, status_code=response.status_code, retryable=_is_retryable(response.status_code))

        raise K2APIError(last_error, retryable=True)

    def _extract_content(self, data: Any) -> str:
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise K2APIError("K2 Think returned an unexpected response shape.") from exc

        content = message.get("content") or message.get("reasoning_content") or ""
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part) for part in content
            )
        text = strip_reasoning(str(content))
        if not text:
            raise K2APIError("K2 Think returned an empty answer. Try again with a shorter CV or JD.")
        return text

    def _format_http_error(self, response: requests.Response) -> str:
        body = redact((response.text or "").strip(), self.settings.api_key)
        snippet = body[:240] if body else "no response body"
        if response.status_code in {401, 403}:
            return "K2 Think rejected the server key. The host needs to rotate K2_API_KEY in secrets."
        if response.status_code == 404:
            return "K2 Think endpoint not found. The host should check K2_API_BASE and K2_MODEL in secrets."
        if response.status_code == 429:
            return "K2 Think rate-limited the request. Wait a moment and retry."
        if response.status_code == 400:
            return "K2 Think rejected the request format. Try a shorter CV or JD, then run again."
        return f"K2 Think HTTP {response.status_code}: {snippet}"

    @staticmethod
    def _backoff(attempt: int) -> None:
        time.sleep(min(8.0, 0.75 * (2 ** (attempt - 1))))
