# Phase 2 Plan 3 Summary: Methods Badge End to End & Live RLS Probe

**Executed:** 2026-10-05
**Status:** Completed
**Requirements Delivered:** PROF-05, PROF-06, D-05, D-06, D-07, D-08, D-12

---

## What Changed

1. **Database Access & Column Grants** ([findings/repos/profiles.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/findings/repos/profiles.py)):
   - Added `methods_hash` and `methods_reason` to `PROFILE_COLUMNS`.
   - `update_own` raises `ProfileWriteError` when zero rows are updated (e.g. on RLS rejection).

2. **Domain Service & Hash-Gated AI Suggestion** ([findings/services/profile_service.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/findings/services/profile_service.py)):
   - `save_profile`: computes SHA256 input hash over research fields; skips AI call if no signal (`ai_status="skipped"`) or if research fields are unchanged (`ai_status="unchanged"`).
   - Invokes `suggest_methods` upon content changes, writing `methods_suggested`, `methods_reason`, and `methods_hash` in a second write (`ai_status="updated"`).
   - Robust error handling: `AIUnavailable` or secondary write failures gracefully return `ai_status="unavailable"` without rolling back or blocking the core profile save.
   - `set_methods_override`: validates enum value (`qualitative`, `quantitative`, `mixed`, or `None`), updating only `methods_override` with RLS error mapping.
   - Prohibits `methods_override` from ever being included in `save_profile` updates.

3. **App Initialization** ([app.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/app.py)):
   - Configures Gemini client on boot via `configure(settings.gemini_api_key)`. If absent, gracefully runs in disabled mode without network calls.

4. **UI Methods Badge Component** ([ui/profile_view.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/ui/profile_view.py)):
   - Added `methods_badge(profile)`: renders `st.badge` with color and Material icon (`:material/analytics:` for quantitative, `:material/psychology:` for qualitative, `:material/merge:` for mixed).
   - Displays source indicator: `· AI-suggested` or `· set by you`.
   - Displays AI explanation via `st.text` when present and not overridden.
   - Displays `Not classified yet` in neutral gray when unclassified.

5. **Profile Page Reactive Flow** ([views/profile.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/views/profile.py)):
   - Wrapped save operation in `st.spinner("Saving your profile...")`.
   - Shows contextual toast feedback based on `ai_status` (`Profile saved. Methods label updated.` on new classification; warning when AI is unavailable).
   - Added `st.segmented_control` for manual orientation override (`auto`, `qualitative`, `quantitative`, `mixed`) with instantaneous state update and rerun.

6. **Live RLS Probe Script** ([scripts/check_live.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/scripts/check_live.py)):
   - Implemented `probe_credentials()` and `run_probe()` implementing P1-P9:
     - P1: Probe user signs in.
     - P2: Probe updates own profile with valid fields.
     - P3: Demo user can select probe row by ID (visibility check).
     - P4: Demo user raw update on probe row affects 0 rows.
     - P5: `update_own` from demo client targeting probe ID raises `ProfileWriteError`.
     - P6: Probe profile retains original name.
     - P7: Updating generated ungranted column (`methods_effective`) raises error.
     - P8: Inserting unowned profile row raises error.
     - P9: Finally block resets probe `is_complete` to `False`.

7. **Test Suites**:
   - [tests/test_profile_page.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/tests/test_profile_page.py): added AppTest coverage for Save with AI suggestion, Save with `AIUnavailable`, Save without API key, and segmented control override toggle.
   - [tests/test_profile_service.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/tests/test_profile_service.py): added tests for secondary methods update failure fallback and payload isolation.

---

## Verification Results

- `ruff check .`: 0 errors.
- `pytest tests/test_profile_service.py tests/test_profile_page.py -q -k "methods or badge or override or ai"`: 11 passed, 15 deselected in 9.49s.
- `pytest tests -q`: 107 passed in 41.00s.
- Acceptance criteria for 02-03 all verified.
