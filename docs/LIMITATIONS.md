# Limitations

## Free-tier constraints

- **Gemini quotas.** The free tier allows roughly 500 text requests per day per model (15 per
  minute) and 1,000 embedding requests per day. A heavy demo could exhaust them. The app caches
  matches, skips unchanged embeddings, and falls back to embedding-only ranking when Gemini fails.
- **Google may use free-tier inputs.** Text sent to the free Gemini API can be used to improve
  Google's products. Do not paste confidential material into autofill or profile fields.
- **Supabase pauses after a week without activity.** A daily GitHub Actions job prevents it, but
  scheduled workflows are disabled after 60 days without repository activity.
- **Streamlit Community Cloud sleeps after 12 hours** without traffic. The first visit after sleep
  needs a manual wake-up.

## Authentication and identity

- Sign-up uses email and password with email confirmation turned off, so anyone can create an
  account with any email address. There is no email verification, password reset or MFA.
- **No identity or credential verification.** Nothing checks that a user is who they say or holds
  the career stage they claim. ORCID or institutional email checks are out of scope.
- A browser refresh keeps the user signed in through a first-party refresh-token cookie; clearing
  cookies signs the user out.

## Data

- **Synthetic profiles.** Most of the pool is 80 AI-generated researchers, clearly labelled
  "Synthetic". They do not correspond to real people. Their example.org emails do not receive mail,
  and requests to them are accepted automatically so the full flow can be demonstrated.
- The pool is small, so match quality at scale is untested. Rankings on a few thousand real
  profiles would need an approximate-nearest-neighbour index.

## AI behaviour

- **Explanations can be wrong or generic.** "Why you match" text comes from a language model. The
  app checks it is grounded in terms from both profiles and drops it otherwise, but a plausible
  statement is not a verified one.
- **Methods labels are suggestions.** The qualitative / quantitative / mixed badge is inferred
  from short text and can be mistaken; users can override it.
- **Bias.** Ranking reflects the wording of profiles, so researchers who describe their work in
  common or fashionable terms may rank higher, and the models may reflect biases in their training
  data. No fairness evaluation was performed.
- **Autofill quality** depends on the pasted text or CV. Scanned PDFs without a text layer may
  yield little. Users must review everything before saving.

## Product scope

- No in-app chat; contact email is revealed after acceptance instead.
- No notifications; users check the Connections page.
- Skips last only for the current session.
- No admin or moderation tools, and no reporting or blocking of users.
- Matching is pairwise only; there is no group or team matching.
