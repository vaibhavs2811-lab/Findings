"""AppTest tests for Connect button and D-12 connection filtering on My Matches (Plan 05-02)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from streamlit.testing.v1 import AppTest

from findings.services import connection_service, matching
from tests.fakes_connections import ConnectionsFake, ConnectionStore

APP = str(Path(__file__).resolve().parent.parent / "app.py")
SECRETS = {
    "SUPABASE_URL": "https://abc.supabase.co",
    "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_x",
}

VIEWER_ID = "00000000-0000-0000-0000-000000000001"
MATCH1_ID = "00000000-0000-0000-0000-000000000002"
MATCH2_ID = "00000000-0000-0000-0000-000000000003"


def _make_match_result(items: list[dict[str, Any]]) -> matching.MatchResult:
    return matching.MatchResult(
        items=items,
        source="ai",
        notice=None,
        from_cache=False,
    )


def test_matches_connect_flow(monkeypatch):
    store = ConnectionStore()
    store.add_profile(VIEWER_ID, "Viewer", "PhD", email="viewer@example.org")
    store.add_profile(MATCH1_ID, "Dr. Match One", "Postdoc", email="match1@example.org")

    items = [
        {
            "id": MATCH1_ID,
            "full_name": "Dr. Match One",
            "career_stage": "Postdoc",
            "methods_effective": "quantitative",
            "interests": ["Robotics"],
            "score": 90,
            "strength": "Strong match",
            "why": "Grounded explanation",
        }
    ]

    monkeypatch.setattr(
        matching,
        "get_matches",
        lambda *a, **k: _make_match_result(items),
    )

    fake = ConnectionsFake(VIEWER_ID, store)
    at = AppTest.from_file(APP, default_timeout=15)
    at.secrets.update(SECRETS)
    at.session_state["sb"] = fake
    at.session_state["user"] = {"id": VIEWER_ID, "email": "viewer@example.org"}
    at.run()
    at.switch_page("views/matches.py").run()
    assert not at.exception

    # Find Connect button on match card
    match_btn = next((b for b in at.button if b.key == f"connect_peer_match_{MATCH1_ID}"), None)
    assert match_btn is not None

    # Open dialog and submit
    match_btn.click().run()
    assert not at.exception

    note_box = next((t for t in at.text_area if t.key == f"connect_note_peer_match_{MATCH1_ID}"), None)
    assert note_box is not None
    note_box.input("Let's write a grant together!").run()

    send_btn = next((b for b in at.button if b.key == f"connect_send_peer_match_{MATCH1_ID}"), None)
    assert send_btn is not None
    send_btn.click().run()
    assert not at.exception

    # Per D-12: candidate is now connected (status='pending') and must be dropped from rendered matches
    at.run()
    text_vals = [t.value for t in at.text]
    assert not any("Dr. Match One" in t for t in text_vals)
    # Empty matches notice shown
    info_vals = [i.value for i in at.info]
    assert any(matching.NO_MATCHES_NOTICE in i for i in info_vals)


def test_matches_d12_drops_existing_connections(monkeypatch):
    store = ConnectionStore()
    store.add_profile(VIEWER_ID, "Viewer", "PhD", email="viewer@example.org")
    store.add_profile(MATCH1_ID, "Dr. Connected", "Postdoc", email="conn@example.org")
    store.add_profile(MATCH2_ID, "Dr. Unconnected", "Faculty", email="unconn@example.org")

    items = [
        {
            "id": MATCH1_ID,
            "full_name": "Dr. Connected",
            "career_stage": "Postdoc",
            "strength": "Strong match",
        },
        {
            "id": MATCH2_ID,
            "full_name": "Dr. Unconnected",
            "career_stage": "Faculty",
            "strength": "Good match",
        },
    ]

    monkeypatch.setattr(
        matching,
        "get_matches",
        lambda *a, **k: _make_match_result(items),
    )

    fake = ConnectionsFake(VIEWER_ID, store)
    # Pre-populate connection between VIEWER and MATCH1
    connection_service.send_request(fake, VIEWER_ID, MATCH1_ID, "Pre-existing")

    at = AppTest.from_file(APP, default_timeout=15)
    at.secrets.update(SECRETS)
    at.session_state["sb"] = fake
    at.session_state["user"] = {"id": VIEWER_ID, "email": "viewer@example.org"}
    at.run()
    at.switch_page("views/matches.py").run()
    assert not at.exception

    text_vals = [t.value for t in at.text]
    # MATCH1 dropped by D-12
    assert not any("Dr. Connected" in t for t in text_vals)
    # MATCH2 still rendered
    assert any("Dr. Unconnected" in t for t in text_vals)
