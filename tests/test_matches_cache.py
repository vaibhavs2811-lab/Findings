"""Tests for match caching, connections invalidation, fallback ladder, and refresh cooldown (Plan 04-03)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from streamlit.testing.v1 import AppTest

from findings.ai import rerank
from findings.repos import matches as matches_repo
from findings.services import matching
from tests.fakes_matching import FakeMatchingSupabase

APP = str(Path(__file__).resolve().parent.parent / "app.py")
SECRETS = {
    "SUPABASE_URL": "https://abc.supabase.co",
    "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_x",
}

USER_ID = "00000000-0000-0000-0000-000000000001"
CAND1_ID = "00000000-0000-0000-0000-000000000002"
CAND2_ID = "00000000-0000-0000-0000-000000000003"
CAND3_ID = "00000000-0000-0000-0000-000000000004"


def _make_profile(
    pid: str = USER_ID,
    methods: str = "qualitative",
    interests: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": pid,
        "full_name": "Test User",
        "career_stage": "PhD",
        "methods_effective": methods,
        "interests": interests or ["Robotics", "HCI"],
        "skills": ["Python"],
        "is_complete": True,
        "is_synthetic": False,
        "embedding_hash": "dummy_hash",
        "embedding_model": "gemini-embedding-2",
        "embedded_at": "2026-10-05T00:00:00+00:00",
    }


def _make_rpc_rows() -> list[dict[str, Any]]:
    return [
        {
            "id": CAND1_ID,
            "full_name": "Dr. Alice",
            "career_stage": "Postdoc",
            "methods_effective": "quantitative",
            "interests": ["Robotics"],
            "skills": ["ROS"],
            "is_synthetic": False,
            "similarity": 0.85,
        },
        {
            "id": CAND2_ID,
            "full_name": "Bob Synth",
            "career_stage": "PhD",
            "methods_effective": "qualitative",
            "interests": ["HCI"],
            "skills": ["Interviews"],
            "is_synthetic": True,
            "similarity": 0.72,
        },
    ]


def test_compute_match_key_sensitivity():
    p1 = _make_profile(interests=["Robotics"])
    p2 = _make_profile(interests=["Robotics", "Computer Vision"])

    key1 = matches_repo.compute_match_key(p1, "peer")
    key2 = matches_repo.compute_match_key(p2, "peer")
    assert key1 != key2

    # Mode sensitivity
    key_mentor = matches_repo.compute_match_key(p1, "mentor")
    assert key1 != key_mentor

    # Non-rerank field changes (e.g. institution or full_name) should not change match_key
    # (since rerank prompt sanitizes and excludes private/identifying fields)
    p3 = dict(p1)
    p3["full_name"] = "Different Name"
    p3["institution"] = "Different Univ"
    assert matches_repo.compute_match_key(p3, "peer") == key1


def test_rung1_fresh_ai_cache_hit(monkeypatch):
    fake = FakeMatchingSupabase(initial_profile=_make_profile())
    fake.rpc_rows = _make_rpc_rows()

    cached_items = [
        {
            "id": CAND1_ID,
            "full_name": "Dr. Alice",
            "score": 92,
            "strength": "Strong match",
            "why": "Cached AI why",
            "why_source": "ai",
            "similarity": 0.85,
        }
    ]
    key = matches_repo.compute_match_key(_make_profile(), "peer")
    now_iso = datetime.now(timezone.utc).isoformat()
    fake.tables["match_cache"] = [
        {
            "user_id": USER_ID,
            "mode": "peer",
            "profile_hash": key,
            "source": "ai",
            "results": cached_items,
            "created_at": now_iso,
        }
    ]

    # Spy on rerank to ensure it is NOT called
    called = []
    monkeypatch.setattr(
        rerank, "rerank_candidates", lambda *a, **k: called.append(True)
    )

    res = matching.get_matches(fake, USER_ID, mode="peer", refresh=False)
    assert res.from_cache is True
    assert res.source == "ai"
    assert res.notice is None
    assert len(res.items) == 1
    assert res.items[0]["id"] == CAND1_ID
    assert len(called) == 0  # No AI call
    assert len(fake.rpc_calls) == 0  # No RPC call


def test_profile_change_invalidates_cache(monkeypatch):
    fake = FakeMatchingSupabase(initial_profile=_make_profile(interests=["Bio"]))
    fake.rpc_rows = _make_rpc_rows()

    # Seed cache with OLD profile hash
    old_profile = _make_profile(interests=["Robotics"])
    old_key = matches_repo.compute_match_key(old_profile, "peer")
    fake.tables["match_cache"] = [
        {
            "user_id": USER_ID,
            "mode": "peer",
            "profile_hash": old_key,
            "source": "ai",
            "results": [{"id": CAND1_ID, "full_name": "Dr. Alice"}],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    ]

    ai_called = []

    def _mock_rerank(me, cands):
        ai_called.append(True)
        return [
            matching.to_item(c, me, score=88, why="Fresh", why_source="ai")
            for c in cands
        ]

    monkeypatch.setattr(rerank, "rerank_candidates", _mock_rerank)

    res = matching.get_matches(fake, USER_ID, mode="peer", refresh=False)
    assert res.from_cache is False
    assert res.source == "ai"
    assert len(ai_called) == 1
    assert len(fake.rpc_calls) == 1  # RPC was called


def test_connections_exclusion_filters_cached_and_live():
    fake = FakeMatchingSupabase(initial_profile=_make_profile())
    fake.rpc_rows = _make_rpc_rows()

    # Pre-populate connection between USER_ID and CAND1_ID
    fake.tables["connections"] = [
        {"requester_id": USER_ID, "recipient_id": CAND1_ID, "status": "pending"}
    ]

    # Pre-populate cache containing both CAND1 and CAND2
    key = matches_repo.compute_match_key(_make_profile(), "peer")
    cached_items = [
        {"id": CAND1_ID, "full_name": "Dr. Alice", "source": "ai"},
        {"id": CAND2_ID, "full_name": "Bob Synth", "source": "ai"},
    ]
    fake.tables["match_cache"] = [
        {
            "user_id": USER_ID,
            "mode": "peer",
            "profile_hash": key,
            "source": "ai",
            "results": cached_items,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    ]

    res = matching.get_matches(fake, USER_ID, mode="peer", refresh=False)
    # CAND1 must be excluded from cached results because of active connection
    assert len(res.items) == 1
    assert res.items[0]["id"] == CAND2_ID


def test_embedding_cache_ttl_expiry(monkeypatch):
    fake = FakeMatchingSupabase(initial_profile=_make_profile())
    fake.rpc_rows = _make_rpc_rows()

    key = matches_repo.compute_match_key(_make_profile(), "peer")

    # Embedding cache older than 10 minutes (600s)
    old_time = (
        datetime.now(timezone.utc) - timedelta(seconds=601)
    ).isoformat()
    fake.tables["match_cache"] = [
        {
            "user_id": USER_ID,
            "mode": "peer",
            "profile_hash": key,
            "source": "embedding",
            "results": [{"id": CAND1_ID, "full_name": "Dr. Alice"}],
            "created_at": old_time,
        }
    ]

    # Mock AI re-attempt on expired embedding cache
    monkeypatch.setattr(
        rerank,
        "rerank_candidates",
        lambda me, cands: [
            matching.to_item(c, me, score=90, why="Live AI", why_source="ai")
            for c in cands
        ],
    )

    res = matching.get_matches(fake, USER_ID, mode="peer", refresh=False)
    assert res.from_cache is False
    assert res.source == "ai"
    assert len(fake.rpc_calls) == 1


def test_stale_ai_cache_fallback_when_live_fails(monkeypatch):
    fake = FakeMatchingSupabase(initial_profile=_make_profile())
    fake.rpc_rows = _make_rpc_rows()

    key = "different_older_key"
    cached_ai = [
        {
            "id": CAND2_ID,
            "full_name": "Bob Synth",
            "score": 85,
            "why": "Old AI explanation",
        }
    ]
    fake.tables["match_cache"] = [
        {
            "user_id": USER_ID,
            "mode": "peer",
            "profile_hash": key,
            "source": "ai",
            "results": cached_ai,
            "created_at": "2026-10-01T12:00:00+00:00",
        }
    ]

    # Live AI fails
    def _fail_rerank(*a, **k):
        raise rerank.AIUnavailable("Gemini quota exceeded")

    monkeypatch.setattr(rerank, "rerank_candidates", _fail_rerank)

    res = matching.get_matches(fake, USER_ID, mode="peer", refresh=False)
    assert res.notice == matching.STALE_AI_NOTICE
    assert res.from_cache is True
    assert res.source == "ai"
    assert len(res.items) == 1
    assert res.items[0]["id"] == CAND2_ID


def test_forced_fallback_env_skips_cache(monkeypatch):
    fake = FakeMatchingSupabase(initial_profile=_make_profile())
    fake.rpc_rows = _make_rpc_rows()

    key = matches_repo.compute_match_key(_make_profile(), "peer")
    fake.tables["match_cache"] = [
        {
            "user_id": USER_ID,
            "mode": "peer",
            "profile_hash": key,
            "source": "ai",
            "results": [{"id": CAND1_ID, "full_name": "Dr. Alice"}],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    ]

    # Set forced fallback switch
    monkeypatch.setenv("FINDINGS_FORCE_AI_FALLBACK", "1")

    res = matching.get_matches(fake, USER_ID, mode="peer", refresh=False)
    assert res.from_cache is False
    assert res.source == "embedding"
    assert res.notice == matching.FALLBACK_NOTICE


def test_app_test_refresh_button_and_cooldown():
    fake = FakeMatchingSupabase(initial_profile=_make_profile())
    fake.rpc_rows = _make_rpc_rows()

    fake.auth._store("test@example.org")
    at = AppTest.from_file(APP, default_timeout=15)
    at.secrets.update(SECRETS)
    at.session_state["sb"] = fake
    at.session_state["user"] = {"id": USER_ID, "email": "test@example.org"}
    at.run()
    at.switch_page("views/matches.py").run()

    assert not at.exception
    # Find Refresh button
    refresh_btn = next((b for b in at.button if b.key == "btn_refresh_peer"), None)
    assert refresh_btn is not None

    # First click sets cooldown timestamp and reruns
    refresh_btn.click().run()
    assert not at.exception
    assert "matches_last_refreshed_peer" in at.session_state

    # Immediate second click hits cooldown
    refresh_btn = next((b for b in at.button if b.key == "btn_refresh_peer"), None)
    refresh_btn.click().run()
    assert not at.exception
    # Toast displayed for cooldown
    toasts = [t.value for t in at.toast]
    assert any("Please wait" in t and "before refreshing" in t for t in toasts)
