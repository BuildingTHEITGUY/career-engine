from config import Settings
from utils.security import RateLimitError, clip_text, consume_quota, redact


def _settings(key: str = "sk-secret-key") -> Settings:
    return Settings(
        api_key=key,
        api_base="https://api.k2think.ai/v1",
        model="MBZUAI-IFM/K2-Think-v2",
        reasoning_effort="low",
        timeout=5,
        max_retries=1,
        max_calls_per_session=2,
        max_calls_per_hour=2,
        max_input_chars=40,
    )


def test_redact_strips_key_and_bearer() -> None:
    raw = "Authorization: Bearer sk-secret-key failed for sk-secret-key"
    cleaned = redact(raw, "sk-secret-key")
    assert "sk-secret-key" not in cleaned
    assert "Bearer [redacted]" in cleaned


def test_clip_text() -> None:
    assert "truncated" in clip_text("x" * 80, 40)


def test_quota_blocks_after_session_cap() -> None:
    settings = _settings()
    times = consume_quota([], settings, now=1_000)
    times = consume_quota(times, settings, now=1_010)
    try:
        consume_quota(times, settings, now=1_020)
        assert False, "expected RateLimitError"
    except RateLimitError:
        pass


def test_demo_mode_skips_quota() -> None:
    settings = _settings(key="")
    assert consume_quota([1, 2, 3], settings) == [1, 2, 3]
