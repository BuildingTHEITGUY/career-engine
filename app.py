"""Building THE IT GUY: Career Engine — Streamlit frontend."""

from __future__ import annotations

import streamlit as st

from config import APP_NAME, APP_TAGLINE, VALID_REASONING_EFFORTS, override_settings
from data.samples import SAMPLES
from utils.documents import detect_weak_bullets, extract_pdf_text
from utils.export import build_markdown_report
from utils.gap_analysis import GapAnalysis, run_gap_analysis
from utils.personas import PERSONAS, get_persona
from utils.rewriter import RewritePack, rewrite_bullets
from utils.security import RateLimitError, clip_text, consume_quota, redact

st.set_page_config(
    page_title=APP_NAME,
    page_icon="▣",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Serif:wght@500;600&display=swap');

    html, body, [class*="css"]  {
        font-family: "IBM Plex Sans", sans-serif;
    }
    .hero-kicker {
        color: #D4A017;
        letter-spacing: 0.18em;
        font-size: 0.76rem;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 0.35rem;
    }
    .hero-title {
        font-family: "IBM Plex Serif", serif;
        font-size: 2.05rem;
        line-height: 1.2;
        margin: 0 0 0.4rem 0;
    }
    .hero-sub {
        color: #9AA8BD;
        font-size: 1.02rem;
        max-width: 46rem;
    }
    .score-card, .info-chip {
        background: #121A2B;
        border: 1px solid #243049;
        border-radius: 16px;
        padding: 1rem 1.1rem;
    }
    .score-number {
        font-family: "IBM Plex Serif", serif;
        font-size: 3rem;
        line-height: 1;
        color: #F4D27A;
    }
    .muted { color: #9AA8BD; font-size: 0.92rem; }
    .rewrite-after {
        background: #16302a;
        border-left: 3px solid #3ecf8e;
        padding: 0.75rem 0.9rem;
        border-radius: 0 12px 12px 0;
        margin-top: 0.45rem;
    }
    .rewrite-before {
        background: #2a1c1c;
        border-left: 3px solid #d36b6b;
        padding: 0.75rem 0.9rem;
        border-radius: 0 12px 12px 0;
    }
    div[data-testid="stSidebar"] {
        background: #0A101B;
    }
    .stButton > button {
        border-radius: 12px;
        font-weight: 600;
        letter-spacing: 0.01em;
    }
</style>
"""


def _init_state() -> None:
    defaults = {
        "persona_key": "student",
        "cv_text": "",
        "jd_text": "",
        "analysis": None,
        "rewrites": None,
        "last_error": "",
        "k2_call_times": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _load_sample(persona_key: str) -> None:
    sample = SAMPLES[persona_key]
    st.session_state.cv_text = sample["cv"]
    st.session_state.jd_text = sample["jd"]
    st.session_state.analysis = None
    st.session_state.rewrites = None
    st.session_state.last_error = ""


def _settings_from_ui(effort: str):
    return override_settings(reasoning_effort=effort)


def _prepare_k2_call(settings) -> tuple[str, str] | None:
    try:
        st.session_state.k2_call_times = consume_quota(list(st.session_state.k2_call_times), settings)
    except RateLimitError as exc:
        st.session_state.last_error = str(exc)
        return None
    cv = clip_text(st.session_state.cv_text, settings.max_input_chars)
    jd = clip_text(st.session_state.jd_text, settings.max_input_chars)
    return cv, jd


def _safe_error(exc: Exception, settings) -> str:
    return redact(str(exc), settings.api_key)


def render_analysis(analysis: GapAnalysis) -> None:
    left, right = st.columns([1.1, 1.4], gap="large")
    with left:
        st.markdown(
            f'<div class="score-card"><div class="muted">Match score</div>'
            f'<div class="score-number">{analysis.match_score}%</div></div>',
            unsafe_allow_html=True,
        )
        st.progress(analysis.match_score / 100.0)
        st.caption(f"Source: {analysis.source.replace('-', ' ')}")
    with right:
        st.markdown(analysis.summary)
        if analysis.warning:
            st.warning(analysis.warning)
        labels = {
            "hard_skills": "Hard skills",
            "enterprise_terminology": "Enterprise terms",
            "persona_fit": "Persona fit",
            "ats_keywords": "ATS keywords",
        }
        cols = st.columns(4)
        for column, (key, value) in zip(cols, analysis.breakdown.items()):
            column.metric(labels.get(key, key), f"{value}%")

    st.divider()
    skills, terms = st.columns(2)
    with skills:
        st.subheader("Missing hard skills")
        if not analysis.missing_hard_skills:
            st.success("No obvious hard-skill gaps for this persona.")
        for item in analysis.missing_hard_skills:
            with st.expander(item.name, expanded=False):
                if item.why:
                    st.write(item.why)
                if item.next_step:
                    st.markdown(f"**Close the gap:** {item.next_step}")
    with terms:
        st.subheader("Missing enterprise terminology")
        if not analysis.missing_enterprise_terms:
            st.success("JD terminology is well represented.")
        for item in analysis.missing_enterprise_terms:
            with st.expander(item.name, expanded=False):
                if item.why:
                    st.write(item.why)
                if item.next_step:
                    st.markdown(f"**CV phrase:** {item.next_step}")

    if analysis.matched_skills:
        st.subheader("Already landing")
        st.write(" · ".join(analysis.matched_skills))

    wins, flags, questions = st.columns(3)
    with wins:
        st.subheader("Quick wins")
        for item in analysis.quick_wins:
            st.markdown(f"- {item}")
    with flags:
        st.subheader("ATS risk flags")
        for item in analysis.ats_risk_flags:
            st.markdown(f"- {item}")
    with questions:
        st.subheader("Interview pressure tests")
        for item in analysis.interview_questions:
            st.markdown(f"- {item}")

    plan = analysis.plan_30_60_90
    if any(plan.get(key) for key in ("30_days", "60_days", "90_days")):
        st.subheader("30 / 60 / 90 close-the-gap plan")
        p1, p2, p3 = st.columns(3)
        for column, key, title in (
            (p1, "30_days", "30 days"),
            (p2, "60_days", "60 days"),
            (p3, "90_days", "90 days"),
        ):
            with column:
                st.markdown(f"**{title}**")
                for item in plan.get(key, []):
                    st.markdown(f"- {item}")


def render_rewrites(pack: RewritePack) -> None:
    if pack.warning:
        st.warning(pack.warning)
    if not pack.items:
        st.info("No rewrites yet.")
        return
    for index, item in enumerate(pack.items, start=1):
        with st.expander(f"Bullet {index}: {item.original[:72]}", expanded=index == 1):
            st.markdown(f'<div class="rewrite-before">{item.original}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="rewrite-after">{item.rewritten}</div>', unsafe_allow_html=True)
            if item.why_stronger:
                st.caption(item.why_stronger)
            meta = []
            if item.verbs_used:
                meta.append("Verbs: " + ", ".join(item.verbs_used))
            if item.metrics_added:
                meta.append("Metrics: " + ", ".join(item.metrics_added))
            if meta:
                st.caption(" · ".join(meta))
            st.code(item.rewritten, language=None)


def main() -> None:
    _init_state()
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("### Dual-persona toggle")
        persona_key = st.radio(
            "Evaluation track",
            options=list(PERSONAS.keys()),
            format_func=lambda key: PERSONAS[key].label,
            key="persona_key",
            help="Student Track scores labs and fundamentals. Professional Track scores ITIL, governance, and risk.",
        )
        persona = get_persona(persona_key)
        st.caption(persona.audience)
        for item in persona.evaluates:
            st.markdown(f"- {item}")

        st.divider()
        st.markdown("### K2 Think v2")
        effort = st.select_slider("Reasoning effort", options=list(VALID_REASONING_EFFORTS), value="medium")
        settings = _settings_from_ui(effort)
        if settings.is_configured:
            st.success("K2 Think connected")
        else:
            st.info("Demo mode — add K2_API_KEY in `.env` or host secrets.")
        st.caption(f"Model `{settings.model}`")

        st.divider()
        if st.button("Load sample CV + JD", use_container_width=True):
            _load_sample(persona_key)
            st.rerun()
        st.caption("CV text is sent to K2 Think only when you run analysis or rewrite. Nothing is stored by this app.")

    st.markdown('<div class="hero-kicker">Open source · ATS · Job-fit</div>', unsafe_allow_html=True)
    st.markdown(f'<h1 class="hero-title">{APP_NAME}</h1>', unsafe_allow_html=True)
    st.markdown(f'<p class="hero-sub">{APP_TAGLINE} Powered by K2 Think v2.</p>', unsafe_allow_html=True)

    cv_col, jd_col = st.columns(2, gap="large")
    with cv_col:
        st.subheader("Current CV")
        pdf = st.file_uploader("Or drop a PDF", type=["pdf"], label_visibility="collapsed")
        if pdf is not None:
            signature = f"{pdf.name}:{pdf.size}"
            if st.session_state.get("pdf_signature") != signature:
                try:
                    st.session_state.cv_text = extract_pdf_text(pdf)
                    st.session_state.pdf_signature = signature
                    st.toast("PDF text extracted.")
                except Exception as exc:
                    st.error(str(exc))
        st.text_area(
            "Paste your CV",
            key="cv_text",
            height=320,
            placeholder="Paste the plain-text CV you actually submit to ATS portals…",
        )
    with jd_col:
        st.subheader("Target job description")
        st.text_area(
            "Paste the JD",
            key="jd_text",
            height=388,
            placeholder="Paste the full job description, including required skills and nice-to-haves…",
        )

    weak_preview = detect_weak_bullets(st.session_state.cv_text)
    action, rewrite_action, clear_action = st.columns([1.4, 1.4, 1])
    run_clicked = action.button("Run gap analysis", type="primary", use_container_width=True)
    rewrite_clicked = rewrite_action.button("Rewrite weak bullets", use_container_width=True)
    if clear_action.button("Clear results", use_container_width=True):
        st.session_state.analysis = None
        st.session_state.rewrites = None
        st.session_state.last_error = ""
        st.rerun()

    if not st.session_state.cv_text.strip() or not st.session_state.jd_text.strip():
        st.caption("Paste both a CV and a JD, or load a sample from the sidebar.")

    if run_clicked:
        if len(st.session_state.cv_text.strip()) < 80 or len(st.session_state.jd_text.strip()) < 40:
            st.error("Add more CV and JD text before running analysis.")
        else:
            prepared = _prepare_k2_call(settings)
            if prepared:
                cv_text, jd_text = prepared
                with st.spinner("K2 Think is scoring fit, skills, and terminology…"):
                    try:
                        st.session_state.analysis = run_gap_analysis(
                            cv_text,
                            jd_text,
                            persona,
                            settings,
                        )
                        st.session_state.last_error = ""
                    except Exception as exc:
                        st.session_state.last_error = _safe_error(exc, settings)

    if rewrite_clicked:
        if len(st.session_state.cv_text.strip()) < 40:
            st.error("Paste a CV (or weak bullets) before rewriting.")
        else:
            prepared = _prepare_k2_call(settings)
            if prepared:
                cv_text, jd_text = prepared
                seed = detect_weak_bullets(cv_text) or [
                    line.strip() for line in cv_text.splitlines() if line.strip()
                ][:6]
                with st.spinner("Rewriting duty statements into achievement bullets…"):
                    try:
                        st.session_state.rewrites = rewrite_bullets(
                            seed,
                            cv_text,
                            jd_text,
                            persona,
                            settings,
                        )
                        st.session_state.last_error = ""
                    except Exception as exc:
                        st.session_state.last_error = _safe_error(exc, settings)

    if st.session_state.last_error:
        st.error(st.session_state.last_error)

    analysis: GapAnalysis | None = st.session_state.analysis
    rewrites: RewritePack | None = st.session_state.rewrites

    tabs = st.tabs(["Gap analysis", "Action-verb rewriter", "Export"])
    with tabs[0]:
        if analysis:
            render_analysis(analysis)
        else:
            st.info("Run gap analysis to see match score, missing hard skills, and enterprise terms.")
            if weak_preview:
                st.caption(f"{len(weak_preview)} weak bullet(s) already detected in the CV.")
    with tabs[1]:
        if rewrites:
            render_rewrites(rewrites)
        else:
            st.info("Rewrite weak bullets to get quantified, ATS-safe replacements in expanders.")
            if weak_preview:
                st.write("Detected weak lines:")
                for line in weak_preview:
                    st.markdown(f"- {line}")
    with tabs[2]:
        report = build_markdown_report(persona, analysis, rewrites)
        st.download_button(
            "Download markdown report",
            data=report,
            file_name="it-guy-career-engine-report.md",
            mime="text/markdown",
            use_container_width=True,
            disabled=not (analysis or rewrites),
        )
        st.code(report, language="markdown")


if __name__ == "__main__":
    main()
