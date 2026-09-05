---
title: Building THE IT GUY Career Engine
emoji: ▣
colorFrom: yellow
colorTo: indigo
sdk: docker
app_port: 8501
pinned: false
license: mit
---

# Building THE IT GUY: Career Engine

Open-source ATS optimizer and job-fit comparator. Paste a CV and a job description, pick **Student Track** or **Professional Track**, and get a match score, missing hard skills, missing enterprise terminology, and rewritten achievement bullets.

Powered by **K2 Think v2** (`MBZUAI-IFM/K2-Think-v2`) over an OpenAI-compatible API. Without a key, the app still runs a deterministic ATS overlap so demos and contributions never hard-fail.

## Why this exists

Students fail ATS filters because CVs read like duty lists. Professionals fail senior screens because they never write ITIL, risk, or governance language. This tool scores the gap and rewrites the bullets.

## Features

- **Dual-persona toggle** — Student Track (cloud basics, labs, security fundamentals) vs Professional Track (ITIL, governance, risk metrics, IT projects).
- **Gap analysis engine** — K2 Think returns a match score plus missing hard skills and enterprise terms.
- **Action-verb rewriter** — weak bullets become quantified, achievement-oriented lines.
- **Local ATS prior** — keyword overlap and weak-verb detection even when the API is down.
- **PDF ingest**, 30/60/90 plan, interview questions, markdown export.
- **Honest fallbacks** — API and JSON errors degrade to local scoring instead of a blank page.

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
streamlit run app.py
```

On macOS / Linux, use `source .venv/bin/activate` and `cp .env.example .env`.

### K2 Think v2

1. Get an API key from [k2think.ai](https://www.k2think.ai/) or the [Cerebras K2 endpoint](https://cerebras.ai/k2think).
2. Keep the key off the UI and out of git:

**Local only:** copy `.env.example` to `.env` and set `K2_API_KEY=...`. `.env` is gitignored. Do not upload that file to a public repo or Space.

**Public host:** do not use `.env`. Add `K2_API_KEY` in the platform Secrets panel (Streamlit Cloud or Hugging Face). The server reads it; the browser never sees it.

## Project layout

```
app.py                 Streamlit UI
config.py              Env + secrets
utils/k2_client.py     Retries, timeouts, reasoning-strip
utils/gap_analysis.py  Persona + CV + JD → structured report
utils/rewriter.py      Action-verb rewrite desk
utils/local_ats.py     Deterministic overlap
utils/personas.py      Student / Professional rubrics
utils/prompts.py       JSON contracts for K2
utils/parsers.py       Fence / think-block JSON extraction
utils/documents.py     PDF + weak-bullet detection
utils/export.py        Markdown report
data/samples.py        Demo CV / JD pairs
tests/                 Offline unit tests
```

## Tests

```bash
python -m pytest
```

## Deploy a public app without exposing the key

Do **not** put the key in `.env` on the public host. Use the host secret store. The app reads `st.secrets` and environment variables on the server only.

Hugging Face removed the Streamlit SDK (April 2025). New Streamlit Spaces must use Docker, and Gradio/Docker Spaces now need a paid HF plan. **Use Streamlit Community Cloud if you want a free public host.**

**Streamlit Community Cloud (recommended, free)**
1. Push this repo to GitHub without `.env`.
2. Open [https://share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. **Create app** → pick the repo → main file `app.py` → Deploy.
4. App menu → **Settings → Secrets** and paste:

```toml
K2_API_KEY = "your-real-key"
K2_API_BASE = "https://api.k2think.ai/v1"
K2_MODEL = "MBZUAI-IFM/K2-Think-v2"
```

**Hugging Face Spaces (only if you have HF PRO)**
1. Create a Space with **Docker** (not Gradio, not Static). Streamlit SDK no longer exists.
2. Upload this repo, including `Dockerfile`. Do not upload `.env`.
3. Space → **Settings → Variables and secrets → New secret** named `K2_API_KEY`.

What stays secure by design:
- No key field in the sidebar
- Key never written into reports, errors, or the page
- Per-session and hourly caps so visitors cannot drain your quota
- Input size cap before the model is called

**Public URLs**
- Engine: `https://buildingtheitguy.streamlit.app` (set this in Streamlit Cloud → Settings → General)
- Brand front door: `https://cv.buildingtheitguy.com` (GitHub Pages in `/docs` embeds the engine; the K2 key stays in Streamlit Secrets)

The public site still spends *your* K2 credits. Watch usage. If you need zero shared spend, host in demo mode and omit the secret.

Do not commit real CVs. Text is sent to K2 Think only when someone clicks analyze or rewrite.

## A better public-build plan

Your original 12-week loop is good. The version that actually ranks as a utility repo is narrower:

1. **Week 1 — Ship a demo that works without an API key.** Record the sample CV path, not a broken spinner. LinkedIn hook: “I got tired of watching students fail ATS filters, so I wrote the grader.”
2. **Week 2 — One public before/after per persona.** Student Cloud Support and IT Governance Analyst are already bundled in `data/samples.py`. Post the score, three missing terms, and two rewritten bullets. Invite forks for DOCX and a Security Track.
3. **Week 3 — Host it.** Hugging Face Spaces or Streamlit Cloud. The gate should be “star the repo,” not a follow-wall. Follow-walls look like a lead magnet; stars compound GitHub ranking.
4. **Weeks 4–12 — Tuesday case studies + labeled issues.** Every Tuesday: one real (anonymized) breakdown. Every Thursday: review PRs. Keep `CONTRIBUTING.md` as the onboarding. Do not add a dozen features before the first 20 stars.

What usually kills these repos: paywalled demos, no sample data, and PRs with nowhere to land. This codebase is built to avoid all three.

## License

MIT
