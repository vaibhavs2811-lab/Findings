"""Tests for hash-gated vector embedding computation on save and lazily in matching service."""

from __future__ import annotations

from typing import Any

from findings.ai import embeddings
from findings.ai.client import AIUnavailable
from findings.ai.methods import MethodsSuggestion
from findings.services import matching, profile_service
from tests.fakes_matching import FakeMatchingSupabase

USER_ID = "00000000-0000-0000-0000-000000000001"


def _neutralise_methods(monkeypatch):
    """Neutralise Phase 2 methods Gemini call so no network calls happen."""
    monkeypatch.setattr(
        profile_service,
        "suggest_methods",
        lambda _p, **_k: MethodsSuggestion(label="quantitative", reason="Testing"),
    )


def test_ensure_embedding_unchanged(monkeypatch):
    profile = {
        "id": USER_ID,
        "full_name": "Test User",
        "career_stage": "PhD",
        "interests": ["Robotics"],
        "is_complete": True,
    }
    phash = embeddings.profile_hash(profile)
    meta = {
        "id": USER_ID,
        "embedding_hash": phash,
        "embedding_model": embeddings.EMBED_MODEL,
        "embedded_at": "2026-10-05T00:00:00+00:00",
    }
    sb = FakeMatchingSupabase(initial_profile={**profile, **meta})

    embed_calls = []
    monkeypatch.setattr(embeddings, "embed_profile", lambda text: embed_calls.append(text) or [0.1] * 768)

    status = matching.ensure_embedding(sb, USER_ID, profile)
    assert status == "unchanged"
    assert len(embed_calls) == 0


def test_ensure_embedding_updated_on_changed_hash_or_model(monkeypatch):
    profile = {
        "id": USER_ID,
        "full_name": "Test User",
        "career_stage": "PhD",
        "interests": ["Robotics"],
        "is_complete": True,
    }
    meta = {
        "id": USER_ID,
        "embedding_hash": "stale_hash",
        "embedding_model": embeddings.EMBED_MODEL,
        "embedded_at": "2026-10-05T00:00:00+00:00",
    }
    sb = FakeMatchingSupabase(initial_profile={**profile, **meta})

    embed_calls = []
    mock_vec = [0.2] * 768
    monkeypatch.setattr(embeddings, "embed_profile", lambda text: embed_calls.append(text) or mock_vec)

    status = matching.ensure_embedding(sb, USER_ID, profile)
    assert status == "updated"
    assert len(embed_calls) == 1

    # Verify update payload keys
    updates = [args for table, op, args in sb.log if table == "profiles" and op == "update"]
    assert len(updates) == 1
    payload = updates[0]
    assert set(payload.keys()) == {"embedding", "embedding_model", "embedding_hash", "embedded_at"}
    assert payload["embedding"] == mock_vec
    assert payload["embedding_model"] == embeddings.EMBED_MODEL
    assert payload["embedding_hash"] == embeddings.profile_hash(profile)


def test_ensure_embedding_exception_returns_stale_or_failed(monkeypatch):
    profile = {
        "id": USER_ID,
        "full_name": "Test User",
        "career_stage": "PhD",
        "interests": ["Robotics"],
        "is_complete": True,
    }

    def _fail(_text):
        raise AIUnavailable("Embedding API rate limited")

    monkeypatch.setattr(embeddings, "embed_profile", _fail)

    # 1. With previous embedded_at -> returns "stale"
    meta_stale = {
        "id": USER_ID,
        "embedding_hash": "old_hash",
        "embedding_model": embeddings.EMBED_MODEL,
        "embedded_at": "2026-10-05T00:00:00+00:00",
    }
    sb_stale = FakeMatchingSupabase(initial_profile={**profile, **meta_stale})
    status_stale = matching.ensure_embedding(sb_stale, USER_ID, profile)
    assert status_stale == "stale"

    # 2. Without previous embedded_at -> returns "failed"
    meta_none = {
        "id": USER_ID,
        "embedding_hash": None,
        "embedding_model": None,
        "embedded_at": None,
    }
    sb_none = FakeMatchingSupabase(initial_profile={**profile, **meta_none})
    status_failed = matching.ensure_embedding(sb_none, USER_ID, profile)
    assert status_failed == "failed"


def test_ensure_embedding_incomplete_profile_skipped(monkeypatch):
    profile = {
        "id": USER_ID,
        "full_name": "Incomplete User",
        "career_stage": "PhD",
        "interests": [],
        "is_complete": False,
    }
    sb = FakeMatchingSupabase(initial_profile=profile)
    embed_calls = []
    monkeypatch.setattr(embeddings, "embed_profile", lambda text: embed_calls.append(text) or [0.1] * 768)

    status = matching.ensure_embedding(sb, USER_ID, profile)
    assert status == "skipped"
    assert len(embed_calls) == 0


def test_save_profile_twice_identical_content(monkeypatch):
    _neutralise_methods(monkeypatch)

    embed_calls = []
    monkeypatch.setattr(
        embeddings,
        "embed_profile",
        lambda text: embed_calls.append(text) or [0.1] * 768,
    )

    sb = FakeMatchingSupabase(initial_profile={
        "id": USER_ID,
        "full_name": "Old Name",
        "career_stage": "PhD",
        "interests": [],
        "is_complete": False,
    })
    form: dict[str, Any] = {
        "full_name": "Test User",
        "career_stage": "PhD",
        "interests": ["Robotics", "AI"],
    }

    # First save: triggers embedding
    res1 = profile_service.save_profile(sb, USER_ID, form)
    assert res1["embedding_status"] == "updated"
    assert len(embed_calls) == 1

    # Second save with identical content: does not trigger embedding
    res2 = profile_service.save_profile(sb, USER_ID, form)
    assert res2["embedding_status"] == "unchanged"
    assert len(embed_calls) == 1


def test_get_matches_behavior_on_ensure_embedding_status(monkeypatch):
    cand_row = {
        "id": "00000000-0000-0000-0000-000000000002",
        "full_name": "Peer Candidate",
        "career_stage": "Postdoc",
        "methods_effective": "quantitative",
        "interests": ["Robotics"],
        "similarity": 0.85,
    }

    # Case 1: ensure_embedding returns "failed" -> EMBED_FAILED_NOTICE and no RPC call
    monkeypatch.setattr(matching, "ensure_embedding", lambda _sb, _uid, _p: "failed")
    sb1 = FakeMatchingSupabase(initial_profile={
        "id": USER_ID,
        "full_name": "Test",
        "career_stage": "PhD",
        "interests": ["Robotics"],
        "is_complete": True,
    })
    sb1.rpc_rows = [cand_row]
    res1 = matching.get_matches(sb1, USER_ID, mode="peer")
    assert res1.notice == matching.EMBED_FAILED_NOTICE
    assert len(res1.items) == 0
    assert len(sb1.rpc_calls) == 0

    # Case 2: ensure_embedding returns "stale" -> still calls RPC
    monkeypatch.setattr(matching, "ensure_embedding", lambda _sb, _uid, _p: "stale")
    sb2 = FakeMatchingSupabase(initial_profile={
        "id": USER_ID,
        "full_name": "Test",
        "career_stage": "PhD",
        "interests": ["Robotics"],
        "is_complete": True,
    })
    sb2.rpc_rows = [cand_row]
    res2 = matching.get_matches(sb2, USER_ID, mode="peer")
    assert res2.notice in (None, matching.FALLBACK_NOTICE)
    assert len(res2.items) == 1
    assert len(sb2.rpc_calls) == 1

