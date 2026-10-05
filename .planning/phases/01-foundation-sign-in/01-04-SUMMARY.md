---
phase: 01-foundation-sign-in
plan: 04
subsystem: infra
tags: [github-actions, keepalive, streamlit-cloud, deploy, gemini-quotas, repo-hygiene]
requires: [01-02, 01-03]
provides:
  - supabase-keepalive GitHub Actions workflow (daily + manual, green)
  - Deployed app at https://findings.streamlit.app
  - Measured Gemini free-tier quotas
  - Repo-hygiene tests (no secret material tracked)
affects: [phase-2, phase-3]
tech-stack:
  added: []
  patterns: [secrets via env only, permissions {} workflow, no third-party actions]
key-files:
  created:
    - .github/workflows/keepalive.yml
    - tests/test_repo_hygiene.py
  modified:
    - app.py
    - tests/test_session.py
decisions:
  - "Password sign-in (not OTP) is the auth flow; OTP/SMTP exit checks adapted to sign-up / sign-in / refresh / sign-out"
  - ".streamlit/secrets.toml (URL + publishable key) is committed by user decision; hygiene tests assert no sb_secret_ or other key material in tracked files instead"
metrics:
  duration: ~15 min
  completed: 2026-10-05
status: complete
actuals:
  tokens: 4000
  tasks: 3
  commits: 1
plan_head_before: 899c74042cf1ca03de30e9aee9bb135d1ccf8740
plan_head_after: 60f443c544bea6bcea0579ac5a3f3377af0a77a4
---

# Phase 1 Plan 04: Keep-alive, deploy and quotas Summary

Daily Supabase keep-alive workflow (green on a manual run), app deployed to Streamlit Community Cloud at https://findings.streamlit.app, Python-version sidebar caption, repo-hygiene tests, and measured Gemini quotas.

## What was built

- `.github/workflows/keepalive.yml`: cron `17 6 * * *` plus `workflow_dispatch`, `permissions: {}`, no checkout or third-party actions, secrets only through `env`, `curl --fail` against `/rest/v1/keepalive?select=id&limit=1`, and fails unless the body contains `"id":1`.
- `app.py`: sidebar caption "Findings · Python X.Y.Z" on every run.
- `tests/test_repo_hygiene.py`: `scripts/local.toml` untracked; no `sb_secret_`, JWT, `AIza` or `xsmtpsib-` material in tracked files; publishable key only in `.streamlit/secrets.toml`; keepalive workflow shape (dispatch, cron, endpoint, `permissions: {}`, exactly two secrets, secrets not interpolated in the run script).

## Results for STATE.md (orchestrator to copy)

**Deployed app URL:** https://findings.streamlit.app (loads the "Sign in to Findings" page with "Sign in" and "Create account" tabs). The Python 3.12.x sidebar caption is pending human confirmation.

**Keep-alive run (workflow_dispatch):** success. https://github.com/vaibhavs2811-lab/Findings/actions/runs/37250562753. The user edited `keepalive.yml` in the GitHub web UI (commit 1656443, trailing newline only) to force workflow registration. This worktree's copy was not touched, so expect a trivial merge difference there.

**Measured Gemini free-tier quotas** (AI Studio rate-limit page, project gen-lang-client-0045339077, read 2026-10-05):

| Model | RPM | TPM | RPD |
|-------|-----|-----|-----|
| gemini-3.5-flash-lite | 15 | 250K | 500 |
| gemini-3.1-flash-lite | 15 | 250K | 500 |
| gemini-embedding-2 | 100 | 30K | 1K |
| gemini-3.8-flash (reference) | 5 | 250K | 20 |

All match the research assumption (about 500 RPD for Flash-Lite), so no Phase 3 seeding concern. Embedding TPM is 30K, so keep embedding calls small and spaced when seeding.

**Gemini API key:** not created yet; not needed until a later phase.

## Open human checks (not blocking; for phase verification)

On https://findings.streamlit.app, not yet run by the user:
1. Sidebar caption shows Python 3.12.x. If not, delete the app and redeploy with 3.12 selected.
2. A new account signs up and lands on Home.
3. The demo account signs in.
4. F5 keeps the user signed in. If it does not on Cloud while it works locally, apply the PA-04 fallback (SameSite=Strict to Lax in `findings/core/cookies.py`).
5. Sign-out works from Home and Account.
6. Two browsers signed in as two accounts show only their own email and user id, also after F5.
7. Screenshots for `docs/screenshots/phase-1/` (sign-in, home, demo-login, keepalive-green) are not captured.

## Deviations from Plan

**1. [Rule 1 - Bug] Updated `tests/test_session.py::test_home_sidebar_shows_email_and_sign_out`.** The new Python caption became the first sidebar caption, so the test now checks that the email caption and the Python caption are both present. Included in commit 60f443c.

**2. [User scope] Password flow instead of OTP.** Deployed exit checks were adapted to sign-up, sign-in, refresh and sign-out. `.streamlit/secrets.toml` is tracked by user decision, so hygiene tests do not assert it is ignored.

**3. Task 2 human steps** were completed by the user (push, GitHub secrets, keep-alive run, Streamlit deploy, AI Studio quotas). The Gemini key step was deferred. Task 3 edits to STATE.md are left to the orchestrator, and the deployed exit checks and screenshots stay open, as listed above.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

- `.github/workflows/keepalive.yml`, `tests/test_repo_hygiene.py` and `app.py` exist.
- Commit 60f443c exists.
- 58 tests pass and ruff is clean.
