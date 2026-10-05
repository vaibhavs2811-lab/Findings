# Neural Map: Findings

High-level architecture and logic flow for the Findings web application ("Hinge for researchers").

```
                      +-------------------+
                      |      app.py       |
                      |  (Streamlit Entry)|
                      +---------+---------+
                                |
             +------------------+------------------+
             |                                     |
    +--------v--------+                   +--------v--------+
    | findings.core   |                   |     views/      |
    | - config.py     |                   | - login.py      |
    | - cookies.py    |                   | - home.py       |
    | - session.py    |                   | - profile.py    |
    | - constants.py  |                   | - discover.py   |
    +--------+--------+                   | - researcher.py |
             |                            | - account.py    |
             |                            +--------+--------+
             |                                     |
             |                            +--------v--------+
             |                            |      ui/        |
             |                            | - profile_view  |
             |                            | - cards.py      |
             |                            +--------+--------+
             |                                     |
             +------------------+------------------+
                                |
                   +------------v------------+
                   |   findings.services     |
                   |   - auth_service.py     |
                   |   - profile_service.py  |
                   |   - seed_data.py        |
                   +------+-------------+----+
                          |             |
           +--------------+             +--------------+
           |                                           |
+----------v----------+                     +----------v----------+
|    findings.ai      |                     |    findings.repos   |
| - client.py         |                     | - profiles.py       |
| - prompts.py        |                     | - seed_admin.py     |
| - methods.py        |                     +----------+----------+
| - seed_prompt.py    |                                |
| - embeddings.py     |                                |
+----------+----------+                                |
           |                                           |
           +--------------------+----------------------+
                                |
                                |
                   +------------v------------+
                   |    Supabase Backend     |
                   | - Auth (Email / Demo)   |
                   | - Database (Postgres)   |
                   | - pgvector (768 dims)   |
                   | - match_profiles RPC    |
                   +-------------------------+
```

## Logic Flows

1. **Authentication Flow**
   - User enters email in `views/login.py` (or clicks 1-click Demo Researcher).
   - `auth_service.py` triggers 6-digit email OTP via Supabase Auth (or demo password).
   - User verifies code; session saved in `session.py` and synced across browser refreshes via `cookies.py`.

2. **Session & Routing Flow**
   - `app.py` initializes config from `st.secrets`.
   - Checks session status:
     - Unauthenticated: Renders `views/login.py`.
     - Authenticated: Renders navigation bar (`Home`, `Discover`, `My Profile`, `Account`, hidden `Researcher`).

3. **Profile & Methods Orientation Flow (Phase 2 Delivered)**
   - Profile management handled via `findings/repos/profiles.py` repository with Supabase RLS.
   - Profile inputs: career stage (defaults mentoring toggles), research interests, skills, gives / needs.
   - On Save: `findings/services/profile_service.py` computes SHA256 input hash over research fields; if changed, calls `findings/ai/methods.py` via `findings/ai/client.py`.
   - Gemini Flash-Lite fallback chain classifies methods orientation (`qualitative`, `quantitative`, `mixed`) with <=140 char rationale.
   - Fail-open architecture: if AI unavailable, profile still saves with toast notification.
   - UI: `ui/profile_view.py` renders sanitized profile card with `methods_badge` (color, material icon, source tag `AI-suggested` vs `set by you`, and rationale text).
   - In view mode: `views/profile.py` provides `st.segmented_control` allowing instant user override (`auto`, `qualitative`, `quantitative`, `mixed`).

4. **Researcher Pool & Discover Flow (Phase 3 Delivered)**
   - **Synthetic Generation:** `findings/services/seed_data.py` (spec matrix across 6 career stages, 14 fields, 10 regions, 3 demo pairs) -> `findings/ai/seed_prompt.py` -> `scripts/seed_generate.py` generates 80 realistic synthetic researchers saved to `data/seed_profiles.json`.
   - **Embedding Pipeline:** `findings/ai/embeddings.py` formats profile text (`search_document: ` prefix, debiased to exclude name/institution/gender), embeds using `gemini-embedding-2` (768 dims, L2 normalized, SHA256 hashed) with deterministic offline fallback.
   - **Ingestion & Caching:** `scripts/seed_load.py` computes diversity metrics (mean cosine -0.0005, 0 duplicates > 0.90), caches vectors to `data/seed_embeddings.json`, and loads into `profiles` and `profile_contacts` via `findings/repos/seed_admin.py` using deterministic UUID5.
   - **Discover Grid:** `views/discover.py` queries `list_public` with indexed filters (`methods_effective`, `career_stage`, keyword interest search, completed only). Cards rendered via `ui/cards.py` with `Synthetic` badge, methods badge, top interests, and 1-click Skip (session-isolated).
   - **Public Profile View:** `views/researcher.py` displays full public details; strictly suppresses contact email (`show_email=False`).

5. **AI Peer Matching & Shortlisting Flow (Phase 4 Active)**
   - pgvector RPC `match_profiles(query_vector, mode, k=15)` finds cosine nearest neighbors excluding self and existing connections.
   - Gemini reranks candidates with grounded explanations citing mutual interests and methods complementarity.
   - Caching layer avoids re-computation until profile changes; graceful fallback to embedding-only rank if Gemini is unavailable.
