# Stack Research

**Domain:** AI-powered researcher-matching web app ("Hinge for researchers"), Python + Streamlit + Supabase + Gemini, free tier only, 2-week course project with a live demo
**Researched:** 2026-10-05
**Overall confidence:** MEDIUM-HIGH. Versions, auth flow, Supabase limits, Community Cloud behaviour and Gemini model IDs were verified against official docs or the live PyPI index today. Gemini free-tier request quotas are the one area that is LOW confidence, because Google no longer publishes the numbers in the docs (see "Gemini free-tier quotas").

The stack was chosen by the user. This document makes it prescriptive and current, and flags where the 2026 reality differs from what most tutorials and training data say.

## Headline Findings (read these first)

1. **Supabase's built-in email sender cannot run this demo.** It only delivers to addresses that are members of your Supabase organization, and it is capped at 2 emails per hour. Anyone else gets "Email address not authorized". A custom SMTP provider is **mandatory** for the OTP login to work for graders and classmates. Use Brevo (no domain needed) or Resend (domain needed). Set this up on day 1. Brevo needs account approval before it will send.
2. **Both the "Magic Link" and the "Confirm signup" email templates must contain `{{ .Token }}`.** A brand-new email address that calls `sign_in_with_otp` receives the *Confirm signup* template, not the Magic Link one. Only editing one template gives new users a link and no code.
3. **`gemini-embedding-2` is the current embedding model, and it behaves differently from `gemini-embedding-001`.** It has no `task_type` field (you put the task in the text as a prefix), it auto-normalizes truncated dimensions, and it **returns one aggregated vector if you pass a list of strings**. Embed one text per call.
4. **Gemini 3.x models think at "high" by default.** Set `thinking_level` to `low` or `minimal` for every call here, or latency and token spend will hurt the live demo.
5. **Free-tier Gemini is split in two.** The Flash models (3.5/3.6/3.7/3.8) are reported at about 20 requests per day. The Flash-Lite models (3.5, 3.1) are reported at about 500 per day. Use `gemini-3.5-flash-lite` as the workhorse. Read the real numbers from the AI Studio dashboard on day 1.
6. **Never share a Supabase client across users in Streamlit.** One client per browser session, in `st.session_state`. `@st.cache_resource` or a module-level client would leak one user's login to the next.
7. **Community Cloud now defaults to Python 3.14.** Pick 3.12 in "Advanced settings" at deploy time. It cannot be changed afterwards without delete and redeploy, and `runtime.txt` / `.python-version` are ignored.
8. **Supabase is deprecating the `anon` and `service_role` keys by end of 2026.** Use `sb_publishable_...` and `sb_secret_...` keys for a new project.

## Recommended Stack

### Core Technologies

| Technology | Version (verified 2026-10-05) | Purpose | Why Recommended | Confidence |
|------------|-------------------------------|---------|-----------------|------------|
| Python | **3.12** (select explicitly in Community Cloud "Advanced settings") | Runtime, local and cloud | Streamlit 1.65 needs >=3.10; supabase 2.32 needs >=3.9; google-genai 2.28 needs >=3.10. 3.12 is mature and every dependency ships wheels for it. Community Cloud's default is now 3.14, which is newer than most of this stack has been exercised on. Develop locally on the same minor version. | HIGH (versions), MEDIUM (3.14 default is from a May 2026 forum thread) |
| streamlit | **1.65.0** | UI and hosting runtime | Has everything needed: `st.navigation`/`st.Page`, `st.dialog`, `st.fragment`, `st.form`, `st.status`, `st.pills`, `st.segmented_control`, `st.toast`, `st.file_uploader`, `st.data_editor` (all confirmed present in 1.65.0). Community Cloud installs streamlit by default but pin it anyway so local and cloud match. | HIGH |
| supabase (supabase-py) | **2.32.0** | Auth, PostgREST queries, RPC | Official client. Pulls in `supabase-auth`, `postgrest`, `realtime`, `storage3` at the same 2.32.0 line. Auth client exposes `sign_in_with_otp`, `verify_otp`, `set_session`, `refresh_session`, `get_user`, `sign_out`. | HIGH |
| google-genai | **2.28.0** | Gemini generation and embeddings | The current official unified SDK (`from google import genai`). Supports `models.generate_content` with `response_schema` (Pydantic), `Part.from_bytes` for PDFs, `models.embed_content` with `output_dimensionality`. The newer `client.interactions` API needs >=2.3.0 and is also present. | HIGH |
| pydantic | **2.13.x** (comes with google-genai) | Response schemas and validation | Gemini's `response_schema` accepts a Pydantic model directly, and `model_validate_json` gives typed, validated output. Use the same models for form state and DB payloads. | HIGH |
| Supabase Postgres + Auth + RLS | managed (Free plan) | Database, passwordless auth, per-user write control | See free-tier limits below. 500 MB is vastly more than ~100 profiles need. | HIGH |
| pgvector | managed, enabled via `create extension vector with schema extensions;` | Embedding shortlist | Docs-standard pattern: `extensions.vector(N)` column plus a `match_*` SQL function called through `supabase.rpc()` (PostgREST does not expose the `<=>` operator directly). | HIGH |
| Gemini text model | **`gemini-3.5-flash-lite`** primary, **`gemini-3.1-flash-lite`** fallback | PDF/text autofill, methods-orientation suggestion, rerank + "why you match" | Cheapest free-tier-eligible 3.x models and, per secondary sources, the only text models with a usable daily quota (~500/day vs ~20/day for Flash). Quotas are per model, so a fallback chain across two models also raises effective capacity. `gemini-3.1-flash-lite` has an announced earliest shutdown of 2027-05-07, which is fine for this project. | HIGH (IDs, free-tier eligibility), LOW (quota numbers) |
| Gemini embedding model | **`gemini-embedding-2`**, `output_dimensionality=768` | Profile vectors | Released 2026-04-22, no shutdown announced, free tier available, 8,192-token input, auto-normalizes truncated dims. `gemini-embedding-001` still works (shutdown 2028-05-14) but is text-only, needs manual normalization, and is not listed on the pricing page. Do not mix the two models in one column. | HIGH |
| Streamlit Community Cloud | Free | Hosting | Deploys from GitHub, secrets in the dashboard, 12-hour sleep. See limits below. | HIGH |
| GitHub Actions (cron) | free | Supabase keep-alive | Scheduled workflows are free on public repos. See keep-alive section for the caveats. | HIGH |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pypdf | **6.19.0** | Pre-flight check of uploaded CVs (page count, encrypted or empty) | Optional. Gemini reads PDFs natively (up to 50 MB or 1,000 pages, inline or via Files API), so you do not need pypdf to extract text. Use it only to reject encrypted or oversized PDFs with a friendly message before spending a Gemini call. Skip it if time is short. |
| Brevo SMTP (service, not a library) | free plan, 300 emails/day | Custom SMTP for Supabase Auth OTP emails | Default recommendation for a student with no domain. Verify a single sender address, use `smtp-relay.brevo.com` port 587 with the SMTP key. |
| Resend SMTP (service) | free plan, 100 emails/day, up to 3 domains | Alternative custom SMTP | Choose it only if you own a domain you can verify. Without a verified domain, Resend only delivers to your own account email. |
| pytest | latest | Unit tests (prompts, schema parsing, match-cache logic) | Needed for the rubric's test report. Keep Gemini and Supabase behind thin wrapper modules so they can be faked. |
| `streamlit.testing.v1.AppTest` | ships with Streamlit | Headless UI smoke tests | Cheap way to produce repeatable test evidence for the report. |
| ruff | latest | Lint and format | Dev only. |
| tenacity | 9.1.x (already a google-genai dependency) | Retries | Not needed as a direct dependency. Prefer the SDK's built-in `types.HttpRetryOptions` via `types.HttpOptions(retry_options=...)`. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `.streamlit/secrets.toml` (gitignored) | Local secrets | Same keys as the Community Cloud "Secrets" box. Paste the whole file into the dashboard when deploying. |
| `requirements.txt` | Dependency manifest | Community Cloud uses the first dependency file it finds (`uv.lock`, then others, then `requirements.txt`, then `pyproject.toml`) and processes `requirements.txt` with uv, falling back to pip. Use exactly one dependency file. |
| GitHub Actions (`actions/checkout@v7`, `actions/setup-python@v7` if you need Python) | Keep-alive workflow | The keep-alive job only needs `curl`, so no checkout or Python is required. |
| Supabase SQL editor | Schema, RLS, `match_*` functions | Keep the SQL in `supabase/schema.sql` in the repo so the architecture doc and graders can read it. |

## Installation

```bash
# Local dev (Python 3.12)
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install pytest ruff          # dev only, not in requirements.txt
```

`requirements.txt` (pin so cloud equals local):

```text
streamlit==1.65.0
supabase==2.32.0
google-genai==2.28.0
pydantic>=2.13,<3
pypdf==6.19.0        # optional, drop if you skip CV pre-flight checks
```

`.streamlit/secrets.toml` (never commit; paste the same content into Community Cloud):

```toml
SUPABASE_URL = "https://<ref>.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "sb_publishable_..."
GEMINI_API_KEY = "..."
# NOT in Streamlit Cloud secrets. Local seeding script only (use a separate .env or env var):
# SUPABASE_SECRET_KEY = "sb_secret_..."
```

## Verified Facts by Topic

### 1. Versions and runtime

| Item | Value | Source / confidence |
|------|-------|---------------------|
| streamlit | 1.65.0, requires Python >=3.10 | PyPI JSON, 2026-10-05. HIGH |
| supabase | 2.32.0, requires Python >=3.9 | PyPI JSON. HIGH |
| google-genai | 2.28.0, requires Python >=3.10 | PyPI JSON. HIGH |
| pypdf | 6.19.0, requires Python >=3.9 | PyPI JSON. HIGH |
| All four installed together on Python 3.12.10 | resolved cleanly (pydantic 2.13.5, supabase-auth 2.32.0, postgrest 2.32.0) | Local venv install. HIGH |
| Community Cloud Python | Supports released versions still receiving security updates; you cannot use EOL, prerelease or feature versions. Default has moved to 3.14 (forum, May 2026). Choose in "Advanced settings"; changing later means delete and redeploy; `runtime.txt` and `.python-version` are ignored. One forum report says the selection was ignored during a platform lag, with delete-and-redeploy as the workaround. | Streamlit docs (HIGH) plus forum threads (MEDIUM) |

Make the code version-agnostic across 3.12 to 3.14 (no 3.12-only syntax), because the platform may not honour the selection.

### 2. Supabase Auth: email OTP from supabase-py

Flow (docs: "Passwordless email logins", Python tab; SDK signatures confirmed in the installed package):

1. **Dashboard setup (once):**
   - Authentication, Emails (Templates): edit **Magic Link** *and* **Confirm signup** so the body contains `{{ .Token }}`, for example `<h2>Your Findings login code</h2><p>Enter this code: {{ .Token }}</p>`. Remove `{{ .ConfirmationURL }}` from both.
   - Authentication, SMTP: enable custom SMTP (Brevo or Resend).
   - Authentication, Rate Limits: the custom-SMTP default is **30 emails per hour** (project-wide), which is enough for a demo but is shared by every user. Raise it before a rehearsal with many people.
2. **Send code:** `sb.auth.sign_in_with_otp({"email": email, "options": {"should_create_user": True}})`. Success returns `user=None, session=None`. Show an "enter the code" box. Users get one request per **60 seconds** (cooldown) and codes expire after **1 hour** by default (Auth Providers, Email, "Email OTP expiration").
3. **Verify code:** `res = sb.auth.verify_otp({"email": email, "token": code, "type": "email"})`. `res.session` holds `access_token` and `refresh_token`. `type` accepts `'signup' | 'invite' | 'magiclink' | 'recovery' | 'email_change' | 'email'`. The docs use `'email'` for the OTP flow. If a brand-new user fails verification with `'email'` during the first-day spike, retry with `'signup'`. This is a quick test, not a known bug.
4. **After verify**, the same client instance automatically uses the user's JWT for `table()` and `rpc()` calls (supabase-py listens for `SIGNED_IN`, `TOKEN_REFRESHED`, `SIGNED_OUT` and rewrites the PostgREST Authorization header), so RLS sees `auth.uid()`.

| Fact | Confidence |
|------|------------|
| Built-in SMTP: only team/org-member addresses are allowed, limit is 2 messages/hour, "can change without notice", no SLA, not for production | HIGH (Supabase SMTP docs) |
| After enabling custom SMTP, delivery works for all addresses with an initial limit of 30 messages/hour, adjustable | HIGH (same page) |
| `{{ .Token }}` is a 6-digit OTP usable instead of `{{ .ConfirmationURL }}` | HIGH (email templates docs) |
| New users via `signInWithOtp` receive the Confirm signup template (so edit both templates) | MEDIUM (Supabase GitHub discussion #28947; not stated on the passwordless docs page) |
| Brevo free: 300 emails/day, sender verification works with a single address, no domain; Brevo may rewrite or re-sign the visible sender, so check spam folder | MEDIUM (pricing page for 300/day, community write-ups for single-sender) |
| Resend free: 100 emails/day, 3 domains, must verify a domain to send to arbitrary recipients; `onboarding@resend.dev` only reaches your own account email | MEDIUM-HIGH (pricing page, Resend docs via search) |
| Advisable for the demo? **Yes, required**, not optional (see headline finding 1) | HIGH |

Practical advice: also add an `is_demo_account` path in your pre-demo checklist. Create the demo account on a team-member email early, and rehearse with a non-team address to prove the custom SMTP works. If the email sending path breaks on demo day, the whole app is locked, so record this as the top demo risk.

### 3. Per-user Supabase session in Streamlit (no cross-user leakage)

Why this matters: Streamlit runs one Python process for all users. Module globals and `@st.cache_resource` objects are shared by every browser session. A supabase-py client is **stateful** (it stores the logged-in session and rewrites its own auth header), so sharing one client means the last user to log in becomes everyone's identity.

Rules (HIGH, derived from the verified client behaviour above plus Streamlit's cache semantics):

- Create the client **inside the session**: `st.session_state["sb"] = create_client(url, publishable_key)` the first time the script runs for that session. Default storage is in-memory per client (`SyncMemoryStorage`), which is exactly what you want.
- Never use `@st.cache_resource` or a module-level `supabase = create_client(...)` for anything authenticated. A cached client is acceptable **only** for read-only access to public data with the publishable key and no logged-in session, and you should not need it.
- Never put the secret key in the Streamlit app. Only the local seeding script uses it.
- Pass user identity from `res.user.id` in `st.session_state`, but treat RLS as the source of truth.
- A browser refresh creates a new Streamlit session and therefore logs the user out. That is acceptable for this project ("session persists while the user navigates"). Document it in the Limitations file. Cookie-based persistence adds a third-party component and security risk, so do not build it unless everything else is done.
- Handle token expiry: access tokens are short-lived. supabase-py has `auto_refresh_token=True` by default, but the refresh runs on the client's own timers, so wrap the data layer with one retry that calls `sb.auth.refresh_session()` on an auth error (HTTP 401 or "JWT expired").

```python
# auth.py
import streamlit as st
from supabase import create_client

def get_sb():
    if "sb" not in st.session_state:
        st.session_state["sb"] = create_client(
            st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_PUBLISHABLE_KEY"]
        )
    return st.session_state["sb"]

def send_code(email: str):
    get_sb().auth.sign_in_with_otp({"email": email, "options": {"should_create_user": True}})

def verify_code(email: str, code: str):
    res = get_sb().auth.verify_otp({"email": email, "token": code.strip(), "type": "email"})
    st.session_state["user"] = res.user
    return res

def sign_out():
    sb = st.session_state.pop("sb", None)
    if sb:
        sb.auth.sign_out()
    st.session_state.pop("user", None)
```

Gate every page with `if "user" not in st.session_state: st.stop()` (or build the page list conditionally with `st.navigation`). Streamlit also ships `st.login` / `st.user`, but those are OIDC (Google, Microsoft and similar) and do not give you Supabase JWTs, so skip them.

### 4. Supabase pgvector

- Enable: `create extension if not exists vector with schema extensions;`
- Column: `embedding extensions.vector(768)`. **768** is the recommended choice: `gemini-embedding-2` truncates its native 3072 dimensions (Matryoshka). Google documents 768, 1536 and 3072 as the recommended sizes (flexible range 128 to 3072). 768 uses a quarter of the storage, keeps quality close to full size (MTEB for 001 was 67.99 at 768 vs 68.16 at 2048), and stays under pgvector's 2,000-dimension HNSW limit for `vector` type. With ~100 rows, no index is needed at all (exact scan is instant). If you add one: `create index on profiles using hnsw (embedding vector_cosine_ops);`
- Store `embedding_model text` and `embedded_at` so a model change forces a clean re-embed.
- Match function, called as `sb.rpc("match_profiles", {...}).execute()`. Keep it `security invoker` (the default for `language sql`) so RLS still applies, and **do not return contact email or other private columns**. Return only what the Discover card needs.

```sql
create or replace function match_profiles(
  query_embedding extensions.vector(768),
  match_count int default 15,
  exclude_user uuid default null,
  filter_methods text default null
)
returns table (id uuid, similarity float)
language sql stable
as $$
  select p.id, 1 - (p.embedding <=> query_embedding) as similarity
  from profiles p
  where p.embedding is not null
    and (exclude_user is null or p.id <> exclude_user)
    and (filter_methods is null or p.methods_orientation = filter_methods)
  order by p.embedding <=> query_embedding
  limit least(match_count, 50);
$$;
```

From Python, pass the embedding as a plain `list[float]`: `sb.rpc("match_profiles", {"query_embedding": vec, "match_count": 15, "exclude_user": uid})`. For inserts and updates, a `list[float]` is also accepted for a `vector` column. (Pattern verified from Supabase docs, which show the JS equivalent; confirm the Python list serialization in the first spike, MEDIUM.)

Mentorship mode filters on career stage in the same function (pass a `stage_filter text[]` or add a second function). Because RLS is row-level, not column-level, **keep contact email in a separate table or behind a `security definer` function that checks for an accepted connection**. Never put `email` in the same table or view as the publicly readable profile.

### 5. Gemini free tier: models, embeddings, structured output, PDFs

**Model IDs (docs: models page, pricing page, deprecations page, fetched 2026-10-05):**

| Use | Model ID | Free tier | Notes |
|-----|----------|-----------|-------|
| Default for autofill, orientation label, rerank | `gemini-3.5-flash-lite` | Yes (free of charge) | Released 2026-07-21. Docs tell new projects to use "3.5 Flash-Lite or 3.8 Flash". |
| Fallback | `gemini-3.1-flash-lite` | Yes | Earliest shutdown 2027-05-07, replacement 3.5 Flash-Lite. |
| Optional quality tier (rerank on demo day only) | `gemini-3.8-flash` | Yes | About 20 requests/day reported, so spend it only deliberately. Its paid price steps up on 2027-01-01, irrelevant on free tier. |
| Embeddings | `gemini-embedding-2` | Yes (text input free) | 8,192 token input. Use `output_dimensionality=768`. |

Avoid: `gemini-2.5-*` (access limited to legacy users who used them before; docs say new projects should not use them), `gemini-3-flash-preview` and other `-preview` IDs (deprecated or short-lived), all Pro models (paid-only since April 2026 per a secondary source), `text-embedding-004` (shut down 2026-01-14), `embedding-001` and `gemini-embedding-exp*` (shut down).

#### Gemini free-tier quotas

LOW confidence. Google's rate-limit page now says limits depend on tier and "can be viewed in Google AI Studio"; it publishes no per-model free-tier numbers. Secondary sources dated Sept 2026 report about **20 requests/day** for Gemini 3.5/3.6/3.7/3.8 Flash and about **500 requests/day** for 3.5 and 3.1 Flash-Lite. Other sources quote 15 RPM and 1,500 RPD, but they are dated May to July 2026 and conflict. No source gave an embedding quota. Rate limits apply per project, not per API key, so a second key in the same project does not help.

Action for Phase 1: open https://aistudio.google.com/rate-limit and write the real RPM/TPM/RPD for the three models into the Limitations doc. Design for the pessimistic case: assume about 10 RPM and a few hundred requests/day for Flash-Lite, and an unknown embedding quota.

Budget sketch (so the quota is not a surprise):
- Seeding: 60 to 100 profiles. Generate 4 to 5 profiles per call (about 20 calls) and embed one text per call (60 to 100 calls), spaced out with a short sleep. Run it once, commit the JSON, and never run it live.
- Autofill: 1 call per use. Rerank: 1 call per user per profile change (cache by profile hash). Embedding: 1 call per profile save.
- Rehearsal and demo: expect well under 100 calls. Fine on Flash-Lite, tight on Flash.

**Privacy caveat (HIGH, from the pricing page):** on the free tier "Used to improve our products: Yes". Everything sent (including uploaded CV text and PDFs) may be used by Google. Use synthetic or consenting data for the demo, show a notice next to the upload box, and state this in the AI-use declaration and Limitations. A secondary source also says the free tier is unavailable in the EU/UK/Switzerland (LOW, unverified). Check the Gemini API terms if graders or demo users are in those regions.

**Embeddings (docs: embeddings page):**
- `gemini-embedding-2`: no `task_type` parameter. Instead put the task in the text. Retrieval: query `task: search result | query: {text}`, document `title: {title} | text: {content}` (use `title: none` if empty). Symmetric tasks: `task: classification | query: {text}`, `task: clustering | query: {text}`, `task: sentence similarity | query: {text}` (the last is explicitly "not for search or retrieval"). Use the same format on both sides of a comparison.
- **Passing a list to `contents` produces ONE aggregated embedding**, not one per item. Embed in a loop, one string per call. (The Batch API gives per-item embeddings but is not available on the free tier.)
- Truncated dimensions are auto-normalized (3072 is always normalized). With `gemini-embedding-001` you must normalize yourself.
- Recommended embedding recipe for peer matching: embed a structured profile string (interests, methods, experience, skills, bio) with a symmetric prefix on both profiles, and compare by cosine. For mentorship, embed "offers + needs" and "wants to learn + can contribute" as separate vectors using the asymmetric query/document format. Run a 20-minute A/B on the seed data before locking prefixes. Docs do not say which symmetric prefix is best for "find similar people" (MEDIUM).

```python
# llm.py (excerpt)
from google import genai
from google.genai import types

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])   # safe to share: stateless
EMBED_MODEL = "gemini-embedding-2"

def embed(text: str) -> list[float]:
    r = client.models.embed_content(
        model=EMBED_MODEL,
        contents=text,                                   # ONE string per call
        config=types.EmbedContentConfig(output_dimensionality=768),
    )
    return r.embeddings[0].values
```

The Gemini client is stateless and can be cached with `@st.cache_resource` (unlike the Supabase client).

**Structured JSON output and inline PDFs (docs: structured output and document processing pages; SDK fields confirmed in the installed package):**

The docs now lead with the new Interactions API (`client.interactions.create(..., response_format=...)`, GA since June 2026, and recommended for new projects). `generateContent` "remains fully supported" in the SDK. **Recommendation: use `client.models.generate_content`** for this project, behind one wrapper module, because:
- `response_schema=PydanticModel` and `types.Part.from_bytes(...)` are the shortest, best-documented path (no manual base64).
- Interactions stores state on Google's side by default (`store=true`, kept 1 day on free tier). CV PDFs are personal data, so you would have to remember `store=False` everywhere.
- Switching later is a one-file change.
Confidence: MEDIUM (no live call possible without an API key during research; the parameter names are confirmed against the installed SDK, and the doc examples for this exact path are the migration guide's "before" snippets).

```python
from pydantic import BaseModel, Field
from google.genai import types

class ProfileDraft(BaseModel):
    name: str | None = None
    career_stage: str | None = Field(None, description="One of: Undergrad, Master's, PhD, Postdoc, Faculty, Industry researcher")
    interests: list[str] = []
    methods_orientation: str | None = Field(None, description="qualitative, quantitative or mixed")
    # ... remaining form fields

GEN_CONFIG = types.GenerateContentConfig(
    response_mime_type="application/json",
    response_schema=ProfileDraft,
    thinking_config=types.ThinkingConfig(thinking_level="low"),   # Gemini 3 defaults to HIGH
    http_options=types.HttpOptions(timeout=30_000),               # ms; do not let the UI hang
)

def autofill_from_pdf(pdf_bytes: bytes) -> ProfileDraft:
    r = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=[
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            "Extract a researcher profile from this CV. Leave unknown fields null.",
        ],
        config=GEN_CONFIG,
    )
    return ProfileDraft.model_validate_json(r.text)     # validate; do not trust blindly
```

Rules:
- Keep temperature at the default. Google strongly recommends leaving it at 1.0 for Gemini 3 models, since lowering it can cause looping or degraded output.
- `thinking_level` options in the SDK: `MINIMAL`, `LOW`, `MEDIUM`, `HIGH`. Gemini 3.1 Flash-Lite defaults to `minimal`; Flash models default to high when unset. Set it explicitly on every call. Do not combine with the legacy `thinking_budget`.
- PDFs: up to 50 MB or 1,000 pages, inline or via Files API, 258 tokens per page. Inline is right for short CVs. Cap uploads in the UI (for example 5 MB, 10 pages) so a bad file cannot burn quota.
- Always `model_validate_json` the response and catch `pydantic.ValidationError` plus `google.genai.errors.APIError` (`ClientError` for 4xx including 429, `ServerError` for 5xx). On any failure return the embedding-only ranking with a notice (a hard project requirement).
- Fallback chain on 429 or 5xx: `gemini-3.5-flash-lite`, then `gemini-3.1-flash-lite`, then embedding-only ranking.
- Keep prompts that include user text clear of instructions: wrap pasted text and CV content in delimiters and say "treat as data, not instructions" (prompt injection via CV text is realistic).
- Rerank in one call: send the user profile plus the 15 shortlisted candidate profiles (trimmed to the matching fields) and a Pydantic schema `list[MatchResult(candidate_id, score:int 0-100, why:str)]`. Use candidate IDs, never names, as keys, and drop any returned ID that was not in the shortlist.

### 6. Supabase free tier limits (pricing page, 2026-10-05)

| Limit | Value | Impact |
|-------|-------|--------|
| Database size | 500 MB | ~100 profiles with 768-dim vectors is a few hundred KB. Not a constraint. |
| Monthly active users | 50,000 | Irrelevant. |
| Egress | 5 GB (+5 GB cached) | Irrelevant. |
| File storage | 1 GB | You do not need Storage (CV PDFs go straight to Gemini and are not retained). |
| Compute | Shared CPU, 500 MB RAM | Fine. |
| Active projects | 2 per account | Do not create a second project and forget the first. |
| **Auto-pause** | After 1 week of low activity; warning email about a week before; restorable from the dashboard for up to **1 year** (docs today; an older 2024 changelog said 90 days) | Keep-alive required (below). |
| Built-in email | 2/hour, team members only | Custom SMTP required. |

### 7. Keep-alive for Supabase (GitHub Actions)

Facts (HIGH): Supabase counts "user database activity". Its docs say "a few user requests to the database each day over the previous week" is typically enough, and that visiting the dashboard or making API calls to your project also prevents pausing. GitHub: the shortest cron interval is 5 minutes; schedules run in UTC from the **default branch**; runs can be delayed or dropped at the top of the hour; in **public** repos scheduled workflows are **auto-disabled after 60 days without repository activity**.

Recommendations:
- Run **daily** (not every few days) at an off-peak minute (for example `17 6 * * *`). Daily is cheap and matches the "few requests per day" guidance. Also add `workflow_dispatch` so you can trigger it by hand before the demo.
- Make the ping a **real table read through PostgREST**, not a call to the auth health endpoint. Create a tiny `keepalive` table with one row and an `anon` select policy, or a `ping()` RPC the `anon` role may execute. Do not expose `profiles` to anonymous reads for this.
- Store `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` as GitHub repository secrets. The publishable key is designed to be safe in GitHub Actions. Do not use the secret key here.
- Make the job fail loudly (`curl --fail`) so GitHub emails you if Supabase is paused. Commits keep the 60-day clock from disabling the schedule. The project will be done well before that, but note it in the pre-demo checklist.

```yaml
# .github/workflows/keepalive.yml
name: supabase-keepalive
on:
  schedule:
    - cron: "17 6 * * *"
  workflow_dispatch:
jobs:
  ping:
    runs-on: ubuntu-latest
    steps:
      - name: Read one row through PostgREST
        run: |
          curl --fail --silent --show-error \
            "${{ secrets.SUPABASE_URL }}/rest/v1/keepalive?select=id&limit=1" \
            -H "apikey: ${{ secrets.SUPABASE_PUBLISHABLE_KEY }}"
```

(HIGH on the mechanism; the publishable key working as the `apikey` header for PostgREST reads is stated in Supabase's API-keys docs. Test the workflow once with `workflow_dispatch` in Phase 1.)

### 8. Streamlit Community Cloud limits

| Item | Value | Confidence |
|------|-------|------------|
| Sleep | Apps with no traffic for **12 hours** hibernate; anyone with access can wake it with "Yes, get this app back up!" (a wake takes seconds to a minute, longer on a cold dependency build) | HIGH (docs; the 12-hour change from 24 was dated March 2025 in a forum thread) |
| Waking by automation | Staff said commits do not wake an app but reset the countdown; whether a cron HTTP ping wakes it is unverified | LOW. **Do not rely on automation.** Open the app yourself 30 minutes before the demo (already in the checklist). |
| Resources | CPU 0.078 to 2 cores, memory 690 MB to 2.7 GB, storage up to 50 GB (docs state "as of February 2024") | MEDIUM (docs, possibly stale) |
| Memory fit | This app (no local model, no big DataFrames) uses a few hundred MB. | HIGH |
| Secrets | App settings, Secrets box, paste TOML; read with `st.secrets["KEY"]`; never commit `secrets.toml` | HIGH |
| Repo | Must be on GitHub; deploying needs admin rights on the repo; a public repo works with default OAuth scopes (private repos need the broader `repo` scope) | HIGH |
| Config | `.streamlit/config.toml` is only read from the repo **root** per branch; Community Cloud overrides some settings (for example `client.showErrorDetails = false`) | HIGH |
| OS | Debian 11 ("bullseye"); `packages.txt` for apt packages (not needed here) | HIGH |
| Updates | App redeploys from GitHub pushes, rate-limited to 5 per minute | HIGH |
| Logs | Need `sys.stdout.flush()` to appear promptly | HIGH |
| Region | Hosted in the US, not configurable | HIGH |

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `generate_content` + Pydantic `response_schema` | Gemini Interactions API (`client.interactions.create`) | If you later want server-side multi-turn state or agent features. Not needed for one-shot extraction and rerank. |
| `gemini-embedding-2` @ 768 dims | `gemini-embedding-001` (task_type, list inputs in one call, manual normalize) | If `embedding-2` hits a free-tier embedding quota you cannot work around, since `001` batches a list in one request. Requires re-embedding everything; they are different vector spaces. |
| 768 dims | 1536 or 3072 dims | If you see poor match quality in the A/B. With ~100 rows storage and speed are irrelevant, only the 2,000-dim HNSW index limit matters (skip the index or use `halfvec`). |
| Brevo SMTP | Resend SMTP | If you own a domain and want nicer DX. 100/day cap on free vs Brevo's 300/day. |
| Email OTP via supabase-py | Email + password | Fallback if SMTP cannot be fixed before the demo. Needs `sign_up` and `sign_in_with_password`, and still sends a confirmation email unless auto-confirm is on. Treat it as a break-glass option, not the plan. |
| supabase-py (REST) | Direct Postgres (psycopg/SQLAlchemy) | Not recommended. Skips RLS and the user-JWT model, and Supabase's direct database host is IPv6-only unless you use the pooler (MEDIUM, from general Supabase knowledge). |
| Supabase pgvector | In-memory numpy cosine over all profiles | Genuinely viable at ~100 rows, but the project requires pgvector and it scales, so keep pgvector. |
| `gemini-3.5-flash-lite` | `gemini-3.8-flash` | Only for a single high-stakes rerank when you have confirmed spare quota. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Supabase built-in SMTP | 2 emails/hour and team-member recipients only; login would fail for everyone else | Brevo or Resend custom SMTP |
| Magic-link login | Token arrives in the URL fragment, which Streamlit cannot read (and email scanners can pre-fetch and burn links) | 6-digit OTP with `{{ .Token }}` |
| `@st.cache_resource` or a module-level Supabase client for authenticated calls | Shared across all users; one login overwrites everyone's session | `st.session_state["sb"]` created per session |
| Putting `email` in a publicly readable `profiles` table | RLS is row-level, not column-level, so the "hidden until accept" rule would leak | Separate `contacts` table or a `security definer` function gated on an accepted connection |
| Legacy `anon` / `service_role` JWT keys | Being deprecated by end of 2026 | `sb_publishable_...` in the app and Actions; `sb_secret_...` only in the local seeding script |
| Secret key (or `service_role`) in Streamlit Cloud secrets | Bypasses all RLS; a bug or injected prompt could expose all data. Supabase also rejects secret keys from browser-like User-Agents | Keep it local-only for seeding |
| `gemini-2.5-*`, `gemini-3-flash-preview`, other `-preview` IDs, Pro models, `text-embedding-004`, `embedding-001` | Restricted, deprecated, shut down, or paid-only | `gemini-3.5-flash-lite` / `gemini-3.1-flash-lite` / `gemini-embedding-2` |
| Passing a list of texts to `embed_content` with `gemini-embedding-2` | Returns one aggregated vector, silently corrupting a "one vector per profile" design | One call per text |
| `task_type=` with `gemini-embedding-2` | Not supported for this model | Task prefix inside the text |
| Default `thinking_level` on Gemini 3 models | Defaults to high on Flash; slow and token-hungry | `thinking_level="low"` or `"minimal"` |
| Lowering `temperature` on Gemini 3 | Google warns it can degrade output | Leave the default |
| `google-generativeai` (the old SDK) or `gotrue` | Superseded by `google-genai` and `supabase-auth` | The pinned packages above |
| LangChain / LlamaIndex / any vector DB SDK | Extra dependency weight and abstraction for a two-call pipeline | Direct `google-genai` plus `supabase` calls |
| `streamlit-authenticator`, `st.login`/`st.user` | Do not produce Supabase sessions; `st.login` needs an OIDC provider | Supabase Auth OTP |
| Relying on a cron ping or empty commits to keep the Streamlit app awake | Unverified; staff say commits only reset the timer | Manual wake before the demo |
| Python 3.14 on Community Cloud (the current default) | Newest runtime, least exercised by this dependency set | Select 3.12 in Advanced settings |

## Stack Patterns by Variant

**If graders or classmates sign in during the demo with many different addresses:**
- Use Brevo with the custom-SMTP rate limit raised above the default 30/hour (Authentication, Rate Limits).
- Because the limit is project-wide, ten people requesting a code in the same minute can hit it.

**If Gemini returns 429 (free-tier quota) during the demo:**
- Serve the cached rerank if the profile has not changed; otherwise show the embedding-only ranking with a notice.
- Because the quota is per project and per model, fall back to `gemini-3.1-flash-lite` before giving up.

**If you do not own a domain:**
- Use Brevo with a single verified sender address, and send a test code to a Gmail/Outlook address to check spam placement.
- Because Resend only reaches your own address without a verified domain.

**If the embedding free tier turns out to be too tight:**
- Fall back to `gemini-embedding-001` with `task_type="SEMANTIC_SIMILARITY"`, 768 dims, manual normalization, and many texts per call, then re-embed everything once.
- Because the list-input behaviour of `001` lets you embed a whole seed set in a single request.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| streamlit 1.65.0 | Python >=3.10 (use 3.12) | Community Cloud docs say the protobuf constraint is Streamlit's own; do not pin protobuf manually |
| supabase 2.32.0 | supabase-auth, postgrest, realtime, storage3, supabase-functions all 2.32.x | They install together; do not pin them individually |
| google-genai 2.28.0 | pydantic 2.13.x | Interactions API needs google-genai >=2.3.0 (satisfied) |
| supabase 2.32.0 + `sb_publishable_` keys | Client validates only the URL format, not the key shape | New-style keys are not JWTs; confirm one login plus one RLS write in the Phase 1 spike (MEDIUM) |
| Supabase `vector(768)` | `gemini-embedding-2` with `output_dimensionality=768` | A dimension mismatch fails on insert; keep the dimension in one constant and in the SQL |

## Items to Verify in the First Spike (cheap, high value)

1. Real Gemini free-tier RPM/RPD/TPM for `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite` and `gemini-embedding-2` from the AI Studio dashboard. LOW confidence today.
2. End-to-end OTP with a **non-team** email through Brevo: new user, then existing user, both receiving a 6-digit code. Confirm `type="email"` verifies for a brand-new user.
3. One authenticated RLS write and one `match_profiles` RPC call using a `sb_publishable_` key and the per-session client.
4. One live `generate_content` call with `response_schema` plus an inline PDF on `gemini-3.5-flash-lite` with `thinking_level="low"`, to confirm latency is acceptable inside Streamlit.
5. Community Cloud: deploy with Python 3.12 selected and print `sys.version` to confirm it was honoured.
6. Keep-alive workflow: trigger by hand once and confirm a 200 from PostgREST.

## Sources

- PyPI JSON API (streamlit, supabase, google-genai, pypdf, pydantic) — versions and `requires_python`, queried 2026-10-05. HIGH
- Local `pip install` of all four packages on Python 3.12.10 plus SDK introspection (`GenerateContentConfig`, `EmbedContentConfig`, `ThinkingConfig`, `supabase-auth` OTP methods, supabase-py auth-to-PostgREST header wiring) — HIGH
- https://ai.google.dev/gemini-api/docs/models — model list. HIGH
- https://ai.google.dev/gemini-api/docs/pricing — free-tier eligibility, "used to improve our products", embedding-2 pricing. HIGH
- https://ai.google.dev/gemini-api/docs/deprecations — shutdown dates (2.5 restrictions, 3.1 Flash-Lite 2027-05-07, embedding-001 2028-05-14, text-embedding-004 2026-01-14). HIGH
- https://ai.google.dev/gemini-api/docs/embeddings — embedding-2 task prefixes, aggregation behaviour, dimensions, normalization, limits. HIGH
- https://ai.google.dev/gemini-api/docs/gemini-3 — `thinking_level`, temperature guidance. HIGH
- https://ai.google.dev/gemini-api/docs/structured-output and /document-processing — Pydantic schemas, inline PDFs, 50 MB / 1,000 page limit. HIGH
- https://ai.google.dev/gemini-api/docs/interactions and /migrate-to-interactions — Interactions API GA, `generateContent` still supported, 1-day free-tier retention with `store=true`. MEDIUM (summarized by a fetch tool)
- https://ai.google.dev/gemini-api/docs/rate-limits — states quotas are only visible in AI Studio. HIGH (that no numbers are published)
- https://www.scriptbyai.com/gemini-api-free-tier-limits/ (Sept 2026), https://tinkerllm.com/blog/gemini-api-free-tier-limits-rate-quotas/ (May 2026), https://www.ayautomate.com/free-models/google-gemini-gemini-3-5-flash (July 2026) — secondary, conflicting quota numbers. LOW
- https://supabase.com/docs/guides/auth/auth-email-passwordless — OTP flow, 60 s cooldown, 1 h expiry, `{{ .Token }}`. HIGH
- https://supabase.com/docs/guides/auth/auth-email-templates — template variables, email prefetching note. HIGH
- https://supabase.com/docs/guides/auth/auth-smtp — built-in SMTP restrictions (team-only, 2/hour), custom SMTP 30/hour default, supported providers. HIGH
- https://supabase.com/docs/guides/auth/rate-limits — rate-limit buckets and the 2/hour built-in note. HIGH
- https://github.com/orgs/supabase/discussions/28947 — new users get Confirm signup template. MEDIUM
- https://supabase.com/docs/guides/ai/semantic-search and /vector-columns — pgvector enable, `vector(N)`, `match_*` function, `rpc()`, HNSW/IVFFlat. HIGH
- https://supabase.com/docs/guides/api/api-keys — publishable/secret keys, anon/service_role deprecation by end of 2026, RLS role mapping. HIGH
- https://supabase.com/pricing and https://supabase.com/docs/guides/platform/free-project-pausing — free-plan limits, pause rules, 1-year restore. HIGH
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows — cron semantics, 60-day auto-disable on public repos. HIGH
- https://docs.streamlit.io/deploy/streamlit-community-cloud/ (status and limitations, app dependencies, secrets management, upgrade Python, manage your app) — limits, sleep, secrets, dependency-file rules. HIGH
- https://discuss.streamlit.io/t/streamlit-cloud-forcing-python-3-14-before-tensorflow-supports-it/121567 (May 2026) and https://discuss.streamlit.io/t/how-to-prevent-the-app-enter-the-sleep-mode/87959 — default Python 3.14, selection quirks, wake behaviour. MEDIUM
- https://resend.com/pricing, https://www.brevo.com/pricing/ and web search results on Resend sandbox and Brevo single-sender setup — SMTP free tiers. MEDIUM

---
*Stack research for: AI-powered researcher-matching app (Streamlit + Supabase + Gemini, free tier)*
*Researched: 2026-10-05*
