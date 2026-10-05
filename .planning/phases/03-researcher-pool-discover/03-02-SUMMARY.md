# Phase 3 Plan 2 Summary: Synthetic Researcher Pool Generation & Dataset

**Executed:** 2026-10-05
**Status:** Completed
**Requirements Delivered:** DATA-01

---

## What Changed

1. **Specification Matrix & Domain Validation** ([findings/services/seed_data.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/findings/services/seed_data.py)):
   - Implemented `build_spec_matrix`: deterministic generator (`random.Random(42)`) creating 80 specifications.
   - Enforced career stage quotas: Undergrad (10), Master's (14), PhD (18), Postdoc (14), Faculty (14), Industry researcher (10).
   - Balanced distribution across 14 research fields, 10 geographic/cultural regions, and 3 methods orientations (qualitative, quantitative, mixed).
   - Structured 3 curated demo anchor pairs in metadata (P1: Public Health Qual PhD + Quant Postdoc; P2: AI Faculty Mentor + Master's Mentee; P3: HCI Industry Quant + PhD Qual).
   - Domain sanitization: `clean_seed_profile` strips disallowed give/need lists based on mentoring toggles and rejects profiles containing emails or URLs.
   - Fictional contact email generation: `contact_email` produces `<slug>.<seed_id>@example.org`.

2. **Structured AI Prompting & Schemas** ([findings/ai/seed_prompt.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/findings/ai/seed_prompt.py)):
   - Created Pydantic models: `SeedProfileItem` and `SeedBatchResponse`.
   - `build_seed_prompt`: structures 5-item batch prompts with system instructions enforcing academic realism and strictly fictional entities.

3. **Resumable Generation Script** ([scripts/seed_generate.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/scripts/seed_generate.py)):
   - CLI tool supporting both live Gemini batch generation (with 4.5s rate-limit pacing) and deterministic offline synthesis.
   - Resumable from disk checkpoints; writes atomic UTF-8 updates to `data/seed_profiles.json` with Windows file lock handling.

4. **Committed Synthetic Dataset** ([data/seed_profiles.json](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/data/seed_profiles.json)):
   - Generated and validated complete 80-profile dataset with metadata, stage quotas, methods distribution, and demo pairs.

5. **Test Suite** ([tests/test_seed_data.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/tests/test_seed_data.py)):
   - 7 unit tests verifying spec matrix quotas, mentoring rules, demo pairs, slugification, profile sanitization, prompt schemas, and JSON dataset integrity.

---

## Verification Results

- `python scripts/seed_generate.py --offline`: Completed successfully; generated 80 profiles matching quotas.
- `ruff check .`: All checks passed! (0 errors)
- `pytest tests/test_seed_data.py`: 7 passed in 0.23s.
- `pytest tests -q`: 133 passed in 45.06s.
