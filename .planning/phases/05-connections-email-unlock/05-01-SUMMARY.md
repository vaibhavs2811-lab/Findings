# Phase 5 Plan 1 Summary: Connections Tracer, Schema Rules, Gated Email Unlock & Reset Probe

**Executed:** 2026-10-05
**Status:** Completed (Offline & Test-verified; Live SQL dashboard paste deferred per user instruction)
**Requirements Delivered:** CONN-01, CONN-02, CONN-03, CONN-04, CONN-05, CONN-06

---

## What Changed

1. **Connections Repository** ([findings/repos/connections.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/findings/repos/connections.py)):
   - `CONNECTION_COLUMNS = "id, requester_id, recipient_id, note, status, created_at, responded_at"` (explicit columns, no star select).
   - `insert_request(sb, requester_id, recipient_id, note)`: inserts client payload restricted strictly to `requester_id`, `recipient_id`, and `note`.
   - `get_by_id(sb, connection_id)`: fetches single connection row by ID.
   - `set_status(sb, connection_id, recipient_id, status)`: updates status (`accepted`/`declined`), scoped strictly to recipient.
   - `list_mine(sb)`: invokes `my_connections` security-definer RPC.

2. **Connection Service Layer** ([findings/services/connection_service.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/findings/services/connection_service.py)):
   - `ConnectionFailure` user-safe exception wrapping.
   - `send_request`: prevents self-requests, enforces `NOTE_MAX = 500`, inserts request, and re-reads row to observe synthetic auto-acceptance.
   - `respond`: updates status for recipient, enforces that only the recipient can answer, and catches already-answered attempts.
   - `list_connections`: categorizes caller connections into `sent`, `received`, and `accepted` tabs while maintaining newest-first order.
   - `connection_states`: maps other researcher IDs to status chips (`sent`, `received`, `connected`, `declined`).

3. **Reusable Connect Component & Dialog** ([ui/connect_button.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/ui/connect_button.py)):
   - Renders "Connect" button opening `@st.dialog("Send a connection request", on_dismiss=_close)`.
   - Input for optional note with 500-char counter and submit button.
   - Displays status chips when connection exists:
     - `"Request sent · waiting for their answer"`
     - `"Connected · email on your Connections page"`
     - `"Not available"` (declined)
     - `"They sent you a request · answer it on your Connections page"`
   - Integrated into [views/researcher.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/views/researcher.py) for public researcher profile pages (hidden on own profile).

4. **Connections Page View** ([views/connections.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/views/connections.py), [app.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/app.py)):
   - Registered in authenticated navigation in `app.py`.
   - Three tabs with live counts: `Received (N)`, `Sent (N)`, `Connected (N)` (D-10).
   - Received tab: shows request details with Accept and Decline action buttons.
   - Sent tab: lists outgoing requests with status badges (`Pending`, `Not accepted`).
   - Connected tab: lists mutual connections; displays unlocked email using `st.code` without HTML injection (the only place in the app where emails appear, D-04). Shows `Synthetic · auto-accepted` badge for synthetic profiles.

5. **Database Schema Additions** ([supabase/schema.sql](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/supabase/schema.sql)):
   - **Section 10 appended:**
     - D-02: Column-level insert permissions on `connections(requester_id, recipient_id, note)` granted to authenticated.
     - D-01: `auto_accept_synthetic()` trigger function on `connections AFTER INSERT` (security definer) automatically setting `status = 'accepted'` for synthetic recipients.
     - D-03: `my_connections()` security-definer RPC returning connection info, where `other_email` is retrieved strictly through `public.get_contact_email(other_id)` when status is `accepted`.

6. **Reset Script, Live Checks, and Local Secrets** ([scripts/reset_connections.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/scripts/reset_connections.py), [scripts/check_live.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/scripts/check_live.py), [scripts/local.toml.example](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/scripts/local.toml.example)):
   - `scripts/reset_connections.py`: resets demo and probe connection rows using `SUPABASE_SECRET_KEY` (service role).
   - `scripts/check_live.py`: added checks C0 through C14 covering privacy gating, mutual lock, recipient-only updates, synthetic auto-accept, and duplicate rejection.
   - `scripts/local.toml.example`: updated with `SUPABASE_SECRET_KEY` placeholder.

7. **Test Suites** ([tests/fakes_connections.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/tests/fakes_connections.py), [tests/test_connections_flow.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/tests/test_connections_flow.py), [tests/test_connections_sql.py](file:///c:/Users/u1233270/Downloads/Personal%20Apps/Findings/tests/test_connections_sql.py)):
   - Multi-user `ConnectionStore` and `ConnectionsFake` implementing RLS and triggers in-memory.
   - Flow test suite covering end-to-end connect from profile page, recipient accept on Connections page, and dual-sided email reveal.
   - Static SQL analysis verifying security definer attributes, column grants, and anti-leakage invariants.

---

## Verification Results

- `python -m ruff check .`: All checks passed! (0 errors)
- `pytest tests/test_connections_flow.py`: 8 passed in 7.86s.
- `pytest tests/test_connections_sql.py tests/test_repo_hygiene.py`: 9 passed in 2.24s.
- `pytest tests/test_discover.py`: 19 passed in 10.39s.
- `pytest`: **191 passed in 61.39s** (0 failures).
