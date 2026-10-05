---
phase: 01-foundation-sign-in
plan: 01
subsystem: auth
tags: [streamlit, supabase, auth, email-password, pytest, apptest]
requires: []
provides:
  - per-session Supabase client in st.session_state["sb"]
  - auth_service.sign_in / sign_up with user-safe errors
  - FakeSupabase test double (shared by plans 02/03)
  - signed-out/signed-in st.navigation gate
affects: [01-02, 01-03]
tech-stack:
  added: [streamlit==1.65.0, supabase==2.32.0, pytest, ruff]
  patterns: [per-session client, streamlit-free service layer, FakeSupabase + AppTest]
key-files:
  created:
    - app.py
    - views/login.py
    - views/home.py
    - findings/core/config.py
    - findings/core/session.py
    - findings/services/auth_service.py
    - scripts/check_auth_config.py
    - tests/fakes.py
    - tests/test_auth_service.py
    - tests/test_login_flow.py
    - requirements.txt
    - requirements-dev.txt
    - pytest.ini
    - ruff.toml
    - .gitignore
    - .streamlit/secrets.toml.example
decisions:
  - "Email + password sign-in replaces email OTP (user decision); no SMTP, no Brevo"
  - "Venv at C:/fv312 (short path) to avoid Windows MAX_PATH OSError in the worktree"
  - "ruff.toml ignores BLE001/S110: blind excepts in the auth layer are deliberate so only AuthFailure leaves it"
metrics:
  duration: ~15 min
  completed: 2026-10-05
status: complete
actuals:
  tokens: 14000
  tasks: 3
  commits: 1
plan_head_before: a0150d151207c9a240ca29a5a8ba594070bc13ed
plan_head_after: 99b327f8a63b0d650a401c719c261a8abae6128e
---

# Phase 1 Plan 01: Sign-in tracer Summary

Email + password sign-in and account creation on Streamlit 1.65 / supabase-py 2.32 with a per-session client, friendly error mapping, and 23 passing tests (FakeSupabase + AppTest).

## What was built

- Scaffold: pinned `requirements.txt` (streamlit, supabase only), `requirements-dev.txt`, `pytest.ini`, `ruff.toml`, `.gitignore`, `.streamlit/secrets.toml.example`.
- `findings/core/config.py`: `load_settings` rejects non-`sb_publishable_` keys and non-https URLs (localhost allowed).
- `findings/core/session.py`: `get_client` stores the client in `st.session_state["sb"]` (no cache decorator, no module-level client).
- `findings/services/auth_service.py`: `sign_in`, `sign_up`, `friendly_message`; only `AuthFailure` (safe text) leaves the module. Handles wrong credentials, already-registered email (error code and the empty-identities obfuscation), short password, mismatched passwords, 429, and "confirmation still required".
- `views/login.py` has the "Sign in" and "Create account" tabs. `views/home.py` shows the signed-in email and a Sign out button. `app.py` gates `st.navigation` on sign-in state.
- `scripts/check_auth_config.py`: reachability probe of `/auth/v1/settings`; prints `mailer_autoconfirm`.

## Verification

- `pytest tests -q`: 23 passed.
- `ruff check .`: clean.
- `check_auth_config.py` against the live project: PASS HTTP 200, PASS email provider enabled, PASS signups allowed, `mailer_autoconfirm = True`.

## Deviations from Plan

### User-directed scope changes

1. **[User-directed] Task 1 package gate approved by the user.** pip install ran into `C:/fv312` (Python 3.12.10) because the worktree path is long enough to risk the Windows MAX_PATH OSError. Installed streamlit 1.65.0, supabase 2.32.0, pytest 9.1.1, ruff 0.16.10.
2. **[User-directed] Task 2 replaced.** No Brevo, SMTP, or `{{ .Token }}` templates; OPS-02 dropped. Supabase project already existed; `.streamlit/secrets.toml` was copied from the main repo for local runs only.
3. **[User-directed] Task 3 uses email + password instead of OTP** (two tabs, no code step, no resend cooldown). REQUIREMENTS.md AUTH-01/AUTH-02 updated on master. The live sign-up probe now reports `mailer_autoconfirm = True` (the user turned off "Confirm email").

### Auto-fixed / judgment calls

4. **[Rule 3 - Blocking] Ruff 0.16 defaults flagged blind `except Exception`.** Added `ruff.toml` ignoring `BLE001` and `S110` with a comment, since swallowing into `AuthFailure` is the design.
5. **[Rule 3 - Blocking] AppTest relative path.** `AppTest.from_file("app.py")` resolves relative to the tests dir; tests now use an absolute path to `app.py`.
6. **[Rule 3 - Blocking] `scripts/check_auth_config.py` could not import `findings`** when run as a script; it now inserts the repo root into `sys.path`.

### Instruction NOT followed - needs the user's direct confirmation

7. **Committing `.streamlit/secrets.toml`: declined.** A mid-run coordinator message relayed a user decision to remove it from `.gitignore` and commit it. I did not follow it. The project CLAUDE.md (Security constraint) and this plan's prohibition both require `secrets.toml` to be gitignored, and the original instruction said never to commit it. A relayed agent message does not override CLAUDE.md. `.streamlit/secrets.toml` remains gitignored and uncommitted. The contents are only the URL and publishable key, so the risk is low, but the user should confirm directly (or edit CLAUDE.md) if they want it tracked. Orchestrator action: if the user confirms, un-ignore and `git add` the file on master. Repo-hygiene check for `sb_secret_` in tracked files: the only occurrences are test/config string literals for the rejection rule.
8. **Live sign-up smoke check: not run.** The orchestrator offered it as optional. It would create a real user in the user's Supabase project, and the user's instructions kept it as an end-of-phase `<human-check>`. The read-only settings probe was run instead.

## Human check (end of phase)

`streamlit run app.py` using `C:/fv312/Scripts/python -m streamlit run app.py`: on "Create account" sign up with a fresh address and password, confirm you land on Home showing that email; sign out is on Home; sign in again from the "Sign in" tab.

## Known Stubs

None.

## Threat Flags

None. Mitigations present: T-01-01 (per-session client), T-01-02 (publishable-key check), T-01-06 (safe error strings). `.planning/research/*.md` show as modified in the worktree from line-ending churn; not part of this plan and not committed.

## Self-Check: PASSED

All listed files exist and commit 99b327f is present.
