"""Tests for findings.repos.profiles repository functions."""

from __future__ import annotations

import pytest

from findings.repos.profiles import (
    PROFILE_COLUMNS,
    PROFILE_SUMMARY_COLUMNS,
    ProfileWriteError,
    get_own_profile,
    update_own,
)
from tests.fakes_profiles import FakeProfilesSupabase


def test_profile_columns_hygiene():
    """PROFILE_COLUMNS and PROFILE_SUMMARY_COLUMNS must never leak star, embedding, or email."""
    for col_str in (PROFILE_COLUMNS, PROFILE_SUMMARY_COLUMNS):
        cols = [c.strip() for c in col_str.split(",")]
        assert "*" not in cols
        assert "embedding" not in cols
        assert "email" not in cols
    full_cols = [c.strip() for c in PROFILE_COLUMNS.split(",")]
    assert "methods_hash" in full_cols
    assert "methods_reason" in full_cols


def test_get_own_profile_defaults_to_profile_columns():
    """get_own_profile reads full PROFILE_COLUMNS by default."""
    sb = FakeProfilesSupabase()
    row = get_own_profile(sb, "user-1")
    assert row is not None
    assert ("table", "profiles") in sb.log
    assert ("select", PROFILE_COLUMNS) in sb.log
    assert ("eq", ("id", "user-1")) in sb.log
    assert ("limit", 1) in sb.log


def test_update_own_calls_update_eq_select():
    """update_own updates payload, filters by user id, and selects PROFILE_COLUMNS."""
    sb = FakeProfilesSupabase()
    payload = {"full_name": "Dr. Marie Curie", "career_stage": "Faculty"}
    res = update_own(sb, "user-1", payload)

    assert res["full_name"] == "Dr. Marie Curie"
    assert res["career_stage"] == "Faculty"
    assert ("table", "profiles") in sb.log
    assert ("update", payload) in sb.log
    assert ("eq", ("id", "user-1")) in sb.log
    assert ("select", PROFILE_COLUMNS) in sb.log


def test_update_own_raises_profile_write_error_on_zero_rows():
    """update_own raises ProfileWriteError when update affects zero rows (e.g. RLS rejection)."""
    sb = FakeProfilesSupabase(zero_rows=True)
    with pytest.raises(ProfileWriteError, match="zero rows"):
        update_own(sb, "user-1", {"full_name": "Test"})
