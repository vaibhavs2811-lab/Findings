# Pre-demo runbook

Run this the day before and again 30 minutes before the demo. Tick each box and record the time.

## 1. Infrastructure awake

- [ ] Supabase project is **Active** (dashboard > project). If paused, restore it and wait for it
      to come back. The daily keep-alive GitHub Action should be green:
      Actions > supabase-keepalive. Trigger it by hand with "Run workflow" if unsure.
- [ ] Open https://findings.streamlit.app. If it shows "get this app back up", click it and wait
      until the sign-in page appears (up to a minute or two).
- [ ] Streamlit Cloud > app > Settings > Secrets contains `SUPABASE_URL`,
      `SUPABASE_PUBLISHABLE_KEY` and `GEMINI_API_KEY`.

## 2. Demo account

- [ ] Sign in with the demo account (email + password).
- [ ] My profile shows a complete profile with a methods badge.
- [ ] Refresh the browser: you stay signed in.

## 3. Pre-warm matches (so the demo is fast)

- [ ] My Matches > Peers: wait for the list. It should say "AI-ranked". Each card has a
      "why you match".
- [ ] My Matches > Mentorship: the same for the direction your demo account supports.
- [ ] If either shows "ranked by profile similarity", Gemini is rate-limited or the key is wrong.
      Check the key, wait a minute and press Refresh matches. The fallback is acceptable for the
      demo but say so out loud.

## 4. Flow rehearsal (about 5 minutes)

1. Sign in, show My profile, change one field, Save (methods badge updates or keeps its value).
2. Discover: filter by methods and stage, search an interest, Skip a card.
3. Open a researcher profile (note: no email, "Synthetic" label).
4. My Matches: show a ranked match and its explanation; switch to Mentorship and show the two-sided
   "what you get / what they get".
5. Send a connection request to a synthetic profile: it is accepted at once and the example.org
   email appears on Connections.
6. Sign out.

## 5. Failure plan

| Symptom | Action |
|---|---|
| Sign-in page does not load | Wake the app; check Streamlit Cloud logs |
| "Matching service is currently unavailable" | Supabase may be paused; restore it, then re-run step 3 |
| Matches show "ranked by profile similarity" | Gemini quota or key issue; continue the demo with the fallback |
| Autofill says unavailable | Fill the form by hand; mention the free-tier quota |
| Account problems | Use the pre-made demo account; do not create accounts live |

## 6. Rehearsal log

| Date | Who | Result | Notes |
|---|---|---|---|
|  |  |  |  |

## 7. Evidence for the test report

Capture screenshots into `docs/screenshots/` and link them from `docs/TEST_REPORT.md`:
sign-in, empty profile form, saved profile with methods badge, methods override, mentoring toggles
by stage, autofill, Discover with filters, researcher page, My Matches (AI and fallback),
Mentorship matches, connection request and accepted email, RLS rejection output from
`scripts/check_live.py`. Do not show keys, passwords or real emails in screenshots.
