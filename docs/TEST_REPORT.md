# Test report

Run on 2026-10-05, Python 3.12, Streamlit 1.65.0.

| Check | Command | Result |
|---|---|---|
| Automated tests | `pytest tests -q` | **229 passed, 0 failed** |
| Lint | `ruff check .` | All checks passed |
| Live Gemini check | `python scripts/check_gemini.py` | PASS on `gemini-3.5-flash-lite` and `gemini-3.1-flash-lite` |
| Live autofill smoke | text autofill with an embedded injection and an email address | Fields extracted; injected instruction ignored; email scrubbed |

Live database checks (`scripts/check_live.py`, `scripts/check_discover.py`, `scripts/check_matching.py`)
need real Supabase credentials in `scripts/local.toml` and write to the live project, so run them
on the demo machine before the demo and paste their output below.

## Automated tests by file

| File | Tests |
|---|---|
| `tests/test_ai_client.py` | 8 |
| `tests/test_auth_service.py` | 15 |
| `tests/test_autofill.py` | 14 |
| `tests/test_connections_flow.py` | 10 |
| `tests/test_connections_sql.py` | 5 |
| `tests/test_cookie_restore.py` | 16 |
| `tests/test_demo_login.py` | 8 |
| `tests/test_discover.py` | 19 |
| `tests/test_discover_connect.py` | 2 |
| `tests/test_embeddings.py` | 6 |
| `tests/test_layering.py` | 2 |
| `tests/test_login_flow.py` | 8 |
| `tests/test_matches_cache.py` | 8 |
| `tests/test_matches_connect.py` | 2 |
| `tests/test_matching.py` | 14 |
| `tests/test_mentorship.py` | 18 |
| `tests/test_methods.py` | 7 |
| `tests/test_profile_page.py` | 11 |
| `tests/test_profile_service.py` | 15 |
| `tests/test_profiles_repo.py` | 4 |
| `tests/test_repo_hygiene.py` | 4 |
| `tests/test_rerank.py` | 7 |
| `tests/test_save_embedding.py` | 6 |
| `tests/test_schema_sql.py` | 1 |
| `tests/test_seed_data.py` | 7 |
| `tests/test_seed_load.py` | 4 |
| `tests/test_session.py` | 8 |

## Use cases

| # | Use case | Requirements | Automated evidence | Screenshot |
|---|---|---|---|---|
| 1 | Sign up, sign in, stay signed in after refresh, sign out | AUTH-01..06 | `test_login_flow`, `test_cookie_restore`, `test_session`, `test_auth_service` | `docs/screenshots/01-sign-in.png` (to capture) |
| 2 | Create and edit a profile | PROF-01, 02 | `test_profile_page`, `test_profile_service`, `test_profiles_repo` | `02-profile-form.png`, `03-profile-saved.png` |
| 3 | Mentoring toggles default from career stage; give/need fields follow the toggles | PROF-03, 04 | `test_profile_page` (stage defaults, give/need fields) | `04-toggles.png` |
| 4 | AI methods badge and override; profile saves if Gemini is down | PROF-05 | `test_methods`, `test_ai_client`, `test_profile_page` | `05-badge.png`, `06-override.png` |
| 5 | Edit only your own profile (RLS) | PROF-06 | `test_schema_sql` (grants, policies), live probe in `scripts/check_live.py` | RLS output (to capture) |
| 6 | Autofill from pasted text or a PDF CV; nothing saved until Save | AUTO-01..04 | `test_autofill` | `07-autofill.png` |
| 7 | Discover: cards, filters, search, Skip | DISC-01..05 | `test_discover` | `08-discover.png` |
| 8 | Public profile page, no email | PROF-07 | `test_discover`, `test_layering` | `09-researcher-page.png` |
| 9 | Seeded pool of 80 researchers (no Synthetic label shown in the UI) | DATA-01, 02 | `test_seed_data`, `test_seed_load`, `test_discover` | `10-discover-pool.png` |
| 10 | AI peer matches with explanations, cached, with fallback | MATCH-01..05 | `test_matching`, `test_rerank`, `test_matches_cache`, `test_embeddings`, `test_save_embedding` | `11-matches-ai.png`, `12-matches-fallback.png` |
| 11 | Mentorship: find a mentor / mentee, two-sided explanation | MENT-01..04 | `test_matching` (mentor modes), `test_mentorship` | `13-mentorship.png` |
| 12 | Connection request, accept/decline, email revealed only after accept | CONN-01..06, DISC-06 | `test_connections_flow`, `test_connections_sql`, `test_discover_connect`, `test_matches_connect` | `14-connections.png` |
| 13 | Keep-alive and deployment | OPS-01, OPS-03 | `.github/workflows/keepalive.yml` run history | Actions run (to capture) |

Screenshots are captured by hand during the rehearsal (see `docs/RUNBOOK.md` section 7) and must
not show keys, passwords or real email addresses.

## UI screenshots (design preview)

Captured on a phone-width viewport from the design preview (`streamlit run preview.py`), which runs
the real app on sample data, so no real accounts or emails appear. They show the dark-first design;
replace or add real-account captures from the deployed app during the rehearsal.

| Page | File |
|---|---|
| Home | `docs/screenshots/ui-home.jpg` |
| My Matches | `docs/screenshots/ui-my-matches.jpg` |
| Discover | `docs/screenshots/ui-discover.jpg` |
| My profile | `docs/screenshots/ui-profile.jpg` |
| Connections | `docs/screenshots/ui-connections.jpg` |
