---
phase: "2"
slug: "researcher-profiles"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-05"
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + `streamlit.testing.v1.AppTest` |
| **Config file** | `pytest.ini` (`testpaths = tests`, `pythonpath = .`) |
| **Interpreter** | `C:/fv312/Scripts/python` (Python 3.12 venv used by Phase 1 verification and `.claude/launch.json`; `.venv` does not exist in this checkout) |
| **Quick run command** | `C:/fv312/Scripts/python -m pytest tests -q -x` |
| **Full suite command** | `C:/fv312/Scripts/python -m pytest tests -q && C:/fv312/Scripts/python -m ruff check .` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `C:/fv312/Scripts/python -m pytest tests -q -x`
- **After every plan wave:** Run the full suite command
- **Before `/gsd-verify-work`:** Full suite must be green, then `scripts/check_live.py` (anon + demo + probe) and `scripts/check_gemini.py` PASS
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

Filled in by the planner/executor per task. Requirement → test mapping (from 02-RESEARCH.md § Validation Architecture):

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| PROF-01 | Save writes nine fields, explicit column list, `is_complete` rule, zero-row update raises | unit | `C:/fv312/Scripts/python -m pytest tests/test_profile_service.py tests/test_profiles_repo.py -q` | ❌ W0 | ⬜ pending |
| PROF-01 | Empty form → fill → Save → view mode; Home CTA | AppTest | `C:/fv312/Scripts/python -m pytest tests/test_profile_page.py -q` | ❌ W0 | ⬜ pending |
| PROF-02 | Six stages match SQL check list | unit + AppTest | `C:/fv312/Scripts/python -m pytest tests/test_schema_sql.py tests/test_profile_page.py -q -k stage` | ❌ W0 | ⬜ pending |
| PROF-03 | Stage → toggle defaults; PhD untouched; override survives rerun | unit + AppTest | `C:/fv312/Scripts/python -m pytest tests/test_profile_service.py tests/test_profile_page.py -q -k "mentoring or toggle"` | ❌ W0 | ⬜ pending |
| PROF-04 | Give/need visibility by toggle; hidden saved as `[]`; normalisation | unit + AppTest | `C:/fv312/Scripts/python -m pytest tests/test_profile_service.py tests/test_profile_page.py -q -k "give or need or normalise"` | ❌ W0 | ⬜ pending |
| PROF-05 | AI client chain/fallback, hash skip, failure-safe save, override, badge | unit (MockTransport) + AppTest | `C:/fv312/Scripts/python -m pytest tests/test_ai_client.py tests/test_methods.py tests/test_profile_page.py -q` | ❌ W0 | ⬜ pending |
| PROF-05 | Real Gemini label on both models | live | `C:/fv312/Scripts/python scripts/check_gemini.py` | ❌ W0 | ⬜ pending |
| PROF-06 | Grant list correct; repo only targets own id | unit | `C:/fv312/Scripts/python -m pytest tests/test_schema_sql.py tests/test_profiles_repo.py -q` | ❌ W0 | ⬜ pending |
| PROF-06 | Second-account probe: visible but not writable, owner row unchanged | live | `C:/fv312/Scripts/python scripts/check_live.py` | ⚠ extend | ⬜ pending |
| Layering | ai/services/repos never import streamlit; no Gemini key tracked | unit | `C:/fv312/Scripts/python -m pytest tests/test_layering.py tests/test_repo_hygiene.py -q` | ❌ W0 / ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/fakes_profiles.py` — `FakeSupabase` subclass with select/eq/limit/update/select-after-update, zero-row and raise modes
- [ ] `tests/test_ai_client.py`, `tests/test_methods.py`, `tests/test_profile_service.py`, `tests/test_profiles_repo.py`, `tests/test_profile_page.py`, `tests/test_schema_sql.py`, `tests/test_layering.py`
- [ ] Update `tests/test_demo_login.py` Home assertions (D-10)
- [ ] `scripts/check_live.py` probe section, `scripts/local.toml.example` (`PROBE_EMAIL`, `PROBE_PASSWORD`), `scripts/check_gemini.py`
- [ ] `google-genai==2.28.0` in `requirements.txt` and installed into `C:/fv312`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Profile persists after sign-out / sign-in on deployed app | PROF-01 | Needs real browser + live DB | Sign in, fill, Save, sign out, sign in, open My profile |
| Save right after typing in a text area keeps the text (A6) | PROF-01 | Browser blur/commit behaviour | Type in Bio, click Save immediately, check view |
| Custom multiselect values reappear as chips on Edit (A7) | PROF-04 | Browser rendering | Add custom interest, Save, Edit |
| Docs screenshots (empty form, badge, override, toggles, RLS output) | all | Rubric evidence | Capture into `docs/screenshots/phase-2/` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
