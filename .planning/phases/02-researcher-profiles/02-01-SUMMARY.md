# Phase 2 Plan 1 Summary: Researcher Profile Form & Read-only View

**Executed:** 2026-10-05
**Status:** Completed
**Requirements Delivered:** PROF-01, PROF-02, PROF-03, PROF-04, D-01, D-02, D-03, D-04, D-10, D-11, D-12

---

## What Changed

1. **Constants & Domain Configuration** ([findings/core/constants.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/findings/core/constants.py)):
   - `CAREER_STAGES`: `("Undergrad", "Master's", "PhD", "Postdoc", "Faculty", "Industry researcher")` matching `supabase/schema.sql`.
   - `STAGE_MENTORING_DEFAULTS`: stage-based presets for `seeking_mentor` and `open_to_mentoring` (PhD unmanaged).
   - Presets for interests, skills, offers, needs, and limits for text/list entries.

2. **Profiles Repository** ([findings/repos/profiles.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/findings/repos/profiles.py)):
   - `PROFILE_COLUMNS`: explicit allow-list of 24 columns without `*`, `embedding`, or email source.
   - `update_own(sb, user_id, payload, columns=PROFILE_COLUMNS)`: updates user row with RLS protection and raises `ProfileWriteError` on zero rows.
   - `get_own_profile(sb, user_id, columns=PROFILE_COLUMNS)`: defaults to full columns.

3. **Profile Service** ([findings/services/profile_service.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/findings/services/profile_service.py)):
   - `mentoring_defaults(stage)`: returns default toggle states.
   - `normalise_text` and `normalise_list`: sanitization, inner-space collapse, case-insensitive deduplication, length bounding.
   - `is_complete` & `missing_for_complete`: enforces presence of name, valid stage, and >=1 interest.
   - `build_payload`: enforces strict allow-list; resets hidden give/need fields to `[]` when corresponding toggles are disabled.
   - `save_profile`: writes via `update_own`, wrapping lower-level exceptions into user-safe `ProfileSaveError`.

4. **UI Components & Pages**:
   - [ui/profile_view.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/ui/profile_view.py): `render_profile` safe read-only card rendering untrusted strings via `st.text` (markdown injection prevention), strictly guarding email display behind `show_email=True`.
   - [views/profile.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/views/profile.py): single scrolling page (no `st.form` or tabs), reactive stage `on_change` callback, toggled give/need multiselects with `accept_new_options=True`, view/edit switching with Edit/Cancel buttons, and toast flash handoff.
   - [views/home.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/views/home.py): CTA linking to `views/profile.py` ("Complete your profile" or "View my profile").
   - [app.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/app.py): registered `views/profile.py` in authenticated navigation.

5. **Live Verification Script** ([scripts/check_live.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/scripts/check_live.py)):
   - Added D11, D12, D13 checking `get_own_profile` with `PROFILE_COLUMNS`, array append update, and rollback restore.

6. **Test Suites**:
   - [tests/fakes_profiles.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/tests/fakes_profiles.py): `FakeProfilesSupabase` query and mutation fake.
   - [tests/test_profiles_repo.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/tests/test_profiles_repo.py): repo column hygiene and `update_own` tests.
   - [tests/test_profile_service.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/tests/test_profile_service.py): pure domain logic and schema verification.
   - [tests/test_profile_page.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/tests/test_profile_page.py): AppTest coverage of form reactive triggers, save round-trip, view mode, email privacy, and markdown safety.
   - [tests/test_demo_login.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/tests/test_demo_login.py): updated Home CTA assertions.

---

## Verification
- `ruff check .`: 0 errors.
- `pytest`: 79 passed in 33.32s.
