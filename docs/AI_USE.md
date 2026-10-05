# AI-use declaration

## AI inside the product

| Feature | Model | What is sent | What comes back |
|---|---|---|---|
| Methods badge | `gemini-3.5-flash-lite`, fallback `gemini-3.1-flash-lite` | Interests, skills, experience, bio, education and "looking for" text (no name, institution or email) | `qualitative` / `quantitative` / `mixed` plus a one-line reason |
| Profile embeddings | `gemini-embedding-2` (768 dimensions) | A structured text built from the profile's research fields | A vector stored in Postgres (pgvector) for similarity search |
| Peer match rerank | flash-lite chain | The user's profile and up to 15 shortlisted candidates, trimmed to matching fields, with temporary ids `c1..cN` instead of names | A score 0-100 and a "why you match" per candidate |
| Mentorship rerank | flash-lite chain | The same, plus the offers / needs / contributable skills / want-to-learn lists | A score plus "why", "what you get" and "what they get" |
| Autofill | flash-lite chain | Text the user pastes or a PDF CV the user uploads | Draft profile fields that pre-fill the form |
| Synthetic data | flash-lite chain | A generation brief (field, stage, methods mix) | 80 invented researcher profiles |

Safeguards: all user text is wrapped in delimiters and marked as data, not instructions; outputs are
parsed against schemas; candidate ids are validated against the shortlist; explanations are
checked for grounding; every AI feature has a non-AI fallback; nothing AI-generated is saved
without the user's action (autofill only pre-fills the form; the methods label can be overridden).
Uploaded CVs are sent inline to Gemini and are not stored by Findings.

## Data handling

Gemini is used on the free tier. Google's terms for the free tier allow inputs and outputs to be
used to improve its products. Users are told not to paste confidential information. Email
addresses are scrubbed from autofill results and are never included in any prompt.

## AI used to build the project

The project was built with Claude Code (Anthropic) using the GSD planning workflow: Claude helped
research the stack, write plans, implement code and tests, and draft the documentation. The
developer chose the product, reviewed the output, supplied credentials and ran the live checks.
The seed profiles were generated with Gemini (see `docs/DATA.md`).

## Responsibility

AI-generated explanations and labels are suggestions, not facts. Contact decisions are made by
people: a connection request is always sent by a user, and an email is revealed only when the
other person accepts.
