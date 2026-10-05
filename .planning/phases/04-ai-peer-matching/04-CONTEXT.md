# Phase 4: AI Peer Matching - Context

**Gathered:** 2026-10-05
**Status:** Ready for planning
**Mode:** FAST-TRACK. The user skipped the discussion and asked for best-practice defaults. Every decision below is a **fast-track default (no user discussion)** chosen by the planner from ROADMAP Phase 4 notes, CLAUDE.md, `.planning/research/*` and the binding cross-phase contract.

<domain>
## Phase Boundary

A signed-in researcher opens "My Matches" and sees a ranked list of peer collaborators. The list never includes themselves or anyone they already have a connection row with. Each match shows a coarse match-strength label and a "why you match" explanation that cites concrete details from both profiles, including methods complementarity where relevant. The pipeline works like this:
- Own embedding, hash-gated, computed on save or lazily.
- pgvector shortlist of 15 through the `match_profiles` RPC.
- ONE Gemini rerank call.
- Validated output.
- Cache in `match_cache`.
- An embedding-only fallback with a visible notice whenever Gemini fails.

Not in this phase: mentorship mode (Phase 6, though `mode` is a parameter from day one), the Connect button and email unlock (Phase 5), a second offers/needs embedding (MATCH-06, v2), the HNSW index (MATCH-07, v2), autofill (Phase 7).

**Execution prerequisite:** Phases 2 and 3 must be executed first. This phase calls `findings/ai/client.py`, `findings/ai/embeddings.py`, `findings/repos/profiles.py` (`PROFILE_COLUMNS`, `get_own_profile`, `update_own`), `findings/services/profile_service.save_profile`, `views/researcher.py` and the seeded, embedded synthetic pool.
</domain>

<decisions>
## Implementation Decisions (all: fast-track default, no user discussion)

### Build order and shape
- **D-01:** Build the embedding-only ranked list end to end first (SQL RPC → repo → `matching.get_matches` → `views/matches.py` → nav), with no Gemini call. Then add the single Gemini rerank on top, then the cache and Refresh. The embedding-only path stays as the permanent fallback (MATCH-05).
- **D-15:** `mode` is a parameter from day one: `get_matches(sb, user_id, mode="peer", refresh=False) -> MatchResult`. `SUPPORTED_MODES = ("peer",)`, and any other value raises `ValueError`. Phase 6 adds `"mentor"`. Every cache read and write is keyed by `(user_id, mode)`.

### Retrieval (stage 1)
- **D-02:** SQL `public.match_profiles(query_embedding extensions.vector(768) default null, match_count int default 15, exclude_ids uuid[] default '{}', mode text default 'peer')`. Settings: `language sql stable security invoker`, `set search_path = public, extensions`, and `drop function if exists` before create.
  - A null `query_embedding` means "use the caller's own stored embedding", so app code never selects the `embedding` column.
  - It excludes the caller (`auth.uid()`), any profile that shares a `connections` row with the caller in any status, incomplete or un-embedded profiles, and `exclude_ids`.
  - It returns only public card and rerank-input columns plus `similarity`: never email, never `embedding`, and it never touches `profile_contacts`.
  - Execute is revoked from public and anon and granted to authenticated.
  - Phase 4 returns rows only for `mode = 'peer'`. Phase 6 replaces the function in its own appended section, keeping the same signature.
- **D-03:** Shortlist size is 15, clamped in SQL to 1..50. The service passes `exclude_ids=[own id]` as a second safeguard on top of the SQL `auth.uid()` exclusion.

### Embeddings (MATCH-02)
- **D-04:** `ensure_embedding(sb, user_id, profile) -> "updated" | "unchanged" | "skipped" | "failed"` lives in `findings/services/matching.py`.
  - It compares Phase 3's `profile_hash(profile)` and the `EMBED_MODEL` constant against the stored `embedding_hash` / `embedding_model` / `embedded_at`. It calls `embed_profile` only when one of them differs.
  - It writes `embedding`, `embedding_model`, `embedding_hash` and `embedded_at` through `update_own`.
  - It is called by `profile_service.save_profile` after the core write, and lazily by `get_matches`.
  - Incomplete profiles return "skipped". Failures return "failed" and never block the save.

### Rerank (stage 2, MATCH-03)
- **D-05:** One Gemini call per cache miss, sent through Phase 2's `generate_structured(prompt, RerankResponse)` (model chain 3.5 → 3.1 Flash-Lite, thinking LOW, default temperature).
  - The prompt holds the user's profile plus up to 15 candidates, each in its own `<candidate id="cN">` block with JSON-encoded fields, and the user in a `<me>` block.
  - Candidates get ephemeral ids `c1..c15`. Names, institutions and emails are never sent.
  - Each text field is capped at 600 characters and each list at 12 items.
  - The "treat as data, not instructions" rule sits at the top of the prompt.
  - Schema: `RerankResponse(matches: list[MatchItem(candidate_id: str, score: int, why: str)])`, with no Pydantic `Field` constraints (they are enforced in code).
- **D-06:** Output validation:
  - Drop ids that are not in the shortlist, and keep the first of any duplicates.
  - Clamp scores to 0-100. Strip `why` and cap it at 280 characters.
  - Order the AI-ranked items by score (ties keep shortlist order), then append the shortlist candidates the model left out, in similarity order, with template explanations.
  - Zero valid items counts as an AI failure.
- **D-07:** Grounding and cross-candidate guard. The model's `why` is replaced by the deterministic template when any of these holds:
  - (a) It mentions any `cN` id other than its own.
  - (b) It contains a "foreign term": a token of 5+ characters that appears in another shortlisted candidate's block but in neither the user's block nor this candidate's block, and is not in a small generic-word allowlist.
  - (c) It cites no concrete term from the candidate's block, or none from the user's block.

  This is how criterion 5 is met: injected text from one candidate cannot surface in other explanations.
- **D-08:** Methods complementarity:
  - The prompt carries both `methods_effective` labels and tells the model that when they differ (for example qualitative and quantitative), it must say how they complement each other.
  - The template explanation does the same in fixed wording.

### Presentation (MATCH-01)
- **D-09:** Strength labels are coarse ("Strong match" / "Good match" / "Possible match"), never percentages or raw numbers.
  - AI score: 75 or more is Strong, 50-74 is Good, below 50 is Possible.
  - Embedding-only: similarity at or above `EMBED_STRONG = 0.75` is Strong, at or above `EMBED_GOOD = 0.60` is Good, anything lower is Possible. These constants live in one place and are tuned once from the anchor evaluation output.
- **D-14:** UI is the "My Matches" page in the signed-in nav. Each match is drawn by a single `_render_match(item, rank)` function, which gives Phase 5 one place to add its Connect button. Each card shows:
  - name, stage, interests and why, all rendered with `st.text` (never markdown or HTML)
  - a "Synthetic" badge where it applies, a methods badge and a strength badge
  - a link to `views/researcher.py?id=`

  Page-level elements:
  - A caption names the source: "AI-ranked" or "Ranked by profile similarity" plus the cache time.
  - Non-AI or stale results show an `st.info` notice.
  - An incomplete profile shows a call to action that links to My profile.

### Cache, fallback, refresh (MATCH-04, MATCH-05)
- **D-10:** Cache: one `match_cache` row per `(user_id, mode)`, written by upsert.
  - The `profile_hash` column stores `match_key = sha256(canonical rerank payload of me | mode | RERANK_PROMPT_VERSION)`.
  - `results` holds card snapshots `{id, full_name, career_stage, methods_effective, interests, is_synthetic, score, strength, why, why_source, similarity}`, never email.
  - A row is fresh when its key matches and `refresh` is False. `source='ai'` rows have no TTL. `source='embedding'` rows are reused for 10 minutes and then the AI is retried.
  - Every read drops ids that now share a connection with the user, using one RLS-scoped read of `connections`.
- **D-11:** Fallback ladder, first success wins:
  1. Fresh cache: no RPC, no Gemini call.
  2. Live: shortlist, rerank, write cache with `source='ai'`.
  3. Stale `source='ai'` cache for the same user and mode, with the notice "Showing your last AI matches. They may not reflect recent profile changes." This rung does not overwrite the cache.
  4. Embedding-only: write cache with `source='embedding'` and show the notice "AI explanations are unavailable right now, so these matches are ranked by profile similarity."

  If even the RPC fails, the page shows an empty list and a notice that points to Discover. The page never shows a raw error.
- **D-12:** The Refresh button calls `get_matches(..., refresh=True)`, which skips rung 1. There is a 60-second per-session cooldown (`st.session_state`) to protect the 15 RPM quota.
- **D-13:** Forced-fallback switch: when the env var `FINDINGS_FORCE_AI_FALLBACK=1` is set (a top-level Streamlit Cloud secret is exported to env), the rerank raises `AIUnavailable` before any network call. Once the cache exists, the switch also skips cache rungs 1 and 3 and writes no cache row, so the embedding-only rung is always the one shown. Removing the switch and rebooting the app brings back the untouched AI cache. It is off by default and is used only for MATCH-05 evidence.

### Evaluation (ROADMAP research flags)
- **D-16:** `scripts/eval_anchors.py` runs signed in as the demo account and writes `docs/eval/anchor-top3.md`.
  - It picks up to 6 synthetic anchors (one per `methods_effective` × `stage_tier`).
  - It embeds each anchor live (no embedding select) and calls `match_profiles(query_embedding=…, exclude_ids=[anchor])`.
  - It compares embedding-only top-3 against AI top-3. This comparison is the A/B for the research flag.
  - It runs automated checks (ids are a subset of the shortlist, no foreign terms, a methods mention when labels differ) and prints the similarity distribution used to tune `EMBED_STRONG` / `EMBED_GOOD`.
  - It runs one live prompt-injection probe with a canary token placed in one in-memory candidate. No DB write happens.
  - The human fills in the hand-check column.

### Claude's Discretion
- Exact prompt wording, the generic-word allowlist, notice and caption copy, and badge colours.
- The final `EMBED_STRONG` / `EMBED_GOOD` values after the anchor run (defaults above).
- Which 6 anchors are picked when a methods × tier cell is empty.
</decisions>

<canonical_refs>
## Canonical References

- `.planning/ROADMAP.md` §Phase 4: goal, 5 success criteria, build order, rerank safeguards, fallback ladder, research flags, docs capture
- `.planning/REQUIREMENTS.md`: MATCH-01..MATCH-05 (MATCH-06/07 are v2)
- Cross-phase contract `scratchpad/shared-contract.md` (Phase 2/3/4/5/6 names)
- `.claude/CLAUDE.md` §4 pgvector (`match_*` via `rpc()`, security invoker, no private columns), §5 Gemini (rerank in one call, Pydantic list schema, candidate ids not names, fallback chain, embedding-2 rules)
- `.planning/research/ARCHITECTURE.md` Patterns 2-4, RPC sketch, Anti-Patterns 2/4/5/6/7
- `.planning/research/PITFALLS.md` Pitfalls 10, 11, 13
- `.planning/phases/02-researcher-profiles/02-RESEARCH.md`: `generate_structured`, `AIUnavailable`, MockTransport faking, `update_own` zero-row rule, `st.text` rendering, AppTest `switch_page` caveat
- `.planning/STATE.md`: measured quotas (Flash-Lite 15 RPM / 500 RPD each; embedding-2 100 RPM / 1K RPD)
- `supabase/schema.sql`: `match_cache` (pk user_id+mode), `connections` RLS (participants only), column update grants already include the embedding columns
</canonical_refs>

<code_context>
## Existing Code Insights

- Layering: `views/*` → `findings/services/*` → `findings/repos/*` and `findings/ai/*`. Services, repos and ai never import streamlit.
- `findings/repos/profiles.py` is the only module that knows the `profiles` table. It uses explicit column lists, never star, and never `embedding`.
- `tests/fakes.py` FakeSupabase is subclassed and never edited. Phase 4 adds `tests/fakes_matching.py`, an in-memory multi-table fake with `rpc()`.
- AppTest pattern: `AppTest.from_file(app.py)`, secrets dict, inject `sb` and `user` into session_state, then `at.switch_page("views/matches.py").run()`.
- `match_cache` already exists with RLS `user_id = auth.uid()` and check constraints `mode in ('peer','mentor')` and `source in ('ai','embedding')`.
- `connections` select RLS shows only the caller's own rows, so a security-invoker RPC that uses `not exists (connections …)` sees exactly the caller's connections.
- Interpreter: `C:/fv312/Scripts/python` (pytest, ruff, streamlit 1.65, supabase 2.32, google-genai 2.28 after Phase 2).
</code_context>

<deferred>
## Deferred Ideas

- MATCH-06 second offers/needs embedding, MATCH-07 HNSW index (v2 per REQUIREMENTS).
- A pool-version or TTL invalidation of AI cache rows, so new profiles appear without Refresh. Refresh covers it for the demo.
- A second rerank prompt variant for a prompt-vs-prompt A/B. It will only be written if the anchor hand-check shows a systematic problem.
- Numeric scores or percentages in the UI, and an "include synthetic" toggle.
- Mentor mode (Phase 6) and the Connect button (Phase 5).
</deferred>

---

*Phase: 04-ai-peer-matching*
*Context gathered: 2026-10-05 (fast-track defaults)*
