"""Gap analysis engine: persona + CV + JD → K2 Think structured report."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from config import Settings
from utils.k2_client import K2APIError, K2Client
from utils.local_ats import LocalATSResult, score_local_ats
from utils.parsers import ParseError, as_dict_list, as_str_list, clamp_score, extract_json_object
from utils.personas import Persona
from utils.prompts import SYSTEM_ANALYST, gap_analysis_prompt


@dataclass
class GapItem:
    name: str
    why: str
    next_step: str


@dataclass
class GapAnalysis:
    match_score: int
    breakdown: dict[str, int]
    summary: str
    matched_skills: list[str] = field(default_factory=list)
    missing_hard_skills: list[GapItem] = field(default_factory=list)
    missing_enterprise_terms: list[GapItem] = field(default_factory=list)
    ats_risk_flags: list[str] = field(default_factory=list)
    quick_wins: list[str] = field(default_factory=list)
    interview_questions: list[str] = field(default_factory=list)
    plan_30_60_90: dict[str, list[str]] = field(default_factory=dict)
    local: LocalATSResult | None = None
    source: str = "k2"
    warning: str = ""


def run_gap_analysis(
    cv_text: str,
    jd_text: str,
    persona: Persona,
    settings: Settings,
) -> GapAnalysis:
    local = score_local_ats(cv_text, jd_text, persona)
    if not settings.api_key:
        return _from_local(
            local,
            warning="No K2 API key configured. Showing deterministic ATS overlap only.",
        )

    try:
        client = K2Client(settings)
        raw = client.chat(
            [
                {"role": "system", "content": SYSTEM_ANALYST},
                {"role": "user", "content": gap_analysis_prompt(cv_text, jd_text, persona, local.score)},
            ],
            temperature=0.15,
            max_tokens=4096,
        )
        payload = extract_json_object(raw)
        analysis = _from_payload(payload, local)
        analysis.local = local
        return analysis
    except (K2APIError, ParseError) as exc:
        fallback = _from_local(local, warning=str(exc))
        fallback.source = "local-fallback"
        return fallback


def _from_payload(payload: dict[str, Any], local: LocalATSResult) -> GapAnalysis:
    raw_breakdown = payload.get("score_breakdown") or {}
    breakdown = {
        "hard_skills": clamp_score(raw_breakdown.get("hard_skills"), local.score),
        "enterprise_terminology": clamp_score(raw_breakdown.get("enterprise_terminology"), local.score),
        "persona_fit": clamp_score(raw_breakdown.get("persona_fit"), local.score),
        "ats_keywords": clamp_score(raw_breakdown.get("ats_keywords"), local.score),
    }
    plan = payload.get("plan_30_60_90") or {}
    return GapAnalysis(
        match_score=clamp_score(payload.get("match_score"), local.score),
        breakdown=breakdown,
        summary=str(payload.get("summary") or "K2 Think completed the comparison.").strip(),
        matched_skills=as_str_list(payload.get("matched_skills")),
        missing_hard_skills=_items(payload.get("missing_hard_skills"), "skill", "why_it_matters", "how_to_close"),
        missing_enterprise_terms=_items(
            payload.get("missing_enterprise_terms"),
            "term",
            "context",
            "suggested_cv_phrase",
        ),
        ats_risk_flags=as_str_list(payload.get("ats_risk_flags")),
        quick_wins=as_str_list(payload.get("quick_wins")),
        interview_questions=as_str_list(payload.get("interview_questions")),
        plan_30_60_90={
            "30_days": as_str_list(plan.get("30_days")),
            "60_days": as_str_list(plan.get("60_days")),
            "90_days": as_str_list(plan.get("90_days")),
        },
        local=local,
        source="k2",
    )


def _items(value: Any, name_key: str, why_key: str, next_key: str) -> list[GapItem]:
    items: list[GapItem] = []
    for row in as_dict_list(value):
        name = str(row.get(name_key) or "").strip()
        if not name:
            continue
        items.append(
            GapItem(
                name=name,
                why=str(row.get(why_key) or "").strip(),
                next_step=str(row.get(next_key) or "").strip(),
            )
        )
    return items


def _from_local(local: LocalATSResult, warning: str) -> GapAnalysis:
    missing_skills = [
        GapItem(
            name=term,
            why="Present in the job description and missing from the CV text.",
            next_step=f"Add a truthful bullet that proves {term} with a lab, ticket, or project.",
        )
        for term in local.missing
    ]
    return GapAnalysis(
        match_score=local.score,
        breakdown={
            "hard_skills": local.score,
            "enterprise_terminology": max(0, local.score - 8),
            "persona_fit": local.score,
            "ats_keywords": local.score,
        },
        summary=(
            "Local ATS overlap only. Connect K2 Think v2 for a hiring-manager narrative, "
            "enterprise-term extraction, and a 30/60/90 close-the-gap plan."
        ),
        matched_skills=local.overlap,
        missing_hard_skills=missing_skills,
        missing_enterprise_terms=missing_skills[:8],
        ats_risk_flags=local.notes + [f"Weak phrase: {phrase}" for phrase in local.weak_phrases],
        quick_wins=[
            "Mirror missing JD terms only where you have real evidence.",
            "Replace duty verbs with quantified outcomes.",
        ],
        interview_questions=[],
        plan_30_60_90={},
        local=local,
        source="local",
        warning=warning,
    )
