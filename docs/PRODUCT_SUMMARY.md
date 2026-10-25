# Findings: product summary

Findings is "Hinge for researchers". Researchers build a profile, an AI layer ranks and explains the
best collaborators, and a mentorship mode pairs juniors with mentors so the exchange runs both ways.
Everything runs on free tiers: Streamlit Community Cloud, Supabase and Google Gemini.

## Features and how they work

| Feature | How it works |
|---|---|
| **Sign up / sign in** | Supabase Auth with email and password (email confirmation off, so no SMTP needed). One Supabase client per browser session; a refresh-token cookie restores the session after a page refresh. A demo account keeps a live demo independent of any inbox. |
| **Profiles** | One form with the fixed career-stage list, free-text fields, and list fields (interests, skills, give/need) entered as suggestions plus custom values. The two mentoring toggles default from career stage and can be overridden. |
| **Methods badge** | On save, one Gemini call labels the profile qualitative, quantitative or mixed, with a one-line reason. It only runs when the relevant text changed (hash check). The user can override it, and the effective value is computed in the database. If Gemini fails, the profile still saves. |
| **AI autofill** | Paste text or upload a PDF CV. Gemini returns a structured draft that pre-fills the form (empty fields only by default). Nothing saves until the user clicks Save. Emails are scrubbed, PDFs are sent inline and never stored. |
| **Discover** | Cards for the seeded pool of 80 researchers (and real users), with filters for methods, career stage and interest keyword, plus a session-only Skip. |
| **Peer matching** | Each profile gets a 768-dimension embedding (`gemini-embedding-2`) stored in pgvector. A database function returns the 15 nearest profiles. One Gemini call reranks them with a score and a "why you match" for each. Results are cached per user and mode. |
| **Mentorship matching** | Same pipeline, filtered across the junior/mentor split. The shortlist blends embedding similarity with give/need overlap. The rerank scores both directions and explains what each side gets. |
| **Connections** | Send a request with a note, accept or decline, and see sent, received and connected lists. The contact email is revealed to both people only after acceptance. |
| **Messages** | Chat between people with an accepted connection. A `messages` table is protected by database rules (only the two participants of an accepted connection with a real person can read or write; no edits or deletes; rate limited). The thread refreshes every few seconds with a Streamlit fragment, with unread counts and read receipts. |
| **Guide chatbot** | A Help button in the top bar. Gemini answers from a fixed description of the site plus non-personal facts about you (counts and flags only), and suggests pages to visit. If Gemini fails, a built-in keyword FAQ answers instead. Capped at 30 questions a session. |
| **Resilience** | Gemini failures fall back to the stale cached result, then to embedding-only ranking with a visible notice. Two models are tried in turn (`gemini-3.5-flash-lite`, then `gemini-3.1-flash-lite`). A daily GitHub Action keeps the Supabase project from pausing. |
| **UI** | A minimal, Apple-inspired design system: top navigation bar, light and dark themes, one blue accent, light-gray cards, pill buttons, initials avatars, score rings, line icons and a live profile preview. |

## Architecture choices

- **Streamlit + Supabase + Gemini.** The only stack that meets the $0 requirement end to end: UI and hosting, Postgres/Auth/RLS/pgvector, and generation plus embeddings.
- **Layering.** `views/` and `ui/` (Streamlit) call `findings/services`, which call `findings/repos` (Supabase) and `findings/ai` (Gemini). Services, repos and AI code never import Streamlit, which keeps them testable and reusable by scripts.
- **Security lives in the database.** The app uses only the publishable key. Row Level Security limits writes to your own row, with column-level grants. The email sits in its own table with no policies and is read only through a security-definer function that checks for an accepted connection. The secret key exists only on the developer machine, for seeding.
- **No cross-user leakage.** Each browser session gets its own Supabase client in `st.session_state`, never a cached global one.
- **Embeddings first, LLM second.** pgvector narrows the pool cheaply with no Gemini call; the LLM only reranks 15 candidates in one request. That fits the free-tier quotas and keeps latency low.
- **Cache and hash-gating.** Match results are cached per user and mode and keyed on a profile hash. Embeddings and methods labels are recomputed only when the relevant text changes.
- **Graceful degradation.** Every AI feature has a non-AI fallback, so the demo never depends on a single Gemini call succeeding.
- **Untrusted text.** Profile and CV text is wrapped in delimiters and marked as data in every prompt. Rerank output is validated: candidate IDs must come from the shortlist, explanations must be grounded in both profiles, and temporary IDs replace names.
- **Structured output.** Gemini responses are parsed against Pydantic schemas, and a model chain with explicit low thinking level handles failures.
- **UI built on constraints.** Streamlit sanitises HTML, so icons are CSS masks defined in the stylesheet. User text is escaped, and long free text is shown with native text elements. Neutral colours derive from the text colour so the light and dark themes both work, and the top navigation uses Streamlit's built-in top bar.
- **Chat without websockets.** Streamlit cannot receive pushed updates, so a fragment polls every few seconds. Access control stays in the database (a security-definer `can_chat` check used by the row policies), not in the Python.
- **Guide without leakage.** The guide prompt carries only counts and flags; the question is wrapped as untrusted data; model output is shown as plain text and page links are limited to a fixed whitelist.
- **Tested without the network.** 281 tests (pytest and Streamlit AppTest) use in-memory fakes. `preview.py` runs the real app on sample data for design checks.

## Where to look

| Topic | Location |
|---|---|
| Schema, RLS, RPCs | `supabase/schema.sql` |
| Matching pipeline | `findings/services/matching.py`, `findings/ai/rerank.py`, `findings/ai/mentorship_prompt.py` |
| Gemini client | `findings/ai/client.py` |
| Design system | `ui/theme.css`, `ui/components.py`, `ui/icons.py` |
| Detail | `docs/ARCHITECTURE.md`, `docs/AI_USE.md`, `docs/LIMITATIONS.md` |
