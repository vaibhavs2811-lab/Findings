# Phase 3 Plan 1 Summary: Discover UI & Public Profile View

**Executed:** 2026-10-05
**Status:** Completed
**Requirements Delivered:** DISC-01, DISC-02, DISC-03, DISC-04, DISC-05, PROF-07, DATA-03 (UI)

---

## What Changed

1. **Repository Queries & Column Projections** ([findings/repos/profiles.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/findings/repos/profiles.py)):
   - Defined explicit column lists: `CARD_COLUMNS` and `PUBLIC_PROFILE_COLUMNS`, strictly omitting embeddings, embedding hashes, and emails.
   - Added `list_public`: queries complete profiles ordered by real researchers first (`is_synthetic` ascending), then alphabetically by name. Applies PostgREST `.in_()` filters for methods and career stage, collapses whitespace for case-insensitive Python keyword filtering over interests, and excludes caller ID and skipped IDs.
   - Added `get_public`: parses `profile_id` as UUID; gracefully returns `None` for invalid UUID strings with zero queries, projecting valid rows to `PUBLIC_PROFILE_COLUMNS`.

2. **Card & Badge UI Components** ([ui/cards.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/ui/cards.py)):
   - `badge_markdown`: constructs safe markdown line using only whitelisted enum values (`:gray-badge[...]`, `:blue-badge[...]`, and `:orange-badge[:material/smart_toy: Synthetic profile]`).
   - `synthetic_badge`: renders standalone orange badge with smart_toy icon for synthetic researchers.
   - `render_card`: renders bordered card with name, badges, mentoring role caption, top 3 interests, "View profile" link, and "Skip" action button. Safe rendering via `st.text` for all user strings.

3. **Discover View** ([views/discover.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/views/discover.py)):
   - Rendered 3-column filter row with `st.pills` for methods orientation, `st.multiselect` for career stages, and `st.text_input` for keyword search.
   - Implemented session-scoped Skip state: `skipped_owner` tagged to active user; restores cleanly via "Show skipped (N)".
   - 3-column responsive card grid under "Showing N researchers" counter.

4. **Public Researcher Profile View** ([views/researcher.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/views/researcher.py)):
   - Hidden page routed via `?id=<uuid>` with back-link to Discover.
   - Displays synthetic badge and read-only profile via `render_profile` with `show_email=False`. Never queries `profile_contacts` or `get_contact_email`.

5. **Navigation & App Integration** ([app.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/app.py)):
   - Added visible `views/discover.py` with `:material/travel_explore:` icon.
   - Added hidden `views/researcher.py` for query param navigation.

6. **Test Suite** ([tests/test_discover.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/tests/test_discover.py)):
   - 19 new unit and AppTests verifying column security, query filtering, badge safety, synthetic labelling, keyword and filter combinations, skip isolation across accounts, and profile view email privacy.

---

## Verification Results

- `ruff check .`: All checks passed! (0 errors)
- `pytest tests/test_discover.py`: 19 passed in 7.66s.
- `pytest tests -q`: 126 passed in 41.16s.
