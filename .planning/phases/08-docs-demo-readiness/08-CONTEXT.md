# Phase 8: Docs & Demo Readiness - Context

**Gathered:** 2026-10-05
**Status:** Ready for planning
**Mode:** Fast-track. The user skipped the discussion and asked for best-practice defaults. Every decision below is marked "fast-track default (no user discussion)" and can be changed by editing this file before execution.

<domain>
## Phase Boundary

The project is ready to grade and demo. Every rubric document exists, describes the system that actually shipped in Phases 1-7, and passes an automated docs gate. The test report has screenshot evidence for every use case plus the anchor-profile top-3 evaluation. A pre-demo runbook (T-24h / T-2h / T-30min) exists and has been run end to end in one live rehearsal on the deployed URL.

Requirements: DOCS-01, DOCS-02, DOCS-03, DOCS-04, DOCS-05, DOCS-06, OPS-04.

**Execution order:** Phases 2-6 must be executed before this phase, and Phase 7 must be executed or explicitly cut. The docs describe the shipped code, so writing them earlier would document a plan rather than a product.

Not in this phase: new product features, schema changes, dependency changes, a forced-failure config flag (REL-01, v2), or an in-app About page.

</domain>

<decisions>
## Implementation Decisions

### Document set and location
- **D-01:** fast-track default (no user discussion). All rubric documents are Markdown files under `docs/`: `docs/ARCHITECTURE.md`, `docs/TEST_REPORT.md`, `docs/LIMITATIONS.md`, `docs/AI_USE.md`, `docs/DATA.md` and `docs/RUNBOOK.md`. The one exception is `README.md` at the repo root, which holds setup, the user manual and an index of every file in `docs/`. GitHub and the graders land on the root README, so that is where it goes.
- **D-02:** fast-track default (no user discussion). The architecture diagram is Mermaid inside `docs/ARCHITECTURE.md`. GitHub renders Mermaid, so there is no image export and no diagram tool. It needs at least:
  - a component `flowchart`: Streamlit views → services → repos / ai → Supabase / Gemini, plus Streamlit Cloud, the GitHub Actions keep-alive and the local seed scripts
  - a `sequenceDiagram` of the matching pipeline with its fallback ladder

  A components table maps every box to real file paths.
- **D-03:** fast-track default (no user discussion). Screenshots rules:
  - Format and location: PNG files under `docs/screenshots/phase-N/`, named `NN-slug.png`.
  - Size: 2 MB hard limit each, aim for under 1 MB.
  - Framing: cropped to the browser content area.
  - Shot list: the "Docs capture" line of each phase in ROADMAP.md.
  - Phase 8 fills gaps and does not re-shoot phases that already have their set. Phase 1's set is known to be missing (01-VERIFICATION.md).
  - Phase 1's "code entry" shot becomes the **Create account** tab, because sign-in changed to email + password on 2026-10-05.
  - Phase 8's own capture ("final runbook checklist with rehearsal results") is the filled rehearsal log in `docs/RUNBOOK.md`, not a PNG.
- **D-04:** fast-track default (no user discussion). `docs/RUNBOOK.md` contains:
  - the pre-demo checklist in three windows: T-24h, T-2h and T-30min
  - a timed demo script (the order of the live walkthrough)
  - fallback plays ("if X breaks, do Y")
  - a freeze rule
  - a rehearsal log table (date, step ID, step, PASS/FAIL, notes)

  Seven step IDs are mandatory and stable, because the docs gate checks them: `RB-KEEPALIVE`, `RB-SUPABASE`, `RB-WAKE`, `RB-LOGIN`, `RB-WARM-PEER`, `RB-WARM-MENTOR`, `RB-DEMO`.

### Content accuracy
- **D-05:** fast-track default (no user discussion). The docs describe the shipped system. Every fact is read at execution time from the code, `supabase/schema.sql`, `data/seed_profiles.json`, STATE.md and the phase SUMMARY/VERIFICATION files. That covers file and module names, page titles, table and RPC names, model IDs, quotas and counts. Nothing is copied from planning intent.

  Where planning docs and code disagree, the code wins and the plan SUMMARY lists the mismatch. Example: SKELETON.md and PROJECT.md still describe email OTP and Brevo, but the shipped auth is email + password with email confirmation off.
- **D-06:** fast-track default (no user discussion). `scripts/check_docs.py` (standard library only) is the automated docs gate. It checks:
  - required files and headings
  - that every repo path a doc cites exists (tracked or committable), or is a deliberately git-ignored local file
  - drift: every `views/*.py` appears in ARCHITECTURE, every table in `schema.sql` appears in DATA, every Gemini model ID in the code appears in AI_USE, and the seed profile count appears in DATA
  - a secret-pattern scan

  It also has a `--shots` screenshot inventory, an `--evidence` mode (screenshots, use-case results, rehearsal log) and a `--self-test` that proves the gate can fail. `tests/test_docs.py` runs it inside the normal pytest suite, so a later code change that breaks the docs fails the tests.
- **D-07:** fast-track default (no user discussion). Phase 7 is conditional. If `findings/services/autofill.py` exists, README, AI_USE and TEST_REPORT cover autofill. Any part that was cut (PDF first, then text) is listed in LIMITATIONS under cut and deferred features with its requirement ID. TEST_REPORT marks a cut part CUT instead of leaving it out.

### Test report
- **D-08:** fast-track default (no user discussion). `docs/TEST_REPORT.md` contains:
  - a summary: date, deployed URL, commit tested, totals
  - automated evidence: pytest counts, ruff, `scripts/check_live.py`, `scripts/check_docs.py` and `scripts/demo_preflight.py`, each with its command, date and result
  - use-case sections UC-01 to UC-07: sign-in, profile, Discover, matches including the fallback, connections including the email unlock, mentorship, and autofill if it shipped. Each has requirement IDs, steps, expected result, result (PASS, FAIL or CUT), screenshots and its negative tests
  - the anchor-profile top-3 evaluation
  - the rehearsal result

  A result is PASS only when the phase verification passed and the screenshot exists. Failures are reported honestly.
- **D-09:** fast-track default (no user discussion). The anchor-profile evaluation comes from Phase 4's artifact. To find it, search the Phase 4 directory, `docs/`, `scripts/` and `tests/` for "anchor". If none exists, the live rehearsal includes a hand check of the demo account's top-3 peer and top-3 mentorship matches (relevant / partly / not, with a one-line reason). That check is reported as a single-anchor evaluation, and LIMITATIONS states the small sample. Results are never invented.

### Secrets and privacy in docs
- **D-10:** fast-track default (no user discussion). No doc or screenshot contains a secret: no Supabase secret key, Gemini key, demo password, refresh token or contents of `scripts/local.toml`. The README tells readers to create their own account in the Create account tab, which works because Supabase email confirmation is off. Demo credentials go to the graders out of band. The Supabase URL and publishable key appear only in the already-committed `.streamlit/secrets.toml` (user decision 2026-10-05) and are not repeated in the docs.
- **D-11:** fast-track default (no user discussion). Screenshot redaction rules:
  - Use only the demo account, test accounts with example.org or throwaway addresses, and synthetic profiles.
  - Never capture the Streamlit Cloud secrets box, Supabase API-key pages, the AI Studio key page, devtools or cookies, a personal inbox, or terminal output that prints config files.
  - Autofill shots use a fabricated CV.
  - Claude opens every non-app screenshot (GitHub, terminal, tables) before it is committed and confirms that nothing sensitive is visible.

### Demo readiness
- **D-12:** fast-track default (no user discussion). `scripts/demo_preflight.py` automates the runbook steps a machine can check. It uses only the publishable key and the demo credentials from env vars or the gitignored `scripts/local.toml`, the same way `scripts/check_live.py` does. It checks:
  - Supabase is active (keepalive read)
  - the demo account signs in
  - the demo profile is complete and has a mentoring toggle on
  - peer and mentorship matches are pre-warmed through the real `get_matches` path, and whether each came from AI or embeddings
  - the pool has at least 60 profiles
  - the keep-alive workflow's last run
  - the app URL's HTTP status

  Waking the Streamlit app and the browser walkthrough stay human, because a cron or HTTP ping is not relied on to wake the app.
- **D-13:** fast-track default (no user discussion). One live rehearsal on the deployed URL runs the whole RUNBOOK in order in one sitting: T-24h, then T-2h, then T-30min, then the timed demo script. It is logged in the RUNBOOK rehearsal log. The demo-script part is captured as a 2-3 minute backup screen recording kept outside git. The RUNBOOK tells the team to repeat T-24h the day before the demo and to freeze after the final rehearsal: no merges, no dependency or schema changes, no Cloud reboots unless a runbook step fails.
- **D-14:** fast-track default (no user discussion). Phase 8 runs only after Phases 2-6 are executed and Phase 7 is executed or explicitly cut. The first task of each plan checks this and stops if it fails.

### Claude's Discretion
- Wording, document length, extra headings beyond the required ones, Mermaid styling, and whether ARCHITECTURE adds an `erDiagram`.
- Timings in the demo script and fallback plays beyond the required ones.
- The order of sections inside the README, as long as the required headings exist.
- Whether `scripts/demo_preflight.py` imports `demo_credentials` from `scripts/check_live.py` or keeps a small copy.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope & requirements
- `.planning/ROADMAP.md` §Phase 8 (goal, four success criteria, notes) and the **Docs capture** line of every phase (the screenshot shot list)
- `.planning/REQUIREMENTS.md` §Documentation (DOCS-01..06), §Deployment & Operations (OPS-04), §v2 Requirements and §Out of Scope (inputs to LIMITATIONS)
- `.planning/PROJECT.md` (constraints: $0, privacy, demo reliability)
- `.claude/CLAUDE.md` (stack facts, Gemini usage rules, free-tier limits, secrets decision)

### Evidence sources
- `.planning/STATE.md`: measured Gemini quotas, deployed URL https://findings.streamlit.app, keep-alive run link
- `.planning/phases/0N-*/0N-*-SUMMARY.md`, `0N-VERIFICATION.md`, `0N-UAT.md` for Phases 1-7: what shipped, deviations, pass/fail evidence
- `.planning/phases/01-foundation-sign-in/01-VERIFICATION.md`: notes that `docs/screenshots/phase-1/*` is missing

### Research behind the defaults
- `.planning/research/PITFALLS.md`: Pitfall 13 (bias, anchor evaluation), Pitfall 15 (pause/sleep runbook), Pitfall 17 (demo-day failures, rehearsal, backup recording, freeze), the documentation pitfalls (AI use covers product and build, specific limitations, test report with negative tests)
- `.planning/research/SUMMARY.md` and `.planning/research/STACK.md` §5-8 (quotas, Google free-tier data use, keep-alive, Community Cloud limits)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/check_live.py`: `demo_credentials()` (env `FINDINGS_DEMO_EMAIL`/`FINDINGS_DEMO_PASSWORD`, else `scripts/local.toml`), the PASS/FAIL `report()` line style, exit codes 0/1/2, and a `__main__` guard so the module can be imported.
- `tests/test_repo_hygiene.py`: `SECRET_PATTERNS` and the publishable-key rule. The docs gate mirrors these patterns. This test also rescans every tracked file once the docs are committed.
- `findings/core/config.py`: `load_local_settings()` refuses any Supabase key that does not start with `sb_publishable_`. The preflight must load settings through it.
- `.claude/launch.json`: the local run command (`C:/fv312/Scripts/python.exe -m streamlit run app.py --server.port 8501`), which is the fallback play when Streamlit Cloud is down.
- `.github/workflows/keepalive.yml`: workflow `supabase-keepalive`, cron `17 6 * * *`, `workflow_dispatch`.

### Established Patterns
- Layering: `views/*.py` → `findings/services/*` → `findings/repos/*` and `findings/ai/*`. Services, repos and ai never import streamlit.
- Interpreter: `C:/fv312/Scripts/python`. Tests: `C:/fv312/Scripts/python -m pytest -q`. Lint: `C:/fv312/Scripts/python -m ruff check .`
- Scripts print one `PASS`/`FAIL` line per check and never print keys, tokens or passwords.

### Integration Points
- The README "Documentation" section links every file in `docs/`.
- `tests/test_docs.py` joins the existing pytest suite (`pytest.ini` testpaths = tests).

</code_context>

<specifics>
## Specific Ideas

- Graders reward specific limitations over generic ones. Name the quota numbers, the final-decline rule, the email-confirmation-off consequence, the session-only Skip and the privacy trade-off (profile text is visible to every signed-in user; email only after accept).
- The AI-use declaration must cover both the AI inside the product and the AI used to build it (Claude Code with the GSD workflow; check `git log` trailers), plus the fact that Google may use free-tier Gemini inputs to improve its products.
- The fallback should look like a feature in the demo. The RUNBOOK fallback plays say what to tell the audience.

</specifics>

<deferred>
## Deferred Ideas

- Automated screenshot capture (Playwright or similar): a new dependency, not needed for a one-off capture.
- A hosted docs site (MkDocs or GitHub Pages) and PDF export of the docs.
- A `FORCE_GEMINI_FAIL` config flag for an on-demand fallback (REL-01, v2).
- An in-app About / Limitations page.

</deferred>

---

*Phase: 08-docs-demo-readiness*
*Context gathered: 2026-10-05 (fast-track, defaults applied without user discussion)*
