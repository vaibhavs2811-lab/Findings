# Phase 3: Researcher Pool & Discover - Context

**Gathered:** 2026-10-05
**Status:** Ready for planning
**Mode:** fast-track. The user skipped the discussion and asked for best-practice defaults. Every decision below is a **fast-track default (no user discussion)**, taken from ROADMAP Phase 3 notes, `.planning/research/{ARCHITECTURE,PITFALLS,STACK}.md`, `.claude/CLAUDE.md` and the shared cross-phase contract.

<domain>
## Phase Boundary

A signed-in researcher opens **Discover** and browses 60-100 clearly labelled researchers as cards (name, career stage, methods badge, top interests, "Synthetic profile" label). They can filter by methods and career stage, search by interest keyword, combine those, Skip cards for the rest of the session, and open anyone's public profile page (no contact email). The pool is a committed, reproducible synthetic dataset: a one-off Gemini generator writes `data/seed_profiles.json`, and a local loader (secret key only on the laptop) inserts it with 768-dim embeddings, `is_synthetic = true` and example.org contacts.

Not in this phase: the Connect button on cards and profile pages (DISC-06, Phase 5), the pgvector `match_profiles` RPC and embeddings on profile save (Phase 4, which reuses this phase's `findings/ai/embeddings.py`), synthetic auto-accept (Phase 5), persistent skips (DISC-07, v2).

Cross-phase: Phase 2 must execute first. It supplies `findings/ai/client.py` (`generate_structured`, `AIUnavailable`), `findings/repos/profiles.py` (`PROFILE_COLUMNS`, `get_own_profile`, `update_own`), `findings/core/constants.py` (`CAREER_STAGES`, `METHODS_LABELS`), `ui/profile_view.py` (`render_profile`), the `methods_hash`/`methods_reason` columns, and `google-genai==2.28.0` in the interpreter.

</domain>

<decisions>
## Implementation Decisions

All entries: fast-track default (no user discussion).

### Seed pool (DATA-01)
- **D-01:** The pool has **80** synthetic profiles (inside the 60-100 range). They come from a deterministic spec matrix (`random.Random(42)`) over 14 research fields x 6 career stages x 3 methods labels x mentoring role x 10 name regions. Stage quotas for n=80 are Undergrad 10, Master's 14, PhD 18, Postdoc 14, Faculty 14, Industry researcher 10. Within each stage the methods labels rotate, so qual/quant/mixed are balanced. Mentoring: Undergrad and Master's are seeking. Postdoc, Faculty and Industry are open. PhD rotates through seeking / open / both. Every third Postdoc is both.
- **D-02:** Gemini writes only free text and lists (name, institution, education, experience, bio, looking_for, interests, skills, give/need lists). Career stage, methods label and mentoring toggles come from the spec, so code is the source of truth and the model is not. Give/need lists that the toggles do not allow are cleared, using the same rule as Phase 2 D-03.
- **D-03:** Generation calls Phase 2's `generate_structured` with **5 specs per call** (about 16 calls). Calls are spaced 4.5 s apart (Flash-Lite limit is 15 RPM) and capped at 30 per run. After every batch, an atomic UTF-8 checkpoint is written to `data/seed_profiles.json` with `ensure_ascii=False`. A re-run resumes from the missing `seed_id`s. The JSON is committed.
- **D-04:** All people and institutions are fictional. Generated text must not contain emails, URLs or phone numbers; any profile whose text contains `@` or `http` is dropped and regenerated. Contact emails are built in code as `<ascii-name-slug>.<seed_id>@example.org` and live only in the private contacts table.
- **D-05:** The spec builds in three deliberate demo pairs, recorded in the JSON `meta`. P1 is a qualitative PhD and a quantitative Postdoc working on the same public-health topic. P2 pairs a Faculty mentor and a Master's junior: the mentor's needs match the junior's contributable skills, and the mentor's offers match the junior's learning goals. P3 pairs a quantitative Industry researcher and a qualitative PhD in HCI. Phase 4 uses these pairs for its anchor evaluation and Phase 8 documents them.

### Loading and embeddings (DATA-02, DATA-03)
- **D-06:** The loader gives each seed a deterministic id, `uuid5(<Findings seed namespace>, seed_id)`. It upserts profiles with `is_synthetic = true`, `is_complete = true`, `methods_suggested` set from the spec, `methods_override = null` and a fixed `methods_reason` ("Synthetic profile: methods label set by the seed spec"), and it upserts contacts on conflict. Before writing, it checks that none of its ids belongs to a non-synthetic row. It never deletes anything, and it can be re-run.
- **D-07:** The Supabase secret key (`SUPABASE_SECRET_KEY`, which must start with `sb_secret_`) is read **only** from gitignored `scripts/local.toml` by `scripts/seed_load.py`. It is never printed, never put in Streamlit secrets, and never imported by app code. The app's config keeps rejecting any key that is not publishable.
- **D-08:** `findings/ai/embeddings.py` calls `gemini-embedding-2` with `output_dimensionality=768`, one string per call. It L2-normalises in code and asserts length 768. Every profile gets the same symmetric prefix: `task: sentence similarity | query: `. The embedded text covers career stage, methods, interests, skills, experience, looking_for, the four give/need lists and bio. It **excludes** name, institution, education (which can name institutions), email and any gender cue, to reduce prestige and identity bias.
- **D-09:** `profile_hash` is sha256 over model id, dimension, text version and the embedding text. The loader stores it in `embedding_hash`, together with `embedding_model` and `embedded_at`. A gitignored cache, `data/seed_embeddings.json` (keyed by seed_id and hash), means a reload costs zero Gemini calls. Embedding calls are spaced 1 s apart (embedding limits: 100 RPM / 30K TPM).
- **D-10:** Diversity check: after embedding, the loader prints mean and max pairwise cosine, the mean nearest-neighbour cosine, near-duplicate pairs (cosine >= 0.95), and counts by stage, methods, field and mentoring role. A mean above 0.8 prints a WARNING, and the human checkpoint decides whether to regenerate. It does not hard-fail, because a shared text template raises the baseline similarity.

### Discover and profile page (DISC-01..05, PROF-07, DATA-03)
- **D-11:** Discover lists complete profiles, real researchers first and then synthetic ones, alphabetical within each group. It excludes the viewer and skipped ids and shows everything on one page (no pagination) under a "Showing N researchers" caption. Cards sit in a 3-column grid of bordered containers. Each card shows the name, a stage badge, a methods badge ("Methods not set" when null), a mentoring-role caption, the top 3 interests, the Synthetic badge, a "View profile" link and a Skip button.
- **D-12:** Filters: methods as multi-select `st.pills`, career stage as `st.multiselect` over the six stages, and an interest keyword `st.text_input` (case-insensitive substring match against each interest). Filters combine with AND, and an empty filter adds no constraint. Methods and stage filters run in PostgREST as `in` filters on the indexed columns. The keyword filter and exclusions run in Python after the fetch, because a substring match inside an array cannot be expressed without a schema change.
- **D-13:** Skip appends the id to `st.session_state["skipped_ids"]`, tagged with `skipped_owner = user id` so a different sign-in in the same browser session starts clean. A skipped card stays hidden for the rest of the session, across page switches. A "Show skipped (N)" button restores the skipped cards.
- **D-14:** The public profile page `views/researcher.py` is registered with `st.Page(..., visibility="hidden")` and opened with `st.page_link(..., query_params={"id": ...})`. The `id` is parsed as a UUID before any query, and an invalid or unknown id shows "not found". The page reuses Phase 2's `render_profile(profile)` with the email flag left at its default (off), adds the Synthetic badge, and never reads the contacts table or calls the contact-email RPC.
- **D-15:** Repos select explicit columns. `CARD_COLUMNS` and `PUBLIC_PROFILE_COLUMNS` never include `*`, the vector column, the hash/model bookkeeping columns or any email. User-written text is rendered with `st.text`. Badge markdown is built only from whitelisted enum values (stage, methods, synthetic), and unsafe HTML is never enabled.
- **D-16:** The synthetic label is one helper in `ui/cards.py`: `synthetic_badge(profile)` renders an orange "Synthetic profile" badge, and the card's badge line uses the same text. Discover also shows a caption explaining that synthetic profiles are AI-generated examples. Later phases (matches, connections) reuse `synthetic_badge`.
- **D-17:** Phase 3 makes **no schema change** and has no SQL Editor step. The existing RLS select policy (`is_complete or own row`) already lets signed-in users read complete profiles, and the loader's service-role writes bypass RLS by design.

### Claude's Discretion
- Exact field list, region list and the wording of the generation prompt, within D-01..D-05.
- Card copy, badge colours and icons, and the empty-state wording.
- Whether near-duplicate seeds found by D-10 are regenerated. This is decided at the loader checkpoint.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and requirements
- `.planning/ROADMAP.md` §Phase 3: goal, five success criteria, notes (shared builder, diversity, quota, fallback demo), docs-capture list
- `.planning/REQUIREMENTS.md` §Discover, §Seed Data, §Profiles (PROF-07)
- Shared cross-phase contract (orchestrator scratchpad `shared-contract.md`): Phase 3 artifact names and signatures

### Stack and AI usage
- `.claude/CLAUDE.md` §4 pgvector (768 dims, embedding_model/embedded_at), §5 Gemini (embedding-2 task prefixes, one text per call, thinking level, error classes)
- `.planning/research/PITFALLS.md` Pitfall 6 (secret key), 7 (quota), 8 (mixed embedding models), 12 (seeding), 13 (bias: exclude name/institution)
- `.planning/research/ARCHITECTURE.md` Pattern 3 (compute-on-write embeddings with hash), seeding flow
- `.planning/STATE.md` §Blockers: measured quotas (Flash-Lite 15 RPM / 500 RPD each; embedding-2 100 RPM / 30K TPM / 1K RPD)

### Existing foundation
- `supabase/schema.sql`: profiles columns, `profiles_select` policy, indexes on `methods_effective` and `career_stage`, profile_contacts with privileges revoked
- `.planning/phases/02-researcher-profiles/02-CONTEXT.md` and `02-RESEARCH.md`: `render_profile`, `generate_structured`, AppTest patterns (badge renders as markdown, `st.text` for user text)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `findings/repos/profiles.py`: explicit-column pattern, `res.data or []` idiom. Phase 3 appends `list_public` / `get_public` and leaves Phase 2 functions alone.
- `findings/core/config.py`: `load_local_settings()` gives the Supabase URL for scripts.
- `scripts/check_live.py`: `report()`, PASS/FAIL lines, exit 0/1/2 and demo credentials from `scripts/local.toml`. `scripts/check_discover.py` copies this shape.
- `tests/fakes.py`: `FakeSupabase` (auth fake) is subclassed and never edited.
- Verified in Streamlit 1.65.0 (scratch prototype, this session): `st.Page(visibility="hidden")` plus `st.page_link(..., query_params=...)` works. AppTest supports `at.query_params[...]`, `at.switch_page(...)`, `at.pills[0].set_value([...])`, and a Skip `on_click` callback that persists in `session_state`.
- Verified postgrest-py 2.32: `.in_("career_stage", ["Industry researcher", "Master's"])` encodes as `in.(Industry researcher,Master's)`, and `upsert(..., on_conflict=..., returning=ReturnMethod.minimal)` exists.

### Established Patterns
- `views -> services -> repos/ai`. Repos and ai never import streamlit, and `ui/` is imported only by views.
- Interpreter for every verify command: `C:/fv312/Scripts/python`, run from the repo root.

### Integration Points
- `app.py`: the signed-in page list gains Discover (visible) and Researcher (hidden).
- Phase 4 imports `embed_profile`, `profile_embedding_text` and `profile_hash`. Phase 5 adds its connect button to `views/discover.py` cards and `views/researcher.py`.

</code_context>

<specifics>
## Specific Ideas

- Docs capture for `docs/screenshots/phase-3/`: Discover grid with Synthetic labels, each filter applied, keyword search, Skip, profile page with no email, and the loader's diversity stats output.

</specifics>

<deferred>
## Deferred Ideas

- Persistent skips across sessions (DISC-07, v2)
- Connect from card or profile page (DISC-06, Phase 5)
- HNSW index (MATCH-07, v2). With about 100 rows, an exact scan is enough.
- A seeded pending request from a synthetic profile to the demo account (REL-02, v2)
- Pagination or infinite scroll on Discover

</deferred>

---

*Phase: 03-researcher-pool-discover*
*Context gathered: 2026-10-05 (fast-track defaults)*
