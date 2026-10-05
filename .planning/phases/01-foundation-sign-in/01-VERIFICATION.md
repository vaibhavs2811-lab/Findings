---
phase: 01-foundation-sign-in
verified: 2026-10-05T04:01:00Z
status: passed
score: 6/6 must-haves verified
covered_files:
  - ".github/workflows/keepalive.yml"
  - ".planning/phases/01-foundation-sign-in/01-01-PLAN.md"
  - ".planning/phases/01-foundation-sign-in/01-01-SUMMARY.md"
  - ".planning/phases/01-foundation-sign-in/01-02-PLAN.md"
  - ".planning/phases/01-foundation-sign-in/01-02-SUMMARY.md"
  - ".planning/phases/01-foundation-sign-in/01-03-PLAN.md"
  - ".planning/phases/01-foundation-sign-in/01-03-SUMMARY.md"
  - ".planning/phases/01-foundation-sign-in/01-04-PLAN.md"
  - ".planning/phases/01-foundation-sign-in/01-04-SUMMARY.md"
  - "app.py"
  - "findings/core/config.py"
  - "findings/core/cookies.py"
  - "findings/core/session.py"
  - "findings/repos/profiles.py"
  - "findings/services/auth_service.py"
  - "scripts/check_live.py"
  - "supabase/schema.sql"
  - "tests/test_cookie_restore.py"
  - "tests/test_repo_hygiene.py"
  - "tests/test_session.py"
  - "views/account.py"
  - "views/home.py"
  - "views/login.py"
covered_digest: "v2:sha256:a97c85a0c08a0799c9182399629fb4764d4328538c46725d560c0ec5a818dd3b"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 4/6
  gaps_closed:
    - "SC3 refresh persistence: previous run had no real-browser evidence; the F5 fix (26e6e3f) plus Cloud UAT item 4 now supply it"
    - "SC5a Python 3.12 on Cloud: UAT item 1 pass"
  gaps_remaining: []
  regressions: []
---

# Phase 1: Foundation & Sign-in Verification Report

**Phase Goal:** A researcher can open the live Findings app on Streamlit Cloud, sign in with email + password (changed by user from emailed code) or with the demo account, stay signed in across refreshes, and sign out.
**Verified:** 2026-10-05
**Status:** passed
**Re-verification:** Yes. The previous report was stale after the F5 fix (commit 26e6e3f changed `findings/core/cookies.py`, `findings/core/session.py`, `app.py` and the tests).

Judged against the user-directed changes: AUTH-01/02 are email + password (no OTP, no Brevo); OPS-02 is descoped by the user; `.streamlit/secrets.toml` (URL + publishable key only) is committed by user decision; the demo account is an ordinary password account.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SC1: A brand-new address creates an account and is signed in straight away; a returning address signs in; both with email + password | VERIFIED | `views/login.py` Sign in / Create account tabs call `auth_service.sign_in` / `sign_up`. `tests/test_login_flow.py` covers sign-up landing on Home, wrong password, validation, duplicate email. `check_live.py` D1 signs in against the real project. UAT 2 (new sign-up lands on Home): pass on Cloud. |
| 2 | SC2: The demo account signs in with email + password on the same Sign in tab, no inbox | VERIFIED | `check_live.py` re-run by me: 14 passed, 0 failed (D1 demo sign-in, D2 own profile row, D7 own contact email). UAT 3: pass on Cloud. |
| 3 | SC3: A signed-in user stays signed in after F5 and can sign out from any page | VERIFIED | See the F5 analysis below. Sign-out: sidebar button in `app.py` (every signed-in page) plus Account button; `session.sign_out` uses local scope, deletes `user` and `sb`, sets `clear_cookie`; `app.py` passes it to `cookies.sync(clear=...)` and the bridge deletes the cookie. Tests `test_sign_out_clears_browser_cookie`, `test_sign_out_from_any_page`, `test_sign_out_error_still_clears_local_state`. UAT 4 and 5: pass on Cloud. |
| 4 | SC4: Two simultaneous browsers each see only their own account and data | VERIFIED | Client only in `st.session_state["sb"]` (`session.get_client`), no cache decorator or module-level client (AST test passes). RLS in `supabase/schema.sql`. Live D4 cross-user update 0 rows, D5 `is_synthetic` flip rejected, D6 `profile_contacts` unreadable, D9 connections empty. UAT 6: pass with two real browsers. |
| 5a | SC5 (part): The deployed app runs on Python 3.12 | VERIFIED | `app.py` renders `Python {platform.python_version()}` in the sidebar. UAT 1: user confirmed 3.12.x on https://findings.streamlit.app. |
| 5b | SC5 (part): No secret key in the repo or Cloud/GitHub secrets, and the daily keep-alive workflow is green | VERIFIED | `.streamlit/secrets.toml` (tracked by user decision, 2 lines) holds only `SUPABASE_URL` and an `sb_publishable_` key. `config.load_settings` rejects any key not starting `sb_publishable_`. `tests/test_repo_hygiene.py` passes. `.github/workflows/keepalive.yml`: cron `17 6 * * *`, `workflow_dispatch`, `permissions: {}`, `curl --fail` on `/rest/v1/keepalive`. Run 37250562753 success per orchestrator (`gh` unavailable to me; not re-queried). `check_live.py` A1: anon reads the keepalive row. UAT 7: pass. |

**Score:** 6/6 truths verified, 0 present-but-behavior-unverified.

### F5 refresh persistence after the fix (the behavior-dependent truth)

Code read at the current HEAD (not from SUMMARY):

- `findings/core/cookies.py`: `st.components.v2.component("findings_cookie", ...)` bridge JS reads and writes `findings_rt` in the browser (`Path=/; Max-Age=604800; SameSite=Lax; Secure`), deletes it when `data.clear`, and calls `setStateValue("rt", cur)` only when `cur !== d.seen` (no rerun loop). `sync()` allowlist-validates `want` against `[A-Za-z0-9_.\-]{8,512}` before it reaches the browser, validates the reported token, and uses the server `st.context.cookies` read only as a fallback before the browser has reported.
- `findings/core/session.py`: `restore_from_cookie(token)` records `restore_attempted = token`, so each token is tried once per session; failures show Sign in. `cookie_value()` returns the live session's refresh token (rotation is synced). `sign_out` sets `clear_cookie`.
- `app.py`: `get_client` then `refresh_if_needed` then `cookies.sync(session.cookie_value(), clear=pop("clear_cookie"))` then `restore_from_cookie` then `st.rerun()`, all before `st.navigation`.
- Tests: `tests/test_cookie_restore.py` (bridge JS flags, unsafe `want` never sent, validated browser token, server fallback only before the browser reports, restore once, reused token falls to sign in, rotated token synced, sign-out clears cookie).

Behavioral evidence: real-browser localhost run with the server fallback disabled (simulating Cloud) by the orchestrator (F5 kept the user signed in three times; sign-out then F5 stayed signed out; fresh sign-in then F5 stayed signed in), plus UAT 4 and 5 passed by the user on https://findings.streamlit.app after the fix was pushed (commit 09:22 +05:30, UAT recorded 03:59Z, i.e. after it). I cannot read the Cloud deployment revision from the repo, so "UAT ran against the redeployed fix" rests on that timing and on the user's report. Because the Cloud proxy strips custom cookies, a pass on Cloud is itself evidence the bridge, not the server cookie, is doing the work.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app.py` | Settings, per-session client, cookie sync, restore, gated navigation, sidebar sign-out | VERIFIED | 44 lines, order as above |
| `findings/core/cookies.py` | Browser cookie bridge | VERIFIED | Substantive, wired from `app.py`, allowlist on write and read |
| `findings/core/session.py` | Per-session client, restore/refresh/sign_out | VERIFIED | Imported by app and all views |
| `findings/core/config.py` | Publishable-key-only settings | VERIFIED | Rejects non-publishable keys |
| `findings/services/auth_service.py` | sign_in / sign_up with safe errors | VERIFIED | Wired from `views/login.py` |
| `views/login.py`, `views/home.py`, `views/account.py` | Sign in/up, own-record Home, Account | VERIFIED | Home reads own row via the user's client |
| `findings/repos/profiles.py` | Own profile read | VERIFIED | Explicit columns |
| `supabase/schema.sql` | Schema, RLS, RPC, keepalive | VERIFIED | Live behaviour confirmed by `check_live.py` |
| `scripts/check_live.py` | Live anon + demo RLS probe | VERIFIED | 14 passed, 0 failed |
| `.github/workflows/keepalive.yml` | Daily + manual PostgREST read | VERIFIED | See truth 5b |
| `tests/test_repo_hygiene.py` | No tracked secrets | VERIFIED | Passes |
| `docs/screenshots/phase-1/*` | Phase 1 screenshots | MISSING (not a success criterion) | Planned in 01-04; feeds DOCS-03 in Phase 8. Warning only. |

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| `app.py` | `cookies.sync` | `sync(session.cookie_value(), clear=...)` before restore and `nav.run()` | WIRED |
| `app.py` | `session.restore_from_cookie` | token returned by `sync`, then `st.rerun()` | WIRED |
| `session.sign_out` | `cookies.sync` | `clear_cookie` flag popped in `app.py` | WIRED |
| `views/login.py` | `auth_service.sign_in` / `sign_up` | form submit, `set_signed_in`, rerun | WIRED |
| `views/home.py` | `repos/profiles.get_own_profile` | session client + user id | WIRED |
| `auth.users` insert | `profiles` + `profile_contacts` | trigger `on_auth_user_created` | WIRED (live D2, D7) |
| keepalive.yml | `public.keepalive` | curl with publishable key | WIRED (live A1) |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Real Data | Status |
|----------|---------------|--------|-----------|--------|
| `views/home.py` | `profile` | `profiles` select under user JWT | Yes (live D2: 1 row) | FLOWING |
| `views/account.py` | `user` | Supabase auth response in session state | Yes | FLOWING |
| `app.py` cookie sync | `session.cookie_value()` | live `auth.get_session().refresh_token` | Yes | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Test suite | `C:/fv312/Scripts/python -m pytest tests -q` | 58 passed | PASS |
| Lint | `C:/fv312/Scripts/ruff check .` | All checks passed | PASS |
| Live RLS / demo sign-in | `C:/fv312/Scripts/python scripts/check_live.py` | 14 passed, 0 failed | PASS |
| Debt markers | grep TBD/FIXME/XXX/TODO in app, findings, views, scripts, supabase, .github | none | PASS |

### Probe Execution

Step 7c: SKIPPED. No `probe-*.sh` scripts exist or are declared in the plans; `check_live.py` serves as the live probe and was run above.

### Requirements Coverage

All nine phase IDs appear in PLAN frontmatter and in REQUIREMENTS.md traceability for Phase 1. No orphaned requirements.

| Requirement | Source Plan | Status | Evidence |
|-------------|-------------|--------|----------|
| AUTH-01 | 01-01, 01-04 | SATISFIED | login tabs, auth_service, tests, UAT 2 |
| AUTH-02 | 01-01, 01-04 | SATISFIED | sign-up returns a session and lands on Home; UAT 2 |
| AUTH-03 | 01-02 | SATISFIED | check_live D1/D2/D7; UAT 3 |
| AUTH-04 | 01-03 | SATISFIED | cookie bridge code and tests, localhost browser run, UAT 4 on Cloud |
| AUTH-05 | 01-03 | SATISFIED | sidebar and Account sign-out, tests, UAT 5 |
| AUTH-06 | 01-01, 01-02, 01-03 | SATISFIED | AST test, distinct-client test, live RLS probes, UAT 6 |
| OPS-01 | 01-04 | SATISFIED | Deployed; UAT 1 (3.12) and UAT 7 (no secret key); tracked secrets.toml is publishable-only by user decision |
| OPS-02 | 01-01 | DESCOPED by user decision (2026-10-05) | Struck through in REQUIREMENTS.md. Not a gap. |
| OPS-03 | 01-04 | SATISFIED | Workflow shape verified; run 37250562753 success per orchestrator; live A1 |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `findings/core/session.py` | 87 | `k.startswith("otp_")` leftover from the OTP design | Info | Dead cleanup, harmless |
| `.planning/phases/01-foundation-sign-in/COVERAGE.md`, ROADMAP Phase 1 text, STATE.md | | Still mention OTP/Brevo/OPS-02 | Info | Stale planning docs |
| `.planning/REQUIREMENTS.md` | | AUTH/OPS checkboxes and traceability still "Pending" | Info | Orchestrator should tick Phase 1 items when closing the phase |

No unreferenced debt markers, no stubs, no blockers. Prohibitions hold: no cached or module-level client, config refuses non-publishable keys, cookie carries only the refresh token with allowlist validation on both sides, local-scope sign-out, keepalive has `permissions: {}`, no email column on `profiles`, no policy on `profile_contacts`, demo password and `scripts/local.toml` untracked.

### Human Verification Required

None outstanding. UAT items 1 to 7 in `01-UAT.md` are all `pass` (7/7, 0 issues).

### Gaps Summary

No gaps. Code, tests (58), lint, and the live Supabase probe (14/14) agree with the human UAT on the deployed app. Two residual notes, neither blocking: the Cloud deployment revision and the keep-alive run result were not independently re-queried by me (reported by the orchestrator and user), and Phase 1 screenshots for DOCS-03 were not captured.

---

_Verified: 2026-10-05_
_Verifier: Claude (gsd-verifier)_
