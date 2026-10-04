# Project Research Summary

**Project:** Findings — "Hinge for researchers": AI-powered web app matching academic collaborators and mentors
**Domain:** Streamlit + Supabase + Gemini (free tier), passwordless OTP auth, pgvector + LLM rerank
**Course context:** Graded demo by ~2026-10-19 (~2 weeks), $0 budget, reliability > breadth
**Researched:** 2026-10-05
**Confidence:** MEDIUM-HIGH overall

## Executive Summary

Findings is a two-stage retrieve-then-rerank matcher for researchers. The standard pattern has two stages. Stage 1 is a pgvector semantic search, which is cheap and reliable. Stage 2 is a single batched Gemini call that reranks and explains the top ~15 candidates, which makes the results flexible and explainable. If Gemini fails, the app falls back to embedding-only ranking. This design fits free-tier limits and keeps a live demo resilient.

The technical risk is in the infrastructure details, not the algorithm:
- Supabase email-OTP auth requires custom SMTP on day 1.
- Supabase clients must be per user, because a globally cached client leaks sessions between users.
- Gemini quotas are unpublished, per project, and shared by development, seeding and the demo.

**Recommended approach:**
- **Days 1–2 (Foundation):**
  - Supabase schema with RLS, column grants and security-definer RPCs.
  - Custom SMTP and the OTP template fix.
  - Email privacy enforced in the database.
  - Gemini quota check in AI Studio.
  - Streamlit skeleton deployed to Cloud.
- **Days 2–5:** Profile CRUD, the AI base (embeddings, autofill), seed data (~60–100 synthetic profiles), and Discover cards with filters.
- **Days 5–10:**
  - The matching pipeline: shortlist RPC, Gemini rerank, match cache and fallback ladder.
  - Connections: request, accept, and email unlock.
  - Mentorship mode.
- **Days 10–14:** Hardening, test coverage, documentation (architecture, limitations, AI-use declaration), and the demo checklist.

**Key risks and mitigation:**
1. **OTP email delivery fails without custom SMTP.**
   - Supabase's built-in SMTP only sends to team members, at about 2 emails per hour.
   - Both email templates must contain `{{ .Token }}`.
   - Mitigation: use Brevo (300/day, no domain needed) or Resend (100/day, domain required), and keep a password-based demo account as a fallback.
2. **A shared Supabase client leaks login state across users.**
   - Every session needs its own client in `st.session_state`, never cached globally.
   - Mitigation: a two-browser, two-account test is part of the Phase 1 exit criteria.
3. **Gemini free-tier quotas are unpublished, per project, and shared by all traffic.**
   - Reported limits are about 20 requests/day for Flash and about 500/day for Flash-Lite (LOW confidence).
   - Mitigation: read the real limits in AI Studio on day 1, cache aggressively, fall back to embedding-only ranking, and pre-warm the demo account's cache.
4. **Embedding dimension mismatch.**
   - `gemini-embedding-2` defaults to 3072 dimensions, but the schema uses `vector(768)`.
   - Mitigation: set `output_dimensionality=768` explicitly, store `embedding_model` on each row, and normalize in code. Normalizing is harmless even though embedding-2 already auto-normalizes.

Process can prevent every one of these risks; none of them requires a change to the architecture.

## Key Findings

### Recommended Stack (STACK.md)

**Mandatory day-1 setup:**
1. Custom SMTP is required. Supabase's default SMTP only sends to team members, at 2 emails per hour. Use Brevo (300/day, single-sender verification, no domain) or Resend (100/day, domain required).
2. Edit both the "Magic Link" and the "Confirm signup" templates to include `{{ .Token }}`. A brand-new user gets the Confirm signup template, not Magic Link.

**Core stack (verified 2026-10-05):**
- **Python 3.12.** Community Cloud defaults to 3.14, so pick 3.12 explicitly in Advanced settings at deploy time. It can't be changed later without deleting and redeploying.
- **streamlit 1.65.0** (`st.navigation`, `st.dialog`, `st.form`)
- **supabase 2.32.0** (auth OTP, PostgREST, RLS, RPC)
- **google-genai 2.28.0.** Not the deprecated `google-generativeai` package.
- **pydantic 2.13.x** (for `response_schema`)
- **pypdf 6.19.0** (optional, only for PDF pre-flight checks)

**Gemini models (free-tier eligible):**
- **Text generation:**
  - Primary: `gemini-3.5-flash-lite`.
  - Fallback: `gemini-3.1-flash-lite`. Quotas are per model, so the fallback also adds capacity.
  - Set `thinking_level` to low or minimal; the default is high, which is slow and can truncate JSON.
- **Embeddings:**
  - Use `gemini-embedding-2` at 768 dimensions.
  - It has no `task_type`, so put the task prefix in the text.
  - Embed **one string per call**, because a list of strings returns one aggregated vector.
- **Structured output and PDFs:** call `client.models.generate_content` with a Pydantic `response_schema`, and pass PDFs inline with `types.Part.from_bytes` (up to 50 MB).

**Supabase keys:** the legacy `anon` and `service_role` keys are being deprecated by the end of 2026.
- Use `sb_publishable_...` in the app.
- Use `sb_secret_...` only in the local seed script.

**Key rule:** pin the Python version, every package version, and the Cloud Advanced settings. Deploy a skeleton to Cloud in Phase 1 so secrets, version and SMTP problems surface early.

### Expected Features (FEATURES.md)

**Table stakes:**
- Passwordless email OTP, with the session persisting inside the app.
- A profile with career stage (fixed list), interests, skills, methods, education, experience, bio and looking_for.
- Filters for methods, stage and keywords.
- A connection request with accept or decline, and the email revealed on accept (the core privacy mechanic).
- Discover cards, with synthetic profiles labelled.

**Differentiators:**
1. AI match ranking with a "why you match" explanation that cites concrete overlaps.
2. Symbiotic mentorship that matches the mentor's offers and needs against the junior's contributable skills and learning goals, with both directions spelled out.
3. AI-suggested methods orientation that the user can override.
4. Methods complementarity, such as pairing qual and quant researchers for mixed-methods work.
5. Graceful Gemini degradation, with a visible fallback notice.

**Anti-features (defer or drop):**
- In-app chat. Unlock the contact email instead.
- Swipe UI. Use cards with buttons instead.
- Publication imports, which are fragile.
- Credential verification, which adds friction.
- Notifications.
- h-index or RG-score style metrics.
- Live Gemini calls on every page load.

**Critical path for feature dependencies:** auth, profiles, seed data and embeddings come first, then Discover, then the match pipeline, then connections, then mentorship.

**Cut order if time slips:** PDF autofill first, then text autofill, then explanation chips. Never cut the fallback or the database-enforced email gating.

### Architecture Approach (ARCHITECTURE.md)

**Layers** (`views -> services -> (repos, ai)`; `ui` is used only by views):
- **Presentation:** Streamlit pages declared through `st.navigation`, gated by auth.
- **Services:** auth, profile, matching and connection services that orchestrate the lower layers.
- **Repos:** CRUD and RPC calls for profiles, connections and the match cache.
- **AI:** a stateless Gemini client plus embeddings, rerank, autofill and prompts.
- **Database:** the single source of truth. RLS, column grants and security-definer RPCs enforce privacy.

`repos` and `ai` never import streamlit, so the offline seed script reuses them unchanged. One shared `embedding_text()` builder keeps the seeded and real embeddings in the same vector space.

**Two-stage matching pipeline:**
1. **Stage 1 (SQL, no API call):** the `match_profiles(query_vector, mode, k=15)` RPC returns the top 15 by cosine similarity, filtered by methods or stage. Mentor mode adds an opposite-stage-tier filter.
2. **Stage 2 (one Gemini call):**
   - The prompt contains the user plus the 15 candidates.
   - The response is `list[{candidate_id, score 0-100, explanation, they_give_you, you_give_them}]`.
   - Candidates get ephemeral ids `c1..c15`, so the model can't invent real ones.
3. **Fallback ladder** (the first one that works wins):
   1. Fresh cache.
   2. Live AI.
   3. Stale cache, with a notice.
   4. Embedding-only ranking (short TTL).
   5. Tag overlap.

**Embeddings:**
- Compute embeddings when a profile is saved, not when matching. Skip the call when the hash of text plus model hasn't changed.
- Never re-embed the querying user; read their stored vector.

**Privacy enforced in the database:**
- Email never lives in `profiles`. It goes in `profile_contacts`, which has RLS on and no policies.
- Only the `get_contact_email(other_id)` security-definer RPC reveals it, and only when an accepted connection exists.
- Only the recipient can change a request's status. A trigger allows only pending → accepted/declined.
- A unique index on `least`/`greatest` of the two ids blocks duplicate pairs.

**Schema:**
- `profiles.id` equals `auth.uid()` for real users and is a random UUID for synthetic ones, with no foreign key to `auth.users`.
- Derived generated columns: `stage_tier`, `methods_effective`, `open_to_mentoring` and `seeking_mentor`.
- The offers and needs columns must be in the first migration.

### Critical Pitfalls (PITFALLS.md)

1. **A shared Supabase client leaks sessions across users.** `st.cache_resource` shares one user's JWT with everyone. Test with two browsers and two accounts.
2. **Hiding email in the UI instead of the database.** RLS only filters rows, not columns, so use a separate table plus a security-definer RPC.
3. **Silent RLS failures.**
   - With RLS off, a table is world-readable.
   - With no policy, queries return an empty result silently.
   - An update that RLS blocks returns an empty list with no error.
   - The SQL editor bypasses RLS, so tests run there pass misleadingly.
4. **Gemini quotas are unpublished and per project.** Read them in AI Studio on day 1. Development, seeding and the demo all draw from the same bucket.
5. **Service-role or secret key leaks.** Only the seed script uses that key. Never commit it and never put it in the Cloud secrets.
6. **OTP template asymmetry and email limits.** Edit both templates and verify with a fresh external address.
7. **Embedding dimension mismatch or mixed models.** Set `output_dimensionality=768`, store `embedding_model` on each row, and re-embed everything at once if the model changes.
8. **Reruns lose auth.** A browser refresh starts a new session and signs the user out. List it as a limitation; cookie restore is optional polish.
9. **Reruns repeat API calls.** Put Gemini calls behind an explicit button, a `session_state` guard and a database cache lookup.
10. **Untrustworthy Gemini output:** malformed JSON, hallucinated scores, invented reasons and prompt injection. Defenses:
    - Use a response schema with Pydantic.
    - Set thinking to low.
    - Validate the returned ids against the shortlist.
    - Check that cited evidence actually appears in the profile.
    - Show coarse labels instead of fake percentages.
    - Render explanations as plain text.
    - Cap field lengths.
11. **Homogeneous synthetic data.** Build a spec matrix of field × stage × methods × region, generate 4–8 profiles per call into a resumable JSON checkpoint written as UTF-8, and check that pairwise cosine similarity stays below about 0.8.
12. **Matching quality and bias.** Leave institution, name and gender out of the embedding text. Keep an evaluation set of anchor profiles with hand-checked top 3 in the test report.
13. **Junior/mentor split ambiguity.** The spec says "early PhD", but the stage list has a single "PhD". **Decide this during requirements.**
14. **Keep-alive and cold starts.**
    - Run a daily GitHub Actions cron that does a real PostgREST read, with `workflow_dispatch` for manual runs.
    - GitHub auto-disables crons after 60 days without repo activity.
    - A cron ping won't keep the Streamlit app awake, so wake it manually with a T-24h / T-2h / T-30min runbook.
15. **Rubric gaps.**
    - The AI-use declaration must cover both the AI inside the product and the AI used to build it.
    - Disclose that Google may use free-tier Gemini inputs, including CVs.
    - Collect screenshots as each phase finishes.

## Implications for Roadmap

### Suggested Phase Structure

| Phase | Goal | Notes | Research |
|-------|------|-------|----------|
| P0/P1 | Schema, RLS, RPCs, SMTP, quota check, skeleton, auth, Cloud deploy, keep-alive | Everything depends on this | Short spike: OTP templates, Brevo, AI Studio limits |
| P2 | Profile CRUD (+ give/need fields, methods override) | Manual save, RLS | Light |
| P3 | AI base and seed data (embeddings, seed generate/load) | Embedding pipeline is the critical path | Moderate: structured output, quota batching, diversity |
| P4 | Discover cards + filters | Also the fallback demo path | None |
| P5 | Peer matching (RPC, rerank, cache, fallback) | **Highest risk.** Build embedding-only first, rerank on top | High: prompt design, grounding, injection tests |
| P6 | Connections + email unlock | Must use the `get_contact_email()` RPC | Light |
| P7 | Mentorship mode | Mostly configuration of P5; parameterize by mode from the start | Light |
| P8 | Autofill (text then PDF), hardening, docs, demo prep | Autofill can be cut; docs can't | None; checklist-driven |

Autofill is independent of matching, so it can run alongside P4–P6.

**Phase gates:**
- **P1 exit:**
  - Two-browser, two-account test passes with no cross-talk.
  - OTP works for a non-team email, for both new and returning users.
  - Keep-alive cron is green.
  - Skeleton runs on Cloud with Python 3.12.
- **P3 exit:**
  - At least 60 seed rows exist, written as UTF-8.
  - Diversity statistics are checked.
  - No real emails are used.
  - `is_synthetic` is visible in the UI.
- **P5 exit:**
  - Gemini returns valid JSON and scores are clamped.
  - Missing candidates are appended.
  - The fallback has been forced with `FORCE_GEMINI_FAIL`.
  - The fallback notice is visible, and the cache survives a restart.
- **P8 exit:**
  - Two-user connections test passes, with email hidden before accept and visible after.
  - The fallback has been tested deliberately.
  - The demo runbook has been rehearsed.
  - The docs match the code.

**Documentation is an exit criterion for every phase**, with screenshots collected as each phase finishes, not left to the end.

### Why This Order
1. **Foundation unblocks everything.** Auth, schema, SMTP and keep-alive are hard to change later. A paused Supabase project or broken SMTP on demo day stops the demo.
2. **Profiles and the AI base can run in parallel**, which shortens the critical path.
3. **Discover is the fallback demo.** If matching breaks, cards and filters still show a working app.
4. **Matching is the highest risk.** Embed early so the rerank sits on a proven base.
5. **Connections and mentorship are mostly configuration.**
6. **The final phase is integration and rehearsal.**

### Research Flags
- Gemini quota check in AI Studio (P1, 10 minutes).
- OTP template behaviour for new and returning users (P1, 15 minutes).
- Rerank prompt A/B and a hallucination spot-check (P5).
- Seed diversity metrics (P3).
- Fallback path exercised with `FORCE_GEMINI_FAIL=1` (P5/P8).

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | PyPI checked and packages installed together on Python 3.12 |
| Features | MEDIUM | Competitor research came from secondary sources; dependencies are sound |
| Architecture | MEDIUM-HIGH | Standard retrieve-then-rerank; the SQL is a sketch that hasn't been run |
| Pitfalls | MEDIUM-HIGH | Official docs plus experience-based items, to confirm with spikes |
| Gemini free-tier quotas | LOW | Unpublished; must verify on day 1 |

### Gaps to Address
1. **Gemini quota budget.** Read the real numbers in AI Studio on day 1 and budget for the pessimistic case.
2. **PhD stage split.** Either split the "PhD" stage into early and late, or add `open_to_mentoring` / `seeking_mentor` flags. Decide in requirements, because changing it later means re-deriving columns and re-embedding.
3. **Requests to synthetic profiles.** No auto-accept is recommended. Seed a pending request from a synthetic profile to the demo account, and use a second real account for the live accept.
4. **Persisting Skip.** Either add a `skips` table or keep Skip session-only.
5. **Declined requests.** The unique-pair index makes a decline final.
6. **Browser refresh logs the user out.** List it as a limitation; cookie restore is optional.

## Key Decisions (Locked)

| Decision | Rationale |
|----------|-----------|
| Streamlit + Supabase + Gemini free tier on Community Cloud | User constraint |
| Email OTP instead of magic link | Streamlit can't read a magic link's URL-fragment token |
| Custom SMTP (Brevo) | Built-in SMTP fails for anyone outside the team |
| Embeddings + pgvector shortlist, then Gemini rerank | Fits free-tier quotas |
| Per-user client in `session_state` | Prevents cross-session leaks |
| `gemini-embedding-2`, 768 dimensions, normalized in code | Current model; keeps the vector space consistent (verify free-tier eligibility on day 1) |
| Match cache + fallback ladder | Graceful degradation when Gemini fails |
| Email revealed only after an accepted connection, enforced in the database | Core privacy mechanic |
| Synthetic profiles use `@example.org` emails and are visibly labelled | Honesty; no real addresses |

## Sources

- `.planning/research/STACK.md`: PyPI, Supabase docs (auth OTP, SMTP, pgvector, keys, limits), Google Gemini API docs (models, deprecations, embeddings, structured output, PDFs), Streamlit Community Cloud docs, and supabase-py installed source.
- `.planning/research/FEATURES.md`: ResearchGate, Academia.edu, MentorCruise, Chronus and Hinge product mechanics (secondary sources).
- `.planning/research/ARCHITECTURE.md`: Supabase RLS, RPC and pgvector docs, Streamlit `st.navigation` and session-state docs, and community threads on shared-client leaks.
- `.planning/research/PITFALLS.md`: Gemini deprecations page, Supabase auth and RLS docs, Streamlit caching docs, and experience-based items flagged as such.

---
*Research completed: 2026-10-05*
*Ready for roadmap: yes*
