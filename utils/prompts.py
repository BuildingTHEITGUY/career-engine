"""Prompt contracts for K2 Think v2."""

from __future__ import annotations

from utils.personas import Persona

SYSTEM_ANALYST = (
    "You are Building THE IT GUY Career Engine, a precise ATS and hiring-manager analyst. "
    "You evaluate CVs against job descriptions for a selected persona. "
    "Return ONLY valid JSON. No markdown, no preamble, no chain-of-thought."
)

SYSTEM_REWRITER = (
    "You are Building THE IT GUY Career Engine rewrite desk. "
    "You turn weak CV bullets into quantified, achievement-oriented bullets that survive ATS parsers. "
    "Never invent employers, titles, tools, or metrics the CV does not support. "
    "If a number is missing, use a conservative placeholder in [brackets] the candidate can fill. "
    "Return ONLY valid JSON. No markdown, no preamble."
)


def gap_analysis_prompt(cv_text: str, jd_text: str, persona: Persona, local_score: int) -> str:
    lenses = "\n".join(f"- {item}" for item in persona.lenses)
    evaluates = "\n".join(f"- {item}" for item in persona.evaluates)
    return f"""Analyze this candidate for the {persona.label} ({persona.audience}).

Evaluation pillars:
{evaluates}

Scoring lenses:
{lenses}

A deterministic local ATS keyword overlap already scored this pair at {local_score}%.
Use that as a prior. You may adjust it, but stay internally consistent.
match_score is an integer 0-100.

Extract:
- missing hard skills the JD needs and the CV does not prove
- missing enterprise terminology / ATS keywords the JD uses
- matched skills already present
- ATS risk flags (tables, images, missing keywords, weak verbs, date gaps)
- quick wins the candidate can apply in under 2 hours
- interview questions a hiring manager would ask because of the gaps

JSON schema:
{{
  "match_score": 0,
  "score_breakdown": {{
    "hard_skills": 0,
    "enterprise_terminology": 0,
    "persona_fit": 0,
    "ats_keywords": 0
  }},
  "summary": "2-3 sentences",
  "matched_skills": ["string"],
  "missing_hard_skills": [
    {{"skill": "string", "why_it_matters": "string", "how_to_close": "string"}}
  ],
  "missing_enterprise_terms": [
    {{"term": "string", "context": "string", "suggested_cv_phrase": "string"}}
  ],
  "ats_risk_flags": ["string"],
  "quick_wins": ["string"],
  "interview_questions": ["string"],
  "plan_30_60_90": {{
    "30_days": ["string"],
    "60_days": ["string"],
    "90_days": ["string"]
  }}
}}

CV:
\"\"\"
{cv_text.strip()}
\"\"\"

JOB DESCRIPTION:
\"\"\"
{jd_text.strip()}
\"\"\"
"""


def rewrite_prompt(bullets: list[str], cv_text: str, jd_text: str, persona: Persona) -> str:
    numbered = "\n".join(f"{idx}. {bullet}" for idx, bullet in enumerate(bullets, start=1))
    return f"""Rewrite each weak CV bullet for the {persona.label}.

Rules:
- Lead with a strong past-tense action verb.
- Keep the candidate's real tools and scope.
- Add a metric, volume, time, or outcome. Use [metric] if unknown.
- Mirror useful JD terminology without keyword stuffing.
- One sentence per rewrite, 18-32 words.
- Preserve truthfulness.

JSON schema:
{{
  "rewrites": [
    {{
      "original": "string",
      "rewritten": "string",
      "why_stronger": "string",
      "verbs_used": ["string"],
      "metrics_added": ["string"]
    }}
  ]
}}

WEAK BULLETS:
{numbered}

CV CONTEXT:
\"\"\"
{cv_text.strip()[:6000]}
\"\"\"

TARGET JD:
\"\"\"
{jd_text.strip()[:4000]}
\"\"\"
"""
