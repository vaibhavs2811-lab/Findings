# API Coverage — Google Gemini API (google-genai 2.28.0) and Supabase delta, Phase 2

> Full coverage by default. Opt-outs are explicit, reasoned decisions.
> Phase 2 integrates the Gemini API for the first time through the shared `findings/ai/` client. Supabase was matrixed in Phase 1, and only the Phase 2 delta is listed below.

| capability | decision | reason |
|---|---|---|
| gemini.models.generate_content | INTEGRATE | |
| gemini.generate_content.response_schema (Pydantic structured output) | INTEGRATE | |
| gemini.generate_content.system_instruction | INTEGRATE | |
| gemini.generate_content.thinking_config (thinking_level) | INTEGRATE | |
| gemini.generate_content.inline_parts (Part.from_bytes via the parts= argument) | INTEGRATE | |
| gemini.http_options.timeout | INTEGRATE | |
| gemini.model_fallback_chain (3.5-flash-lite then 3.1-flash-lite) | INTEGRATE | |
| gemini.models.generate_content_stream | OPT-OUT | not needed: every call is a one-shot structured JSON answer that is validated as a whole |
| gemini.models.embed_content | OPT-OUT | not needed yet: Phase 3 adds findings/ai/embeddings.py (gemini-embedding-2, 768 dims) per the shared contract |
| gemini.models.count_tokens | OPT-OUT | not needed: input size is bounded in code (1500 chars per text field, 15 list items) |
| gemini.models.list / models.get | OPT-OUT | not needed: model ids are pinned constants in TEXT_MODELS |
| gemini.files (upload/get/delete) | OPT-OUT | explicitly out of scope: CV PDFs are sent inline and never stored with Google (privacy); Phase 7 uses inline parts |
| gemini.caches (context caching) | OPT-OUT | not needed: prompts are short and single-use |
| gemini.batches | OPT-OUT | not needed: Batch API is not available on the free tier |
| gemini.chats (multi-turn sessions) | OPT-OUT | not needed: every call is one-shot |
| gemini.live (realtime audio/video) | OPT-OUT | explicitly out of scope: no realtime or audio features |
| gemini.interactions | OPT-OUT | not needed: stores state server side by default; generate_content covers one-shot extraction (CLAUDE.md) |
| gemini.tools (function calling, search grounding, code exec, URL context) | OPT-OUT | not needed: classification must use only the user's own profile text; grounding would add unvetted content and quota cost |
| gemini.generate_images / generate_videos / edit_image | OPT-OUT | explicitly out of scope: no image or video features, and paid-only models |
| gemini.tunings | OPT-OUT | not needed: no fine-tuning on a free-tier course project |
| gemini.safety_settings (custom thresholds) | OPT-OUT | not needed: defaults are fine; a blocked or empty response is treated as a failure and falls through the model chain |
| gemini.http_options.retry_options (SDK retries) | OPT-OUT | not needed: the model chain is the retry; SDK retries on a per-model 429 would only burn free quota |
| gemini.operations (long-running) | OPT-OUT | not needed: no long-running operations are used |
| gemini.vertexai / ADC authentication | OPT-OUT | explicitly out of scope: free Gemini API key only ($0 budget) |
| supabase.postgrest.update(...).select(columns) | INTEGRATE | |
| supabase.postgrest.select (own row, full PROFILE_COLUMNS) | INTEGRATE | |
| supabase.postgrest.insert | OPT-OUT | not needed: profile rows are created by the signup trigger; the live probe calls insert only to prove RLS rejects it |
| supabase.auth.sign_up (probe account) | OPT-OUT | not needed: the probe account is created in the dashboard with Auto Confirm so the probe stays deterministic |
