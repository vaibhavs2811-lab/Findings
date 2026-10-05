---
phase: 01-foundation-sign-in
plan: 03
subsystem: auth
tags: [streamlit, supabase, session, cookie, sign-out, apptest]
requires: [01-01]
provides:
  - sign_out() (local scope) on every signed-in page via sidebar
  - Account page
  - findings_rt refresh-token cookie restore across browser refresh
  - AST + two-session isolation tests
affects: [01-04]
tech-stack:
  added: []
  patterns: [refresh token only in cookie, idempotent st.html cookie script, auto_refresh_token=False]
key-files:
  created:
    - findings/core/cookies.py
    - views/account.py
    - tests/test_session.py
    - tests/test_cookie_restore.py
  modified:
    - findings/core/session.py
    - app.py
    - views/home.py
decisions:
  - "Cookie carries only the refresh token; allowlist regex on read and write"
  - "Sidebar Sign out replaces the Home-page button (Account page keeps its own)"
metrics:
  duration: ~10 min
  completed: 2026-10-05
status: complete
actuals:
  tokens: 9000
  tasks: 2
  commits: 2
plan_head_before: 94b55e49af1f3816f28c05999a54868dd5b87745
plan_head_after: 094de4efe930d0246edf55ebe8f86aa8a1389173
---

# Phase 1 Plan 03: Sign out, cookie restore, isolation Summary

Sign out from any page (local-scope revoke), refresh-token cookie restore with rotation and stale-token handling, and AST/two-session proof that no client is cached or shared; 47 tests pass, ruff clean.

## What was built

- `findings/core/cookies.py`: `read_refresh_token`, `build_cookie_script`, `sync_cookie` for `findings_rt` (Path=/, Max-Age=604800, SameSite=Strict, Secure). Values outside `[A-Za-z0-9_.-]{8,512}` are rejected on read and never embedded in JS (`sync_cookie` falls back to the expire script).
- `findings/core/session.py`: client built with `ClientOptions(auto_refresh_token=False)`; `restore_once`, `refresh_if_needed`, `cookie_value`, and `sign_out()` (scope "local", AuthError swallowed, clears user/sb/otp_ keys, keeps `restore_attempted`).
- `app.py`: restore -> refresh -> navigation (Home, Account) -> sidebar email + Sign out -> `sync_cookie(cookie_value())` -> `nav.run()`.
- Tests: `test_session.py` (8) and `test_cookie_restore.py` (16 incl. parametrized).

## Deviations from Plan

- **[User-directed] OTP references adapted to password flow.** No OTP state exists; `otp_` key cleanup in `sign_out` is kept harmlessly.
- **[Judgment] Task commit split.** `findings/core/cookies.py` and the restore/refresh functions in `session.py` and the `app.py` wiring were written alongside Task 1 (since `session.py`/`app.py` import them), so commit 2dff5cd contains that code; commit 094de4e adds the Task 2 tests. All behavior in both task specs is covered.
- **[Judgment] Home-page Sign out button removed** (views/home.py) because the sidebar now provides it on every page; avoids duplicate buttons.
- `sign_out` signature changed from `sign_out(sb)` to `sign_out()` (reads the client from session state, usable as an `on_click` callback).
- Used `C:/fv312/Scripts/python` instead of `.venv/Scripts/python` per orchestrator instruction.

## Verification

- `pytest tests -q`: 47 passed. `ruff check .`: clean.

## Human check (end of phase)

Locally with `C:/fv312/Scripts/python -m streamlit run app.py`: sign in, press F5 and still see Home; DevTools Application -> Cookies shows `findings_rt` with SameSite Strict and Secure; click Sign out (sidebar, from Home and from Account), press F5, see Sign in and no `findings_rt`; edit the cookie to garbage, F5, see Sign in with no error. Also two-browser isolation: sign in as different users in two browsers and confirm each shows its own email.

## Known Stubs

None.

## Threat Flags

None. Mitigations in place: T-01-15/16 (allowlist, refresh-token-only, Secure/Strict), T-01-17 (restore once, AuthError -> Sign in), T-01-18 (local sign-out + cookie cleared), T-01-24 (AST scan + two-session test).

## Self-Check: PASSED

Files exist; commits 2dff5cd and 094de4e present.
