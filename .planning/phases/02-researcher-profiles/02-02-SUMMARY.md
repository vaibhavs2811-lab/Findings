# Phase 2 Plan 2 Summary: Shared Gemini Client & Methods Classifier

**Executed:** 2026-10-05
**Status:** Completed
**Requirements Delivered:** PROF-05, D-05, D-07, D-08, D-09

---

## What Changed

1. **Package Legitimacy & Dependency Pin** ([requirements.txt](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/requirements.txt)):
   - Confirmed `google-genai==2.28.0` is Google's official Python SDK from `github.com/googleapis/python-genai` and approved via human verification checkpoint.
   - Pinned `google-genai==2.28.0` in `requirements.txt` and installed into the environment.

2. **Shared Gemini Client** ([findings/ai/client.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/findings/ai/client.py)):
   - Streamlit-free client module with 15s timeout and no automatic retries.
   - `TEXT_MODELS`: fallback chain `("gemini-3.5-flash-lite", "gemini-3.1-flash-lite")`.
   - `make_client`, `configure`, and `generate_structured`: sends Pydantic schema as `response_schema` with `ThinkingLevel.LOW`, catching per-model exceptions and moving to the next model in the chain before raising `AIUnavailable`.
   - Never logs prompt text, response bodies, or API keys (logs only model id and exception type).

3. **Untrusted Prompt Delimiting** ([findings/ai/prompts.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/findings/ai/prompts.py)):
   - `wrap_untrusted`: wraps user data inside XML-like tags, escaping `<` and `>` inside the JSON payload to prevent delimiter breakout.
   - `METHODS_SYSTEM` & `methods_prompt`: system instructions directing the model to treat user fields strictly as data and classify methods orientation into qualitative, quantitative, or mixed.

4. **Methods Domain & Hashing** ([findings/ai/methods.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/findings/ai/methods.py)):
   - `MethodsSuggestion`: structured Pydantic model (`label: Literal["qualitative", "quantitative", "mixed"]`, `reason: str`).
   - `methods_input`: allow-list filter extracting only research fields (interests, skills, experience, bio, education, looking_for), strictly dropping name, institution, career stage, toggles, and email.
   - `methods_hash`: SHA256 over normalized, casefolded, deduplicated, sorted field values and `PROMPT_VERSION`.
   - `needs_classification` & `has_signal`: skips classification when inputs are unchanged or when all fields are empty.
   - `suggest_methods`: invokes `generate_structured` and trims the reason to at most 140 characters.

5. **Configuration Update** ([findings/core/config.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/findings/core/config.py)):
   - Added optional `gemini_api_key: str | None = None` to `Settings`, loaded cleanly without publishable key validation.

6. **Schema Addition** ([supabase/schema.sql](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/supabase/schema.sql)):
   - Appended idempotent section 10 adding `methods_hash text` and `methods_reason text check (char_length(methods_reason) <= 300)`.
   - Added `grant update (methods_hash, methods_reason) on public.profiles to authenticated` and schema reload notify.

7. **Live Smoke Script & Config Examples**:
   - [scripts/check_gemini.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/scripts/check_gemini.py): smoke test classifying sample profile across both Flash-Lite models, gracefully skipping with code 2 if no key is present.
   - [scripts/local.toml.example](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/scripts/local.toml.example): added `PROBE_EMAIL`, `PROBE_PASSWORD`, and `GEMINI_API_KEY` placeholders.
   - [.streamlit/secrets.toml.example](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/.streamlit/secrets.toml.example): added security guidance and `GEMINI_API_KEY` comment.

8. **Test Suites**:
   - [tests/test_ai_client.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/tests/test_ai_client.py): offline SDK tests using `httpx.MockTransport` covering success, 429 fallback, 500 error wrapping, thinking level LOW, response schema validation, and PDF part payloads.
   - [tests/test_methods.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/tests/test_methods.py): prompt injection escaping, input filtering, hash invariance, and reason truncation.
   - [tests/test_layering.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/tests/test_layering.py): AST scan ensuring backend modules never import Streamlit and secrets.toml has no Gemini key.
   - [tests/test_schema_sql.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/tests/test_schema_sql.py): schema grant order, policy checks, and section 10 assertions.

---

## Verification
- `ruff check .`: 0 errors.
- `pytest`: 97 passed in 47.77s.
- `check_gemini.py`: exits 2 (clean SKIP when key absent).
- `schema.sql`: 6 insertions, 0 deletions.
