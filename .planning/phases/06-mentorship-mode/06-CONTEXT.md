# Phase 6: Mentorship Mode - Context

**Gathered:** 2026-10-05
**Status:** Ready for planning
**Mode:** fast-track. The user skipped discussion. Every decision below is a **fast-track default (no user discussion)** chosen from the roadmap notes, the research files and the shared cross-phase contract.

<domain>
## Phase Boundary

On My Matches, a signed-in researcher switches from Peers to Mentorship. If they are seeking a mentor, they get ranked mentors. If they are open to mentoring, they get ranked mentees. Ranking scores two-way give/need fit, and every match explains both sides of the exchange. This reuses the Phase 4 pipeline (`matching.get_matches`), the Phase 4 cache and fallback ladder, and the Phase 5 connect button.

Not in this phase:
- A second offers/needs embedding (MATCH-06, v2)
- Filters inside the mentorship view
- Changes to the profile form (Phase 2 owns the toggles and give/need fields)
- Changes to the seed data (Phase 3)

Execution prerequisite: Phases 2-5 are executed first. The Phase 4 matching pipeline is the base this phase extends.

</domain>

<decisions>
## Implementation Decisions (all: fast-track default, no user discussion)

### Modes and who sees what
- **D-01:** `get_matches(sb, user_id, mode, refresh)` accepts three modes:
  - `"peer"`
  - `"mentor"`: the viewer wants mentors
  - `"mentee"`: the viewer wants mentees

  Each mode gets its own `match_cache` row, so a PhD with both toggles keeps two caches. An appended, idempotent `ALTER` widens the `match_cache_mode_check` constraint to `('peer','mentor','mentee')`. — **Reversibility:** reversible (additive constraint change).
- **D-02:** The viewer's own toggles decide which views they can use:
  - `seeking_mentor` → "Find a mentor"
  - `open_to_mentoring` → "Find a mentee"
  - both → a second switch to pick between them
  - neither → an empty state that links to My profile

  The service enforces the same rule: it returns an empty result with a notice and makes no RPC call. That way the view and the service cannot disagree.
- **D-03:** Candidate eligibility is enforced in SQL.
  - **Mentor candidates:** `open_to_mentoring = true` and a strictly later career stage than the viewer.
  - **Mentee candidates:** `seeking_mentor = true` and a strictly earlier career stage.
  - **Stage order:** Undergrad 1 < Master's 2 < PhD 3 < Postdoc 4 = Industry researcher 4 < Faculty 5.
  - **Always excluded:** self, anyone already in a connection row with the viewer (any status), `exclude_ids`, incomplete profiles, and profiles with no embedding.
  - **Symmetry:** if B is one of A's mentors, then A is one of B's mentees.

### SQL
- **D-04:** A new appended "Phase 6" section of `supabase/schema.sql` holds:
  - the immutable function `public.stage_rank(text)`
  - the RPC `public.match_mentorship(match_count int, exclude_ids uuid[], mode text)`:
    - `security invoker`, so RLS still applies
    - reads the caller's own stored embedding on the server, so the client sends no vector
    - returns the same card columns as Phase 4's `match_profiles`, plus the four give/need arrays, both toggles and similarity
    - never returns email or embedding
    - execute is revoked from `public` and `anon` and granted to `authenticated`

  Phase 4's `match_profiles` is not edited.

### Ranking
- **D-05:** The RPC returns up to 40 eligible candidates. The service orders them by `0.5 × similarity + 0.5 × give/need fit` and sends the top 15 to the rerank.
- **D-06:** Give/need fit is measured in both directions:
  - **What the junior gets:** the mentor's `offers` against the junior's `want_to_learn`
  - **What the mentor gets:** the junior's `contributable_skills` against the mentor's `needs`

  Each direction is scored 0-1 by deterministic keyword overlap, and the fit is the mean of the two. In `"mentor"` mode the viewer is the junior. In `"mentee"` mode the viewer is the mentor.
- **D-07:** One Gemini rerank call per mentorship cache miss or Refresh. It goes through the same Phase 2 client call that the Phase 4 rerank uses.
  - **Prompt:** role framing, ephemeral ids `c1..cN`, and matching fields only (stage, interests, methods, skills, the four give/need lists). No names, institutions or UUIDs. All profile text sits inside the Phase 2 data delimiters ("treat as data, not instructions").
  - **Schema:** `MentorMatchItem(candidate_id, score, why, they_give_you, you_give_them)`.
  - **Validation:** the same rules as peers: unknown ids are dropped, scores are clamped to 0-100, and missing candidates are appended.

### Explanations and UI
- **D-08:** Every mentorship match has two one-sentence fields:
  - `they_give_you`: what the viewer gets
  - `you_give_them`: what the candidate gets

  Each one names specific listed items. When a direction has no real overlap, it says so plainly. The UI shows them in two columns with role-explicit labels:
  - `"mentor"` mode: "What you get from this mentor" / "What this mentor gets from you"
  - `"mentee"` mode: "What you get from this mentee" / "What this mentee gets from you"

  LLM and profile text are rendered only as plain text.
- **D-09:** Mentorship uses the same cache table and the same ladder as peers: fresh cache → live AI → stale cache with notice → embedding-only with notice.
  - **Mentorship cache hash:** sha256 of Phase 4's profile hash, the viewer's career stage, the viewer's four give/need lists and `MENTOR_PROMPT_VERSION`.
  - **Peer hash:** unchanged, byte for byte.
  - **Refresh:** one Refresh button per mode.
- **D-10:** The fallback works the same way as for peers (MENT-04). On any AI failure, mentorship items:
  - follow the blended order
  - show score `round(100 × blended)`, mapped through the Phase 4 strength label
  - show the same kind of notice as peers
  - get `they_give_you` / `you_give_them` from the overlapping give/need items. If nothing overlaps, they use the top two listed items or "has not listed … yet".

  Fallback results are cached with `source='embedding'`, the same as peers.
- **D-11:** A `st.segmented_control` "Peers / Mentorship" sits at the top of `views/matches.py` (key `match_view`, default Peers, and `None` is treated as Peers). Users with both toggles get a second control, "Find a mentor / Find a mentee" (key `mentor_direction`). Mentorship cards reuse the Phase 4 card (strength label, Synthetic label, why) and the Phase 5 `connect_button`, with keys that include the mode.
- **D-12:** If the viewer's own give/need fields for the active direction are both empty, the view shows an info hint that links to My profile. Results still show, so the user never hits a dead end.

### Verification
- **D-13:** A new `scripts/check_mentorship_live.py` reads the demo credentials from the gitignored `scripts/local.toml`. It checks:
  - the RPC eligibility rules in both directions
  - that anon cannot call the RPC
  - that no row has an email or embedding key
  - that `match_cache` accepts `'mentee'`
  - eligible counts for each direction

  An opt-in `--ai` run makes one rerank call per mode the demo account can use, checks that both exchange fields are filled, and checks that a second call is served from the cache.

### Claude's Discretion
- Exact UI copy apart from the D-08 labels, the stopword list, the `MENTOR_PROMPT_VERSION` strings, and the shape of the test fakes. Fakes subclass `tests/fakes.py` and never edit it.

</decisions>

<canonical_refs>
## Canonical References

- `.planning/ROADMAP.md` §Phase 6: goal, 4 success criteria, notes (`they_give_you` / `you_give_them`, cache keyed by user + mode), docs capture list
- `.planning/REQUIREMENTS.md` §Mentorship Mode: MENT-01..MENT-04
- Shared contract (scratchpad `shared-contract.md`): Phase 4 `get_matches` / `MatchResult(items, source, notice)` / `MatchItem(candidate_id, score, why)`, Phase 5 `connect_button`, Phase 2 `generate_structured` / `AIUnavailable` / prompt delimiters
- `supabase/schema.sql`: `profiles` (`seeking_mentor`, `open_to_mentoring`, `offers`, `needs`, `contributable_skills`, `want_to_learn`, `stage_tier`), `match_cache` (PK user_id + mode)
- `.planning/research/ARCHITECTURE.md` §Pattern 2, §Pattern 4, §Data Flow 3 (mentor-mode differences)
- `.planning/research/PITFALLS.md` Pitfall 14 (junior/mentor edge cases, empty states, incoherent give/need)
- `.planning/research/FEATURES.md`: symbiotic mentorship mode, demo script step 3
- `.planning/phases/02-researcher-profiles/02-CONTEXT.md` D-03 (give/need fields depend on the toggles; hidden fields are cleared)
- `.claude/CLAUDE.md` §5: rerank rules (one call, ids not names, drop unknown ids, fallback chain)

</canonical_refs>

<deferred>
## Deferred Ideas

- Separate offers/needs embeddings for better recall of complementary mentors (MATCH-06, v2)
- Methods or stage filters inside the mentorship view
- Mentor capacity or availability limits
- Remembering the last selected mode across sessions

</deferred>

---

*Phase: 06-mentorship-mode*
*Context gathered: 2026-10-05 (fast-track defaults)*
