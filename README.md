# Findings

Findings is "Hinge for researchers": a web app that matches like-minded researchers who want to
collaborate, and pairs junior researchers with mentors so the exchange runs both ways. Each
researcher builds a profile, an AI layer ranks the best collaborators and explains why, and
mentorship mode scores two-way give/need fit. Contact email stays hidden until a connection is
accepted.

Live app: https://findings.streamlit.app

## What you can do

| Feature | Where | What it does |
|---|---|---|
| Sign up / sign in | Sign in page | Email and password. A demo account exists so a demo never depends on an inbox. A browser refresh keeps you signed in. |
| My profile | My profile | Name, career stage, institution, education, interests, experience, skills, bio, "looking for". The two mentoring toggles default from career stage, and the four give/need fields appear according to the toggles. Gemini suggests a qualitative / quantitative / mixed badge on save; you can override it. |
| Autofill | My profile (edit mode) | Paste a bio or CV text, or upload a PDF CV (5 MB, 10 pages). Gemini pre-fills the form. Nothing is saved until you click Save. |
| Discover | Discover | Browse researcher cards, filter by methods and career stage, search interests, Skip a card for the session. Most of the pool is a synthetic (AI-generated) research community; see `docs/DATA.md`. |
| Researcher profile | From any card or match | Public fields only. No contact email. |
| My Matches (peers) | My Matches > Peers | pgvector shortlist of 15, then one Gemini rerank with a "why you match" for each. Cached; Refresh has a 60 s cooldown. |
| Mentorship | My Matches > Mentorship | Find a mentor (if you are seeking one) or find a mentee (if you are open to mentoring). Ranked on two-way give/need fit, with "what you get" and "what they get" on every card. |
| Connections | Connections | Send a request with a note from a card, match or profile. The recipient accepts or declines. After accept, both people see each other's email. Requests to synthetic profiles are auto-accepted. |

If Gemini is unavailable or rate-limited, matching falls back to embedding-similarity ranking with
a visible notice. The app never crashes on an AI failure.

## Run it locally

Requirements: Python 3.12.

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt -r requirements-dev.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # Supabase URL + publishable key only
.venv/Scripts/python -m streamlit run app.py
```

Put the Gemini key in a file outside the repo, `~/.streamlit/secrets.toml` (Windows:
`C:\Users\<you>\.streamlit\secrets.toml`):

```toml
GEMINI_API_KEY = "your key from https://aistudio.google.com/apikey"
```

On Streamlit Community Cloud, set the same key in the app's Secrets box. Never put it in the
committed `.streamlit/secrets.toml`.

## Database setup

1. Create a free Supabase project.
2. Open the SQL Editor and run the whole of `supabase/schema.sql`. It is idempotent, so re-running
   it is safe.
3. In Authentication > Providers > Email, turn off "Confirm email" so sign-up works without SMTP.
4. Create a demo user and put its login in `scripts/local.toml` (gitignored; template in
   `scripts/local.toml.example`).
5. Optional: seed the synthetic pool with `python scripts/seed_load.py` (needs the Supabase secret
   key in `scripts/local.toml`; see `docs/DATA.md`).

## Tests and checks

```bash
.venv/Scripts/python -m pytest tests -q
.venv/Scripts/python -m ruff check .
.venv/Scripts/python scripts/check_gemini.py   # live: needs a Gemini key
.venv/Scripts/python scripts/check_live.py     # live: needs scripts/local.toml and a probe account
```

## Project layout

```
app.py              entry point, navigation, session bootstrap
views/              Streamlit pages (one file per page)
ui/                 reusable UI pieces (cards, profile view, connect dialog, autofill panel)
findings/core/      config, session, cookie bridge, constants
findings/services/  business logic (no Streamlit)
findings/repos/     Supabase table and RPC access (no Streamlit)
findings/ai/        Gemini client, prompts, rerank, embeddings (no Streamlit)
supabase/schema.sql the single idempotent migration (tables, RLS, RPCs, triggers)
scripts/            seed generation/loading, live checks
tests/              pytest + Streamlit AppTest
docs/               architecture, test report, limitations, AI use, data, runbook
```

## Documents

- [Architecture](docs/ARCHITECTURE.md)
- [Test report](docs/TEST_REPORT.md)
- [Limitations](docs/LIMITATIONS.md)
- [AI-use declaration](docs/AI_USE.md)
- [Data and sources](docs/DATA.md)
- [Pre-demo runbook](docs/RUNBOOK.md)
