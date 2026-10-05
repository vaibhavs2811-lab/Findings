# Phase 4 Plan 1 Summary: Base AI Peer Matching Tracer & Embedding-on-Save

**Executed:** 2026-10-05
**Status:** Completed
**Requirements Delivered:** MATCH-01 (base tracer), MATCH-02

---

## What Changed

1. **Database Schema & Vector Shortlist RPC** ([supabase/schema.sql](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/supabase/schema.sql)):
   - Appended Phase 4 `match_profiles` SQL function (`security invoker`, `set search_path = public, extensions`).
   - Computes cosine similarity via `1 - (p.embedding <=> cv.vec)`.
   - Filters out caller (`auth.uid()`), any profile sharing a `connections` row with the caller in any status, uncompleted or un-embedded profiles, and `exclude_ids`.
   - Strict projection: returns public metadata and similarity; strictly never reads `profile_contacts` and never returns email or vector embedding columns.
   - Revoked execute from `public` and `anon`; granted exclusively to `authenticated`.

2. **Repository RPC Wrappers & Embedding Metadata** ([findings/repos/profiles.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/findings/repos/profiles.py)):
   - Implemented `match_profiles(sb, ...)` calling the database RPC.
   - Added `EMBED_META_COLUMNS = "embedding_hash, embedding_model, embedded_at"` and `get_embedding_meta(sb, user_id)`.

3. **Domain Matching Service** ([findings/services/matching.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/findings/services/matching.py)):
   - Implemented `get_matches(sb, user_id, mode="peer", refresh=False) -> MatchResult`.
   - Mode parameter validation: strictly allows `"peer"` (raises `ValueError` otherwise) preparing for Phase 6 `"mentor"` mode.
   - Coarse match-strength categorization: `strength_from_similarity` and `strength_from_score` ("Strong match" / "Good match" / "Possible match").
   - Deterministic grounding via `template_why(me, cand)`: cites up to 3 shared interests/skills and generates methods complementarity statements ("Their X methods complement your Y approach.").
   - `ensure_embedding(sb, user_id, profile)`: hash-gated embedding computation (`gemini-embedding-2`, 768 dims, L2 normalized) storing `embedding_hash`, `embedding_model`, and `embedded_at`.

4. **My Matches View & Navigation** ([views/matches.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/views/matches.py), [app.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/app.py)):
   - Registered `views/matches.py` under signed-in navigation right after Discover.
   - Built single hook `_render_match(item, rank)` providing isolated insertion point for Phase 5 Connect buttons.
   - Rendered all user content using `st.text` for complete script/HTML injection immunity.
   - Displayed coarse strength badges, methods orientation badges, and orange `Synthetic` labels.

5. **Profile Save Hook** ([findings/services/profile_service.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/findings/services/profile_service.py)):
   - Connected `ensure_embedding` at the conclusion of `save_profile`.
   - Non-blocking error containment: embedding failures never prevent core profile saves.

6. **Test Suites & Smoke Verification** ([tests/fakes_matching.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/tests/fakes_matching.py), [tests/test_matching.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/tests/test_matching.py), [tests/test_save_embedding.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/tests/test_save_embedding.py), [scripts/check_matching.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/scripts/check_matching.py)):
   - Added `FakeMatchingSupabase` supporting in-memory table mutations and `match_profiles` RPC emulation.
   - 12 unit and AppTest tests in `test_matching.py` verifying ranking, filtering, static schema guarantees, and UI rendering.
   - 6 unit tests in `test_save_embedding.py` verifying hash-gating, idempotency, and fallback behavior.
   - Built `scripts/check_matching.py` with M1-M7 verification assertions.
   - Total test suite: **161 passed in 36.74s**.

---

## Verification Results

- `python -m ruff check .`: All checks passed! (0 errors)
- `python scripts/check_matching.py`: PASS M1 (anon access safely blocked), SKIP M2-M7 (when unconfigured).
- `pytest tests/test_matching.py`: 12 passed in 2.45s.
- `pytest tests/test_save_embedding.py`: 6 passed in 1.05s.
- `pytest`: 161 passed in 36.74s.
