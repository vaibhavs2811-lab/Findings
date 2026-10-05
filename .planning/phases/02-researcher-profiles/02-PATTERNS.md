# Phase 2: Researcher Profiles - Pattern Map

**Mapped:** 2026-10-05
**Files analyzed:** 27 (11 modified, 16 new)
**Analogs found:** 21 / 27 (all analog paths verified git-tracked via `git ls-files`)

Phase 1 is small (about 12 source files), so the analogs below are the whole codebase. Layering is `views/*.py` -> `findings/services/*` -> `findings/repos/*`. Services, repos and `ai/` never import streamlit.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `findings/repos/profiles.py` (mod: PROFILE_COLUMNS, `update_own`, `ProfileWriteError`) | repo | CRUD | itself (`get_own_profile`) | exact |
| `findings/core/config.py` (mod: `gemini_api_key`) | config | transform | itself | exact |
| `findings/core/constants.py` (new) | config/constants | n/a | `findings/services/auth_service.py` module constants (lines 9-11) | partial |
| `findings/services/profile_service.py` (new) | service | CRUD + transform | `findings/services/auth_service.py` | role-match |
| `findings/ai/__init__.py`, `client.py`, `schemas.py`, `methods.py` (new) | service (external API) | request-response | `auth_service.py` (error wrapping to a user-safe exception) | partial |
| `ui/__init__.py`, `ui/badges.py`, `ui/profile_view.py` (new) | component | transform | `views/account.py` (simple render) | partial |
| `views/profile.py` (new) | view | CRUD, event-driven (callbacks) | `views/home.py` + `views/account.py` | role-match |
| `views/home.py` (mod: CTA) | view | request-response | itself | exact |
| `app.py` (mod: nav) | config/route | n/a | itself lines 27-30 | exact |
| `supabase/schema.sql` (mod: 2 ALTERs + grant list) | migration | n/a | itself (lines 16-33, 214-220 per RESEARCH) | exact |
| `requirements.txt` (mod) | config | n/a | itself | exact |
| `.streamlit/secrets.toml.example` (mod) | config | n/a | itself | exact |
| `tests/fakes_profiles.py` (new) | test helper | CRUD | `tests/fakes.py` `FakeQuery`/`FakeSupabase` | exact |
| `tests/test_profile_page.py` (new) | test (AppTest) | request-response | `tests/test_demo_login.py` | exact |
| `tests/test_profile_service.py`, `test_profiles_repo.py`, `test_methods.py` (new) | test | transform | `tests/test_auth_service.py`, `tests/test_demo_login.py` (repo test using `RecordingQuery`) | role-match |
| `tests/test_ai_client.py` (new) | test | request-response | none (use RESEARCH MockTransport sketch) | none |
| `tests/test_schema_sql.py`, `tests/test_layering.py` (new) | test | file-I/O | `tests/test_repo_hygiene.py` | role-match |
| `tests/test_demo_login.py` (mod: Home assertions) | test | request-response | itself | exact |
| `scripts/check_live.py` (mod: probe P1-P8) | script | request-response | itself (`run_demo`, `report`, `denied_or_empty`) | exact |
| `scripts/check_gemini.py` (new) | script | request-response | `scripts/check_live.py` (`main`, SKIP exit 2) | role-match |
| `scripts/local.toml.example` (mod: PROBE_*) | config | n/a | itself | exact |

## Pattern Assignments

### `findings/repos/profiles.py` (repo, CRUD)

**Analog:** itself, lines 1-13. Keep the module docstring, `from __future__ import annotations`, explicit-column-list rule, and the `res.data or []` idiom.

```python
"""Profiles table access. No streamlit import; the only module that knows the table name."""
from __future__ import annotations

# Explicit column list: never star, never the embedding column.
PROFILE_SUMMARY_COLUMNS = "id, full_name, career_stage, is_complete, created_at"

def get_own_profile(sb, user_id: str) -> dict | None:
    res = sb.table("profiles").select(PROFILE_SUMMARY_COLUMNS).eq("id", user_id).limit(1).execute()
    rows = res.data or []
    return rows[0] if rows else None
```

Keep `PROFILE_SUMMARY_COLUMNS` and the `get_own_profile` signature. `tests/test_demo_login.py` imports both. Add a `columns` parameter defaulting to the summary, so Home is unchanged. Add `PROFILE_COLUMNS` (full, no `*`, no `embedding`, no email), `ProfileWriteError`, and `update_own(sb, user_id, payload, columns=PROFILE_COLUMNS)` as in RESEARCH Pattern 2 (`.update(payload).eq("id", user_id).select(columns).execute()`, raise on zero rows).

---

### `findings/core/config.py` (config)

**Analog:** itself, lines 15-35. Frozen dataclass plus `load_settings(source)`.

```python
@dataclass(frozen=True)
class Settings:
    supabase_url: str
    supabase_publishable_key: str
# ... return Settings(supabase_url=url, supabase_publishable_key=key)
```

Add `gemini_api_key: str | None = None` as a defaulted field. Populate it with `source.get("GEMINI_API_KEY")`. This must not raise when the key is missing, and it gets no `sb_publishable_` validation. `st.secrets` is a Mapping, so `.get` works. Add the key as a comment in `.streamlit/secrets.toml.example` only. Never add it to the tracked `.streamlit/secrets.toml`.

---

### `findings/services/profile_service.py` (service, CRUD + transform)

**Analog:** `findings/services/auth_service.py`

**Conventions to copy** (lines 1-22): module docstring, `from __future__ import annotations`, a module-level user-safe exception, and pure helper functions with private underscore helpers.

```python
class AuthFailure(Exception):
    """Carries a message that is safe to show to the user."""

def _normalise_email(email: str) -> str:
    email = (email or "").strip().lower()
    if len(email) > 254 or not _EMAIL_RE.match(email):
        raise AuthFailure("Enter a valid email address.")
    return email
```

**Error wrapping pattern** (lines 45-52): catch specific errors first, then a broad `Exception`, and raise a user-safe message `from None`. Copy this for `save_profile`. A repo failure becomes a user-safe `ProfileSaveError`. An `AIUnavailable` is caught and returned as `ai_status="unavailable"`, never raised, because the profile must still save (D-08).

```python
    try:
        res = sb.auth.sign_in_with_password({...})
    except (AuthApiError, AuthError) as err:
        raise AuthFailure(friendly_message(err)) from None
    except Exception:
        raise AuthFailure(_GENERIC) from None
```

The first parameter is `sb`, the Supabase client, passed in and never created here. Pure helpers (`normalise_list`, `is_complete`, `mentoring_defaults`, `methods_hash`, `needs_classification`) come from RESEARCH "Pure helpers" and Pattern 5. For the payload allow-list, never send `methods_effective`, `stage_tier`, `id`, `is_synthetic` or `created_at`.

---

### `findings/ai/*` (service, request-response)

**Analog:** no Gemini code exists. For the exception design, copy the `AuthFailure` pattern above: one user-safe exception (`AIUnavailable`) wraps all lower-level errors with `raise ... from last`. Use the full code from RESEARCH Patterns 3-4 (`make_client`, `generate_structured`, `MethodsSuggestion`, `build_prompt`). Rules:
- No streamlit import. The key is injected via `make_client(api_key)`, and the module never reads env or secrets.
- A broad `except Exception` is allowed (`ruff.toml` ignores BLE001; auth_service already does this).
- Log only the exception type, never the prompt or body.
- Do not set `temperature` or `Field(max_length=...)`. Truncate the reason to 140 characters in code.

---

### `views/profile.py` (view, CRUD + callbacks)

**Analogs:** `views/home.py` (profile load with a try/except), `views/account.py` (session use, button, `st.rerun()`).

**Session and user pattern** (`views/home.py` lines 1-11):
```python
import streamlit as st

from findings.core import session
from findings.repos.profiles import get_own_profile

user = session.current_user() or {}
...
try:
    profile = get_own_profile(st.session_state["sb"], user.get("id", ""))
except Exception:
    st.warning("Could not load your profile record. Try again in a moment.")
```

Views are flat top-level scripts, not functions. They use `st.session_state["sb"]` for the client, and every write goes through it so RLS applies. Button plus rerun idiom (`views/account.py` lines 9-11):
```python
if st.button("Sign out", type="primary", key="account_sign_out"):
    session.sign_out()
    st.rerun()
```
Always pass explicit `key=` on buttons. The form, `_seed`, stage `on_change` callback, flash toast hand-off and override segmented control come from RESEARCH Patterns 1 and 6. Build the Gemini client in the view with `make_client(settings.gemini_api_key)`, or inside the service, catching `AIUnavailable`. Render user text only with `st.text`, never `st.markdown`.

---

### `views/home.py` (view, mod)

**Analog:** itself, lines 15-20. Replace the `info`/`success` branches with the CTA. When `profile is None` or `not profile["is_complete"]`, show `st.info(...)` plus `st.page_link("views/profile.py", label="Complete your profile")`. Keep the `try/except Exception -> st.warning` wrapper. `tests/test_demo_login.py` asserts the old copy ("Profile record found", "No profile record yet."), so update those assertions in the same plan.

---

### `app.py` (nav, mod)

**Analog:** itself, lines 27-30.
```python
pages = [
    st.Page("views/home.py", title="Home", default=True),
    st.Page("views/account.py", title="Account"),
]
```
Insert `st.Page("views/profile.py", title="My profile")` between Home and Account. `st.page_link` only works for pages registered here.

---

### `supabase/schema.sql` (migration)

**Analog:** itself. The file is a single idempotent script. Edit the section-8 `grant update (...)` list in place to append `methods_hash, methods_reason`. Add the two `alter table ... add column if not exists` statements after the `create table` block, and end the file with `notify pgrst, 'reload schema';`. Exact SQL is in RESEARCH "Schema Changes". The existing list is preceded by `revoke update ...`, so editing in place is idempotent.

---

### `tests/fakes_profiles.py` (test helper)

**Analog:** `tests/fakes.py` lines 27-41 and 99-105. Subclass it; do not edit it.

```python
class FakeQuery:
    def __init__(self, rows): self._rows = rows
    def select(self, *_a, **_k): return self
    def update(self, *_a, **_k): return self
    def eq(self, *_a, **_k): return self
    def execute(self): return SimpleNamespace(data=self._rows)

class FakeSupabase:
    def __init__(self, rows=None):
        self.auth = FakeAuth()
        self.rows = rows if rows is not None else []
    def table(self, _name):
        return FakeQuery(self.rows)
```

`FakeQuery` has no `limit()`, so the new query class needs `limit`, `update(payload)` that merges into its row, a post-update `select(cols)`, call recording, and modes to return `[]` or raise. `RecordingQuery` and `ProfileFake` in `tests/test_demo_login.py` (lines 15-40) are a local recording pattern worth mirroring (log of `("select", cols)`, `("eq", (col, val))`).

---

### `tests/test_profile_page.py` and Home test updates (AppTest)

**Analog:** `tests/test_demo_login.py` lines 1-14.
```python
APP = str(Path(__file__).resolve().parent.parent / "app.py")
SECRETS = {"SUPABASE_URL": "https://abc.supabase.co", "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_x"}
```
Use `AppTest.from_file(APP, default_timeout=15)`, `at.secrets.update(SECRETS)`, then `at.session_state["sb"] = <fake>` and `at.session_state["user"] = {...}`. After a click that calls `switch_page`, assert immediately, then use `at.switch_page("views/profile.py").run()` explicitly (RESEARCH Pitfall 5).

---

### `tests/test_schema_sql.py` and `tests/test_layering.py`

**Analog:** `tests/test_repo_hygiene.py` lines 1-30. Use `ROOT = Path(__file__).resolve().parent.parent`, `git ls-files` via `subprocess.run([...], cwd=ROOT, capture_output=True, text=True, check=True)`, and a regex scan of file text. For layering, assert that no tracked `findings/{ai,services,repos}/**/*.py` contains `import streamlit`. For the schema, parse the grant list and the career-stage check.

---

### `scripts/check_live.py` (probe, mod) and `scripts/check_gemini.py` (new)

**Analog:** `scripts/check_live.py`.

**Helpers to reuse** (lines 20-45): `report(check_id, ok, detail)`, `denied_or_empty(fn)`, `raises(fn)`, and the `RESULTS` dict.

**Credentials loader** (lines 47-57): env var first, then `scripts/local.toml` via `tomllib`. Copy it as `probe_credentials()` reading `PROBE_EMAIL` / `PROBE_PASSWORD`.

**Check style** (lines 98-102):
```python
try:
    other = str(uuid.uuid4())
    rows = sb.table("profiles").update({"full_name": "x"}).eq("id", other).execute().data
    report("D4", len(rows or []) == 0, f"{len(rows or [])} rows")
except Exception as err:
    report("D4", False, f"error {type(err).__name__}")
```
Note that D4 targets a random uuid, which proves little. The probe must use a real second account whose profile is complete, so it is visible (P3: 1 row read, P4: 0 rows on update, P5: owner re-read unchanged). Reset the probe's `is_complete=false` at the end. Never print secrets, only `type(err).__name__`.

**Main/SKIP convention** (lines 131-146): return 2 with a "SKIP: ..." message when credentials are absent, return 1 on any failure, else 0, with `sys.exit(main())`. `check_gemini.py` follows the same shape: SKIP (exit 2) without `GEMINI_API_KEY`.

---

## Shared Patterns

### Layering and no-streamlit rule
**Source:** `findings/repos/profiles.py`, `findings/services/auth_service.py`, `findings/core/config.py` (none import streamlit). **Apply to:** `findings/ai/*`, `profile_service.py`, `constants.py`. Only `views/` and `ui/` import streamlit.

### Explicit column lists, RLS-through-session client
**Source:** `findings/repos/profiles.py` line 5-11. **Apply to:** every read and write. No `*`, no `embedding`, and no email in profile payloads (email lives in `profile_contacts`, behind an RPC).

### User-safe errors
**Source:** `findings/services/auth_service.py` lines 14, 45-52. **Apply to:** `profile_service`, `ai/client`. Wrap lower-level exceptions in one module exception with a safe message, `from None` or `from last`. Views catch it and show `st.warning` / `st.toast`.

### Views: current user and client
**Source:** `views/home.py` lines 6-11, `views/account.py` lines 5-11. `session.current_user() or {}`, `st.session_state["sb"]`, explicit button keys, `st.rerun()` after state change.

### Test doubles
**Source:** `tests/fakes.py` (subclass only) and `tests/test_demo_login.py` (`APP`, `SECRETS`, `at.session_state[...]` injection).

### Secrets hygiene
**Source:** `tests/test_repo_hygiene.py` `SECRET_PATTERNS` (already scans for `AIza...`). The Gemini key stays out of the tracked `.streamlit/secrets.toml`.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `findings/ai/client.py`, `methods.py`, `schemas.py` | service | request-response | No external-API or Gemini code exists. Use RESEARCH Patterns 3-5 (verified with MockTransport). |
| `tests/test_ai_client.py` | test | request-response | No HTTP-mock tests exist. Use the RESEARCH `httpx.MockTransport` sketch. |
| `ui/badges.py`, `ui/profile_view.py` | component | transform | No `ui/` package or reusable render functions exist. Use RESEARCH Pattern 6 and the `st.text`-only rule. |
| `views/profile.py` form and seed logic | view | event-driven | No forms with callbacks exist (login view not mapped for form idioms). Use RESEARCH Pattern 1. |

## Metadata

**Analog search scope:** all tracked source (`git ls-files`, excluding `.planning`): `app.py`, `findings/`, `views/`, `tests/`, `scripts/`, `supabase/`.
**Files read:** `repos/profiles.py`, `core/config.py`, `services/auth_service.py`, `views/home.py`, `views/account.py`, `app.py`, `tests/fakes.py`, parts of `tests/test_demo_login.py`, `tests/test_repo_hygiene.py`, `scripts/check_live.py`, `.streamlit/secrets.toml.example`. `views/login.py` and `supabase/schema.sql` were not re-read (schema line numbers come from RESEARCH).
**Pattern extraction date:** 2026-10-05
