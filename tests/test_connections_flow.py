"""Tests for connection tracer flow, repository, service, UI components, and views."""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from findings.repos import connections as connections_repo
from findings.services import connection_service
from findings.services.connection_service import ConnectionFailure
from tests.fakes_connections import ConnectionsFake, ConnectionStore

APP = str(Path(__file__).resolve().parent.parent / "app.py")
SECRETS = {
    "SUPABASE_URL": "https://abc.supabase.co",
    "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_x",
}

USER_A = "00000000-0000-0000-0000-000000000001"
USER_B = "00000000-0000-0000-0000-000000000002"
USER_C = "00000000-0000-0000-0000-000000000003"
SYNTH_ID = "00000000-0000-0000-0000-000000000099"


@pytest.fixture
def store() -> ConnectionStore:
    s = ConnectionStore()
    s.add_profile(USER_A, "Dr. Alice", "Postdoc", email="alice@uni.edu")
    s.add_profile(USER_B, "Bob Smith", "PhD", email="bob@lab.org")
    s.add_profile(USER_C, "Charlie Brown", "Faculty", email="charlie@inst.edu")
    s.add_profile(SYNTH_ID, "Synthetic Mentor", "Faculty", email="synth@example.org", is_synthetic=True)
    return s


def test_insert_request_payload_columns(store: ConnectionStore):
    fake_a = ConnectionsFake(USER_A, store)
    res = connections_repo.insert_request(fake_a, USER_A, USER_B, "Hello Bob")
    assert res.get("requester_id") == USER_A
    assert res.get("recipient_id") == USER_B
    assert res.get("note") == "Hello Bob"
    assert res.get("status") == "pending"


def test_send_request_to_self_fails(store: ConnectionStore):
    fake_a = ConnectionsFake(USER_A, store)
    with pytest.raises(ConnectionFailure, match="You can't send a request to yourself"):
        connection_service.send_request(fake_a, USER_A, USER_A, "note")


def test_send_request_note_too_long(store: ConnectionStore):
    fake_a = ConnectionsFake(USER_A, store)
    long_note = "x" * 501
    with pytest.raises(ConnectionFailure, match="Keep the note under 500 characters"):
        connection_service.send_request(fake_a, USER_A, USER_B, long_note)


def test_send_request_to_synthetic_auto_accepted(store: ConnectionStore):
    fake_a = ConnectionsFake(USER_A, store)
    # Target is synthetic: DB flips row to accepted
    row = connection_service.send_request(fake_a, USER_A, SYNTH_ID, "Collab note")
    assert row.get("status") == "accepted"
    assert row.get("responded_at") is not None


def test_respond_by_non_recipient_fails(store: ConnectionStore):
    fake_a = ConnectionsFake(USER_A, store)
    fake_c = ConnectionsFake(USER_C, store)

    # A sends to B
    row = connection_service.send_request(fake_a, USER_A, USER_B, "Hi")
    cid = row["id"]

    # C tries to respond to A->B request
    with pytest.raises(ConnectionFailure, match="Only the person who received this request can answer it"):
        connection_service.respond(fake_c, USER_C, cid, accept=True)


def test_list_connections_and_states(store: ConnectionStore):
    fake_a = ConnectionsFake(USER_A, store)

    # A sends to B (pending)
    connection_service.send_request(fake_a, USER_A, USER_B, "Hi Bob")
    # C sends to A (pending)
    fake_c = ConnectionsFake(USER_C, store)
    connection_service.send_request(fake_c, USER_C, USER_A, "Hi Alice from C")
    # A sends to Synth (accepted)
    connection_service.send_request(fake_a, USER_A, SYNTH_ID, "Hi Synth")

    # A's connections
    a_conns = connection_service.list_connections(fake_a, USER_A)
    assert len(a_conns["sent"]) == 1
    assert a_conns["sent"][0]["other_id"] == USER_B
    assert len(a_conns["received"]) == 1
    assert a_conns["received"][0]["other_id"] == USER_C
    assert len(a_conns["accepted"]) == 1
    assert a_conns["accepted"][0]["other_id"] == SYNTH_ID
    assert a_conns["accepted"][0]["other_email"] == "synth@example.org"

    # States map for A
    states_a = connection_service.connection_states(fake_a, USER_A)
    assert states_a[USER_B]["state"] == "sent"
    assert states_a[USER_C]["state"] == "received"
    assert states_a[SYNTH_ID]["state"] == "connected"


def test_researcher_page_hides_connect_on_own_profile(store: ConnectionStore, monkeypatch):
    from findings.repos import profiles

    # Mock get_public for own profile
    monkeypatch.setattr(
        profiles,
        "get_public",
        lambda sb, pid: store.profiles.get(pid),
    )

    fake_a = ConnectionsFake(USER_A, store)
    fake_a.auth._store("alice@uni.edu")

    at = AppTest.from_file(APP, default_timeout=15)
    at.secrets.update(SECRETS)
    at.session_state["sb"] = fake_a
    at.session_state["user"] = {"id": USER_A, "email": "alice@uni.edu"}
    at.query_params["id"] = USER_A
    at.run()
    at.switch_page("views/researcher.py").run()

    assert not at.exception
    # No connect button should exist on own profile
    connect_btns = [b for b in at.button if "connect" in (b.key or "").lower()]
    assert len(connect_btns) == 0


def test_app_test_connections_tracer_end_to_end(store: ConnectionStore, monkeypatch):
    from findings.repos import profiles

    monkeypatch.setattr(
        profiles,
        "get_public",
        lambda sb, pid: store.profiles.get(pid),
    )

    fake_a = ConnectionsFake(USER_A, store)
    fake_a.auth._store("alice@uni.edu")

    # 1. User A visits B's profile and clicks Connect
    at_a = AppTest.from_file(APP, default_timeout=15)
    at_a.secrets.update(SECRETS)
    at_a.session_state["sb"] = fake_a
    at_a.session_state["user"] = {"id": USER_A, "email": "alice@uni.edu"}
    at_a.query_params["id"] = USER_B
    at_a.run()
    at_a.switch_page("views/researcher.py").run()
    assert not at_a.exception

    # Find Connect button and click it
    btn_connect = next((b for b in at_a.button if b.key == f"connect_prof_{USER_B}"), None)
    assert btn_connect is not None
    btn_connect.click().run()
    assert not at_a.exception

    # Type note and click Send request in dialog
    note_area = next((t for t in at_a.text_area if t.key == f"connect_note_prof_{USER_B}"), None)
    assert note_area is not None
    note_area.input("Excited to collaborate on multimodal ML").run()

    btn_send = next((b for b in at_a.button if b.key == f"connect_send_prof_{USER_B}"), None)
    assert btn_send is not None
    btn_send.click().run()
    assert not at_a.exception

    # 2. Check User A's Connections page -> Sent tab shows Pending
    at_a.switch_page("views/connections.py").run()
    assert not at_a.exception

    text_vals = [t.value for t in at_a.text]
    captions = [c.value for c in at_a.caption]
    assert any("Pending" in c for c in captions)
    assert any("Excited to collaborate" in t for t in text_vals)
    # B's email must NOT appear on A's page
    assert not any("bob@lab.org" in t for t in text_vals)

    # 3. User B visits Connections page -> Received tab shows A's request
    fake_b = store and fake_a.for_user(USER_B)
    at_b = AppTest.from_file(APP, default_timeout=15)
    at_b.secrets.update(SECRETS)
    at_b.session_state["sb"] = fake_b
    at_b.session_state["user"] = {"id": USER_B, "email": "bob@lab.org"}
    at_b.run()
    at_b.switch_page("views/connections.py").run()
    assert not at_b.exception

    text_vals_b = [t.value for t in at_b.text]
    assert any("Excited to collaborate" in t for t in text_vals_b)
    # A's email is NOT shown before accept
    assert not any("alice@uni.edu" in t for t in text_vals_b)

    # Find Accept button and click it
    btn_accept = next((b for b in at_b.button if (b.key or "").startswith("accept_")), None)
    assert btn_accept is not None
    btn_accept.click().run()
    assert not at_b.exception

    # 4. Now B sees A's email on Connected tab
    at_b.run()
    code_vals_b = [c.value for c in at_b.code]
    assert any("alice@uni.edu" in c for c in code_vals_b)

    # 5. User A visits Connections page -> now sees B's email on Connected tab
    at_a.run()
    code_vals_a = [c.value for c in at_a.code]
    assert any("bob@lab.org" in c for c in code_vals_a)
