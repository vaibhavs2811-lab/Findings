# Requirements: Findings

**Defined:** 2026-10-05
**Core Value:** A signed-in researcher can open Findings and get a ranked list of AI-picked collaborators (or mentors/mentees), each with a believable "why you match" explanation, then send one of them a connection request. That works live, reliably, in the demo.

## v1 Requirements

Requirements for the graded demo (~2026-10-19). Each maps to one roadmap phase.

### Authentication

- [ ] **AUTH-01**: User can request a 6-digit sign-in code by email and sign in by typing it into the app. This works for any email address because custom SMTP (Brevo) is configured
- [ ] **AUTH-02**: A first-time user's account is created automatically on their first successful code sign-in, for both the "new user" and "returning user" email templates
- [ ] **AUTH-03**: A pre-made demo account can sign in with email + password, so the live demo never depends on an inbox
- [ ] **AUTH-04**: User stays signed in after a browser refresh (cookie-based session restore)
- [ ] **AUTH-05**: User can sign out from any page
- [ ] **AUTH-06**: Each browser session is isolated. Two users signed in at the same time never see each other's session or data (per-session Supabase client, never cached globally)

### Profiles

- [ ] **PROF-01**: User can create and save a profile with name, career stage, institution, education background, research interests, research experience, skills, bio, and "looking for"
- [ ] **PROF-02**: Career stage is picked from a fixed list: Undergrad / Master's / PhD / Postdoc / Faculty / Industry researcher
- [ ] **PROF-03**: User has "Seeking a mentor" and "Open to mentoring" toggles. They default from career stage (Undergrad/Master's → seeking; Postdoc/Faculty/Industry → open; PhD → user chooses) and the user can override them
- [ ] **PROF-04**: User can fill structured give/need fields: what they **offer** (e.g. methods training, co-authorship, guidance), what they **need** (e.g. data collection, lit review, coding, transcription), **skills they can contribute**, and what they **want to learn**
- [ ] **PROF-05**: Methods orientation (qualitative / quantitative / mixed) is AI-suggested from the profile text when the profile is saved. The user can override it, and the profile shows the effective value as a badge
- [ ] **PROF-06**: User can edit only their own profile. Writes to anyone else's are rejected by Row Level Security
- [ ] **PROF-07**: User can open another researcher's profile page and see their public fields. Contact email is never shown here

### AI Autofill

- [ ] **AUTO-01**: User can paste text (bio, CV text, Scholar/LinkedIn "about") and have Gemini pre-fill the profile form with structured fields
- [ ] **AUTO-02**: User can upload a PDF CV and have Gemini pre-fill the profile form the same way
- [ ] **AUTO-03**: Autofill only pre-fills the form. The user reviews and edits, and nothing is saved until they click Save
- [ ] **AUTO-04**: If autofill fails (rate limit, bad file, malformed output), the user sees a clear message and can still fill the form manually

### Discover

- [ ] **DISC-01**: User can browse researcher profiles as cards showing name, career stage, methods badge, top interests, and a "Synthetic" label where applicable
- [ ] **DISC-02**: User can filter cards by methods orientation (qual / quant / mixed)
- [ ] **DISC-03**: User can filter cards by career stage
- [ ] **DISC-04**: User can search cards by interest keyword
- [ ] **DISC-05**: User can Skip a card, which hides it for the rest of the session
- [ ] **DISC-06**: User can open a connection request directly from a card

### AI Matching (peer collaborators)

- [ ] **MATCH-01**: User can open "My Matches" and see a ranked list of the best peer collaborators (excluding themselves and existing connections). Each match has a match-strength label and a "why you match" explanation that cites concrete details from both profiles
- [ ] **MATCH-02**: Each profile's embedding (Gemini, 768-dim) is computed when the profile is saved, and only when its content changed. A pgvector search then shortlists the top ~15 candidates with no Gemini call
- [ ] **MATCH-03**: One Gemini call reranks the shortlist with structured output. Methods complementarity (e.g. qual + quant for mixed methods) is considered, returned candidates are validated against the shortlist, and profile text is treated as untrusted input
- [ ] **MATCH-04**: Match results are cached per user and mode, and reused until the user's profile changes or they click Refresh
- [ ] **MATCH-05**: If Gemini fails or is rate-limited, the user still sees matches ranked by embedding similarity, with a visible notice instead of an error

### Mentorship Mode

- [ ] **MENT-01**: User can switch to Mentorship mode. Users seeking a mentor see ranked mentors, and users open to mentoring see ranked mentees
- [ ] **MENT-02**: Mentorship ranking scores give/need fit in both directions: the mentor's needs against the junior's contributable skills, and the mentor's offers against the junior's learning goals
- [ ] **MENT-03**: Each mentorship match explains both sides of the exchange: what the junior gets and what the mentor gets
- [ ] **MENT-04**: Mentorship matches use the same cache and fallback behaviour as peer matches

### Connections

- [ ] **CONN-01**: User can send a connection request with a short note from a match, a card, or a profile page
- [ ] **CONN-02**: User can see incoming pending requests and accept or decline each one
- [ ] **CONN-03**: Only the recipient can accept or decline a request. A duplicate request between the same two people is blocked
- [ ] **CONN-04**: Once a request is accepted, both users can see each other's contact email. Before that, the email can't be read by any query (enforced in the database, not just the UI)
- [ ] **CONN-05**: User can see their sent, received, and accepted connections on a Connections page
- [ ] **CONN-06**: A request sent to a synthetic profile is accepted automatically, revealing its example.org address, and is labelled as synthetic

### Seed Data

- [ ] **DATA-01**: A one-off seed script generates 60–100 diverse synthetic researcher profiles with Gemini, spread across fields, career stages, methods, and mentoring roles, and saves them to a committed JSON file
- [ ] **DATA-02**: A loader inserts the seed profiles into Supabase with embeddings, `is_synthetic = true`, and example.org emails. It uses the secret key locally only
- [ ] **DATA-03**: Synthetic profiles are visibly labelled everywhere they appear

### Deployment & Operations

- [ ] **OPS-01**: The app is deployed on Streamlit Community Cloud on Python 3.12, with secrets set in the Cloud dashboard. No secrets are committed to the repo
- [ ] **OPS-02**: Custom SMTP is configured, and both Supabase email templates send the 6-digit code
- [ ] **OPS-03**: A daily GitHub Actions workflow queries Supabase so the project never auto-pauses, and it can also be run manually
- [ ] **OPS-04**: A pre-demo runbook exists and has been rehearsed. It covers waking the Streamlit app, confirming Supabase is active, testing the demo login, pre-warming the demo account's matches, and a live rehearsal

### Documentation (rubric-required)

- [ ] **DOCS-01**: README / user manual covering setup and how to use each feature
- [ ] **DOCS-02**: Architecture diagram that matches the implemented system
- [ ] **DOCS-03**: Test report with screenshots of each use case
- [ ] **DOCS-04**: Limitations document. It covers free-tier quotas, synthetic data, no identity verification, AI explanation accuracy, and bias
- [ ] **DOCS-05**: AI-use declaration covering the AI inside the product (autofill, methods label, matching), the AI used to build it, and the fact that Google may use free-tier Gemini inputs
- [ ] **DOCS-06**: Source/data documentation, including how the synthetic dataset was generated

## v2 Requirements

Deferred. Tracked but not in the current roadmap.

### Reliability & Testing

- **REL-01**: Config flag that forces the Gemini path to fail, so the embedding-only fallback can be shown on demand
- **REL-02**: Seeded pending request from a synthetic profile to the demo account

### Discovery

- **DISC-07**: Skips persist across sessions (`skips` table)
- **DISC-08**: Reciprocal / mutual-interest signal in ranking

### Matching

- **MATCH-06**: Second embedding of offers/needs only, for better shortlist recall in mentorship mode
- **MATCH-07**: Approximate nearest-neighbour index (HNSW), once the pool grows past a few thousand profiles

### Profiles

- **PROF-08**: Import publications from ORCID / Google Scholar
- **PROF-09**: Verified institutional email or ORCID badge

## Out of Scope

| Feature | Reason |
|---------|--------|
| In-app chat / messaging | Too much build for <2 weeks; the email unlock on accept replaces it |
| Swipe-gesture card UI | Streamlit can't do gestures well; Connect / Skip buttons carry the idea |
| Magic-link login | Streamlit can't read the URL-fragment token; replaced by an email code |
| Email/push notifications for requests | Costs SMTP quota; users check the Connections page |
| Admin / moderation dashboard | Course-project scale |
| h-index / reputation metrics | Excludes juniors, which works against the mentorship goal |
| Group / team matching | Pairwise matching only for v1 |
| Fine-tuned or custom ML models | Prompted Gemini + embeddings are enough; $0 budget |
| Live Gemini calls on every page load | Free-tier quota; matches are cached and refreshed on demand |
| Any paid service or tier | Hard $0 constraint |
| Native mobile apps | Web only |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| (filled by roadmapper) | | |

**Coverage:**
- v1 requirements: 51 total
- Mapped to phases: 0 (pending roadmap)
- Unmapped: 51 ⚠️

---
*Requirements defined: 2026-10-05*
*Last updated: 2026-10-05 after initial definition*
