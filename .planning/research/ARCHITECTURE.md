# Architecture Research

**Domain:** AI-assisted researcher matching / recommendation app (Streamlit + Supabase + Gemini, free tier only)
**Project:** Findings
**Researched:** 2026-10-05
**Confidence:** MEDIUM-HIGH (structure and Supabase/pgvector patterns HIGH; exact Gemini free-tier quotas and which embedding model is free-tier-eligible are LOW and must be re-checked in AI Studio at build time)

## Standard Architecture

The canonical shape for an LLM-assisted matcher on this stack is a **retrieve-then-rerank pipeline behind a thin service layer**, with Postgres as the single source of truth and the LLM treated as an unreliable, quota-limited enhancer (never a hard dependency). Streamlit is only the presentation layer; all business rules that must be enforced (who can read what, who can accept a connection) live in Postgres (RLS, column grants, triggers, security-definer RPCs), not in Python.

### System Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                  PRESENTATION  (Streamlit Community Cloud)               │
│  app.py (page config + auth gate + st.navigation)                        │
│  ┌───────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌─────────┐  │
│  │ Login │ │ Profile │ │Discover │ │ Matches  │ │ Mentor- │ │Connect- │  │
│  │       │ │+autofill│ │+filters │ │ (peer)   │ │ ship    │ │ ions    │  │
│  └───┬───┘ └────┬────┘ └────┬────┘ └────┬─────┘ └────┬────┘ └────┬────┘  │
│      └──────────┴───────────┴───────────┴────────────┴───────────┘       │
│                 ui/ components (cards, badges, filters) - dumb            │
├──────────────────────────────────────────────────────────────────────────┤
│                         SERVICE LAYER (pure Python)                      │
│  ┌──────────────┐ ┌─────────────────┐ ┌────────────────┐ ┌────────────┐  │
│  │ auth_service │ │ profile_service │ │ matching_      │ │ connection_│  │
│  │ (OTP, sess.) │ │ (save+embed+tag)│ │ service (2-stg)│ │ service    │  │
│  └──────┬───────┘ └───┬─────────┬───┘ └───┬────────┬───┘ └─────┬──────┘  │
│         │             │         │         │        │           │         │
├─────────┼─────────────┼─────────┼─────────┼────────┼───────────┼─────────┤
│         │   REPOSITORY LAYER (repos/)     │   AI LAYER (ai/)    │         │
│         │  profiles / connections /       │  embeddings, rerank,│         │
│         │  match_cache  (supabase-py,     │  autofill, methods  │         │
│         │  per-user client, anon key)     │  (google-genai,     │         │
│         │                                 │  NO streamlit imp.) │         │
└─────────┼─────────────────────────────────┼─────────────────────┼─────────┘
          ▼                                 ▼                     ▼
┌──────────────────────────────┐  ┌──────────────────────────────────────┐
│ SUPABASE (free)              │  │ GEMINI API (free tier)               │
│  Auth (email OTP)            │  │  generateContent (JSON schema)       │
│  Postgres + RLS + pgvector   │  │  embed_content (768-dim)             │
│  RPCs: match_profiles,       │  └──────────────────────────────────────┘
│        get_contact_email,    │
│        my_connections        │   ┌──────────────────────────────────────┐
│  Tables: profiles,           │   │ OFFLINE (laptop only)                │
│   profile_contacts,          │◄──│  scripts/seed_generate.py -> JSON    │
│   connections, match_cache   │   │  scripts/seed_load.py (service role) │
└──────────────▲───────────────┘   └──────────────────────────────────────┘
               │ every ~3 days
┌──────────────┴───────────────┐
│ GitHub Actions keep-alive    │
└──────────────────────────────┘
```

Dependency rule (enforce in code review): `views -> services -> (repos, ai)`; `ui` is imported only by `views`; `repos` and `ai` **never import streamlit** (so the offline seed script reuses them unchanged) and never import each other; only `services` composes them.

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| `app.py` entrypoint | `st.set_page_config`, build per-session Supabase client, auth gate, declare pages via `st.navigation`, run selected page. Runs on every rerun of every page, so keep it cheap | `st.navigation({...}).run()` with the page list depending on `is_authenticated` |
| `views/*.py` (pages) | One screen each: collect input, call a service, render. No SQL, no Gemini calls, no business rules | Plain scripts or functions passed to `st.Page` |
| `ui/` components | Reusable stateless rendering: profile card, match card (score bar + explanation + give/need), synthetic badge, filter bar | Functions taking dataclasses/dicts; buttons return intent, caller acts |
| `core/config.py` | One place that reads secrets: `st.secrets` inside the app, env vars / `.streamlit/secrets.toml` via `tomllib` in scripts | Frozen dataclass `Settings` built once |
| `core/session.py` | Create/store/retrieve the **per-user** Supabase client and auth state in `st.session_state`; `require_auth()` guard | See Pattern 1 |
| `repos/` (profiles, connections, match_cache) | Typed CRUD and RPC calls; the only module that knows table/column/RPC names. Takes a client as argument | Functions `get_profile(client, id)`, `rpc_match_profiles(client, ...)`, Pydantic models in `repos/models.py` |
| `ai/` (client, embeddings, autofill, methods, rerank, prompts, schemas) | All Gemini access, prompts, JSON schemas, retry/timeout, validation. Returns validated Pydantic objects or raises one `AIUnavailable` exception | `google-genai` `Client`, `response_schema=PydanticModel`, `embed_content` |
| `services/profile_service.py` | Save-profile use case: validate -> upsert -> compute text+hash -> embed if hash changed -> AI methods label if missing -> persist | Orchestrates repos + ai; embed failure does not fail the save |
| `services/matching_service.py` | The two-stage pipeline, cache read/write, fallback ladder, mode handling | See Pattern 2 |
| `services/connection_service.py` | Send / accept / decline, reverse-request detection, contact-email unlock | Thin over repos; DB enforces the rules |
| `profile_text.py` (shared) | Canonical "embedding text" and `profile_hash` builders. Used by app **and** seed script so synthetic and real embeddings live in the same space | Pure functions, no I/O |
| `supabase/migrations/*.sql` | Schema, RLS, grants, triggers, RPCs; versioned and re-runnable | Applied via SQL editor or Supabase CLI; committed to repo |
| `scripts/` | Offline seed generate + load, optional cache pre-warm | Plain Python using `ai/` + service-role client |
| `.github/workflows/keepalive.yml` | Cron DB ping | `curl` to PostgREST with anon key |

## Recommended Project Structure

```
findings/
├── app.py                         # entrypoint: config, auth gate, st.navigation
├── requirements.txt               # pinned (Streamlit Cloud installs from this)
├── .streamlit/
│   ├── config.toml                # theme, maxUploadSize = 5 (MB, CV PDFs)
│   └── secrets.toml               # GITIGNORED; mirrored in Cloud dashboard
├── findings/                      # importable package (shared by app + scripts)
│   ├── core/        config.py  session.py  errors.py  constants.py
│   ├── repos/       models.py  profiles.py  connections.py  match_cache.py
│   ├── ai/          client.py  embeddings.py  autofill.py  methods.py
│   │                rerank.py  prompts.py  schemas.py
│   ├── services/    auth_service.py  profile_service.py
│   │                matching_service.py  connection_service.py
│   └── profile_text.py            # embedding text + hashing (shared, pure)
├── views/                         # NOT named pages/ (avoid legacy auto-discovery)
│   ├── login.py  profile.py  discover.py  matches.py
│   ├── mentorship.py  connections.py  about.py   # about = limitations/AI-use page
├── ui/            cards.py  filters.py  badges.py
├── scripts/       seed_generate.py  seed_load.py  prewarm_cache.py
├── data/seed/     synthetic_profiles.json     # committed, reproducible
├── supabase/migrations/
│   ├── 001_extensions_profiles.sql
│   ├── 002_connections.sql
│   ├── 003_rls_policies.sql
│   ├── 004_rpcs.sql               # match_profiles, get_contact_email, my_connections
│   └── 005_match_cache.sql
├── tests/         test_profile_text.py  test_rerank_parsing.py  test_rls.md (manual two-account script)
├── docs/          architecture.md  limitations.md  ai-use.md  data-sources.md  test-report/
└── .github/workflows/keepalive.yml
```

### Structure Rationale

- **`findings/` package separate from `views/`:** the seed script and tests import `findings.ai` / `findings.repos` without ever importing Streamlit. If `ai/` imported `st.secrets` the offline script would crash. Config is injected.
- **`views/` instead of `pages/`:** with `st.navigation` the `pages/` directory is legacy auto-routing; naming it `views/` avoids accidental double registration and makes it obvious pages are declared in `app.py`.
- **`repos/` is the only SQL-shaped code:** schema changes touch one folder, and the rest of the code deals in Pydantic models.
- **`profile_text.py` is shared and pure:** the hash that gates re-embedding, the text that gets embedded, and the cache key all come from one function, so they cannot drift apart.
- **Migrations committed:** the rubric wants architecture/data documentation; SQL files double as that documentation and make the project re-creatable if the Supabase project is lost.

## Architectural Patterns

### Pattern 1: Per-session Supabase client in `st.session_state`

**What:** Each browser session builds its own `supabase.create_client(url, anon_key)`, signs in through it, and keeps it in `st.session_state["sb"]`. All repository calls receive that client, so PostgREST requests carry that user's JWT and RLS applies.
**When to use:** Always, for every user-scoped operation. The service-role key is never in the app.
**Trade-offs:** Client (and session) is lost on full browser refresh because `session_state` is per websocket session; persisting a refresh token in a cookie fixes that but adds fragility (treat as polish, see PITFALLS-style note below).

```python
# findings/core/session.py
import streamlit as st
from supabase import create_client
from findings.core.config import settings

def get_client():
    if "sb" not in st.session_state:
        st.session_state["sb"] = create_client(settings.supabase_url, settings.supabase_anon_key)
    return st.session_state["sb"]

def current_user():
    sb = get_client()
    session = sb.auth.get_session()          # refreshes the JWT if it has expired
    return session.user if session else None

def require_auth():
    if current_user() is None:
        st.switch_page(LOGIN_PAGE)           # or: show only the login page in st.navigation
        st.stop()
```

```python
# findings/services/auth_service.py  (OTP flow, two steps)
def send_code(sb, email):
    sb.auth.sign_in_with_otp({"email": email, "options": {"should_create_user": True}})

def verify_code(sb, email, code):
    res = sb.auth.verify_otp({"email": email, "token": code, "type": "email"})
    return res.session  # client now holds the session; postgrest calls carry the JWT
```

**Hard rule:** never put this client in `st.cache_resource`, a module global, or `st.cache_data` args. Those are shared across all visitors; one user's login would authenticate everyone (well-documented Streamlit+Supabase failure, confirmed in community threads). `st.cache_resource` is fine only for the stateless Gemini client.

### Pattern 2: Retrieve (pgvector) -> Rerank (Gemini) -> Cache -> Fallback ladder

**What:** Stage 1 is a cheap SQL similarity search over stored embeddings (no API call, because the viewer's own embedding is already stored). Stage 2 is **one** Gemini call that reranks all ~15 candidates at once and returns validated JSON. Results are cached per (user, mode) keyed by a profile hash. Failures degrade down a ladder instead of erroring.
**When to use:** Every match request.
**Trade-offs:** Cache can show slightly stale candidate pools (new profiles arrive, others edit); mitigate with a soft TTL + manual refresh button (with cooldown). One batched rerank call is cheaper and faster than per-candidate calls but needs a compact prompt and ID mapping.

Fallback ladder (first success wins):

1. Fresh cache (`profile_hash` matches AND `age < TTL`) -> zero API calls.
2. Live path: stage 1 RPC -> one Gemini rerank -> validate -> write cache (`source='ai'`).
3. Stale cache for the same user/mode (hash may differ only if profile edited; if hash differs, skip this rung) -> show with notice "showing saved results".
4. Embedding-only: stage-1 order, score = scaled similarity, explanation = deterministic template from overlapping tags; cache with `source='embedding'` and a **short** TTL (so the next visit retries AI rather than being stuck on the degraded result). UI shows a notice.
5. If the viewer has no embedding (embed failed at save): retry the embed once; if still failing, tag/filter overlap ordering in SQL; else Discover-style list with a notice.

```python
# findings/services/matching_service.py (shape, not final code)
def get_matches(sb, me: Profile, mode: Literal["peer", "mentor"], force=False) -> MatchResult:
    key = match_hash(me, mode)                         # sha256(profile_text + mode + PROMPT_VERSION + EMBED_MODEL)
    cached = cache_repo.get(sb, me.id, mode)
    if cached and cached.profile_hash == key and not force and cached.is_fresh():
        return hydrate(sb, cached)                     # live-join profile rows by id
    if me.embedding is None:
        me = profile_service.ensure_embedding(sb, me)  # may raise AIUnavailable
    cands = profiles_repo.match_profiles(sb, me.embedding, k=15, mode=mode)   # RPC, stage 1
    try:
        ranked = rerank.rerank(me, cands, mode)        # ONE Gemini call, validated, retried once
        source = "ai"
    except AIUnavailable:
        if cached and cached.profile_hash == key:
            return hydrate(sb, cached, notice="stale")
        ranked = fallback.embedding_only(me, cands, mode)
        source = "embedding"
    cache_repo.put(sb, me.id, mode, key, ranked, source)
    return hydrate(sb, ranked, source=source)
```

### Pattern 3: Compute-on-write embeddings with a content hash

**What:** Embed when a profile is saved, not when it is matched. Store `embedding`, `embedding_hash` (sha256 of the canonical embedding text + model id), and `embedding_model`. On save, skip the Gemini call if the hash is unchanged.
**When to use:** Always. It moves nearly all embedding traffic to save-time and makes stage 1 of matching a pure SQL call.
**Trade-offs:** A failed embed at save leaves `embedding IS NULL`; the save must still succeed, and matching lazily retries.

```python
# findings/profile_text.py
def embedding_text(p) -> str:
    # Deliberately EXCLUDES name/email; includes stage so mentors vs juniors separate semantically
    return "\n".join([
        f"Career stage: {p.career_stage}",
        f"Field and interests: {', '.join(p.interests)}",
        f"Methods: {p.methods_effective or ''}",
        f"Skills: {', '.join(p.skills)}",
        f"Offers: {', '.join(p.offers)}",
        f"Needs: {', '.join(p.needs)}",
        f"Experience: {p.experience}",
        f"Looking for: {p.looking_for}",
        f"Bio: {p.bio}",
    ])

def text_hash(text: str, model: str) -> str:
    return hashlib.sha256(f"{model}|{text}".encode()).hexdigest()
```

Embedding specifics (verified against Google docs): use `output_dimensionality=768` (MRL truncation; recommended sizes 768/1536/3072). `gemini-embedding-001` does **not** auto-normalize truncated vectors, so L2-normalize in code (cheap, idempotent, harmless for `gemini-embedding-2` which does normalize), then cosine and inner-product orderings are identical. `gemini-embedding-2` (GA April 2026) has no `task_type`; for `gemini-embedding-001` use `SEMANTIC_SIMILARITY` for both sides (symmetric profile-to-profile matching), not `RETRIEVAL_QUERY`/`RETRIEVAL_DOCUMENT`. Keep the model id in one constant and store it per row; embedding spaces are incompatible across models, so a model change means re-embedding everyone (the seed script must be re-runnable for that reason). Decide the model **once, in Phase 0**, and stick with it.

### Pattern 4: Schema-constrained LLM output with validate-and-map-back

**What:** Every Gemini call that feeds code uses `response_mime_type="application/json"` plus a Pydantic `response_schema`, then re-validates in Python (schema constraints like min/max are not reliably enforced by the API). Candidates are given short ephemeral IDs (`c1`..`c15`) in the prompt and mapped back to UUIDs, so the model can never invent or corrupt a real ID. Unknown IDs are dropped; missing candidates are appended in stage-1 order with an "unscored" flag.
**When to use:** rerank, autofill, methods suggestion, seed generation.
**Trade-offs:** Slightly more code; eliminates the dominant demo-day failure (malformed JSON / hallucinated IDs).

```python
# findings/ai/schemas.py
class MatchItem(BaseModel):
    candidate_id: str                    # "c1".."c15"
    score: int                           # 0-100; clamp after parsing
    explanation: str                     # 1-2 sentences, grounded in provided fields only
    they_give_you: list[str] = []        # mentor mode: their offers that fit your needs
    you_give_them: list[str] = []        # mentor mode: your offers/skills that fit their needs

class RerankResponse(BaseModel):
    matches: list[MatchItem]

class ProfileDraft(BaseModel):           # autofill; EVERYTHING optional (documents are incomplete)
    full_name: str | None = None
    career_stage: Literal["Undergrad","Master's","PhD","Postdoc","Faculty","Industry researcher"] | None = None
    institution: str | None = None
    education: str | None = None
    interests: list[str] = []
    experience: str | None = None
    skills: list[str] = []
    offers: list[str] = []
    needs: list[str] = []
    bio: str | None = None
    methods_suggestion: Literal["qualitative","quantitative","mixed"] | None = None
```

Operational settings for every call: explicit timeout (~20 s), at most one retry on 429/5xx/invalid JSON with short backoff, low temperature (0.2), model id from config, all failures normalized to `AIUnavailable`. Treat profile text and CV text as **untrusted data** inside delimiters; render explanations with plain `st.write`/`st.markdown` and never `unsafe_allow_html=True` on user or LLM text.

### Pattern 5: Database-enforced privacy (RLS + column grants + security-definer RPCs)

**What:** Python never decides who may see an email or accept a request. Postgres does. Email lives in a table no client policy can read; the only path out is a security-definer function that checks for an accepted connection.
**When to use:** All privacy-relevant data.
**Trade-offs:** More SQL up front; but the Streamlit code can be wrong or malicious-input-tolerant without leaking data, and the privacy requirement is demonstrable in the rubric (show it failing from the SQL editor as the anon role).

## Supabase Schema

Decision summary (opinionated):

- **`profiles.id` equals `auth.uid()` for real users, random UUID for synthetic ones; no FK to `auth.users`.** This makes every RLS predicate a trivial `id = auth.uid()`, lets `connections` point at `profiles.id` uniformly (real or synthetic recipients), and avoids polluting Auth with ~100 fake users. Integrity is kept by a trigger that creates the real user's profile on signup and one that deletes it when the auth user is deleted. (Alternative: nullable `auth_user_id` FK + separate PK; correct but every policy needs a join/helper function. Not worth it at this scale.)
- **Email never lives on `profiles`.** It lives in `profile_contacts` (RLS enabled, no policies = no client access) and is read only via `get_contact_email()` / `my_connections()`. Column-level `REVOKE` on `profiles.email` is rejected because `select *` from PostgREST would then fail with permission denied.
- **Derived values are Postgres generated columns** (`stage_tier`, `open_to_mentoring`, `seeking_mentor`, `methods_effective`), so filters in SQL/RPC use them directly and they cannot drift from `career_stage`.
- **One `offers`/`needs` vocabulary for everyone** (not separate mentor and junior columns). Mentor: offers = training/co-authorship/guidance, needs = data collection/lit review/coding. Junior: offers = skills they can contribute, needs = what they want to learn. The give/need complement then is the same symmetric test in both directions (`A.offers` vs `B.needs`, `B.offers` vs `A.needs`), UI labels change by tier only.
- **Embedding stays a column on `profiles`** (768-dim). Repositories select explicit columns for list views so the vector is not shipped to Discover.

```sql
-- 001: extensions + profiles
create extension if not exists vector with schema extensions;

create table public.profiles (
  id               uuid primary key default gen_random_uuid(),  -- = auth.uid() for real users
  is_synthetic     boolean not null default false,
  is_complete      boolean not null default false,              -- hidden from Discover until true
  full_name        text not null default '',
  career_stage     text check (career_stage in
                     ('Undergrad','Master''s','PhD','Postdoc','Faculty','Industry researcher')),
  institution      text, education text, experience text, bio text, looking_for text,
  interests        text[] not null default '{}',
  skills           text[] not null default '{}',
  offers           text[] not null default '{}',
  needs            text[] not null default '{}',
  methods_ai       text check (methods_ai in ('qualitative','quantitative','mixed')),
  methods_override text check (methods_override in ('qualitative','quantitative','mixed')),
  methods_effective text generated always as (coalesce(methods_override, methods_ai)) stored,
  stage_tier       text generated always as (
      case when career_stage in ('Undergrad','Master''s','PhD') then 'junior'
           when career_stage in ('Postdoc','Faculty','Industry researcher') then 'senior' end) stored,
  seeking_mentor    boolean generated always as (career_stage in ('Undergrad','Master''s','PhD')) stored,
  open_to_mentoring boolean generated always as (career_stage in ('Postdoc','Faculty','Industry researcher')) stored,
  embedding        extensions.vector(768),
  embedding_hash   text,
  embedding_model  text,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);
create index on public.profiles (methods_effective);
create index on public.profiles (career_stage);
-- No ANN index needed below ~10k rows (exact scan over 100 rows is sub-millisecond and exact).
-- If added later: HNSW with vector_cosine_ops; note filtered ANN queries can under-return (use pgvector >= 0.8 iterative scan).

create table public.profile_contacts (        -- private; RLS on, zero policies
  profile_id uuid primary key references public.profiles(id) on delete cascade,
  email      text not null                    -- synthetic: first.last@synthetic.example (reserved domain)
);
alter table public.profile_contacts enable row level security;

-- auth -> profile bootstrap
create function public.handle_new_user() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  insert into public.profiles (id) values (new.id);
  insert into public.profile_contacts (profile_id, email) values (new.id, new.email);
  return new;
end $$;
create trigger on_auth_user_created after insert on auth.users
  for each row execute function public.handle_new_user();
-- (+ after delete on auth.users -> delete from public.profiles where id = old.id)
```

PhD ambiguity: PROJECT.md says junior = "Undergrad through *early* PhD" but the stage list has one "PhD" entry. The schema above treats **PhD as junior** (simplest, explainable). If the team wants late-PhD mentors, split the list into "PhD (early)" / "PhD (late)" now; changing it later means re-deriving columns and re-embedding. Flag for requirements.

```sql
-- 002: connections
create table public.connections (
  id            uuid primary key default gen_random_uuid(),
  requester_id  uuid not null references public.profiles(id) on delete cascade,
  recipient_id  uuid not null references public.profiles(id) on delete cascade,
  note          text check (char_length(note) <= 500),
  status        text not null default 'pending' check (status in ('pending','accepted','declined')),
  created_at    timestamptz not null default now(),
  responded_at  timestamptz,
  check (requester_id <> recipient_id)
);
-- one connection per unordered pair (blocks A->B plus B->A duplicates)
create unique index connections_pair_uniq on public.connections
  (least(requester_id, recipient_id), greatest(requester_id, recipient_id));
create index on public.connections (recipient_id, status);
create index on public.connections (requester_id, status);

-- 005: match cache
create table public.match_cache (
  user_id      uuid not null references public.profiles(id) on delete cascade,
  mode         text not null check (mode in ('peer','mentor')),
  profile_hash text not null,
  source       text not null check (source in ('ai','embedding')),
  results      jsonb not null,            -- [{profile_id, score, explanation, they_give_you, you_give_them, similarity}]
  created_at   timestamptz not null default now(),
  primary key (user_id, mode)
);
```

The cache stores only IDs + scores + explanations; the page re-reads the profile rows by ID so edits to a candidate show immediately and the cache stays small.

### RLS policies and grants

```sql
-- 003: profiles
alter table public.profiles enable row level security;

create policy "read complete profiles or own"  on public.profiles for select to authenticated
  using (is_complete or id = auth.uid());
create policy "insert own" on public.profiles for insert to authenticated
  with check (id = auth.uid() and not is_synthetic);
create policy "update own" on public.profiles for update to authenticated
  using (id = auth.uid()) with check (id = auth.uid() and not is_synthetic);
-- no delete policy: deletion happens via auth user deletion cascade.
-- Stop users flipping is_synthetic or id via the API:
revoke update on public.profiles from authenticated;
grant  update (full_name, career_stage, institution, education, experience, bio, looking_for,
               interests, skills, offers, needs, methods_ai, methods_override,
               embedding, embedding_hash, embedding_model, is_complete, updated_at)
       on public.profiles to authenticated;
-- anon gets no policies -> the keep-alive ping returns [] but still executes a query.

-- connections
alter table public.connections enable row level security;
create policy "read mine" on public.connections for select to authenticated
  using (auth.uid() in (requester_id, recipient_id));
create policy "send as me" on public.connections for insert to authenticated
  with check (requester_id = auth.uid() and status = 'pending');
create policy "recipient responds" on public.connections for update to authenticated
  using (recipient_id = auth.uid()) with check (recipient_id = auth.uid());
create policy "requester withdraws pending" on public.connections for delete to authenticated
  using (requester_id = auth.uid() and status = 'pending');
revoke update on public.connections from authenticated;
grant  update (status) on public.connections to authenticated;   -- column grant: only status
-- transition guard (pending -> accepted|declined only; stamps responded_at)
create function public.guard_connection_update() returns trigger language plpgsql as $$
begin
  if old.status <> 'pending' then raise exception 'connection already resolved'; end if;
  if new.status not in ('accepted','declined') then raise exception 'invalid status'; end if;
  new.responded_at := now(); return new;
end $$;
create trigger trg_guard_connection before update on public.connections
  for each row execute function public.guard_connection_update();

-- match_cache: own rows only
alter table public.match_cache enable row level security;
create policy "own cache" on public.match_cache for all to authenticated
  using (user_id = auth.uid()) with check (user_id = auth.uid());
```

### RPCs (the controlled doors)

```sql
-- 004a: stage-1 retrieval. SECURITY INVOKER so profiles RLS still applies.
create function public.match_profiles(
  p_query   extensions.vector(768),
  p_mode    text    default 'peer',      -- 'peer' | 'mentor'
  p_k       int     default 15,
  p_methods text    default null,        -- optional filter
  p_stage   text    default null)
returns table (id uuid, similarity float4)
language sql stable security invoker set search_path = public, extensions as $$
  with me as (select stage_tier from profiles where id = auth.uid())
  select p.id, (1 - (p.embedding <=> p_query))::float4
  from profiles p, me
  where p.id <> auth.uid() and p.is_complete and p.embedding is not null
    and (p_mode = 'peer' or p.stage_tier <> me.stage_tier)      -- mentor mode: cross junior/senior split only
    and (p_methods is null or p.methods_effective = p_methods)
    and (p_stage   is null or p.career_stage = p_stage)
    and not exists (select 1 from connections c                  -- hide people already connected/pending/declined
        where least(c.requester_id,c.recipient_id)=least(p.id,auth.uid())
          and greatest(c.requester_id,c.recipient_id)=greatest(p.id,auth.uid()))
  order by p.embedding <=> p_query
  limit least(p_k, 50);
$$;

-- 004b: the ONLY way to read an email
create function public.get_contact_email(p_profile uuid) returns text
language sql stable security definer set search_path = '' as $$
  select c.email from public.profile_contacts c
  where c.profile_id = p_profile
    and (p_profile = auth.uid() or exists (
      select 1 from public.connections x
      where x.status = 'accepted'
        and ((x.requester_id = auth.uid() and x.recipient_id = p_profile)
          or (x.recipient_id = auth.uid() and x.requester_id = p_profile))));
$$;
revoke execute on function public.get_contact_email(uuid) from public, anon;
grant  execute on function public.get_contact_email(uuid) to authenticated;

-- 004c: Connections page in one call; email column is NULL unless accepted
create function public.my_connections() returns table (
  connection_id uuid, direction text, status text, note text, created_at timestamptz,
  other_id uuid, other_name text, other_stage text, other_is_synthetic boolean, other_email text)
language sql stable security definer set search_path = '' as $$
  select c.id,
         case when c.requester_id = auth.uid() then 'sent' else 'received' end,
         c.status, c.note, c.created_at, o.id, o.full_name, o.career_stage, o.is_synthetic,
         case when c.status = 'accepted' then pc.email end
  from public.connections c
  join public.profiles o on o.id = case when c.requester_id = auth.uid() then c.recipient_id else c.requester_id end
  left join public.profile_contacts pc on pc.profile_id = o.id
  where auth.uid() in (c.requester_id, c.recipient_id)
  order by c.created_at desc;
$$;
revoke execute on function public.my_connections() from public, anon;
grant  execute on function public.my_connections() to authenticated;
```

Security-definer rules that must hold: `set search_path = ''` and fully-qualified names inside; `revoke ... from public, anon` then grant to `authenticated` (functions are executable by `public` by default); never expose them in a schema that is not intended for API use. Verify with the anon key from `curl` that `get_contact_email` returns an error and that a second real account gets `null` before acceptance.

Synthetic-profile modelling consequences: `connections` may legitimately point at a synthetic recipient (no FK to Auth), but nobody can accept for them. Recommendation: keep it honest, do not auto-accept. For the demo, (a) use a **second real demo account** to show the accept flow, and (b) run a small `seed_demo_connections` step (service role) that inserts a pending request *from* a synthetic profile *to* the demo account so the recipient-side accept UX can be shown on one screen. Synthetic contact emails use the reserved `synthetic.example` domain and the UI labels them. If the team insists on auto-accept for synthetic recipients, implement as a trigger limited to `is_synthetic` recipients and say so in the limitations doc; this is a product decision for the roadmap, not an architecture need.

## Data Flow

### Request Flow (login to first match)

```
Browser ──► Streamlit script rerun
   app.py: get_client() (session_state) ─► get_session() ─► not signed in ─► Login view
   Login: email ─► sign_in_with_otp ─► Supabase Auth ─► SMTP ─► user inbox (6-digit code)
   code ─► verify_otp ─► session in client ─► trigger creates empty profiles row ─► rerun
   Profile incomplete? ─► route to Profile view (gate Discover/Matches until is_complete)
```

### Key Data Flows

1. **Profile save (manual or post-autofill):**
   `Profile view` -> `profile_service.save()` -> `profiles_repo.upsert(own row)` (RLS/column grants) -> `profile_text.embedding_text()` + `text_hash()` -> if hash differs from stored `embedding_hash`: `ai.embeddings.embed()` (768, normalized) -> `profiles_repo.update(embedding, embedding_hash, embedding_model)`; if `methods_ai` is null or text changed materially: `ai.methods.suggest()` -> `methods_ai`. Any `AIUnavailable` is swallowed into a UI warning; the form data is already saved. `methods_override` is written only by the user's explicit selection. Existing `match_cache` rows become stale implicitly because `profile_hash` changes (no delete needed).

2. **AI autofill:**
   ```
   paste text ──┐                       ┌─► ProfileDraft (JSON, all-optional)
                ├─► ai.autofill.extract ┤      │ (in-memory only; PDF bytes never stored)
   PDF (<=5MB) ─┘   Gemini: Part.from_bytes(pdf, "application/pdf") or text part
                                          ▼
        st.session_state draft ─► on_click callback writes widget keys ─► form prefilled
                                          ▼  user edits + confirms
                                  profile_service.save() (flow 1)
   ```
   Streamlit gotcha: a widget with a `key` ignores `value=` after first render; set `st.session_state[widget_key]` inside an `on_click` callback (runs before the next render) or before the widget is instantiated, then let the rerun show it. Inline PDF upload is fine for CV-sized files (limit the uploader to ~5 MB); do not use the Files API (needless state and cleanup).

3. **Two-stage matching (peer or mentor):**
   ```
   Matches/Mentorship view ──► matching_service.get_matches(me, mode)
      cache hit (hash+TTL)? ────────────────────────────────► hydrate profiles by id ─► render
      miss: RPC match_profiles(my stored embedding, mode, k=15, filters)    [SQL, no API call]
            └► candidates (ids + similarity)
            └► profiles_repo.get_many(ids)  [explicit columns]
            └► ai.rerank.rerank(me, candidates, mode)   [ONE Gemini call, JSON schema]
                  ├─ ok ──► validate/map c1..c15 -> uuids, clamp scores ─► cache(source='ai')
                  └─ fail ─► stale-cache rung ─► embedding-only rung ─► cache(source='embedding', short TTL)
      render: score bar, explanation, (mentor mode) "They give you / You give them", Connect button,
              notice banner if source != 'ai', badge if is_synthetic
   ```
   Mentor mode differences are confined to: the RPC `p_mode='mentor'` filter (opposite `stage_tier`), a different prompt template (give/need complement emphasized, return `they_give_you` / `you_give_them`), and the cache key `mode`. Same service, same cache table, same UI card with an extra section. Stage 1 uses topical similarity of the single embedding; the give/need fit is judged in rerank (a second "offers/needs" embedding is a possible later improvement, not v1).

4. **Connection request lifecycle:**
   `Connect button` -> `connection_service.send(me, other, note)` -> if reverse pending request exists (they already asked you): UI offers Accept instead -> `connections_repo.insert` (RLS: requester = me, status pending; unique-pair index blocks duplicates -> friendly message) -> recipient opens Connections view -> `rpc my_connections()` (emails null) -> Accept/Decline -> `update status` (column grant + recipient-only policy + transition trigger) -> both sides now see `other_email` from `my_connections()`/`get_contact_email()`.

5. **Offline seeding (laptop, not part of the app):**
   ```
   seed_generate.py:  Gemini JSON-schema calls, ~10 profiles per call, with a coverage grid
        (fields x career stages x methods; explicit mix of juniors/seniors, offers/needs filled)
        -> appends each batch to data/seed/synthetic_profiles.json (resumable, deduped by name) -> COMMIT
   seed_load.py:      reads JSON -> findings.profile_text (same builder as app) -> ONE batched
        embed_content call (list of texts) -> insert with SERVICE-ROLE key:
        profiles(id = uuid5(namespace, slug) [deterministic, so reruns upsert not duplicate],
                 is_synthetic = true, is_complete = true, embedding...) + profile_contacts(fake email)
   ```
   Deterministic `uuid5` ids make the load idempotent (`upsert on conflict (id)`), so it can be re-run after a model change to re-embed. The service-role key is read from a local env var/`secrets.toml` only, never from the Streamlit Cloud secrets. Generate with a coverage grid in the prompt rather than "give me 100 researchers" (which collapses to repetitive archetypes), and include the generation prompt and parameters in `docs/data-sources.md`.

6. **Keep-alive:**
   `cron` -> `curl "$SUPABASE_URL/rest/v1/profiles?select=id&limit=1" -H "apikey: $ANON_KEY"` (a real PostgREST -> Postgres query; anon gets `[]` by RLS but the DB executes it). Prefer this over `/auth/v1/health`, which may not count as database activity. Schedule twice a week, plus `workflow_dispatch`:
   ```yaml
   on:
     schedule: [{ cron: "17 6 * * 1,4" }]
     workflow_dispatch:
   jobs:
     ping:
       runs-on: ubuntu-latest
       steps:
         - run: >
             curl -fsS "${{ secrets.SUPABASE_URL }}/rest/v1/profiles?select=id&limit=1"
             -H "apikey: ${{ secrets.SUPABASE_ANON_KEY }}"
   ```
   The `-f` flag makes a non-2xx response fail the workflow so GitHub emails you. This does not wake the Streamlit app (Cloud apps sleep after inactivity and need a browser visit); that stays on the pre-demo checklist.

### State Management

```
st.session_state
  sb                  -> per-user Supabase client (never cached globally)
  profile_draft       -> autofill result awaiting user confirmation
  match_result[mode]  -> last MatchResult (avoids re-querying on every widget rerun)
  last_refresh_at     -> cooldown for the "Refresh matches" button
  filters             -> Discover filter values
Source of truth for everything durable: Postgres.
Streamlit reruns the whole script on every widget interaction -> expensive work
(Gemini, RPC) must sit behind a button, a cache check, or a session_state memo, never bare in the script body.
```

`st.cache_data` is acceptable only for data identical for every viewer (e.g., static constants). Do not cache anything fetched through the per-user client unless the user id is part of the cache key.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Demo (<=100 profiles, <=20 users) | Exact vector scan, no ANN index; cache + one rerank call per user keeps Gemini at a few calls per user; pre-warm demo accounts' cache before the presentation |
| ~1k-10k users | Add HNSW index (`vector_cosine_ops`); move rerank to async/batched where possible; paid Gemini tier or alternate rerank model; add cache invalidation on new-profile arrival; rate-limit per user server-side |
| 100k+ users | Replace Streamlit with a real frontend + API; background embedding queue; precomputed candidate lists; dedicated vector infra only if Postgres tuning is exhausted |

### Scaling Priorities

1. **First bottleneck: Gemini free-tier quota (RPD/RPM), not the database.** Quotas are per project, not per key, and daily resets are at midnight Pacific. Mitigation is architectural: embed on write with hash skip, one batched rerank per (user, mode), cache with TTL, refresh cooldown, pre-warmed demo cache, and the fallback ladder. Published free-tier numbers vary wildly by source (anywhere from tens to ~1,500 requests/day for Flash models, and Google reduced limits in December 2025), so read the real numbers from AI Studio on build day and put the model ids in config.
2. **Second bottleneck: Supabase Auth email.** The default built-in SMTP is limited to about 2 emails/hour project-wide (and is meant for team/testing use); enabling custom SMTP lifts the default to 30/hour and is effectively mandatory for an OTP login that testers and graders will use. Also the **default email template contains a magic link, not the code**: edit the "Magic Link" (and "Confirm signup") template to include `{{ .Token }}`.
3. **Third: Streamlit Cloud cold start / session loss**, a UX and demo-day concern rather than a throughput one.

## Anti-Patterns

### Anti-Pattern 1: Global/cached Supabase client holding a user session

**What people do:** `@st.cache_resource def get_supabase(): return create_client(...)` then `.auth.sign_in...` on it.
**Why it's wrong:** `cache_resource` is shared by all sessions; the first user to sign in authenticates every other visitor, and RLS then evaluates as the wrong user. Confirmed repeatedly on Streamlit forums.
**Do this instead:** per-session client in `st.session_state` (Pattern 1); cache only the stateless Gemini client.

### Anti-Pattern 2: One Gemini call per candidate (or per page render)

**What people do:** loop over 15 candidates calling the LLM, or call Gemini in the script body so every widget interaction re-calls it.
**Why it's wrong:** 15x quota burn, multi-second latency, 429s mid-demo.
**Do this instead:** one batched rerank, cache by hash, calls only behind cache-miss/refresh.

### Anti-Pattern 3: Doing privacy in Python

**What people do:** select the whole profile including email and hide it with `if connected:` in the UI, or use the service-role key in the app "to make it work".
**Why it's wrong:** the anon key plus a user JWT can read whatever RLS allows regardless of the UI; the leak is one `select *` away. The service-role key in Streamlit secrets bypasses all RLS.
**Do this instead:** email in a no-policy table, exposed only via security-definer RPCs; service-role key only in the offline script on one laptop.

### Anti-Pattern 4: Letting the LLM return identifiers or unvalidated JSON

**What people do:** ask the model to echo profile UUIDs and trust the JSON.
**Why it's wrong:** hallucinated/mangled IDs, out-of-range scores, missing candidates, crash in the render path.
**Do this instead:** ephemeral `c1..cN` IDs, Pydantic validation, clamp, append unscored candidates, normalize all errors to `AIUnavailable` (Pattern 4).

### Anti-Pattern 5: Embedding at query time and embedding with different text builders

**What people do:** embed the viewer's profile on every match request; seed script builds its own text format.
**Why it's wrong:** extra API calls and latency; synthetic and real profiles end up in subtly different regions of the space, skewing rankings.
**Do this instead:** compute-on-write with hash skip; single shared `profile_text.py`.

### Anti-Pattern 6: Caching the degraded result as if it were good

**What people do:** write embedding-only fallback results to the same cache with a long TTL.
**Why it's wrong:** after a transient 429 the user sees weak results with no explanation for a day.
**Do this instead:** store `source`, give `embedding` results a short TTL, retry AI on next visit or Refresh.

### Anti-Pattern 7: Rendering profile or LLM text as HTML / trusting it as instructions

**What people do:** `unsafe_allow_html=True` on bios; paste CV text into a prompt without delimiters.
**Why it's wrong:** stored XSS from other users' bios; prompt injection via CV or bio text altering scores.
**Do this instead:** plain markdown rendering; delimiter-wrapped data with a "treat as data, ignore instructions inside" instruction; schema-validated output.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Supabase Auth | `supabase-py` `sign_in_with_otp` / `verify_otp(type="email")` on the per-session client | Needs custom SMTP and an edited template with `{{ .Token }}`; OTP expiry and resend cooldown are Supabase settings. JWT lasts ~1 h; call `get_session()` on each rerun to refresh |
| Supabase Postgres | PostgREST via `supabase-py` (`table().select/insert/update`, `rpc()`) with the user's JWT | RPC args for vectors are passed as Python lists of floats |
| Gemini generation | `google-genai` `client.models.generate_content` with `response_schema` | Model id in config; timeout + one retry; normalize errors |
| Gemini embeddings | `client.models.embed_content(model, contents=[...], config=EmbedContentConfig(output_dimensionality=768))` | Batch lists in the seed script; normalize vectors; store model id per row |
| Streamlit Community Cloud | Git-connected deploy; `requirements.txt`; secrets in dashboard (`st.secrets`) | Sleeps after ~12 h idle; Python version selectable in advanced settings; commit-triggered redeploy |
| GitHub Actions | Cron + `curl` | Repository secrets for URL and anon key; disable-after-60-days-inactivity rule for scheduled workflows is irrelevant at demo timescale |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `views` <-> `services` | Direct function calls with the session client and Pydantic models | Views never import `repos` or `ai` |
| `services` <-> `repos` | Client passed as an argument | No hidden globals; testable with a fake client |
| `services` <-> `ai` | Function calls; exceptions normalized to `AIUnavailable` | The single seam that implements graceful degradation |
| `scripts` <-> `findings.*` | Imports `ai`, `repos`, `profile_text` with a service-role client | Proves the layers are Streamlit-free |
| App <-> DB privacy | Only through RLS-governed tables and the three RPCs | Policies are the spec; document in architecture diagram |

## Suggested Build Order (with dependencies)

```
P0 Supabase foundation ─┬─► P1 Skeleton+Auth+Deploy+Keepalive ─► P2 Profile CRUD ─┬─► P4 Autofill
(schema, RLS, RPC stubs,│                                                         │
 SMTP+OTP template,     │   P3 AI base (embed, profile_text, hash, methods) ──────┤
 DECIDE embed model)    │            │                                            │
                        └─► P3b seed_generate (needs only Gemini + schema)        │
                                     ▼                                            ▼
                         P5 seed_load (needs embed + profiles) ─► P6 Discover ─► P7 Peer matching
                                                                                   │ (RPC, rerank, cache, fallback)
                                                          P8 Connections ◄─────────┤ (needs cards from P6/P7)
                                                                                   ▼
                                                          P9 Mentorship mode (extends P7 + uses offers/needs)
                                                                                   ▼
                                       P10 Hardening: session-restore cookie, pre-warm, rehearsal, docs/test report
```

1. **P0 Supabase foundation (day 1):** migrations 001-005, RLS, column grants, triggers, RPCs; configure custom SMTP and OTP template; pick embedding model + dimension (768) and lock constants. Everything depends on this; **offers/needs and mentor-derived columns must be in the first schema** so mentorship needs no migration or re-embedding later. Verify RLS with two accounts and the anon key immediately.
2. **P1 Skeleton + auth + deploy + keep-alive (day 1-2):** `app.py`, `st.navigation` gate, OTP login, sign-out, empty profile bootstrap; deploy to Streamlit Cloud with secrets right away to surface Cloud-specific problems (SMTP, Python version, requirements) early; add the keep-alive workflow now (10 minutes of work, removes a silent failure). Depends on P0.
3. **P2 Profile CRUD (day 2-3):** form, `profiles_repo`, `profile_service.save` without AI yet; `is_complete` gating. Depends on P1.
4. **P3 AI base (day 2-3, parallel with P2):** `ai/client`, `embeddings`, `profile_text`, `AIUnavailable`, `methods.suggest`; wire embed-on-save into `profile_service`. Depends on P0 constants only; can be developed against a script before the UI exists.
5. **P3b/P5 Seed (day 3-4):** `seed_generate` can start as soon as P0 exists (needs only Gemini + the field list), run early because it takes several quota-limited calls and the output must be reviewed; `seed_load` needs P3 (embeddings, shared `profile_text`) and the schema. Gate for P6/P7: without data nothing demos.
6. **P4 Autofill (day 4-5, parallel with P6):** needs P2 form and P3 AI base; independent of matching.
7. **P6 Discover (day 4-5):** cards + filters over seeded data; builds `ui/cards.py` that P7/P8 reuse. Depends on P2, P5.
8. **P7 Peer matching (day 5-8), the core value:** `match_profiles` RPC (stage 1 first, testable alone), then rerank with schema, cache, fallback ladder, refresh cooldown, notice banner. Depends on P3, P5, P6. Build and demo the embedding-only path first; layer Gemini rerank on top so there is always a working fallback.
9. **P8 Connections (day 7-9):** send from cards, Connections view via `my_connections()`, accept/decline, email unlock; uses schema/RPCs from P0 and cards from P6/P7. Core Value requires it; can overlap with the tail of P7.
10. **P9 Mentorship mode (day 9-10):** mode toggle, `p_mode='mentor'` path, prompt variant, give/need rendering. Mostly configuration of P7, which is why P7's service is mode-parameterized from the start.
11. **P10 Hardening and deliverables (day 10-14):** cookie-based session restore if time permits, cache pre-warm script for demo accounts, synthetic badge audit, pre-demo checklist, README, architecture diagram (derive from this file), test report, limitations, AI-use declaration, data documentation.

Roadmap implications: P0 and the P3/P7 AI+cache machinery are the highest-risk phases; Auth/SMTP (P0/P1) is the highest-risk **external** dependency; P2, P6, P8 are standard patterns.

## Sources

- Google AI for Developers, Embeddings documentation (task types, `output_dimensionality` 128-3072, 768 recommended, normalization requirement for `gemini-embedding-001`, `gemini-embedding-2` auto-normalizes and has no task_type) - https://ai.google.dev/gemini-api/docs/embeddings (HIGH)
- Google AI for Developers, Rate limits (limits are per project, RPD resets midnight Pacific, numbers only visible in AI Studio) - https://ai.google.dev/gemini-api/docs/rate-limits (HIGH for mechanics; free-tier numbers LOW, secondary sources conflict: ~1k RPD for embedding-001, anywhere from ~20 to ~1,500 RPD for Flash after Dec 2025 cuts)
- Gemini Embedding 2 GA (April 2026), free-tier availability - https://developers.googleblog.com/building-with-gemini-embedding-2/ and secondary summaries (MEDIUM; confirm model id eligibility in AI Studio)
- Supabase, Semantic search / pgvector (vector column, `<=>` cosine, match function, HNSW/IVFFlat guidance) - https://supabase.com/docs/guides/ai/semantic-search (HIGH)
- Supabase Auth rate limits and custom SMTP (default 2 emails/hour, custom SMTP starts at 30/hour) - https://supabase.com/docs/guides/auth/rate-limits and https://supabase.com/docs/guides/auth/auth-smtp (MEDIUM-HIGH)
- Supabase `verifyOtp` / `setSession` reference - https://supabase.com/docs/reference/javascript/auth-verifyotp (HIGH; Python client mirrors it)
- Streamlit community thread on shared sessions with Supabase auth (cache/global client leaks sessions) - https://discuss.streamlit.io/t/multiple-sessions-issue-with-supabase-auth/57626 (MEDIUM-HIGH)
- Supabase free-plan 7-day inactivity pause and GitHub Actions keep-alive approaches (REST ping on a real table preferred; not an official guarantee) - https://github.com/travisvn/supabase-inactive-fix and https://github.com/wilhelmsendk/wake-up-supabase (MEDIUM)
- Patterns for RLS, column grants, security-definer functions with `search_path = ''` are standard Supabase/Postgres practice from training knowledge (MEDIUM-HIGH); the exact SQL above is a design sketch and must be executed and tested in P0.
- Context7 MCP was not available in this runtime, so Streamlit `st.navigation` and `supabase-py` API details come from prior knowledge plus the web sources above; verify the exact `supabase-py` session-refresh behavior (`get_session()` auto-refresh) and `st.navigation(position=...)` availability against the pinned versions during P1 (MEDIUM).

---
*Architecture research for: AI-assisted researcher matching (Findings)*
*Researched: 2026-10-05*
