# Walking Skeleton — Findings

**Phase:** 1
**Generated:** 2026-10-05

## Capability Proven End-to-End

A researcher opens the deployed Findings app on Streamlit Community Cloud, signs in with a 6-digit code emailed through Brevo (or the demo password), sees their own email and their own RLS-protected profile record, stays signed in across a browser refresh, and signs out from any page.

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Framework | Streamlit 1.65.0 on Python 3.12, `app.py` entrypoint with `st.navigation` + `st.Page` (page files in `views/`, never `pages/`) | Stack locked in CLAUDE.md; `views/` avoids legacy auto-discovery |
| Layering | `views -> findings.services -> findings.repos`; `findings.core` holds config, session and cookies; `findings.services`/`findings.repos` never import streamlit | Later seed scripts and tests reuse services/repos without Streamlit |
| Data layer | Supabase Postgres via supabase-py 2.32.0 (PostgREST + RPC); one re-runnable migration file `supabase/schema.sql`, applied in the SQL Editor | Full schema lands in Phase 1 so later phases never migrate live data |
| Authorization | RLS on every table; email only in `profile_contacts` (RLS on, zero policies) read through the `get_contact_email()` security-definer RPC; column-level update grants | Privacy enforced in the database, not in Python |
| Auth | Supabase Auth email OTP (6-digit `{{ .Token }}` in both Magic Link and Confirm signup templates) via Brevo custom SMTP; demo account via `sign_in_with_password` | Streamlit cannot read magic-link URL fragments; demo must not depend on an inbox |
| Session | One supabase-py client per browser session in `st.session_state["sb"]`, `auto_refresh_token=False`; refresh token persisted in first-party cookie `findings_rt` (read via `st.context.cookies`, written by `st.html(..., unsafe_allow_javascript=True)`) | No cross-user leakage; refresh survives F5 |
| Keys | App and GitHub Actions use only `sb_publishable_...`; secret key exists only on the developer laptop for later seed scripts (`scripts/local.toml`, gitignored) | RLS stays the source of truth |
| Deployment target | Streamlit Community Cloud, Python 3.12 picked in Advanced settings, secrets pasted in the dashboard | $0 hosting |
| Ops | Daily GitHub Actions cron reading the `keepalive` table through PostgREST, plus `workflow_dispatch` | Prevents Supabase free-tier auto-pause |
| Tests | pytest + `streamlit.testing.v1.AppTest` with `tests/fakes.py::FakeSupabase` injected through `st.session_state["sb"]`; live probes in `scripts/check_auth_config.py` and `scripts/check_live.py` | Repeatable evidence for the rubric test report |
| Directory layout | `app.py`, `findings/{core,services,repos}/`, `views/`, `scripts/`, `supabase/schema.sql`, `tests/`, `.github/workflows/`, `docs/screenshots/phase-N/` | Matches research ARCHITECTURE.md |

## Stack Touched in Phase 1

- [ ] Project scaffold (requirements pins, `.venv` on Python 3.12, pytest, ruff)
- [ ] Routing — `st.navigation` with a signed-out page set (Sign in) and a signed-in page set (Home, Account)
- [ ] Database — real read (own `profiles` row via RLS) and real write (signup trigger creates `profiles` + `profile_contacts`; own-row update in `scripts/check_live.py`)
- [ ] UI — OTP email/code forms and demo password form wired to Supabase Auth
- [ ] Deployment — running on Streamlit Community Cloud (Python 3.12) with keep-alive cron green

## Out of Scope (Deferred to Later Slices)

- Profile editing, methods badge, Gemini client (Phase 2)
- Seed data, Discover cards, `match_profiles` RPC (Phases 3-4)
- Connection requests, `my_connections()` RPC, synthetic auto-accept trigger (Phase 5)
- Mentorship ranking (Phase 6), autofill (Phase 7)
- OAuth/SSO/magic links, password sign-up, password reset, MFA (out of scope for the project)

## Subsequent Slice Plan

- Phase 2: a signed-in researcher creates and edits their own profile with an AI-suggested methods badge
- Phase 3: browse 60-100 labelled synthetic researchers on Discover and open profile pages
- Phase 4: My Matches — pgvector shortlist + Gemini rerank with embedding-only fallback
- Phase 5: connection requests with database-enforced email unlock
- Phase 6: mentorship mode on the Phase 4 pipeline
- Phase 7: AI profile autofill (cuttable)
- Phase 8: rubric documents and demo runbook
