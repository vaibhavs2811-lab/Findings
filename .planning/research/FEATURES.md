# Feature Research

**Domain:** AI-powered researcher collaboration + junior/mentor matching web app ("Hinge for researchers")
**Project:** Findings
**Researched:** 2026-10-05
**Confidence:** MEDIUM. The competitor and mechanic facts come from general web search (the confidence seam rates `websearch` as LOW on its own). They agree with each other and with standard product knowledge, so I treat the landscape as MEDIUM. Complexity estimates are judgments for a Streamlit + Supabase + Gemini stack in under 2 weeks.

## Framing: what the market looks like

| Product family | What it does well | What it lacks (Findings' opening) |
|---|---|---|
| ResearchGate / Academia.edu | Rich profiles (interests, publications, metrics), follow researchers and topics, "suggested researchers" from publication/citation graph, Q&A, paper sharing | No explicit "who should I work with and why." Recommendations are opaque and publication-driven, so they exclude juniors who have no papers. No structured mentor-gives/junior-gives exchange. No methods (qual/quant/mixed) awareness. |
| ORCID-linked expert finders (university "find an expert" tools, Elsevier Pure, Kudos) | Identity and publication verification, keyword/topic search | Search, not matching. Directory UX, no connection flow, no explanations. |
| Mentorship platforms (MentorCruise, Chronus, Mentorly, MentorcliQ) | Profile plus preference-based matching, request/accept flow, program admin tooling, session tracking, rematch | Built for corporate or paid-mentor settings. Mentorship is one-directional (mentor gives, mentee takes). Heavy admin and scheduling features. Nothing research-specific. |
| Dating apps (Hinge) | Prompts that reveal personality, a like with a comment on a specific item, mutual match unlocks contact, ranking by likelihood of reciprocal interest | Not applicable to professional context, but the interaction grammar is the proven hook. |

**Findings' positioning (this is what the demo must show):** a ranked list with a believable "why you match" explanation, plus a two-way give/need mentorship exchange that no competitor has. Everything else is table stakes to build cheaply or leave out.

## Feature Landscape

### Table Stakes (Users Expect These)

Missing these makes the product feel broken or unfinished. Users and graders give no credit for them but penalize their absence.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Passwordless sign-in (email OTP), session persistence, sign-out | Every network has accounts. A demo needs a stable identity. | MEDIUM | Streamlit session-state plus Supabase OTP is the fiddly part (token refresh across reruns). Budget real time. Pre-create a demo account. |
| Researcher profile: name, career stage, institution, education, interests, experience, skills, bio, looking_for | The core object. ResearchGate, Academia.edu, and every mentor platform have it. | LOW | One form, one `profiles` row. Career stage is a fixed enum, which makes the junior/mentor split free. |
| Methods orientation (qual / quant / mixed) on the profile | Stated core feature. The key research-specific field. | LOW | Plain selectbox. AI suggestion is a differentiator layer on top (below). |
| Edit own profile only (RLS) | Basic trust and security. Graders will probe it. | LOW | Supabase RLS policy. Test it explicitly for the test report. |
| Profile cards in a browse view | Discovery feed is the "Hinge" surface. | LOW | `st.container` cards: name, stage, institution, methods badge, top interests, "Synthetic" badge. |
| Filters: methods orientation, career stage, interest keyword | Every directory has filters. This is the minimum discovery. | LOW | Server-side `where` / `ilike`. Keep to these three. |
| Connection request with short note | The Hinge-equivalent action. Without it, matching is a dead end. | LOW-MEDIUM | `connections` table (requester, recipient, note, status). Prevent duplicate and self-requests (unique constraint). |
| Accept / decline incoming requests | The "mutual" half of the mechanic. | LOW | Status update, gated to the recipient by RLS. |
| Connections view (sent / received / accepted) | Users must see state. Otherwise requests vanish. | LOW | Three tabs over one query. |
| Contact reveal only after accept | Core privacy promise in PROJECT.md. Doubles as the "no chat" substitute. | LOW-MEDIUM | Do not fetch email in the browse query. Expose it only through a view or RPC joined on `status='accepted'`, enforced in the database. A UI-only hide is a security bug. |
| Pre-seeded realistic profiles, visibly labelled synthetic | A matching app with an empty pool shows nothing. Labelling is an honesty and rubric requirement. | MEDIUM | Already scoped as a one-off script. Diversity of fields, stages, and methods is what makes the demo convincing. Include deliberately complementary qual+quant pairs and junior/mentor pairs so the AI has good answers to find. |
| Graceful error and empty states | A live demo that throws a stack trace loses points. | LOW | "No matches yet" and "Gemini busy, showing similarity ranking." |
| Sign-up data hygiene: required fields, length limits on free text | Prevents broken cards and prompt-injection-sized bios. | LOW | See safety section. |

### Differentiators (Competitive Advantage)

These align with the Core Value: ranked, explained matches that lead to a connection request, working live.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **AI match ranking with a "why you match" explanation per candidate** | The central differentiator. ResearchGate recommends opaquely. Findings says why in plain language, in two or three sentences, and can cite concrete overlaps. | MEDIUM-HIGH | Two-stage already decided: pgvector shortlist, then Gemini rerank. The explanation quality is what impresses. Ground the prompt in only the two profiles' fields so it can't invent facts (see Pitfalls on hallucinated explanations). Cache per user. Fallback: embedding-only ranking plus a template explanation built from shared interests. |
| **Explanations with structured parts** (shared interests, complementary methods, what each side gains) | Makes the explanation scannable and checkable, which beats a paragraph of fluent text. | LOW-MEDIUM | Ask Gemini for JSON: `score`, `shared_topics[]`, `complementarity`, `why`. Render as chips plus one sentence. Reduces hallucination surface. |
| **Qual + quant complementarity as a matching signal** | Research-specific. A qual person pairing with a quant person for mixed-methods work is a genuine insight, and no generic network does it. | LOW-MEDIUM | A prompt instruction plus the methods field as a rerank input. Not a separate algorithm. Show it in the explanation ("pairs your interviews with their survey modeling"). |
| **Symbiotic mentorship mode: offers/needs vs. contributable skills/learning goals** | The unique value proposition: the exchange runs both ways. Competitors only model mentor-gives, mentee-takes. | MEDIUM | Four structured fields (mentor offers, mentor needs, junior can-contribute, junior wants-to-learn). Matching restricted to the junior to mentor split. The explanation must name both directions explicitly ("You need transcription help, she can do it. She wants to learn mixed-methods design, you offer it."). |
| **AI profile autofill from pasted text or PDF CV** | Removes the biggest onboarding friction. Visually impressive in a demo (paste, watch the form fill). | MEDIUM | Gemini structured output to JSON, reviewed and editable before save (never auto-save). PDF via Gemini native file input. Needs a strict JSON schema, enum mapping (career stage must match the fixed list), and a failure path that leaves the form blank. |
| **AI-suggested methods orientation with user override** | Shows AI helping without taking control. The user stays in charge. | LOW | Same Gemini call as autofill, or a small separate one. Store AI-suggested and user-set values separately. |
| **Match score shown with the explanation** (e.g. 87% fit) | Gives the ranked list a visible, comparable number and adds "wow" to the demo. | LOW | Display only the rerank score. Be careful: scores from an LLM are soft. Show as a band or bar, not false precision. |
| **Mode toggle: Peers vs. Mentorship (Find a mentor / Find a mentee)** | Clear product story and a clean demo path with two flows. | LOW | A top-level `st.radio` or tabs. Same match machinery, different prompt and candidate filter. |
| **Graceful AI degradation visible to the user** | Reliability is a stated priority. A visible "fallback" notice demonstrates engineering maturity to graders. | LOW | Already scoped. Make the fallback visible and honest rather than silent. |
| **Match cache with "refresh matches" button** | Fast demo loads, plus quota protection. A manual refresh gives presenters control. | LOW-MEDIUM | Cache keyed on a profile content hash. Invalidate on profile edit. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| In-app chat / messaging | "Hinge has chat." Feels like the natural next step after a match. | Realtime state, unread counts, moderation, and abuse vectors, all hard on Streamlit's rerun model. Large scope for a <2-week demo. | Email unlocks on accept. Say in the limitations doc that chat is future work. |
| Swipe-card gesture UI | The most literal "Hinge/Tinder" look. | Streamlit can't do gestures well. Custom components eat days. | Card with Connect / Skip buttons, same decision model. |
| Auto-importing publications (Google Scholar, ORCID, Semantic Scholar) | Researchers are defined by publications. Looks impressive. | Scholar has no API. Scraping is brittle and may violate terms. ORCID OAuth needs more setup. Adds auth and data-quality risk, and isn't needed to demonstrate matching. | Paste text or CV already covers publication content for the embedding. List as a limitation. |
| Credential or identity verification (ORCID, institutional email) | Trust. Prevents fakes. | Not required for the demo and adds friction. Synthetic profiles can't pass it anyway. | Be explicit in limitations. Show a "Synthetic" label now and note verification as future work. |
| Email or push notifications for new requests | Real products notify. | SMTP setup, deliverability, and quota on free tiers. Low demo value. | A badge or count on the Connections page. |
| Admin / moderation dashboard | "Real" platforms need moderation. | Course-scale overreach. | Minimal safety set (below) plus a documented limitation. |
| Citation / h-index / "RG Score" metrics on profiles | Familiar from ResearchGate. | Gameable, needs publication data, and reinforces seniority bias that Findings' junior mode is meant to counter. | Match on interests, methods, and give/need. |
| Fully live AI generation on every page load | Looks "more AI." | Burns the free-tier Gemini quota, slows the app, and makes the demo flaky. | Precompute embeddings. Rerank once per user, then cache. |
| Training or fine-tuning a custom matching model | "Real ML." | No interaction data exists, and there's no time. | Embeddings plus an LLM rerank are state of the art for a cold-start system. |
| Real-time collaborative workspace, project boards, or file sharing | Natural follow-on to a match. | Scope explosion. | Out of scope. Describe as a roadmap item. |
| Public profile pages, SEO, social graph (follow/feed/likes) | ResearchGate-style growth. | Turns a matching tool into a social network and requires moderation and content. | Cards in Discover only, behind sign-in. |
| Payment or paid mentor listings (MentorCruise-style) | Common in mentor marketplaces. | Violates the $0 constraint and changes the product. | Reciprocal exchange is the currency. |
| Calendar or session scheduling | Mentor platforms all have it. | Integrations plus time-zone handling. | Contact email after accept, and they arrange it. |
| Group or lab matching (3+ people) | Real collaborations are often multi-person. | Combinatorial matching, a different UI, and a different data model. | Pairwise only. |

## Feature Dependencies

```
Email OTP auth + session
    └──requires──> Profiles table + RLS
                       ├──requires──> Profile form (manual)
                       │                  └──enhanced by──> AI autofill (text/PDF) ──> AI methods suggestion
                       ├──requires──> Seed data (synthetic profiles + embeddings)
                       │                  └──requires──> Embedding pipeline (shared with live profile save)
                       └──requires──> Discover cards + filters

Embedding pipeline (Gemini embeddings -> pgvector)
    └──requires──> Profile text assembled from fields
    └──enables──> Shortlist (top ~15)
                       └──requires──> Gemini rerank + explanation
                                          ├──requires──> Match cache (+ invalidation on profile edit)
                                          ├──requires──> Embedding-only fallback
                                          └──enhanced by──> Methods complementarity signal

Mentorship mode
    ├──requires──> Career stage enum (junior/mentor split)
    ├──requires──> Offers / needs / can-contribute / wants-to-learn fields on profile
    └──requires──> Rerank prompt variant (two-directional explanation)

Connection request
    ├──requires──> Auth + Profiles
    ├──enhances──> Matches and Discover (the "Connect" button on every card)
    └──requires──> Accept/decline ──requires──> Connections view ──gates──> Contact email reveal

Safety basics (field limits, block/skip, duplicate request guard) ──applies to──> Profile form, Connect flow
```

### Dependency Notes

- **Matching requires seed data and embeddings first.** Without 60+ embedded profiles, the AI features can't be demonstrated or tested. The seed script and embedding pipeline are the critical path, not the UI.
- **AI autofill is independent of matching.** It only writes to the profile form, so it can ship after the manual form and be dropped without breaking anything. It is the safest feature to cut.
- **Mentorship mode requires its own data fields.** It can't reuse peer-matching data. The four give/need fields must exist in the schema from the start. Retrofitting later means a migration and re-embedding.
- **Embedding text should include the give/need fields.** Otherwise the shortlist step misses complementary mentors who share no topic keywords.
- **Cache invalidation depends on profile edits.** Key the cache on a profile hash so edits recompute automatically.
- **Contact reveal depends on the connection state machine.** Enforce it in the database (view or RPC), not in the Streamlit UI.
- **Fallback depends on the shortlist step.** The embedding-only ranking is the same shortlist, minus the rerank, so the fallback costs almost nothing.
- **Skip/hide conflicts with a stateless Discover.** If "Skip" must persist, it needs a small `skips` table. Otherwise skipped cards come back on rerun. Decide early, or make Skip session-only.

## Trust and Safety Basics (scoped for this project)

| Item | Needed? | Complexity | Notes |
|------|---------|------------|-------|
| Contact email hidden until accept | Yes, table stakes | LOW-MEDIUM | Enforce in the DB. See above. |
| "Synthetic" badge on seeded profiles | Yes, table stakes | LOW | `is_synthetic` flag, shown on cards and in match results. |
| Decline with no explanation required | Yes | LOW | Reduces social pressure, and it is the "no-fault" off-ramp that mentoring programs recommend. |
| Block or hide a user | Optional (P2) | LOW-MEDIUM | Skip/hide covers most of the need for a demo. A real block needs a table. |
| Request rate limit or duplicate guard | Yes (cheap) | LOW | Unique (requester, recipient) constraint, and a cap on pending requests. |
| Report a profile | No, document as a limitation | LOW | Without a moderator, a report button is theater. |
| Profile text length caps and sanitization | Yes | LOW | Reduces broken layouts and prompt-injection from profile text into the Gemini rerank (profile bios are untrusted input to the model). |
| Mentor/junior safeguarding (power asymmetry, minors) | Document only | LOW | Undergrads are adults, but note that unverified identity is a limitation. Don't add age gates. |
| Privacy note and data-use explanation | Yes (doc) | LOW | The rubric wants AI-use and data documentation. Say plainly that profile text goes to Gemini. |

## MVP Definition

### Launch With (v1: the demo path)

Ordered by dependency and demo-criticality.

- [ ] Email OTP auth and persistent session. Everything else needs identity.
- [ ] Profile form with all fields and RLS. This is the core object.
- [ ] Seed script, ~60-100 labelled synthetic profiles with embeddings. Without these, nothing else can be shown.
- [ ] Discover cards plus three filters. This is the simplest visible win and the fallback demo if AI fails.
- [ ] Connection request, accept/decline, Connections view, and email reveal on accept. This closes the Core Value loop ("then send a request").
- [ ] Peer AI matching: pgvector shortlist, Gemini rerank, explanation, cache, and embedding-only fallback. This is the Core Value.
- [ ] Mentorship mode with give/need fields and a two-sided explanation. This is the distinguishing story.
- [ ] Safe-by-default basics: DB-enforced email gating, field caps, duplicate-request guard, synthetic labels.

### Add After Core Works (v1.x: only if the core is rehearsed and stable)

- [ ] AI autofill from pasted text. Highest-wow, lowest-risk add-on. Do it before PDF.
- [ ] AI autofill from PDF CV. Add after the text path works, using the same schema.
- [ ] AI methods-orientation suggestion with override. It can share the autofill call.
- [ ] Structured explanation chips (shared topics, complementarity) on top of the plain sentence.
- [ ] Persistent Skip/hide, if session-only skip looks weak in rehearsal.
- [ ] Compatibility score bar.

### Future Consideration (v2+: put in the limitations doc)

- [ ] In-app chat, notifications, scheduling.
- [ ] ORCID/Scholar import and identity verification.
- [ ] Report/block with moderation.
- [ ] Outcome feedback loop ("was this match useful?") to tune ranking.
- [ ] Group/lab matching. Project-level matching ("looking for a co-author on X").

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Email OTP auth + session | HIGH | MEDIUM | P1 |
| Profile form + RLS | HIGH | LOW | P1 |
| Seed data + embeddings | HIGH | MEDIUM | P1 |
| Discover cards + filters | HIGH | LOW | P1 |
| Connection request/accept/view + email reveal | HIGH | MEDIUM | P1 |
| Peer AI match + explanation + cache + fallback | HIGH | HIGH | P1 |
| Mentorship mode (two-sided give/need) | HIGH | MEDIUM | P1 |
| DB-enforced privacy + field caps + duplicate guard | HIGH | LOW | P1 |
| AI autofill from text | HIGH | MEDIUM | P2 |
| AI autofill from PDF | MEDIUM | MEDIUM | P2 |
| AI methods suggestion + override | MEDIUM | LOW | P2 |
| Structured explanation chips | MEDIUM | LOW | P2 |
| Match score bar | MEDIUM | LOW | P2 |
| Persistent skip/hide | LOW | LOW-MEDIUM | P3 |
| Block / report | LOW | MEDIUM | P3 (document only) |
| Chat, notifications, scheduling, imports, verification | LOW (for the demo) | HIGH | Out of scope |

**Priority key:**
- P1: Must have for the demo
- P2: Should have, add once P1 is rehearsed
- P3: Nice to have, or documented as a limitation

### Complexity honesty (for the roadmap)

- **Real risk (HIGH):** the AI match pipeline. It touches embeddings, pgvector, the rerank prompt, a JSON schema, a cache, a fallback, and free-tier quotas. Most debugging time will go here. Prototype the rerank on the seed data early.
- **Hidden risk (MEDIUM):** Streamlit auth/session persistence across reruns, and DB-enforced email gating. Both look trivial and both eat a day.
- **Looks hard, is not:** filters, cards, connection states, and the mode toggle. These are CRUD.
- **Quality risk, not code risk:** synthetic data realism and explanation quality. These are what make the demo convincing, so budget time to read the outputs and tune prompts.
- **First thing to cut if time slips:** PDF autofill, then text autofill, then explanation chips. Never cut the fallback or the email gating.

## What Makes a Convincing Demo

1. **Pre-seeded, diverse data.** The pool should contain obvious, findable pairs so the AI "wins" visibly: a qual sociologist and a quant economist on a shared topic, and a PhD student whose "wants to learn" lines up with a postdoc's "offers."
2. **Show the explanation, not just the list.** Ranked cards with a score and a two- or three-sentence "why you match" that cites specific overlaps. This is the single most memorable moment.
3. **Show both directions of the mentorship exchange.** Pick a demo junior whose skills answer a mentor's need and whose goals match the mentor's offer. Then point at both halves in the explanation.
4. **Close the loop on stage.** Send a request with a note, then switch to the second demo account, accept it, and show the email appear. The before/after of "email hidden, then visible" sells the privacy design.
5. **Two accounts ready (junior and mentor/peer), logged in, in two browser profiles.** Pre-warm Supabase and Streamlit. Make sure the OTP email arrives. Have a screenshot backup in case it doesn't.
6. **Have the autofill moment (if built) on a prepared CV.** Use a CV that parses cleanly. Show the user reviewing and editing before saving.
7. **Pre-rehearse the fallback.** Demonstrate it once intentionally (or have it screenshotted) so a Gemini failure live looks like a feature.
8. **Stay on the happy path.** Do one peer flow and one mentorship flow, each under two minutes. Don't free-form query live.
9. **Be upfront about the synthetic data.** The badge is honest, and graders reward it.

## Competitor Feature Analysis

| Feature | ResearchGate / Academia.edu | Mentor platforms (MentorCruise, Chronus) | Hinge | Our Approach |
|---------|-----------------------------|------------------------------------------|-------|--------------|
| Profile | Publications, metrics, interests | Skills, goals, experience, preferences | Photos plus personality prompts | Structured research profile with a methods field, career stage, and give/need |
| Discovery | Follow topics and people, suggested researchers (opaque) | Browse mentor directory, filter | Curated stack | Cards plus filters, plus AI-ranked list |
| Match logic | Publication/citation graph | Preference/profile-field and AI SmartMatch | Predicts mutual interest | Embeddings shortlist, then LLM rerank on research fit and complementarity |
| Explanation | None | Mostly none (a match score at most) | None | Explicit "why you match" per candidate |
| Mentorship exchange | None | One-way (mentor to mentee) | n/a | Two-way: offers/needs vs. contributable skills/learning goals |
| Connection | Follow or message | Request to mentor, admin or auto-pairing | Mutual like, then chat | Request with note, accept, email reveal |
| Safety | Self-reported identity | Vetting (paid) or admin-managed | Reporting and photo verification | Email gating, labels, field caps. Documented limits |
| Cold-start for juniors | Poor (needs papers) | Good, but needs a mentor pool | n/a | Good: matches on interests, skills, and goals, not publication count |

## Sources

- ResearchGate and Academia.edu feature overviews: university library guides (U Toronto HSICT, Tulane, UW HSL, NCSU) and a PMC review of researcher profiles. Confidence MEDIUM (secondary sources, consistent with each other).
- Mentorship platforms (Chronus, MentorCruise) and matching feature roundups: vendor and review sites (softwarefinder, saasworthy, peoplemanagingpeople), which are marketing-adjacent. Confidence LOW-MEDIUM.
- Hinge mechanics (like on a specific prompt or photo with optional comment, mutual match, prompt likes converting better, ranking toward reciprocal interest): Hinge newsroom (hinge.co/newsroom/hinge-2025-product-evolution) and third-party explainers. Confidence MEDIUM. Treat the Gale-Shapley claim as third-party speculation.
- Why mentoring programs fail (availability-only matching, ghosting, no-fault rematch): Chronus, Mentorloop, Mentorly, and Brancher blog posts. Confidence LOW-MEDIUM (vendor content, but consistent).
- LLM explainable recommendation and hallucination risk (ground the prompt in a limited candidate set): arXiv survey literature, including arxiv.org/pdf/2306.05817 and arxiv.org/pdf/2411.00331. Confidence MEDIUM.
- Project constraints: `.planning/PROJECT.md`.

---
*Feature research for: researcher collaboration and mentorship matching (Findings)*
*Researched: 2026-10-05*
