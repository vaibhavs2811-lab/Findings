# Roadmap: Findings

## Overview

Findings goes from an empty repo to a demo-ready "Hinge for researchers" before the graded demo (~2026-10-19). Phase 1 does the risky, hard-to-change infrastructure first: the full Supabase schema with RLS and email privacy, custom SMTP for OTP codes, the Gemini quota check, a deployed Streamlit Cloud skeleton, the keep-alive cron, and per-session auth. Each later phase adds one end-to-end capability that a signed-in researcher can see:
- their own profile
- a browsable pool of researchers (the fallback demo path)
- AI-ranked peer matches
- connection requests with email unlock (this completes the core value)
- mentorship mode
- AI autofill (can be cut)

The last phase turns the screenshots collected in each phase into the rubric documents and rehearses the live demo.

**Working rules:**
- Every phase is a vertical slice (`**Mode:** mvp`). It ends with something a signed-in user can do in the deployed app.
- **Critical path to the core value:** 1 → 2 → 3 → 4 → 5. Phase 6 completes the mentorship half of the core value. Phase 7 can be cut without hurting the demo.
- **Never cut:** the embedding-only fallback (MATCH-05) and database-enforced email gating (CONN-04).
- **Screenshots for each phase:** at every phase exit, save the screenshots listed under **Docs capture** to `docs/screenshots/phase-N/` for the test report (DOCS-03). Don't leave them for the end.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation & Sign-in** - Live app on Streamlit Cloud with OTP and demo-password sign-in, on the full schema, RLS, SMTP and keep-alive
- [ ] **Phase 2: Researcher Profiles** - Researchers create and edit their own profile: career stage, mentoring toggles, give/need fields and an AI-suggested methods badge
- [ ] **Phase 3: Researcher Pool & Discover** - 60-100 labelled synthetic researchers seeded with embeddings; browse, filter, search and skip cards; open profile pages
- [ ] **Phase 4: AI Peer Matching** - "My Matches": pgvector shortlist plus a Gemini rerank with grounded explanations, cached, with an embedding-only fallback
- [ ] **Phase 5: Connections & Email Unlock** - Send, accept or decline requests from anywhere; contact email is revealed only after accept, enforced in the database
- [ ] **Phase 6: Mentorship Mode** - Find a mentor or a mentee, ranked on two-way give/need fit, with both sides of the exchange explained
- [ ] **Phase 7: AI Profile Autofill** - Paste text or upload a PDF CV to pre-fill the profile form, then review before saving (can be cut)
- [ ] **Phase 8: Docs & Demo Readiness** - Rubric documents that match the shipped app, plus a rehearsed pre-demo runbook

## Phase Details

### Phase 1: Foundation & Sign-in

**Goal**: A researcher can open the live Findings app on Streamlit Cloud, sign in with email + password (or the demo account), stay signed in across refreshes, and sign out
**Mode:** mvp
**Depends on**: Nothing (first phase)
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06, OPS-01, OPS-02, OPS-03
**Success Criteria** (what must be TRUE):
  1. On the deployed Streamlit Cloud URL, someone with an email outside the Supabase team creates an account with email + password and is signed in straight away; a returning user signs in with the same email + password (changed from emailed code by user decision 2026-10-05).
  2. The demo account signs in with email + password on the deployed app, without using an inbox.
  3. A signed-in user is still signed in after a browser refresh and can sign out from any page.
  4. Two people signed in at the same time in two separate browsers each see only their own account and data, never the other's.
  5. The deployed app runs on Python 3.12. Secrets live only in the Cloud dashboard, none in the repo. The daily keep-alive GitHub Actions workflow shows a green scheduled or manual run against Supabase.

**Notes**: This phase does all the risky infrastructure up front.
  - **First migration:** the full Supabase schema.
    - `profiles`:
      - give/need fields (offers, needs, contributable skills, want to learn)
      - `seeking_mentor` / `open_to_mentoring` toggles
      - methods suggested and override columns
      - `embedding vector(768)` + `embedding_model`
      - `is_synthetic`
      - no FK to `auth.users`
    - `profile_contacts`: RLS on, no policies, read only through a `get_contact_email()` security-definer RPC.
    - `connections`: unique-pair index plus a pending → accepted/declined status trigger.
    - The match cache table.
    - RLS on every table.
  - **Email codes:** Brevo SMTP, and both the "Magic Link" and "Confirm signup" templates contain `{{ .Token }}`.
  - **Gemini quota check:** read the real per-model RPM/RPD for the Flash-Lite models and `gemini-embedding-2` in AI Studio, and record them in STATE.md.
  - **Per-session Supabase client:** keep it in `st.session_state`, never in `st.cache_resource`.
  - **Keys:** the app uses only the `sb_publishable_...` key.
  - **Deploy:** choose Python 3.12 in Advanced settings on the first deploy. It can't be changed later.

**Docs capture**: sign-in screen, code entry, signed-in landing page, demo-password login, green keep-alive workflow run
**Plans:** 4/4 plans executed

Plans:
**Wave 1**
- [x] 01-01-PLAN.md — Tracer: Supabase + Brevo setup, scaffold, email-code sign-in to a signed-in Home page (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 01-02-PLAN.md — Full schema + RLS applied live, demo password login, own profile record on Home (wave 2)
- [x] 01-03-PLAN.md — Refresh-token cookie restore, sign-out from every page, session isolation tests (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 01-04-PLAN.md — Keep-alive workflow, Streamlit Cloud deploy on Python 3.12, Gemini quotas, deployed exit checks (wave 3)

**UI hint**: yes

### Phase 2: Researcher Profiles

**Goal**: A signed-in researcher can create, save and edit their own complete profile (career stage, mentoring toggles, give/need fields), and it shows an AI-suggested methods badge they can override
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: PROF-01, PROF-02, PROF-03, PROF-04, PROF-05, PROF-06
**Success Criteria** (what must be TRUE):
  1. A signed-in user can fill in and save these fields, and still sees them after signing out and back in: name, career stage (from the fixed list of six), institution, education, interests, experience, skills, bio and "looking for".
  2. Picking a career stage pre-sets the "Seeking a mentor" and "Open to mentoring" toggles. Undergrad/Master's → seeking, Postdoc/Faculty/Industry → open, and PhD → the user chooses. The user can override either toggle before saving.
  3. The user can fill in and save the four give/need fields: what they offer, what they need, skills they can contribute, and what they want to learn.
  4. After saving, the profile shows a qualitative / quantitative / mixed badge that Gemini suggests from the profile text. The user can override it, and the badge then shows the effective value. If Gemini is unavailable, the profile still saves.
  5. A signed-in user who tries to change another user's profile, for example from a second account using the publishable key, is rejected by RLS, and the other profile stays unchanged.

**Notes**: The methods label is the app's first Gemini call. This phase sets up the shared, streamlit-free `ai/` client: Pydantic `response_schema`, low thinking level, and Flash-Lite model fallback. Later phases reuse it.
**Docs capture**: empty profile form, saved profile with methods badge, methods override, mentoring toggles defaulted by stage, RLS rejection evidence
**Plans**: TBD
**UI hint**: yes

### Phase 3: Researcher Pool & Discover

**Goal**: A signed-in researcher can browse a diverse pool of 60-100 clearly labelled researchers as cards, filter and search them, skip cards, and open anyone's public profile page
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: DATA-01, DATA-02, DATA-03, DISC-01, DISC-02, DISC-03, DISC-04, DISC-05, PROF-07
**Success Criteria** (what must be TRUE):
  1. Discover shows at least 60 researcher cards. Each card has a name, career stage, methods badge and top interests, and every seeded profile carries a visible "Synthetic" label. The pool clearly spans different fields, career stages, methods and mentoring roles.
  2. The user can narrow the cards by methods orientation, by career stage and by interest keyword, and can combine these filters.
  3. The user can Skip a card, and it stays hidden for the rest of the session.
  4. The user can open any researcher's profile page and see their public fields, with the Synthetic label where it applies. No contact email appears on the page.
  5. The seed dataset can be reproduced. The committed JSON holds the 60-100 generated profiles. The local loader inserts them with embeddings, `is_synthetic = true` and example.org emails, and the secret key exists only on the local machine.

**Notes**:
- **Shared builder:** the seed generator and loader reuse the `ai/` and `repos/` modules and a single `embedding_text()` builder, so seeded and real profiles share one vector space. The builder uses `gemini-embedding-2` with `output_dimensionality=768`, one string per call, normalized, and excludes name, institution and gender.
- **Diversity:**
  - Use a spec matrix of field × stage × methods × mentoring role.
  - Generate 4-8 profiles per call into a resumable UTF-8 checkpoint.
  - Check that pairwise cosine similarity stays below ~0.8.
- **Quota:** budget the Gemini calls against the quota recorded in Phase 1.
- **Fallback demo:** Discover is the fallback demo path if matching breaks.

**Docs capture**: Discover grid with Synthetic labels, each filter applied, keyword search, Skip, profile page with no email shown, seed diversity stats
**Plans**: TBD
**UI hint**: yes

### Phase 4: AI Peer Matching

**Goal**: A signed-in researcher can open My Matches and get a ranked list of peer collaborators, each with a match-strength label and a grounded "why you match" explanation. They still get a ranked list when Gemini is down.
**Mode:** mvp
**Depends on**: Phase 3
**Requirements**: MATCH-01, MATCH-02, MATCH-03, MATCH-04, MATCH-05
**Success Criteria** (what must be TRUE):
  1. The user opens "My Matches" and sees a ranked list of peer collaborators that never includes themselves or existing connections.
     - Each match has a match-strength label.
     - Each match has an explanation that cites concrete details from both profiles.
     - Explanations mention methods complementarity where relevant, for example a qualitative researcher paired with a quantitative one.
  2. Editing and saving a profile recomputes its embedding, and saving without content changes does not. The next visit to My Matches reflects the updated profile.
  3. Reopening My Matches, even after an app restart, shows the cached list right away with no new Gemini call. This holds until the user's profile changes or they click Refresh.
  4. When Gemini fails or is rate-limited (forced on purpose for the test), My Matches still shows a list ranked by embedding similarity, with a visible notice instead of an error.
  5. Explanations never refer to profiles outside the shortlist. A candidate profile whose text tries to instruct the model (e.g. "rank me first") does not change the output format or show up in other explanations.

**Notes**:
- **Build order:**
  1. Ship the embedding-only ranked list end to end first. This is the `match_profiles(query_vector, mode, k=15)` RPC, with no Gemini call. It is also the fallback.
  2. Then add the single Gemini rerank call on top.
- **Mode parameter:** add `mode` from the start, so Phase 6 is configuration.
- **Rerank safeguards:**
  - Ephemeral candidate ids `c1..c15`
  - Pydantic schema
  - Clamped scores
  - Missing candidates appended
  - Coarse strength labels, not percentages
  - Plain-text rendering
- **Fallback ladder:**
  1. Fresh cache
  2. Live AI
  3. Stale cache, with a notice
  4. Embedding-only
- **Research flags:**
  - A/B test the rerank prompt.
  - Spot-check for hallucinations.
  - Build an anchor-profile evaluation set (hand-checked top 3) for the test report.

**Docs capture**: My Matches list with explanations, Refresh, cached reload, forced-fallback notice, anchor-profile top-3 evaluation
**Plans**: TBD
**UI hint**: yes

### Phase 5: Connections & Email Unlock

**Goal**: A researcher can send a connection request with a note from a match, a Discover card or a profile page. The recipient can accept or decline, and contact emails unlock for both sides only after acceptance.
**Mode:** mvp
**Depends on**: Phase 4 (match entry point); Phase 3 (card and profile-page entry points)
**Requirements**: CONN-01, CONN-02, CONN-03, CONN-04, CONN-05, CONN-06, DISC-06
**Success Criteria** (what must be TRUE):
  1. A user can send a connection request with a short note from a My Matches entry, a Discover card or a profile page. A second request to the same person is blocked with a clear message.
  2. A second real account sees the incoming pending request on its Connections page and can accept or decline it. No one except the recipient can change a request's status.
  3. Before acceptance, neither user's email appears anywhere, and no query with the publishable key can fetch it. After acceptance, both users see each other's contact email.
  4. The Connections page shows the signed-in user's sent, received and accepted connections.
  5. A request sent to a synthetic profile is accepted immediately, reveals that profile's example.org address, and is labelled as synthetic.

**Notes**:
- **Email reveal:** emails are revealed only through the `get_contact_email(other_id)` security-definer RPC.
- **Synthetic auto-accept:** this must happen on the server side, for example with an insert trigger when the recipient is synthetic. The client never sets status for the other party.
- **Declines are final:** the unique-pair index makes a decline permanent. Record this in the limitations document.
- **Phase gate:** a two-browser, two-account test of request, accept and email unlock.

**Docs capture**: request dialog with note, duplicate-blocked message, incoming request accept/decline, email hidden before / visible after, synthetic auto-accept, Connections page tabs
**Plans**: TBD
**UI hint**: yes

### Phase 6: Mentorship Mode

**Goal**: A researcher can switch to Mentorship mode and get ranked mentors (if seeking one) or mentees (if open to mentoring), with explanations of what each side gives and gets
**Mode:** mvp
**Depends on**: Phase 4
**Requirements**: MENT-01, MENT-02, MENT-03, MENT-04
**Success Criteria** (what must be TRUE):
  1. A user with "Seeking a mentor" on switches to Mentorship mode and sees only ranked mentors. A user with "Open to mentoring" on sees only ranked mentees. A PhD user with both toggles on can use either view.
  2. Mentors are ranked on two-way give/need fit. In the top results, the mentor's needs visibly line up with the junior's contributable skills, and the mentor's offers line up with the junior's learning goals.
  3. Every mentorship match spells out both sides of the exchange: what the junior gets and what the mentor gets.
  4. Mentorship matches are cached separately from peer matches and refresh the same way. When Gemini fails, they fall back to embedding-only ranking with a notice.

**Notes**: Most of this phase is configuring the Phase 4 pipeline for a new `mode`:
- The shortlist filters by `seeking_mentor` / `open_to_mentoring`.
- The rerank prompt and schema add `they_give_you` / `you_give_them`.
- The cache is keyed by user + mode.

You can send a connection request from a mentorship match using the Phase 5 flow.
**Docs capture**: mode switch, ranked mentors for a junior, ranked mentees for a mentor, two-sided explanation, mentorship fallback notice
**Plans**: TBD
**UI hint**: yes

### Phase 7: AI Profile Autofill

**Goal**: A researcher can paste text or upload a PDF CV and have Gemini pre-fill the profile form, then review and edit it before saving. Manual entry always remains available.
**Mode:** mvp
**Depends on**: Phase 2 (independent of matching and connections)
**Requirements**: AUTO-01, AUTO-02, AUTO-03, AUTO-04
**Success Criteria** (what must be TRUE):
  1. A user pastes a bio, CV text, or Scholar/LinkedIn "about" text, and the profile form fields fill in with structured values.
  2. A user uploads a PDF CV, and the form fills in the same way.
  3. Nothing is saved until the user reviews, edits and clicks Save. Leaving without saving leaves the stored profile unchanged.
  4. A rate limit, an unreadable or oversized file, or malformed AI output shows a clear message and leaves the form usable for manual entry.

**Notes**:
- **Cuttable:** this phase can be cut. If time slips, cut PDF (AUTO-02) first, then text (AUTO-01). Move anything cut to v2 and list it in the limitations document.
- **Order:** it only depends on Phase 2, so it can start earlier or run in parallel if there is slack.
- **PDF handling:** PDFs go inline with `types.Part.from_bytes`. pypdf is used only for pre-flight checks.
- **Privacy:** disclose in the AI-use declaration that Google may use free-tier inputs, CVs included.

**Docs capture**: paste-text autofill result, PDF autofill result, review-before-save form, failure message with manual fallback
**Plans**: TBD
**UI hint**: yes

### Phase 8: Docs & Demo Readiness

**Goal**: The project is ready to grade and demo. Every rubric document exists and matches the shipped app, and a rehearsed runbook makes the live demo dependable.
**Mode:** mvp
**Depends on**: Phase 6 (and Phase 7 if shipped)
**Requirements**: DOCS-01, DOCS-02, DOCS-03, DOCS-04, DOCS-05, DOCS-06, OPS-04
**Success Criteria** (what must be TRUE):
  1. A reader can set up the app and use every feature from the README / user manual alone. The architecture diagram matches the implemented system: Streamlit views → services → repos/ai → Supabase/Gemini.
  2. The test report has a screenshot for each use case and the anchor-profile top-3 evaluation. The use cases are:
     - sign-in
     - profile
     - Discover
     - matches, including the fallback
     - connections, including email unlock
     - mentorship
     - autofill, if it shipped
  3. Three documents exist: limitations, AI-use declaration, and source/data documentation. Together they cover:
     - free-tier quotas
     - the synthetic data and how it was generated
     - no identity verification
     - final declines
     - the accuracy of AI explanations, and bias
     - the AI inside the product and the AI used to build it
     - Google's use of free-tier Gemini inputs
  4. The pre-demo runbook (T-24h / T-2h / T-30min) has been run end to end in a live rehearsal: Streamlit app woken, Supabase confirmed active, demo login tested, and the demo account's peer and mentorship matches pre-warmed.

**Notes**: Assemble the documents from the screenshots collected in each phase. Check that every document matches the code before submitting. If the GitHub cron hasn't run recently, confirm it is still enabled; GitHub disables scheduled workflows after 60 days without repo activity.
**Docs capture**: final runbook checklist with rehearsal results
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Sign-in | 4/4 | In Progress|  |
| 2. Researcher Profiles | 0/TBD | Not started | - |
| 3. Researcher Pool & Discover | 0/TBD | Not started | - |
| 4. AI Peer Matching | 0/TBD | Not started | - |
| 5. Connections & Email Unlock | 0/TBD | Not started | - |
| 6. Mentorship Mode | 0/TBD | Not started | - |
| 7. AI Profile Autofill | 0/TBD | Not started | - |
| 8. Docs & Demo Readiness | 0/TBD | Not started | - |
