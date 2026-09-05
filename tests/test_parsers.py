from utils.k2_client import strip_reasoning
from utils.parsers import ParseError, clamp_score, extract_json_object


def test_extract_json_from_fence_and_think_block() -> None:
    raw = """
    <think>planning the score</think>
    ```json
    {"match_score": 71, "summary": "Solid junior fit"}
    ```
    """
    payload = extract_json_object(raw)
    assert payload["match_score"] == 71
    assert "Solid" in payload["summary"]


def test_extract_json_from_noisy_prose() -> None:
    raw = 'Here you go:\n{"ok": true, "n": 2}\nThanks.'
    assert extract_json_object(raw)["n"] == 2


def test_extract_json_rejects_empty() -> None:
    try:
        extract_json_object("   ")
        assert False, "expected ParseError"
    except ParseError:
        pass


def test_clamp_score() -> None:
    assert clamp_score(140) == 100
    assert clamp_score(-3) == 0
    assert clamp_score("88.6") == 89
    assert clamp_score("nope", default=12) == 12


def test_strip_reasoning() -> None:
    text = "<think>secret chain</think>\nFinal answer"
    assert strip_reasoning(text) == "Final answer"
