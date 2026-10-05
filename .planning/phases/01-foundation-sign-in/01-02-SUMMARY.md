---
phase: 01-foundation-sign-in
plan: 02
subsystem: database
tags: [supabase, postgres, rls, pgvector, streamlit, pytest]
requires: [01-01]
provides:
  - supabase/schema.sql (full first migration, applied live, re-runnable)
  - get_contact_email security-definer RPC (only door to profile_contacts)
  - findings/repos/profiles.get_own_profile
  - scripts/check_live.py (live anon + demo-user RLS probe)
affects: [01-03, 01-04, phase-02, phase-04, phase-05]
tech-stack:
  added: []
  patterns: [repo layer without streamlit, explicit column lists, column-level update grants]
key-files:
  created:
    - supabase/schema.sql
    - scripts/check_live.py
    - scripts/local.toml.example
    - findings/repos/__init__.py
    - findings/repos/profiles.py
    - tests/test_demo_login.py
  modified:
    - views/home.py
decisions:
  - "No separate demo-login UI: sign-in is email + password for everyone, so the demo account is an ordinary account using the Sign in tab (user decision)"
  - "check_live.py exits 2 with an explicit SKIP line when demo credentials are missing; the D1-D10 checks run once scripts/local.toml exists"
metrics:
  duration: ~25 min
  completed: 2026-10-05
status: complete
actuals:
  tokens: 14000
  tasks: 3
  commits: 3
plan_head_before: 94b55e49af1f3816f28c05999a54868dd5b87745
plan_head_after: 6d2106f
---

# Phase 1 Plan 02: Schema, RLS and own-record Home Summary

Full Phase 1 schema (profiles with give/need fields, private profile_contacts behind `get_contact_email()`, connections with unique-pair index and status guard trigger, match_cache, keepalive, RLS on all five tables) applied live, plus an RLS probe script and an own-profile read on Home.

## What was built

- `supabase/schema.sql`: one idempotent file. Auth triggers create a profiles row and a private profile_contacts row on signup and backfill existing users. Update on profiles is column-granted (never id, is_synthetic, created_at). Connection status changes are recipient-only through a guard trigger. Security-definer functions use `set search_path = ''`.
- `scripts/check_live.py`: probes the live project with the publishable key only (anon checks A1-A4, demo-user checks D1-D10). Never prints keys, tokens or the password.
- `findings/repos/profiles.py`: `get_own_profile` with an explicit column list (no star, no embedding).
- `views/home.py`: shows "Profile record found (created DATE)", a calm "No profile record yet." info, or a friendly warning on any database error.
- `tests/test_demo_login.py`: 7 tests (password sign-in normalisation, friendly wrong-password message, empty password skips Supabase, get_own_profile columns/None, three Home states).

## Verification

- `pytest tests -q`: 30 passed. `ruff check` clean on all files in this plan.
- Schema applied by the user in the SQL Editor (reported "schema applied"). I could not independently confirm that it ran twice without error.
- Live probe, no demo credentials available: `check_live.py` printed 4 passed, 0 failed, and exited 2 (SKIP).

### Live checks

| Check | Status |
| ----- | ------ |
| A1 anon reads keepalive (1 row) | PASS |
| A2 anon cannot read profiles | PASS (permission error) |
| A3 anon cannot read profile_contacts | PASS (permission error) |
| A4 anon cannot call get_contact_email | PASS (error) |
| D1-D10 demo-user checks (sign-in, own-row read/update, cross-user update blocked, is_synthetic blocked, contacts private, get_contact_email self/other, connections empty, sign-out) | PENDING |

Pending: `scripts/local.toml` (or the `FINDINGS_DEMO_EMAIL` / `FINDINGS_DEMO_PASSWORD` env vars) does not exist yet. When the user creates the demo account (Dashboard, Authentication, Users, Add user, Auto Confirm User) and fills `scripts/local.toml`, run `C:/fv312/Scripts/python scripts/check_live.py`. Expect "14 passed, 0 failed". Also a human-check at the end of the phase: sign in with the demo credentials on the Sign in tab and see Home show "Profile record found".

## Deviations from Plan

### User-directed scope changes

1. **[User-directed] No demo-login expander or `sign_in_with_password` function.** Email + password is already the sign-in method for everyone, so `views/login.py` and `findings/services/auth_service.py` were not edited. The existing "Wrong email or password." mapping stays (the plan text said "Email or password is incorrect.").
2. **[User-directed] Demo user creation and schema push were human steps**, done through the dashboard.

### Auto-fixed / judgment calls

3. **[Rule 3 - Blocking] Credential-less run.** The user could not supply demo credentials yet, so the credentialed D1-D10 checks were deferred. The script already skipped them with exit 2; I only made the SKIP wording explicit (commit 6d2106f).
4. **[Out of scope, logged]** `ruff check .` from the repo root reports I001 import-order errors in two plan 01-01 files (`findings/core/session.py`, `tests/test_auth_service.py`). Likely a first-party detection difference because of the worktree path. Not touched (plan 01-03 owns session.py).

## Known Stubs

None.

## Threat Flags

None. Mitigations T-01-08 to T-01-13 are encoded in schema.sql. Anon-side proof (A2-A4) passed live. Demo-user proof (D4-D8, which cover T-01-08 and T-01-09 from the authenticated side) is pending the credentials.

## Self-Check: PASSED

Files exist (schema.sql, check_live.py, local.toml.example, repos/profiles.py, tests/test_demo_login.py). Commits ce91243, 86c395a and 6d2106f are present.
