# Findings

## What This Is

Findings is "Hinge for researchers": a web app that matches like-minded researchers who want to collaborate on a topic. Each researcher builds a profile (interests, research experience, education, career stage, methods), the app sorts profiles into qualitative / quantitative / mixed-methods, and an AI matching layer ranks and explains the best collaborators for them. A separate mentorship mode pairs junior researchers with mentors so the exchange runs both ways: juniors see how research is done, and mentors get help or data from juniors.

It is a course project, graded on a rubric and shown in a live demo.

## Core Value

A signed-in researcher can open Findings and get a ranked list of AI-picked collaborators (or mentors/mentees), each with a believable "why you match" explanation, then send one of them a connection request. That works live, reliably, in the demo.

## Requirements

### Validated

(None yet — ship to validate)

### Active

**Accounts & auth**
- [ ] Passwordless sign-in with a **6-digit email OTP code** (Supabase Auth). Chosen over magic links because Streamlit can't read the token in a magic link's URL fragment
- [ ] Session persists while the user navigates the Streamlit app; user can sign out

**Profiles**
- [ ] Manual profile form that saves to Supabase: name, career stage, institution, education background, research interests, research experience, methods orientation, skills, bio, looking_for
- [ ] Career stage picked from a fixed list: Undergrad / Master's / PhD / Postdoc / Faculty / Industry researcher. Junior = Undergrad through early PhD; mentor-eligible = Postdoc and above
- [ ] Structured give/need fields for the symbiotic exchange. Mentors list what they **offer** (methods training, co-authorship, guidance) and what they **need** (data collection, lit review, coding, transcription). Juniors list the **skills they can contribute** and what they **want to learn**
- [ ] Methods orientation (qualitative / quantitative / mixed): AI suggests a label from the profile text, the user can override it, and it is used both as a Discover filter and as a matching signal (e.g. pairing qual + quant people for mixed-methods work)
- [ ] Users can only edit their own profile (Row Level Security)

**AI autofill**
- [ ] User can **paste text** (bio, CV text, Scholar/LinkedIn "about") OR **upload a PDF CV**; Gemini returns structured JSON that pre-fills the form; the user reviews and edits before saving

**Discover**
- [ ] Browse researcher profiles from Supabase as cards
- [ ] Filter by methods orientation, career stage, and interest keywords

**AI matching (peer collaborators)**
- [ ] Two-stage matching. (1) Gemini embeddings stored in Supabase **pgvector** shortlist the top ~15 candidates by similarity. (2) Gemini reranks that shortlist against the user's profile and returns a score plus a short "why you match" explanation for each
- [ ] Match results are cached per user (recomputed when their profile changes) to stay within free-tier quotas
- [ ] Graceful degradation: if Gemini errors or is rate-limited, show the embedding-only ranking with a notice instead of crashing

**Mentorship mode**
- [ ] Separate "Find a mentor" / "Find a mentee" mode that only matches across the junior ↔ mentor split
- [ ] The AI ranks on give/need fit: how well the mentor's needs match the junior's contributable skills, and the mentor's offers match what the junior wants to learn. Explanations spell out both sides of the exchange

**Connections (the "Hinge" mechanic)**
- [ ] User can send a connection request with a short note to a match or a profile
- [ ] Recipient sees incoming requests and can accept or decline
- [ ] On accept, both users can see each other's contact email. Email stays hidden before that
- [ ] User can see sent / received / accepted connections

**Seed data**
- [ ] One-off seeding script (not a live feature) that generates ~60–100 diverse synthetic researcher profiles via Gemini, spread across fields, career stages, and methods, saves them to a committed JSON file, and inserts them into Supabase tagged `is_synthetic = true` with embeddings
- [ ] Synthetic profiles are visibly labelled in the UI

**Deployment & reliability**
- [ ] Deployed on Streamlit Community Cloud with secrets set in its dashboard
- [ ] A free GitHub Actions cron pings Supabase every few days so the project doesn't auto-pause (7-day idle limit)
- [ ] Pre-demo checklist: Supabase awake, Streamlit app woken (12-hour sleep), demo account works, live rehearsal done

**Documentation deliverables (rubric-required)**
- [ ] README / user manual
- [ ] Architecture diagram
- [ ] Test report with screenshots of the use cases
- [ ] Limitations document
- [ ] AI-use declaration
- [ ] Source / data documentation (including how the synthetic data was made)

### Out of Scope

- In-app chat or messaging — contact email unlocks on accept instead; chat is too much build for a <2-week timeline
- Swipe-card gesture UI — Streamlit can't do it well; cards with Connect / Skip buttons carry the same idea
- Magic-link login — fragile with Streamlit's URL handling; replaced by email OTP
- Paid services of any kind (paid hosting, paid LLM tiers, paid vector DBs) — hard free-tier constraint
- Native mobile apps — web only
- Verifying researcher identity or credentials (ORCID, institutional email checks) — not needed for the demo; listed as a limitation
- Importing publications from Google Scholar / ORCID APIs — nice-to-have, not core to matching
- Notifications (email or push) when a request arrives — users check the Connections page
- Admin dashboard / moderation tooling — course-project scale

## Context

- **Who it's for:** academic researchers from undergrads to faculty and industry researchers. Peers looking for collaborators on a topic, and junior ↔ senior pairs looking for mentorship that benefits both sides.
- **Why it exists:** finding collaborators today runs on conferences, cold emails, and advisor networks. Juniors without networks struggle to get research exposure, and seniors are short on hands for data collection and analysis.
- **Course setting:** graded against a rubric with fixed documentation deliverables and a live demo. Reliability during the demo matters more than feature breadth.
- **The user's suggested starting architecture** (Streamlit + Supabase + Gemini + Streamlit Cloud) is kept and improved:
  - Magic link → email OTP code (works inside Streamlit)
  - Pure LLM ranking → embeddings + pgvector shortlist, then Gemini rerank with explanations, plus a result cache (scales on the free tier)
  - Minimal `profiles` table → expanded schema (career stage, education, experience, methods orientation with AI-suggested vs user-set values, skills, offers/needs, embedding vector) plus a `connections` table (requester, recipient, note, status, timestamps) and a match cache
  - Manual "check Supabase isn't paused" → GitHub Actions keep-alive cron
  - Seeding writes to a committed JSON first, so the synthetic dataset is reproducible and documented
- **Free-tier limits to design around:** Gemini free-tier requests-per-minute and per-day caps (exact current numbers to be confirmed during research), Supabase free project pauses after 7 days idle, Streamlit Community Cloud apps sleep after ~12 hours without traffic.

## Constraints

- **Budget:** $0. Every part (frontend, backend, database, auth, hosting, AI) must run on a free tier — hard requirement from the user
- **Timeline:** under 2 weeks to the demo (by ~2026-10-19) — scope stays on the core build order, and polish comes after core flows work
- **Tech stack:** Python + Streamlit (UI and hosting on Streamlit Community Cloud), Supabase (Postgres, Auth, RLS, pgvector), Google Gemini via `google-genai` (generation and embeddings), GitHub (repo plus Actions cron)
- **Security:** secrets live only in `.streamlit/secrets.toml` locally (gitignored) and in Streamlit Cloud secrets. Only the Supabase anon key is used client-side, with RLS enforcing per-user writes. The service-role key is used only by the local seeding script
- **Privacy:** contact email is hidden until a connection is accepted. Synthetic profiles are clearly labelled
- **Demo reliability:** the AI path must degrade gracefully (embedding-only fallback). The demo must not depend on a single Gemini call succeeding

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Streamlit + Supabase + Gemini + Streamlit Cloud | User's suggested stack, all free tier, fastest path to a Python demo | — Pending |
| Email OTP code instead of magic link | Magic-link tokens come back in a URL fragment Streamlit can't read; OTP works natively | — Pending |
| Embeddings + pgvector shortlist, then Gemini rerank + explanations | Keeps Gemini calls small and few, so it fits free-tier limits; scales past ~50 profiles | — Pending |
| Cache match results per user | Protects the Gemini quota and makes the demo fast | — Pending |
| Request → accept connection mechanic; email unlocks on accept | The "Hinge" feel without building chat | — Pending |
| Methods orientation: AI-suggested + user override; used as a filter and a matching signal | User chose "both"; enables qual + quant pairing for mixed methods | — Pending |
| Career stage list sets the junior/mentor split (Undergrad–early PhD = junior, Postdoc+ = mentor) | Objective and simple to explain | — Pending |
| Separate mentorship match mode with structured offer/need fields | Makes the symbiotic exchange explicit and explainable | — Pending |
| Autofill from pasted text and PDF CV | User wanted both; Gemini handles PDFs natively | — Pending |
| Seed ~60–100 synthetic profiles via a one-off script into a committed JSON | Reproducible, documentable data for the demo and the rubric | — Pending |
| GitHub Actions keep-alive cron for Supabase | Prevents the 7-day auto-pause at no cost | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-10-05 after initialization*
