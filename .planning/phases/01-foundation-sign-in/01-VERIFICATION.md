---
phase: 01-foundation-sign-in
verified: 2026-10-05T09:00:00Z
status: human_needed
score: 4/6 must-haves verified
covered_files:
  - ".github/workflows/keepalive.yml"
  - "app.py"
  - "findings/core/config.py"
  - "findings/core/cookies.py"
  - "findings/core/session.py"
  - "findings/repos/profiles.py"
  - "findings/services/auth_service.py"
  - "scripts/check_live.py"
  - "supabase/schema.sql"
  - "tests/test_repo_hygiene.py"
  - "views/account.py"
  - "views/home.py"
  - "views/login.py"
covered_digest: "v2:sha256:dcbf9eacfe5673d547e2d8dcaa09f27a87be540c6dbfac0df730fd7359a0ffee"
behavior_unverified: 1
overrides_applied: 0
behavior_unverified_items:
  - truth: "A signed-in user is still signed in after a browser refresh (F5) on the deployed app"
    test: "Sign in on https://findings.streamlit.app, press F5"
    expected: "Home still shows the signed-in email; DevTools shows a findings_rt cookie; after Sign out and F5 the cookie is gone and the Sign in page shows"
    why_human: "Unit tests fake st.context.cookies and the Supabase client. Whether Streamlit Cloud (https, st.html script execution, Secure + SameSite=Strict cookie) really writes the cookie and passes it back on a new websocket session can only be seen in a real browser."
human_verification:
  - test: "Python version caption on Cloud"
    expected: "Sidebar caption reads 'Findings · Python 3.12.x' on https://findings.streamlit.app. If not, delete and redeploy the app with 3.12 chosen in Advanced settings."
    why_human: "The caption is computed at runtime on Cloud; the Cloud 'Advanced settings' choice cannot be read from the repo."
  - test: "New sign-up lands on Home"
    expected: "Create account tab, fresh address + 6+ char password, lands on Home showing that email and 'Profile record found'."
    why_human: "Needs a real browser with typed passwords and writes a real user. The backend flag mailer_autoconfirm=True and the AppTest sign-up flow are verified, the deployed UI path is not."
  - test: "Demo account sign-in on Cloud"
    expected: "Sign in tab with the demo email + password lands on Home with 'Profile record found'."
    why_human: "Demo password is not available to the verifier in a browser; check_live.py proves the backend half only."
  - test: "F5 refresh persistence (cookie restore)"
    expected: "See behavior_unverified_items. If it fails on Cloud, apply the PA-04 fallback (SameSite=Strict to Lax in findings/core/cookies.py) or record AUTH-04 as a limitation."
    why_human: "Real browser cookie behaviour on Cloud."
  - test: "Sign out from Home (sidebar) and from Account"
    expected: "Each returns to the Sign in page; F5 afterwards stays signed out; no findings_rt cookie."
    why_human: "Real browser."
  - test: "Two-browser isolation"
    expected: "Two different browsers signed in as two accounts at once each show only their own email and user id on Home and Account, also after F5."
    why_human: "Needs two live browser sessions against the deployed app."
  - test: "Cloud secrets contents"
    expected: "Streamlit Cloud secrets and GitHub Actions secrets contain only SUPABASE_URL / SUPABASE_PUBLISHABLE_KEY (plus optionally GEMINI_API_KEY), no sb_secret_ key and no demo password."
    why_human: "Dashboard contents are not readable from the repo."
---

# Phase 1: Foundation & Sign-in Verification Report

**Phase Goal:** A researcher can open the live Findings app on Streamlit Cloud, sign in (email + password, changed by user from emailed code) or with the demo account, stay signed in across refreshes, and sign out.
**Verified:** 2026-10-05
**Status:** human_needed
**Re-verification:** No, initial verification

Judged against the user-directed changes: AUTH-01/02 are email + password, OPS-02 is descoped by user decision, `.streamlit/secrets.toml` (URL + publishable key) is committed by user decision, and the demo account is an ordinary password account on the Sign in tab.

## Goal Achievement

### Observable Truths

Roadmap success criteria, adapted to the user-directed changes (SC1 and SC5 reworded for password auth and the secrets decision), plus the plan must-haves they absorb.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SC1: On the deployed app a brand-new address creates an account and signs in straight away, and a returning address signs in, with email + password | VERIFIED (code + backend; deployed UI in human list) | `views/login.py` has Sign in and Create account tabs calling `auth_service.sign_in` / `sign_up` (`findings/services/auth_service.py`), which map errors to safe text and reject existing-account obfuscation and "confirmation required". `scripts/check_auth_config.py` live: HTTP 200, email provider enabled, signups allowed, `mailer_autoconfirm = True`. Tests: `tests/test_login_flow.py` (sign-up lands on Home, wrong password, validation, duplicate email). `check_live.py` D1 signs in against the real project. Live "https://findings.streamlit.app" returned 303 (redirect to app), orchestrator reports the sign-in page renders. |
| 2 | SC2: The demo account signs in with email + password on the same Sign in tab, no inbox | VERIFIED (backend; deployed UI in human list) | `check_live.py` re-run by me: 14 passed, 0 failed. D1 demo sign-in, D2 own profiles row visible (1 row), D7 `get_contact_email(self)` returns own email. `scripts/local.toml` is not tracked (`git ls-files` empty, hygiene test passes). |
| 3 | SC3: A signed-in user stays signed in after a browser refresh and can sign out from any page | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED for refresh; sign-out VERIFIED at code level | Refresh: `findings/core/cookies.py` (findings_rt, refresh token only, allowlist regex), `session.restore_once` / `refresh_if_needed` / `cookie_value`, `app.py` calls restore then `sync_cookie(session.cookie_value())` before `nav.run()`. `st.html(..., unsafe_allow_javascript=True)` and `st.context.cookies` both exist in installed streamlit 1.65.0. `tests/test_cookie_restore.py` covers restore, rotation, reused/garbage token, injection with a faked cookie reader. No test or evidence exercises a real browser round trip on Cloud (Secure + SameSite=Strict, script execution, rotation race). Sign-out: sidebar button in `app.py` (every signed-in page) and Account button; `session.sign_out` uses `{"scope": "local"}`, clears user/sb, `tests/test_session.py` `test_sign_out_from_any_page` (Home and Account), `test_sign_out_error_still_clears_local_state` pass. |
| 4 | SC4: Two simultaneous browsers each see only their own account and data | VERIFIED (code + backend; two-browser run in human list) | Client created only in `st.session_state["sb"]` (`findings/core/session.py`); no cache decorator or module-level client (AST test `test_no_cache_decorators_and_no_stray_create_client` passes); `test_two_sessions_get_distinct_real_clients` passes. RLS on all tables in `supabase/schema.sql` (profiles select limited to `is_complete or own id`, update own row only with column grants). Live: D4 cross-user update 0 rows, D5 `is_synthetic` flip rejected, D6 `profile_contacts` unreadable, D9 connections empty. |
| 5a | SC5 (part): The deployed app runs on Python 3.12 | ? UNCERTAIN | `app.py` renders `Findings · Python {platform.python_version()}` in the sidebar; local venv is 3.12.10. The Cloud runtime version cannot be read from the repo and has not been confirmed by a human. Human item 1. |
| 5b | SC5 (part): No secret key in the repo, and the daily keep-alive workflow shows a green run against Supabase | VERIFIED (workflow run per orchestrator; Cloud secrets in human list) | `.streamlit/secrets.toml` tracked by user decision and contains only `SUPABASE_URL` and an `sb_publishable_` key (verified by reading the file). `git grep` for `sb_secret_`, `AIza...`, `xsmtpsib` outside the hygiene test: no hits. `config.load_settings` rejects any key not starting `sb_publishable_`. `tests/test_repo_hygiene.py` passes. `.github/workflows/keepalive.yml`: cron `17 6 * * *`, `workflow_dispatch`, `permissions: {}`, secrets only via `env`, `curl --fail` on `/rest/v1/keepalive`, asserts `"id":1`. Manual run success per orchestrator (run 37250562753); I could not re-query it (`gh` not installed). `check_live.py` A1 independently confirms anon can read the keepalive row (1 row). |

**Score:** 4/6 truths verified (1 present, behavior-unverified; 1 uncertain)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app.py` | Settings, per-session client, restore, gated `st.navigation`, sidebar sign-out, cookie sync | VERIFIED | 43 lines, all wired in order |
| `findings/core/session.py` | Per-session client, restore/refresh/sign_out | VERIFIED | Substantive; imported by app and all views |
| `findings/core/cookies.py` | findings_rt read/build/sync | VERIFIED | Allowlist on read and write; wired from app.py and session.py |
| `findings/core/config.py` | Publishable-key-only settings | VERIFIED | Rejects non-`sb_publishable_` keys |
| `findings/services/auth_service.py` | sign_in / sign_up with safe errors | VERIFIED | Wired from `views/login.py`; no raw exception text leaves the module |
| `views/login.py`, `views/home.py`, `views/account.py` | Sign in/up tabs, own-record Home, Account | VERIFIED | Home reads `get_own_profile` through the user's own client |
| `findings/repos/profiles.py` | Own profile read, explicit columns | VERIFIED | No star, no embedding column |
| `supabase/schema.sql` | Full schema, RLS, RPC, keepalive | VERIFIED | Five tables with RLS; no email column on profiles; no policy on profile_contacts; no FK to auth.users; `get_contact_email` revoked from anon. Live behaviour confirmed by `check_live.py`. Re-run idempotence is by construction (`if not exists`, `drop ... if exists`, `create or replace`, `on conflict`); the executor could not confirm a double run |
| `scripts/check_live.py` | Live anon + demo RLS probe | VERIFIED | Re-run: 14 passed, 0 failed |
| `.github/workflows/keepalive.yml` | Daily + manual PostgREST read | VERIFIED | See truth 5b |
| `tests/test_repo_hygiene.py` | No tracked secrets | VERIFIED | Passes |
| `docs/screenshots/phase-1/*` | Sign-in, home, demo login, keep-alive screenshots | MISSING | No `docs/` directory is tracked. Planned in 01-04 `files_modified` and ROADMAP "Docs capture", not part of a success criterion. Feeds DOCS-03 in Phase 8. Warning only. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app.py` | `session.restore_once` / `refresh_if_needed` | called before `st.navigation` | WIRED | lines 19-21 |
| `app.py` | `cookies.sync_cookie` | `sync_cookie(session.cookie_value())` before `nav.run()` | WIRED | line 42 |
| `views/home.py` | `repos/profiles.get_own_profile` | session client + current user id | WIRED | Live D2 shows the row is readable under RLS |
| `views/login.py` | `auth_service.sign_in` / `sign_up` | form submit, then `session.set_signed_in` + rerun | WIRED | |
| `auth.users` insert | `profiles` + `profile_contacts` | trigger `on_auth_user_created` | WIRED | D2 and D7 prove the rows exist for the demo user |
| Cloud secrets | `config.load_settings` | `st.secrets` | WIRED in code | Deployed app renders the sign-in page, so settings load on Cloud |
| keepalive.yml | `public.keepalive` | curl `/rest/v1/keepalive` with publishable key | WIRED | Table readable by anon (A1) |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `views/home.py` | `profile` | `sb.table("profiles").select(...).eq("id", user_id)` under user JWT | Yes (live D2: 1 row) | FLOWING |
| `views/account.py` | `user` | `st.session_state["user"]` set from the Supabase auth response | Yes | FLOWING |
| `app.py` caption | `platform.python_version()` | Runtime | Yes (value on Cloud unconfirmed) | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Test suite | `C:/fv312/Scripts/python -m pytest tests -q` | 58 passed | PASS |
| Lint | `C:/fv312/Scripts/python -m ruff check .` | All checks passed | PASS |
| Live RLS / demo sign-in | `C:/fv312/Scripts/python scripts/check_live.py` | 14 passed, 0 failed | PASS |
| Auth settings | `scripts/check_auth_config.py` | HTTP 200, signups allowed, autoconfirm true | PASS |
| streamlit APIs used exist | introspect `st.html`, `st.context.cookies` | both present in 1.65.0 | PASS |
| Deployed app reachable | `curl https://findings.streamlit.app` | 303 | PASS (redirect, Streamlit's normal behaviour; page content is JS-rendered, so not inspectable by curl) |
| Deployed behaviours | | | SKIP, routed to human verification |

### Probe Execution

Step 7c: SKIPPED. No `probe-*.sh` scripts exist or are declared in the plans. `scripts/check_live.py` serves as the live probe and was run above.

### Requirements Coverage

All nine phase IDs appear across the PLAN frontmatter (01: AUTH-01, AUTH-02, AUTH-06, OPS-02; 02: AUTH-03, AUTH-06; 03: AUTH-04, AUTH-05, AUTH-06; 04: OPS-01, OPS-03, AUTH-01, AUTH-02) and in REQUIREMENTS.md traceability for Phase 1. No orphaned Phase 1 requirements.

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| AUTH-01 | 01-01, 01-04 | Email + password account creation and sign-in | SATISFIED (code/backend); deployed UI pending human | login tabs, auth_service, tests, autoconfirm true |
| AUTH-02 | 01-01, 01-04 | First-time user creates account from the sign-in page and is signed in at once; returning user signs in | SATISFIED (code/backend); deployed UI pending human | `test_create_account_signs_in_straight_away`; `sign_up` requires a returned session |
| AUTH-03 | 01-02 | Demo account signs in with email + password | SATISFIED (backend) ; deployed UI pending human | check_live D1/D2/D7 |
| AUTH-04 | 01-03 | Stays signed in after a refresh | NEEDS HUMAN | Cookie code and unit tests present; real-browser Cloud behaviour unconfirmed |
| AUTH-05 | 01-03 | Sign out from any page | SATISFIED (code); browser confirmation pending | sidebar + Account buttons, tests |
| AUTH-06 | 01-01, 01-02, 01-03 | Per-session isolation | SATISFIED (code + RLS live); two-browser run pending | AST test, distinct-client test, D4 to D6 |
| OPS-01 | 01-04 | Deployed on Streamlit Cloud, Python 3.12, no secret key in repo | PARTIAL / NEEDS HUMAN | Deployed and reachable; 3.12 and Cloud secrets unconfirmed; tracked secrets.toml holds only URL + publishable key (user-approved) |
| OPS-02 | 01-01 | Custom SMTP | DESCOPED BY USER DECISION (2026-10-05) | Struck through in REQUIREMENTS.md; Supabase confirm-email is off instead. Not a gap. |
| OPS-03 | 01-04 | Daily GitHub Actions keep-alive, also manual | SATISFIED | Workflow shape verified; manual run green per orchestrator; anon read of keepalive confirmed live |

### Anti-Patterns Found

Scanned `app.py`, `findings/**`, `views/**`, `scripts/**`, `supabase/schema.sql`, `.github/workflows/keepalive.yml`.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | | No TBD/FIXME/XXX/TODO markers, stubs or hardcoded empty data flowing to rendering | | |
| `findings/core/session.py` | 89 | `k.startswith("otp_")` leftover from the OTP design | Info | Harmless dead cleanup |
| `.planning/phases/01-foundation-sign-in/COVERAGE.md`, ROADMAP Phase 1 goal and criteria, STATE.md | | Still describe OTP, Brevo, OPS-02 and "0%" progress | Info | Stale planning docs; orchestrator should update ROADMAP/REQUIREMENTS checkboxes and STATE when closing the phase |
| `.planning/REQUIREMENTS.md` | | AUTH/OPS checkboxes and traceability still "Pending" | Info | Update after human checks pass |

Debt-marker gate: no unreferenced markers found, no blocker.

Prohibition check (plan `must_haves.prohibitions`): no cache decorator or module-level client (AST test); config refuses non-publishable keys; no raw exception text rendered (login shows only `AuthFailure` text, home shows a fixed warning); cookie holds only the refresh token and is allowlist-validated; sign-out uses local scope; keepalive has `permissions: {}`; no email column on `profiles`, no select policy on `profile_contacts`, no FK to `auth.users`; demo password and `scripts/local.toml` untracked. All hold. The plan prohibition on committing `.streamlit/secrets.toml` is superseded by the user decision, and the file contains no secret key.

### Human Verification Required

1. **Python 3.12 on Cloud.** Open https://findings.streamlit.app, read the sidebar caption. Expected `Python 3.12.x`. If not, delete and redeploy choosing 3.12.
2. **New sign-up.** Create account with a fresh address and a password of at least 6 characters. Expected: lands on Home with the email and "Profile record found".
3. **Demo sign-in.** Sign in tab with the demo credentials. Expected: Home with "Profile record found".
4. **F5 persistence.** After sign-in press F5. Expected: still on Home; `findings_rt` cookie present (Secure, SameSite=Strict). If not, try SameSite=Lax; if still failing, record AUTH-04 as a limitation.
5. **Sign out.** From the sidebar on Home, and from the Account page. Expected: Sign in page; F5 stays signed out; no cookie.
6. **Two-browser isolation.** Two browsers, two accounts at the same time. Expected: each sees only its own email and id, also after F5.
7. **Cloud and GitHub secrets.** Confirm no `sb_secret_` key or demo password is stored there.

### Gaps Summary

No automated gaps. Every code-level and backend-level must-have is present, substantive and wired, and the live Supabase probe, 58 tests and lint all pass. The status is `human_needed` rather than `passed` because the goal is a statement about the deployed app in a real browser: the Cloud Python version, deployed sign-up and demo sign-in, cookie-based refresh persistence (the one behavior-dependent truth with no real-browser evidence), sign-out from both pages, two-browser isolation, and Cloud secret contents have not been confirmed by a person. AUTH-04 is the highest-risk item (Secure + SameSite=Strict cookie written by an `st.html` script on Cloud); the PA-04 fallback is documented in 01-03-PLAN. Screenshots for DOCS-03 were not captured in Phase 1 and should be gathered during these checks.

---

_Verified: 2026-10-05_
_Verifier: Claude (gsd-verifier)_
