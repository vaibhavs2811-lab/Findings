"""AppTest tests for Connect button and status chips on Discover cards (Plan 05-02)."""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from findings.services import connection_service
from tests.fakes_connections import ConnectionsFake, ConnectionStore

APP = str(Path(__file__).resolve().parent.parent / "app.py")
SECRETS = {
    "SUPABASE_URL": "https://abc.supabase.co",
    "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_x",
}

VIEWER_ID = "00000000-0000-0000-0000-000000000001"
TARGET_ID = "00000000-0000-0000-0000-000000000002"
SYNTH_ID = "00000000-0000-0000-0000-000000000099"


def test_discover_card_connect_flow(monkeypatch):
    store = ConnectionStore()
    store.add_profile(VIEWER_ID, "Viewer Researcher", "Postdoc", email="viewer@example.org")
    store.add_profile(TARGET_ID, "Target Candidate", "PhD", email="target@example.org")

    from findings.repos import profiles

    # Mock list_public to return our target
    monkeypatch.setattr(
        profiles,
        "list_public",
        lambda sb, **kwargs: [store.profiles[TARGET_ID]],
    )

    fake = ConnectionsFake(VIEWER_ID, store)
    fake.auth._store("viewer@example.org")

    at = AppTest.from_file(APP, default_timeout=15)
    at.secrets.update(SECRETS)
    at.session_state["sb"] = fake
    at.session_state["user"] = {"id": VIEWER_ID, "email": "viewer@example.org"}
    at.run()
    at.switch_page("views/discover.py").run()
    assert not at.exception

    # Check Connect button exists on card
    card_btn = next((b for b in at.button if b.key == f"connect_card_{TARGET_ID}"), None)
    assert card_btn is not None

    # Click Connect -> dialog opens
    card_btn.click().run()
    assert not at.exception

    # Input note and submit
    note_box = next((t for t in at.text_area if t.key == f"connect_note_card_{TARGET_ID}"), None)
    assert note_box is not None
    note_box.input("Excited to collaborate on HCI!").run()

    send_btn = next((b for b in at.button if b.key == f"connect_send_card_{TARGET_ID}"), None)
    assert send_btn is not None
    send_btn.click().run()
    assert not at.exception

    # After submit, Discover card should show the 'Request sent' chip
    captions = [c.value for c in at.caption]
    assert any("Request sent · waiting for their answer" in c for c in captions)


def test_discover_card_shows_connected_chip(monkeypatch):
    store = ConnectionStore()
    store.add_profile(VIEWER_ID, "Viewer Researcher", "Postdoc", email="viewer@example.org")
    store.add_profile(TARGET_ID, "Connected Peer", "Faculty", email="peer@example.org")

    from findings.repos import profiles

    monkeypatch.setattr(
        profiles,
        "list_public",
        lambda sb, **kwargs: [store.profiles[TARGET_ID]],
    )

    fake = ConnectionsFake(VIEWER_ID, store)
    # Establish accepted connection
    connection_service.send_request(fake, VIEWER_ID, TARGET_ID, "Hello")
    fake_target = fake.for_user(TARGET_ID)
    cid = store.connections[0]["id"]
    connection_service.respond(fake_target, TARGET_ID, cid, accept=True)

    at = AppTest.from_file(APP, default_timeout=15)
    at.secrets.update(SECRETS)
    at.session_state["sb"] = fake
    at.session_state["user"] = {"id": VIEWER_ID, "email": "viewer@example.org"}
    at.run()
    at.switch_page("views/discover.py").run()
    assert not at.exception

    # Card displays Connected chip instead of Connect button
    captions = [c.value for c in at.caption]
    assert any("Connected · email on your Connections page" in c for c in captions)
    card_btn = next((b for b in at.button if b.key == f"connect_card_{TARGET_ID}"), None)
    assert card_btn is None
