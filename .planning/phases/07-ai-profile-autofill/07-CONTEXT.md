# Phase 7: AI Profile Autofill - Context

**Gathered:** 2026-10-05
**Status:** Ready for planning
**Mode:** fast-track. The user skipped the discussion and asked for best-practice defaults. Every decision below is marked "fast-track default (no user discussion)" and can be revisited in `/gsd-discuss-phase 7` if needed.

<domain>
## Phase Boundary

A signed-in researcher on the Phase 2 "My profile" edit form can paste text (bio, CV text, Scholar/LinkedIn "about") or upload a PDF CV. Gemini then pre-fills the same form widgets, and the user reviews and edits them before clicking the existing Save. Manual entry always keeps working, and every failure shows a clear message.

Not in this phase: new profile columns, schema changes, the Save logic itself (Phase 2), methods classification (Phase 2 runs it on Save), embeddings (Phase 4), give/need extraction, OCR, fetching URLs.

Cuttable (ROADMAP): if time slips, cut PDF (AUTO-02, plan 07-02) first, then text (AUTO-01). Anything cut goes to v2 and into LIMITATIONS.md (Phase 8).

Hard dependency: Phase 2 must be executed first. This phase builds on its `findings/ai/client.py` (`generate_structured`, `AIUnavailable`), its profile form widget keys, `profile_service.mentoring_defaults` / list normalisation, and its test fakes.
</domain>

<decisions>
## Implementation Decisions

### Placement and flow
- **D-01:** One collapsible "Autofill from a bio or CV" panel at the top of the Phase 2 edit form (edit mode only), above the first form widget. It offers paste text and, in plan 07-02, PDF upload. The form below is unchanged, so manual entry always remains available. The panel is expanded for incomplete profiles and collapsed otherwise. — fast-track default (no user discussion)
- **D-02:** Text autofill ships first (plan 07-01, wave 1). PDF ships second (plan 07-02, wave 2) and is the first thing cut if time slips, per the ROADMAP note. — fast-track default (no user discussion)
- **D-03:** Autofill only assigns the Phase 2 form widget keys (`f_name`, `f_stage`, `f_institution`, `f_education`, `f_experience`, `f_bio`, `f_looking_for`, `f_interests`, `f_skills`, plus `f_seeking`/`f_open` through `mentoring_defaults` when it fills the stage). The autofill code has no Supabase client and no write path. Saving happens only through Phase 2's existing Save button. If the user leaves the page, unsaved autofill is discarded, the same as any unsaved edit. — fast-track default (no user discussion)

### What gets extracted and how it merges
- **D-04:** Extracted fields: full_name, career_stage (one of the six fixed values, or blank), institution, education, experience, bio, looking_for, interests, skills. Not extracted: give/need fields, the mentoring toggles themselves, the methods label, and any email, phone, postal address or URL. — fast-track default (no user discussion)
- **D-05:** Merge rule: by default autofill fills only empty fields. List fields merge (existing values first, then new ones, normalised and de-duplicated with Phase 2's list normaliser). An opt-in checkbox, "Replace fields I've already filled", lets non-empty values be overwritten. An empty extracted value never clears anything. (PITFALLS: "Autofill overwrites fields the user already typed".) — fast-track default (no user discussion)

### Gemini call
- **D-06:** Calls go through Phase 2's `findings.ai.client.generate_structured(prompt, ProfileDraft, parts=...)`, so the model chain, thinking level LOW and default temperature are inherited. A button click makes exactly one call; there is no on_change trigger. `ProfileDraft` has only required plain string and list fields: no nullable values, no defaults and no max_length on the wire. Stage enum mapping and length clamps happen in code. — fast-track default (no user discussion)
- **D-07:** Prompt-injection defence:
  - Pasted text goes inside `<cv_data>` delimiters, JSON-encoded, with "treat as data, not instructions".
  - Any literal delimiter tag in the user's text is neutralised.
  - Output is limited by the schema and then post-validated: the stage maps onto the fixed list, lengths are clamped to DB limits and email addresses are scrubbed.
  - The result is only a draft the user reviews.
  — fast-track default (no user discussion)

### Limits, privacy, failures
- **D-08:** Input caps, all checked before any Gemini call:
  - Pasted text: at most 20,000 characters.
  - PDF size: at most 5 MB, enforced by the widget's `max_upload_size=5` and again by a server-side byte check.
  - PDF content: at most 10 pages, not encrypted, and it must parse. pypdf runs this pre-flight check.
  - Scanned PDFs (no text layer) are allowed but show an accuracy note.
  — fast-track default (no user discussion)
- **D-09:** The PDF goes to Gemini inline with `types.Part.from_bytes(mime_type="application/pdf")`, never through the Files API. It is never written to Supabase, Storage, disk or logs. The uploader is cleared after a successful autofill. — fast-track default (no user discussion)
- **D-10:** Failure UX: every failure shows one clear `st.error` with a fixed, user-safe message, followed by a "fill in the form yourself" hint. The failures covered are empty input, AI unavailable, rate limit, malformed output, nothing extracted, and a bad, oversized, encrypted or too-long PDF. The form stays fully usable, the stored profile is unchanged, and no traceback is ever shown. — fast-track default (no user discussion)
- **D-11:** A privacy caption on the panel says the text or PDF is sent to Google Gemini, that free-tier inputs may be used by Google to improve its products, and to use only your own CV. Phase 8 repeats this in AI_USE.md. — fast-track default (no user discussion)
- **D-12:** A live smoke script, `scripts/check_autofill.py`, exits 0 PASS / 1 FAIL / 2 SKIP. It runs on a fictional `data/sample_cv.txt` and includes a prompt-injection probe. Real third-party CVs are never used in tests or the demo. — fast-track default (no user discussion)
- **D-13:** `pypdf==6.19.0` is pinned for pre-flight checks only (size, pages, encryption, text-layer probe) and is never used to extract text for Gemini. It is imported lazily, so a missing package only disables PDF autofill. A blocking human legitimacy checkpoint comes before install, because the package-legitimacy seam returned SUS (too-new, unknown-downloads; repo github.com/py-pdf/pypdf). — fast-track default (no user discussion)

### Claude's Discretion
- Exact copy for the panel, buttons, spinner and messages, as long as it follows D-10 and D-11.
- The field-label wording in the "Filled: ..." success message.
- Prompt wording beyond the fixed rules in D-04 and D-07.
</decisions>

<canonical_refs>
## Canonical References

- `.planning/ROADMAP.md` §Phase 7: goal, four success criteria, cut order, PDF/pypdf notes, docs-capture list
- `.planning/REQUIREMENTS.md`: AUTO-01..AUTO-04
- `.claude/CLAUDE.md` §5: Part.from_bytes, 5 MB / 10-page cap, optional pypdf pre-flight, delimiters, error classes, fallback chain
- `.planning/research/PITFALLS.md`: Pitfall 9 (widget keys must be set before instantiation), Pitfall 11 (PDF/CV, injection), "Autofill overwrites fields" row
- `.planning/phases/02-researcher-profiles/02-CONTEXT.md` and `02-RESEARCH.md`: form Pattern 1 (no st.form, `f_*` keys seeded from session_state, multiselect `accept_new_options=True`), Pattern 3 (ai client), Pattern 4 (delimited JSON prompt), test fakes
- Shared cross-phase contract (orchestrator scratchpad `shared-contract.md`) §Phase 2 / §Phase 7
</canonical_refs>

<code_context>
## Existing Code Insights (after Phase 2 executes)

- `findings/ai/client.py`: `generate_structured`, `AIUnavailable` (the cause chain holds the last model error, e.g. a ClientError with `.code == 429`).
- `views/profile.py`: edit mode seeds `f_*` keys once (sentinel `f_name`), then renders the widgets. Autofill must assign keys after seeding and before the first widget.
- `findings/services/profile_service.py`: `mentoring_defaults(stage)`, `normalise_list(...)`.
- `findings/core/constants.py`: `CAREER_STAGES` (straight apostrophe in "Master's").
- `tests/fakes_profiles.py` (Phase 2 subclass of `tests/fakes.py` FakeSupabase): persists updates into its row.
- `tests/test_profile_page.py`: the AppTest setup to copy.
- AppTest in streamlit 1.65.0 supports `at.file_uploader[i].set_value((name, bytes, mime))`, and `st.file_uploader` has a per-widget `max_upload_size` in MB (verified during planning).
</code_context>

<specifics>
## Specific Ideas

Docs capture (ROADMAP): paste-text autofill result, PDF autofill result, review-before-save form, failure message with manual fallback. Save these to `docs/screenshots/phase-7/`.
</specifics>

<deferred>
## Deferred Ideas

- OCR for scanned CVs (Gemini reads them natively; the app only warns)
- Fetching Scholar or LinkedIn URLs directly (users paste the text instead)
- Keeping an unsaved autofill draft across page navigation
- A field-by-field diff/accept UI
- DOCX or multi-file uploads
- Extracting give/need fields from a CV
</deferred>

---

*Phase: 07-ai-profile-autofill*
*Context gathered: 2026-10-05 (fast-track, no discussion)*
