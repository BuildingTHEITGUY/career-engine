from config import Settings
from data.samples import SAMPLES
from utils.documents import detect_weak_bullets
from utils.export import build_markdown_report
from utils.gap_analysis import run_gap_analysis
from utils.personas import get_persona
from utils.rewriter import rewrite_bullets


def _offline_settings() -> Settings:
    return Settings(
        api_key="",
        api_base="https://api.k2think.ai/v1",
        model="MBZUAI-IFM/K2-Think-v2",
        reasoning_effort="low",
        timeout=5,
        max_retries=1,
    )


def test_detects_weak_student_bullets() -> None:
    weak = detect_weak_bullets(SAMPLES["student"]["cv"])
    assert any("Responsible for" in item or "responsible for" in item.lower() for item in weak)


def test_offline_gap_analysis_does_not_crash() -> None:
    persona = get_persona("student")
    sample = SAMPLES["student"]
    analysis = run_gap_analysis(sample["cv"], sample["jd"], persona, _offline_settings())
    assert analysis.source == "local"
    assert analysis.match_score >= 0
    assert analysis.missing_hard_skills


def test_offline_rewriter_and_report() -> None:
    persona = get_persona("professional")
    sample = SAMPLES["professional"]
    pack = rewrite_bullets([], sample["cv"], sample["jd"], persona, _offline_settings())
    assert pack.items
    assert pack.source == "local"
    report = build_markdown_report(persona, None, pack)
    assert "Rewritten bullets" in report
    assert "Building THE IT GUY" in report
