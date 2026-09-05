"""Gap analysis engine: persona + CV + JD → K2 Think structured report."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from config import Settings
from utils.k2_client import K2APIError, K2Client
from utils.local_ats import LocalATSResult, score_local_ats
from utils.parsers import ParseError, as_dict_list, as_str_list, clamp_score, extract_json_object
from utils.personas import Persona
from utils.prompts import JSON_ONLY_NUDGE, SYSTEM_ANALYST, compact_gap_prompt, micro_gap_prompt
from utils.security import clip_text


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

    client = K2Client(settings)
    attempts = (
        (compact_gap_prompt, 2200, 1600, 8192, "k2"),
        (micro_gap_prompt, 1400, 1000, 4096, "k2-compact"),
    )
    last_error = "K2 Think did not finish a JSON report."
    for builder, cv_limit, jd_limit, tokens, source in attempts:
        try:
            raw = client.chat_json(
                [
                    {"role": "system", "content": SYSTEM_ANALYST},
                    {
                        "role": "user",
                        "content": builder(
                            clip_text(cv_text, cv_limit),
                            clip_text(jd_text, jd_limit),
                            persona,
                            local.score,
                        ),
                    },
                ],
                temperature=0.1,
                max_tokens=tokens,
                nudge=JSON_ONLY_NUDGE,
            )
            payload = extract_json_object(raw)
            analysis = _from_payload(payload, local)
            analysis.local = local
            analysis.source = source
            return analysis
        except (K2APIError, ParseError) as exc:
            last_error = _friendly_k2_error(exc)
            continue

    fallback = _from_local(
        local,
        warning=f"K2 is connected but did not finish the narrative. {last_error}",
    )
    fallback.source = "local-fallback"
    return fallback


def _friendly_k2_error(exc: Exception) -> str:
    if isinstance(exc, ParseError) or "Could not parse" in str(exc):
        return (
            "K2 Think replied, but the report was not valid JSON "
            "(it often writes keys without quotes). We retried a shorter prompt, "
            "then used local ATS overlap so the score stays honest."
        )
    return str(exc)


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
    if isinstance(value, list):
        for row in value:
            if isinstance(row, str) and row.strip():
                items.append(GapItem(name=row.strip(), why="", next_step=""))
                continue
            if not isinstance(row, dict):
                continue
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
            "Local ATS keyword overlap only. The hiring-manager narrative from K2 Think "
            "did not finish this run, so this score is a deterministic prior — not the full engine."
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
