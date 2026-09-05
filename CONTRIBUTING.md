# Contributing

Junior developers: this repo is designed for small, public Pull Requests you can put on a CV.

## Good first issues

1. **DOCX ingest** — extract text from `.docx` uploads beside the existing PDF path in `utils/documents.py`.
2. **More personas** — add a Security Track or Data Track in `utils/personas.py` without breaking Student / Professional.
3. **Cover-letter draft** — a third action that uses the same K2 client and JSON parser.
4. **LinkedIn about rewrite** — 2,000-character version of the CV summary.
5. **Locale packs** — Arabic / French JD terminology lists in `utils/local_ats.py`.
6. **Playwright smoke test** — click “Load sample” and “Run gap analysis” in demo mode.

## How to work

1. Fork the repo and create a branch: `feat/docx-ingest`.
2. Keep changes in one module when you can.
3. Add or update a test in `tests/`.
4. Do not commit `.env`, API keys, or real CVs.
5. Open a PR with a before/after screenshot of the Streamlit UI.

## Local checks

```bash
python -m pytest
```

Never invent metrics in rewriter prompts. If a number is unknown, keep the `[metric]` placeholder.
