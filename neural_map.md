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

5. **AI Peer Matching & Reranking Flow (Phase 4 Delivered)**
   - **Shortlisting & RPC:** `match_profiles` server-side pgvector RPC (`security invoker`) retrieves cosine nearest neighbors in `profiles.embedding` (768-dim) excluding self and active/pending connections from `connections`.
   - **Embedding Synchronization:** `findings/services/profile_service.py` hooks `ensure_embedding` on save. If research profile hash changes, generates new normalized embedding via `gemini-embedding-2` without exposing private columns to Python.
   - **Structured Gemini Reranker:** `findings/ai/rerank.py` maps candidates to privacy-safe ephemeral IDs `c1..cN` (suppressing names, emails, institutions). Single structured LLM call scores candidates (0-100) and produces concise explanations (<280 chars) highlighting shared interests and methods complementarity.
   - **Grounding & Cross-Candidate Leakage Guard:** `validate_why` checks token grounding and blocks cross-candidate foreign terms of >=5 chars not present in either profile. Omitted candidates are safely appended.
   - **4-Rung Fallback Ladder:**
     1. Fresh cache: `match_cache` keyed by `(user_id, mode)` with sha256 profile hash (`source='ai'` no TTL; `source='embedding'` 10 min TTL).
     2. Live AI rerank: updates cache on success.
     3. Stale AI cache: reuses prior AI matches if live AI fails, with user notification.
     4. Embedding-only fallback: falls back to raw vector similarity order with template explanations and non-blocking warning notice.
   - **UI & Controls:** `views/matches.py` renders candidate cards via `ui/cards.py`, showing match strength badges (`Strong match`, `Good match`, `Possible match`), methods badges, and `Refresh matches` with a 60-second session cooldown.
   - **Evaluation & Verification:** `scripts/eval_anchors.py` evaluates 6 synthetic anchors across `methods_effective` × `stage_tier`, confirming prompt injection resistance (canary token probe) and similarity threshold alignment (`docs/eval/anchor-top3.md`).

6. **Connections & Email Unlock Flow (Phase 5 Delivered)**
   - **Connection Actions & Note Dialog:** `ui/connect_button.py` provides modal request dialog (`@st.dialog`) with 500-char note input and live status chips (`Request sent`, `Connected`, `Not available`). Embedded on researcher profile view (`views/researcher.py`), Discover cards (`views/discover.py`, `ui/cards.py`), and My Matches entries (`views/matches.py`).
   - **Inline Reverse Request Acceptance (D-07):** If a recipient researcher views someone who already requested to connect, the button becomes `"Accept their request"` (primary) and accepts inline without navigating away.
   - **Incomplete Profile Guard (D-14):** Users with incomplete profiles (`is_complete = False`) are blocked from sending connection requests with a friendly prompt.
   - **Dynamic Match Filtering (D-12):** My Matches filters out candidates with any existing connection (`sent`, `received`, `connected`, `declined`) on render, ensuring cached match results never show existing connections.
   - **Database Gating & Privacy:**
     - Insert permissions restricted strictly to `(requester_id, recipient_id, note)` on `public.connections`.
     - `auto_accept_synthetic` trigger: security-definer trigger automatically marks connections to synthetic researchers as `accepted` on insert.
     - `my_connections()` security-definer RPC: retrieves user connections (`sent`, `received`, `accepted`), where `other_email` is revealed strictly through `get_contact_email(other_id)` only after mutual acceptance.
   - **Connections Management View:** `views/connections.py` renders tabbed view (`Received`, `Sent`, `Connected`). Unlocks and displays mutual contact email via `st.code` without HTML injection.
   - **Reset & Verification:** `scripts/reset_connections.py` resets demo and probe connection rows; `scripts/check_live.py` implements live probes C0-C14.

7. **Mentorship Matching Mode (Phase 6 Next)**
   - Extends matching mode to `mentor` using give/need exchange scoring, mentorship explanations, and reciprocal offer/needs fit.


