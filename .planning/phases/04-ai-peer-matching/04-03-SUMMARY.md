# Phase 4 Plan 3 Summary: Match Caching, Connections Invalidation, 4-Rung Fallback Ladder & Anchor Evaluation

**Executed:** 2026-10-05
**Status:** Completed
**Requirements Delivered:** MATCH-01, MATCH-04, MATCH-05 (Phase 4 100% complete)

---

## What Changed

1. **Matches Repository & Match Cache Layer** ([findings/repos/matches.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/findings/repos/matches.py)):
   - `compute_match_key`: computes sha256 hash of canonical sanitized profile, mode, and prompt version `RERANK_PROMPT_VERSION`. Ignores non-matching fields (e.g. name, institution) while immediately invalidating when research topics, methods, or skills change.
   - `get_cached_matches`: fetches existing cache row by `(user_id, mode)`.
   - `upsert_cached_matches`: writes or updates cache with source (`ai` or `embedding`), payload, and timestamp.
   - `get_connected_profile_ids`: queries active/pending connections where user is requester or recipient, enabling cache-level and live-level exclusion.

2. **Complete 4-Rung Fallback Ladder** ([findings/services/matching.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/findings/services/matching.py)):
   - **Rung 1 (Fresh Cache):** Checks `match_cache` if not `refresh` and not forced fallback. If `source='ai'` matches hash, returns cached matches without DB RPC or Gemini call. If `source='embedding'`, reuses for up to 10 minutes (`EMBEDDING_CACHE_TTL_SECONDS = 600`).
   - **Rung 2 (Live AI):** Invokes `match_profiles` RPC, passes shortlist to `rerank.rerank_candidates`, and caches result with `source='ai'`.
   - **Rung 3 (Stale AI Fallback):** If live AI fails and prior `ai` cache exists, returns stale matches with notice: *"Showing your last AI matches. They may not reflect recent profile changes."* (does not overwrite cache).
   - **Rung 4 (Embedding-Only Fallback):** If no AI cache exists, computes template explanations, saves with `source='embedding'`, and shows notice: *"AI explanations are unavailable right now, so these matches are ranked by profile similarity."*
   - Filter guard: drops any candidates that currently share a connection with user across all rungs.
   - Forced-fallback switch: respects `FINDINGS_FORCE_AI_FALLBACK=1` per D-13, skipping cache rungs 1 and 3 and writing no cache row.

3. **My Matches View & Refresh Cooldown** ([views/matches.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/views/matches.py)):
   - Added `Refresh matches` button with `_on_refresh_click`.
   - 60-second per-session cooldown enforced in `st.session_state` (`matches_last_refreshed`), displaying toast when clicked within cooldown window.
   - Cache indicator: appends `(cached)` to the header caption (`AI-ranked (cached)` or `Ranked by profile similarity (cached)`).

4. **Anchor Evaluation Report** ([scripts/eval_anchors.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/scripts/eval_anchors.py), [docs/eval/anchor-top3.md](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/docs/eval/anchor-top3.md)):
   - Evaluates 6 synthetic anchors spanning `methods_effective` ('qualitative', 'quantitative', 'mixed') × `stage_tier` ('junior', 'senior').
   - Compares top-3 embedding-only vs AI reranking.
   - Automated checks: verifies candidates are valid shortlist subsets and that methods differences are cited in explanations.
   - Generates similarity distribution stats (min=0.019, p50=0.048, p75=0.061, max=0.108) validating threshold boundaries.
   - Runs prompt injection canary probe (`CANARY_INJECT_X98765`), confirming that adversarial user bio instructions are neutralized and zero tokens leak.

5. **Test Suite** ([tests/test_matches_cache.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/tests/test_matches_cache.py)):
   - 8 unit and AppTest tests covering:
     - Match key calculation sensitivity.
     - Fresh AI cache hit (no RPC, no AI call, `from_cache=True`).
     - Invalidation on profile change.
     - Connections exclusion on cached and live reads.
     - Embedding cache 10-minute TTL expiry.
     - Stale AI cache fallback on live AI failure.
     - Forced fallback env switch (`FINDINGS_FORCE_AI_FALLBACK`).
     - AppTest verifying Refresh button, cooldown toast, and rerun handling.

---

## Verification Results

- `python -m ruff check .`: All checks passed! (0 errors)
- `python scripts/eval_anchors.py`: Generated [docs/eval/anchor-top3.md](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/docs/eval/anchor-top3.md) with 6/6 anchor passes and canary probe pass.
- `pytest tests/test_matches_cache.py`: 8 passed in 2.51s.
- `pytest`: **178 passed in 43.03s** (0 failures).
