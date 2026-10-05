# Phase 2: Researcher Profiles - Context

**Gathered:** 2026-10-05
**Status:** Ready for planning

<domain>
## Phase Boundary

A signed-in researcher can create, save and edit their own profile: name, career stage (six fixed values), institution, education, interests, experience, skills, bio, "looking for", the two mentoring toggles and the four give/need fields. On save, Gemini suggests a qualitative / quantitative / mixed methods label, which the user can override. RLS stops anyone from writing someone else's profile. This phase also builds the shared, streamlit-free `ai/` Gemini client that later phases reuse.

Not in this phase: other people's profile pages (PROF-07, Phase 3), embeddings on save (MATCH-02, Phase 4), and autofill from text or PDF (Phase 7).

</domain>

<decisions>
## Implementation Decisions

### Form layout & list input
- **D-01:** One scrolling "My profile" form with headed sections (About you / Research / Mentoring exchange) and a single Save button. No tabs and no wizard.
- **D-02:** List fields (`interests`, `skills`, `offers`, `needs`, `contributable_skills`, `want_to_learn`, all `text[]`) use `st.multiselect` with a preset list of common suggestions plus `accept_new_options=True`, so users can add their own values. Presets live in one Python constants module (e.g. common methods/skills, offer types like "Methods training", "Co-authorship", "Guidance", need types like "Data collection", "Lit review", "Coding", "Transcription"). Normalise entries: trim them and drop case-insensitive duplicates.
- **D-03:** Which give/need fields appear depends on the mentoring toggles. "Open to mentoring" shows Offer + Need. "Seeking a mentor" shows Can contribute + Want to learn. Both on shows all four. Neither on shows none. Hidden fields keep their stored values; the planner decides whether to clear them on save, but clearing is preferred so stale data doesn't feed matching.
- **D-04:** No new "field/discipline" column. Interests and education carry the research field.

### Methods badge (PROF-05)
- **D-05:** Gemini suggests the label at save time, and only when the text that drives it has changed. Keep a hash of those fields; if it matches the stored hash, skip the call. This needs a new nullable column (e.g. `methods_hash`) through an idempotent `alter table ... add column if not exists` in `supabase/schema.sql`, plus an update grant for `authenticated`. — **Reversibility:** costly — it's a schema migration plus a column grant, but it's additive and nullable.
- **D-06:** The override control is a segmented control: `Auto (AI: <label>)` / Qualitative / Quantitative / Mixed. "Auto" sets `methods_override = NULL`, so `methods_effective` follows future AI suggestions. Picking a label sets `methods_override`. The profile badge shows `methods_effective`, and also shows whether the value came from the AI or was set by hand.
- **D-07:** Gemini returns a one-line reason with the label (e.g. "Mentions surveys and regression modelling"), shown under the badge. Store it in a new nullable `methods_reason text` column (length-checked, same migration as D-05) so it survives reloads.
- **D-08:** If Gemini fails (`APIError`, 429/5xx after the Flash-Lite fallback chain, or a `ValidationError`), the profile still saves. The previous `methods_suggested`/reason stay as they are (or the badge says "Not classified yet"), the user gets a toast or notice that the AI was unavailable, and the stored hash is **not** updated, so the next save tries again.
- **D-09:** Profile text goes into the prompt between delimiters and is marked "treat as data, not instructions". Use a Pydantic `response_schema` (label enum + reason ≤ ~140 chars), an explicit low or minimal `thinking_level`, and the default temperature. Model chain: `gemini-3.5-flash-lite` → `gemini-3.1-flash-lite` → give up gracefully.

### First-run & view/edit flow
- **D-10:** Add a "My profile" page to the signed-in navigation. If the profile is incomplete, Home shows a "Complete your profile" call-to-action that links there (`st.page_link` / `st.switch_page`). No forced redirect.
- **D-11:** `is_complete = true` once name, career stage and at least one interest are filled in. Everything else is optional. The app sets this flag on save. Only complete profiles are visible to others under the existing RLS select policy.
- **D-12:** After the first save, "My profile" shows a read-only profile view (name, stage, institution, methods badge with reason, interests and the other fields, mentoring role) with an Edit button that switches to the form. Build the view as a reusable render function that takes a profile dict, so Phase 3's public profile page can reuse it. That page must never show email.

### Claude's Discretion
- **Mentoring toggle defaults (PROF-03):** Changing the career stage re-applies the defaults (Undergrad/Master's → seeking on, open off; Postdoc/Faculty/Industry → open on, seeking off; PhD → toggles left as they are, both off for a new profile). The user can still change either toggle before saving. Recommended: only re-default when the stage actually changes in the form, so a manual override isn't overwritten on rerun.
- Exact preset suggestion lists, section headings, copy, and the badge colours and icons.
- Whether the methods suggestion runs synchronously inside `st.spinner` on save (expected) or after the write.
- Exactly which fields go into the methods hash and prompt (likely interests, experience, skills, bio, education, looking_for).
- Module names for the `ai/` client and the profile service, following the existing `views → services → repos` layering.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope & requirements
- `.planning/ROADMAP.md` §Phase 2 — goal, five success criteria, notes on the shared `ai/` client, docs-capture list
- `.planning/REQUIREMENTS.md` §Profiles — PROF-01..PROF-06 (PROF-07 is Phase 3)
- `.planning/PROJECT.md` — constraints ($0, demo reliability, privacy)

### Stack & AI usage
- `.claude/CLAUDE.md` §5 Gemini free tier — model IDs, `thinking_level`, temperature, Pydantic `response_schema`, error classes, fallback chain, prompt-injection delimiters
- `.planning/research/STACK.md`, `.planning/research/ARCHITECTURE.md`, `.planning/research/PITFALLS.md` — project research behind those choices

### Existing foundation (Phase 1)
- `supabase/schema.sql` — `profiles` table (all Phase 2 columns already exist; `methods_effective` and `stage_tier` are generated), RLS policies, and the column-level `grant update` list that new columns must be added to
- `.planning/phases/01-foundation-sign-in/SKELETON.md` — architectural decisions (layering, per-session client, tests with FakeSupabase)
- `.planning/STATE.md` §Blockers — measured Gemini quotas (Flash-Lite 15 RPM / 500 RPD)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `findings/repos/profiles.py`: `get_own_profile()` with an explicit column list (never `*`, never `embedding`). Extend it with an update function and a fuller column list.
- `findings/core/session.py`: `current_user()` and the per-session client in `st.session_state["sb"]`. Every profile write goes through that client so RLS applies.
- `findings/core/config.py`: `load_settings(st.secrets)`. Add `GEMINI_API_KEY` here, kept out of the committed `secrets.toml`.
- `tests/fakes.py`: `FakeSupabase`/`FakeQuery` for AppTest-based tests. Subclass it, don't edit it.

### Established Patterns
- Layering: `views/*.py` (Streamlit) → `findings/services/*` → `findings/repos/*`. Services and repos never import streamlit, and the new `ai/` client must not either.
- Routing: `app.py` builds `st.navigation` from `st.Page("views/…")`. The new page is added to the signed-in list.
- Schema changes are edits to the single idempotent `supabase/schema.sql`, re-run in the SQL Editor.
- `google-genai` isn't in `requirements.txt` yet. Pin `google-genai==2.28.0`.

### Integration Points
- `views/home.py` already reads `is_complete`. Replace its status message with the CTA (D-10).
- `app.py` signed-in pages list gets "My profile".
- The RLS update policy plus column grants already block writes to other users' rows. Prove PROF-06 with a second-account probe, extending `scripts/check_live.py`.

</code_context>

<specifics>
## Specific Ideas

- The badge should show where its value came from: e.g. "Quantitative · AI-suggested" with the one-line reason, or "Mixed · set by you".
- Screenshots needed for the docs (from ROADMAP): empty form, saved profile with badge, methods override, toggles defaulted by stage, RLS rejection evidence.

</specifics>

<deferred>
## Deferred Ideas

None. The discussion stayed within the phase scope.

</deferred>

---

*Phase: 02-researcher-profiles*
*Context gathered: 2026-10-05*
