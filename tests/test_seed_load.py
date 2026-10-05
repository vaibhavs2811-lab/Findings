"""Unit tests for seed loader logic, diversity metric computation, and admin repo."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from findings.repos.seed_admin import seed_uuid, upsert_seed_profiles
from scripts.seed_load import calculate_diversity_metrics, get_admin_client


def test_seed_uuid_deterministic():
    u1 = seed_uuid("seed-001")
    u2 = seed_uuid("seed-001")
    u3 = seed_uuid("seed-002")

    assert u1 == u2
    assert u1 != u3
    assert len(u1) == 36  # UUID standard length


def test_calculate_diversity_metrics_orthogonal_and_identical():
    # 1. Orthogonal vectors -> cosine similarity = 0
    orthogonal_profiles = [
        {"seed_id": "s1", "embedding": [1.0, 0.0, 0.0]},
        {"seed_id": "s2", "embedding": [0.0, 1.0, 0.0]},
        {"seed_id": "s3", "embedding": [0.0, 0.0, 1.0]},
    ]
    metrics = calculate_diversity_metrics(orthogonal_profiles)
    assert metrics["mean_pairwise"] == 0.0
    assert metrics["max_pairwise"] == 0.0
    assert metrics["near_duplicates"] == []

    # 2. Near-duplicate vectors -> cosine similarity >= 0.95
    near_dupe_profiles = [
        {"seed_id": "s1", "embedding": [1.0, 0.0]},
        {"seed_id": "s2", "embedding": [0.99, 0.141]},  # dot ~ 0.99
    ]
    m_dupe = calculate_diversity_metrics(near_dupe_profiles)
    assert m_dupe["max_pairwise"] >= 0.95
    assert len(m_dupe["near_duplicates"]) == 1
    assert m_dupe["near_duplicates"][0][0] == "s1"
    assert m_dupe["near_duplicates"][0][1] == "s2"


def test_get_admin_client_validates_key_prefix():
    with pytest.raises(ValueError, match="must start with 'sb_secret_'"):
        get_admin_client("https://abc.supabase.co", "publishable_key_123")


def test_upsert_seed_profiles_batches_and_projects():
    mock_sb = MagicMock()
    mock_profiles_query = MagicMock()
    mock_contacts_query = MagicMock()

    def mock_table(name: str):
        if name == "profiles":
            return mock_profiles_query
        elif name == "profile_contacts":
            return mock_contacts_query
        return MagicMock()

    mock_sb.table.side_effect = mock_table

    profiles = [
        {
            "seed_id": "seed-001",
            "full_name": "Test Researcher",
            "career_stage": "Postdoc",
            "institution": "Test Inst",
            "methods_effective": "quantitative",
            "is_complete": True,
            "email": "test.seed001@example.org",
            "embedding": [0.5] * 768,
            "embedding_hash": "hash123",
            "embedding_model": "gemini-embedding-2",
            "embedded_at": "2026-10-05T00:00:00Z",
        }
    ]

    p_count, c_count = upsert_seed_profiles(mock_sb, profiles)

    assert p_count == 1
    assert c_count == 1

    # Verify upsert called on profiles table
    mock_profiles_query.upsert.assert_called_once()
    upserted_rows = mock_profiles_query.upsert.call_args[0][0]
    assert len(upserted_rows) == 1
    assert upserted_rows[0]["full_name"] == "Test Researcher"
    assert upserted_rows[0]["is_synthetic"] is True
    assert upserted_rows[0]["embedding"] == [0.5] * 768

    # Verify upsert called on profile_contacts table
    mock_contacts_query.upsert.assert_called_once()
    contact_rows = mock_contacts_query.upsert.call_args[0][0]
    assert len(contact_rows) == 1
    assert contact_rows[0]["contact_email"] == "test.seed001@example.org"
