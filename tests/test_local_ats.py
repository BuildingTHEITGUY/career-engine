from data.samples import SAMPLES
from utils.local_ats import score_local_ats
from utils.personas import get_persona


def test_student_sample_is_partial_match() -> None:
    persona = get_persona("student")
    sample = SAMPLES["student"]
    result = score_local_ats(sample["cv"], sample["jd"], persona)
    assert 15 <= result.score <= 85
    assert result.missing
    assert "aws" in result.overlap or "linux" in result.overlap or result.missing


def test_professional_flags_missing_governance_terms() -> None:
    persona = get_persona("professional")
    sample = SAMPLES["professional"]
    result = score_local_ats(sample["cv"], sample["jd"], persona)
    joined = " ".join(result.missing)
    assert any(term in joined for term in ("cobit", "iso 27001", "kri", "residual risk", "nist"))
    assert result.weak_phrases


def test_empty_inputs_score_zero() -> None:
    result = score_local_ats("", "AWS Linux", get_persona("student"))
    assert result.score == 0
