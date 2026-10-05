# Data and sources

## Sources

| Data | Origin | Stored in |
|---|---|---|
| Real user profiles | Typed by users (optionally pre-filled by autofill from their own text or CV) | `profiles` (public fields), `profile_contacts` (email) |
| Synthetic researchers | Generated with Gemini by `scripts/seed_generate.py` | `data/seed_profiles.json` (committed), then `profiles` |
| Embeddings | `gemini-embedding-2`, 768 dimensions | `data/seed_embeddings.json` (cache), `profiles.embedding` |

No scraped or third-party personal data is used.

## How the synthetic dataset was made

1. `scripts/seed_generate.py` builds a quota matrix (career stages, methods orientation, mentoring
   roles, fields) and asks Gemini for small batches of profiles through
   `findings/ai/seed_prompt.py`. Output is validated against a Pydantic schema and written
   atomically, so the run is resumable.
2. The committed `data/seed_profiles.json` holds **80 profiles**:
   - career stage: 18 PhD, 14 Postdoc, 14 Faculty, 14 Master's, 10 Industry researcher, 10 Undergrad
   - methods: 28 quantitative, 27 qualitative, 25 mixed
3. `scripts/seed_load.py` computes an embedding per profile (one text per call), reports diversity
   metrics (pairwise similarity, near-duplicates), and inserts rows with `is_synthetic = true`
   and example.org emails using the Supabase **secret key**, which exists only in the gitignored
   `scripts/local.toml` on the developer machine.
4. The generation is a one-off. It is never run from the deployed app.

The app does not show a "Synthetic" label on these profiles (removed at the project owner's request).
The pool is fictional: names, institutions and histories are invented, and example.org addresses
do not receive mail. Say so when demonstrating, and keep `is_synthetic = true` in the database so
the rows can always be identified.

## Reproducing the data

```bash
.venv/Scripts/python scripts/seed_generate.py     # needs GEMINI_API_KEY (writes data/seed_profiles.json)
.venv/Scripts/python scripts/seed_load.py --dry-run
.venv/Scripts/python scripts/seed_load.py         # needs SUPABASE_SECRET_KEY in scripts/local.toml
```

## Privacy

- Contact email is stored apart from profile data and revealed only after a connection is accepted.
- Prompts to Gemini never include email addresses.
- The Supabase secret key and Gemini key are never committed.
