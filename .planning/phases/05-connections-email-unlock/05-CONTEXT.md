# Phase 5: Connections & Email Unlock - Context

**Gathered:** 2026-10-05
**Status:** Ready for planning
**Mode:** fast-track. The user skipped discussion. Every decision below is a **fast-track default (no user discussion)**, picked as best practice for this stack. Any of them can be revisited with `/gsd-discuss-phase 5`.

<domain>
## Phase Boundary

A signed-in researcher sends a connection request with an optional short note from a My Matches entry, a Discover card or a researcher profile page. The recipient sees it on a Connections page and accepts or declines it. Contact emails become readable for both sides only after acceptance, and the database enforces this, not the UI. A request to a synthetic profile is accepted by the database straight away and reveals that profile's example.org address, with a visible synthetic label. The Connections page lists sent, received and accepted connections.

Not in this phase: notifications (out of scope), withdrawing a pending request in the UI, removing an accepted connection, seeded incoming requests from synthetic profiles (REL-02, v2), and mentorship ranking (Phase 6). Phase 6 reuses this phase's connect button.

**Prerequisite:** Phases 2, 3 and 4 must be executed first. This phase adds buttons to `views/researcher.py`, `views/discover.py` and `views/matches.py`, and its live probe needs the Phase 2 probe account and the Phase 3 synthetic profiles and secret key.
</domain>

<decisions>
## Implementation Decisions

### Database rules (CONN-03, CONN-04, CONN-06)
- **D-01:** Synthetic auto-accept uses an AFTER INSERT trigger `auto_accept_synthetic` on `public.connections` (security definer, `set search_path = ''`). When the recipient's `profiles.is_synthetic` is true, it updates the new row to `accepted`, and the existing `guard_connection_update` trigger stamps `responded_at`. The client always inserts `pending`, and the Phase 1 insert policy stays unchanged. An INSERT ... RETURNING shows the pre-trigger `pending` row, so the service reads the row again after inserting. — fast-track default (no user discussion)
- **D-02:** Clients may insert only `requester_id`, `recipient_id` and `note`, through a column-level insert grant appended to `schema.sql`. The database controls `status`, `created_at` and `responded_at`. — fast-track default (no user discussion)
- **D-03:** `public.my_connections()` is a security-definer RPC (`search_path = ''`, execute revoked from public and anon, granted to authenticated). It returns one row per connection the caller is part of: connection_id, direction (sent/received), status, note, created_at, responded_at, other_id, other_name, other_stage, other_is_synthetic, and other_email. `other_email` comes only from `public.get_contact_email(other_id)` and only when status is `accepted`, so the email gate lives in one function. It never returns `embedding` or any other private column. Because it is security definer, the recipient still sees who asked even if the requester's profile is not yet visible to them. — fast-track default (no user discussion)
- **D-09:** Only the recipient can accept or decline. The existing recipient-only update policy, the status-only update grant and the `guard_connection_update` trigger enforce this. `respond()` filters by `recipient_id` and raises a user-safe error when zero rows change. — fast-track default (no user discussion)

### UI and flow (CONN-01, CONN-02, CONN-05, DISC-06)
- **D-04:** Contact email is shown only on the Connections page "Connected" tab. Profile pages and cards never show it (PROF-07 holds). They show a status chip instead. — fast-track default (no user discussion)
- **D-05:** `ui/connect_button.py` provides `connect_button(sb, user_id, profile_id, key, *, name="", is_synthetic=False, states=None)`. It opens an `st.dialog` with an optional note (at most 500 characters, the DB limit) and a Send button. The dialog is driven by session state: an `on_click` callback stores the open key, and `on_dismiss` clears it. This pattern was verified with AppTest on Streamlit 1.65. It is used on the profile page, Discover cards and My Matches entries, and hidden on your own profile. — fast-track default (no user discussion)
- **D-06:** Each page fetches connection state once per render through `my_connections` and passes it to every button on the page. Connection data never goes through `st.cache_data` or `st.cache_resource`, because it is per-user data (PITFALLS #2). — fast-track default (no user discussion)
- **D-07:** Duplicates are blocked by the database: the unique-pair index is authoritative. The service checks first so it can give a specific, clear message, and maps a race-condition `23505` error to the same message. A reverse request counts as a duplicate, so if the other person already asked you, the button becomes "Accept their request". — fast-track default (no user discussion)
- **D-08:** Declines are final because of the unique-pair index. The requester sees a declined request as "Not accepted". This is listed for the Phase 8 limitations document. — fast-track default (no user discussion)
- **D-10:** The Connections page has three tabs with counts: Received (incoming pending, with Accept and Decline), Sent (outgoing pending and not accepted), and Connected (accepted in either direction, with the email). It is added to the signed-in navigation. — fast-track default (no user discussion)
- **D-11:** Synthetic labelling: the connect dialog says that synthetic profiles accept automatically, a toast after sending says "Auto-accepted (synthetic profile)", and Connected rows show "Synthetic · auto-accepted". — fast-track default (no user discussion)
- **D-12:** My Matches drops anyone you already have a connection with (any status) from the rendered results. This keeps Phase 4's "never includes existing connections" true when results are cached. — fast-track default (no user discussion)
- **D-14:** You can only send a request once your own profile is complete (`is_complete`), so recipients can see who is asking. The service checks this and shows a friendly message. It is a usability rule, not a security boundary. — fast-track default (no user discussion)

### Proof and operations
- **D-13:** Live proof comes from new C-checks in `scripts/check_live.py`. They use the demo account as requester, the Phase 2 probe account as recipient, and one synthetic profile. A new local-only script, `scripts/reset_connections.py`, uses the Phase 3 secret key from gitignored `scripts/local.toml` to delete connections that involve only the demo and probe accounts. This makes the probe and the live demo flow repeatable, and the Phase 8 runbook reuses it. — fast-track default (no user discussion)

### Claude's Discretion
- The exact wording of the messages, chips and toasts, and the tab order inside the stated set.
- Whether the Connected tab shows the email with `st.code` (copyable) or plain `st.text`. User-controlled strings (name, note, email) are never rendered as HTML.
</decisions>

<canonical_refs>
## Canonical References

- `.planning/ROADMAP.md` §Phase 5: goal, five success criteria, notes (email through `get_contact_email`, server-side auto-accept, final declines, two-browser gate), docs-capture list
- `.planning/REQUIREMENTS.md`: CONN-01..CONN-06, DISC-06
- `supabase/schema.sql` sections 5, 8 and 9: `connections`, `connections_pair_uniq`, `guard_connection_update`, connection policies and grants, `get_contact_email`. Extend these by appending; never rewrite them.
- `.planning/research/ARCHITECTURE.md` §"RPCs (the controlled doors)": sketch of `my_connections`
- `.planning/research/PITFALLS.md` Pitfalls 2, 3 and 4, and the "Looks done but isn't" checklist (Connections)
- Shared cross-phase contract (planning scratchpad `shared-contract.md`), section "Phase 5 produces"
</canonical_refs>

<code_context>
## Existing Code Insights

- Layering: `views/*` → `findings/services/*` → `findings/repos/*`. Services and repos never import streamlit. `ui/` holds reusable Streamlit components (created in Phase 2).
- `findings/repos/profiles.py::get_own_profile(sb, user_id)` returns `is_complete` (used for D-14).
- `scripts/check_live.py`: `report()`, `denied_or_empty()`, `raises()` and the credential loaders. Phase 1's D9 check expects 0 connections for the demo account, and Phase 5 must relax it to "only own rows".
- `tests/fakes.py::FakeSupabase` is subclassed and never edited.
- Interpreter: `C:/fv312/Scripts/python`.
</code_context>

<deferred>
## Deferred Ideas

- A withdraw button for pending requests (the DB delete policy already allows it, but there is no UI)
- Disconnecting or removing an accepted connection
- Email or in-app notifications for new requests (out of scope per REQUIREMENTS)
- A seeded pending request from a synthetic profile to the demo account (REL-02, v2)
</deferred>

---

*Phase: 05-connections-email-unlock*
*Context gathered: 2026-10-05 (fast-track defaults)*
