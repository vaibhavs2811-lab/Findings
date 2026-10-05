"""Tests for findings.services.profile_service pure logic and save_profile."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from findings.core.constants import CAREER_STAGES
from findings.services import profile_service as ps
from tests.fakes_profiles import FakeProfilesSupabase

ROOT = Path(__file__).resolve().parent.parent


def test_career_stages_matches_schema_sql():
    """CAREER_STAGES in constants must match the check constraint in supabase/schema.sql."""
    schema_text = (ROOT / "supabase" / "schema.sql").read_text(encoding="utf-8")
    match = re.search(r"career_stage in\s*\((.*?)\)", schema_text, re.DOTALL)
    assert match is not None
    # Unescape doubled SQL single quotes: 'Master''s' -> "Master's"
    raw_items = [
        item.strip().strip("'").replace("''", "'")
        for item in match.group(1).split(",")
    ]
    assert tuple(raw_items) == CAREER_STAGES


def test_mentoring_defaults():
    assert ps.mentoring_defaults("Undergrad") == (True, False)
    assert ps.mentoring_defaults("Master's") == (True, False)
    assert ps.mentoring_defaults("Postdoc") == (False, True)
    assert ps.mentoring_defaults("Faculty") == (False, True)
    assert ps.mentoring_defaults("Industry researcher") == (False, True)
    assert ps.mentoring_defaults("PhD") is None
    assert ps.mentoring_defaults(None) is None
    assert ps.mentoring_defaults("Unknown") is None


def test_normalise_text():
    assert ps.normalise_text("  hello world  ", 10) == "hello worl"
    assert ps.normalise_text("   ", 100) is None
    assert ps.normalise_text(None, 100) is None


def test_normalise_list():
    raw = [" Surveys ", "surveys", "", "  ", "Big   data"]
    assert ps.normalise_list(raw) == ["Surveys", "Big data"]

    # 25 items capped to 20
    long_list = [f"Item {i}" for i in range(25)]
    res = ps.normalise_list(long_list)
    assert len(res) == 20
    assert res[0] == "Item 0"
    assert res[-1] == "Item 19"

    # Truncate to 80 chars
    long_item = "A" * 100
    assert ps.normalise_list([long_item]) == ["A" * 80]


def test_is_complete():
    valid = {"full_name": "Alice", "career_stage": "PhD", "interests": ["AI"]}
    assert ps.is_complete(valid) is True

    # Missing name
    assert ps.is_complete({"full_name": "  ", "career_stage": "PhD", "interests": ["AI"]}) is False
    # Missing stage
    assert ps.is_complete({"full_name": "Alice", "career_stage": "Other", "interests": ["AI"]}) is False
    assert ps.is_complete({"full_name": "Alice", "career_stage": None, "interests": ["AI"]}) is False
    # Missing interests
    assert ps.is_complete({"full_name": "Alice", "career_stage": "PhD", "interests": []}) is False


def test_missing_for_complete():
    empty_form = {}
    missing = ps.missing_for_complete(empty_form)
    assert "your name" in missing
    assert "a career stage" in missing
    assert "at least one research interest" in missing

    partial = {"full_name": "Bob", "career_stage": "Undergrad", "interests": []}
    assert ps.missing_for_complete(partial) == ["at least one research interest"]


def test_build_payload_allow_list_and_toggle_rules():
    form = {
        "full_name": "Dr. Alice",
        "career_stage": "Faculty",
        "institution": "MIT",
        "education": "PhD MIT",
        "experience": "10 years",
        "bio": "Bio text",
        "looking_for": "Collaborators",
        "interests": ["NLP", "HCI"],
        "skills": ["Python"],
        "offers": ["Methods training"],
        "needs": ["Lit review"],
        "contributable_skills": ["Coding"],
        "want_to_learn": ["Survey design"],
        "seeking_mentor": False,
        "open_to_mentoring": False,
        "untrusted_field": "injected",
        "id": "stolen-id",
        "is_synthetic": True,
    }

    payload = ps.build_payload(form)

    # Disallowed keys must not be present
    for forbidden in ("id", "is_synthetic", "untrusted_field", "stage_tier", "methods_effective"):
        assert forbidden not in payload

    # Give/need fields forced empty when toggles are False
    assert payload["offers"] == []
    assert payload["needs"] == []
    assert payload["contributable_skills"] == []
    assert payload["want_to_learn"] == []
    assert payload["seeking_mentor"] is False
    assert payload["open_to_mentoring"] is False
    assert payload["is_complete"] is True

    # With toggles True
    form_with_toggles = dict(form)
    form_with_toggles["seeking_mentor"] = True
    form_with_toggles["open_to_mentoring"] = True
    payload2 = ps.build_payload(form_with_toggles)
    assert payload2["offers"] == ["Methods training"]
    assert payload2["needs"] == ["Lit review"]
    assert payload2["contributable_skills"] == ["Coding"]
    assert payload2["want_to_learn"] == ["Survey design"]


def test_save_profile_success():
    sb = FakeProfilesSupabase()
    form = {"full_name": "Alice", "career_stage": "PhD", "interests": ["AI"]}
    saved = ps.save_profile(sb, "user-1", form)
    assert saved["full_name"] == "Alice"
    assert saved["career_stage"] == "PhD"
    assert saved["is_complete"] is True


def test_save_profile_error_wraps_in_profile_save_error():
    sb = FakeProfilesSupabase(zero_rows=True)
    form = {"full_name": "Alice", "career_stage": "PhD", "interests": ["AI"]}
    with pytest.raises(ps.ProfileSaveError, match="Could not save your profile"):
        ps.save_profile(sb, "user-1", form)


def test_save_profile_hash_gated_methods_suggestion(monkeypatch):
    from findings.ai.methods import MethodsSuggestion

    calls: list[dict] = []

    def mock_suggest(profile, **_kwargs):
        calls.append(profile)
        return MethodsSuggestion(label="mixed", reason="Combines surveys with machine learning.")

    monkeypatch.setattr(ps, "suggest_methods", mock_suggest)

    sb = FakeProfilesSupabase()
    form = {"full_name": "Alice", "career_stage": "PhD", "interests": ["AI", "Surveys"]}

    # 1. First save: calls suggest_methods, updates methods fields
    res1 = ps.save_profile(sb, "user-1", form)
    assert res1["ai_status"] == "updated"
    assert res1["methods_suggested"] == "mixed"
    assert res1["methods_reason"] == "Combines surveys with machine learning."
    assert res1["methods_effective"] == "mixed"
    assert len(calls) == 1

    # 2. Second save with identical data: unchanged, no AI call
    res2 = ps.save_profile(sb, "user-1", form)
    assert res2["ai_status"] == "unchanged"
    assert len(calls) == 1

    # 3. Third save with case change only: unchanged, no AI call
    form_case = dict(form, interests=["ai", "surveys "])
    res3 = ps.save_profile(sb, "user-1", form_case)
    assert res3["ai_status"] == "unchanged"
    assert len(calls) == 1


def test_save_profile_skips_ai_when_no_signal(monkeypatch):
    calls: list[dict] = []
    monkeypatch.setattr(ps, "suggest_methods", lambda p, **_k: calls.append(p))

    sb = FakeProfilesSupabase()
    form = {"full_name": "Alice", "career_stage": "PhD", "interests": []}
    res = ps.save_profile(sb, "user-1", form)
    assert res["ai_status"] == "skipped"
    assert len(calls) == 0


def test_save_profile_handles_ai_unavailable(monkeypatch):
    from findings.ai.client import AIUnavailable

    def mock_fail(_p, **_k):
        raise AIUnavailable("Service busy")

    monkeypatch.setattr(ps, "suggest_methods", mock_fail)

    sb = FakeProfilesSupabase()
    form = {"full_name": "Alice", "career_stage": "PhD", "interests": ["AI"]}
    res = ps.save_profile(sb, "user-1", form)

    assert res["ai_status"] == "unavailable"
    assert res["full_name"] == "Alice"
    assert res["methods_suggested"] is None


def test_set_methods_override():
    sb = FakeProfilesSupabase()

    res1 = ps.set_methods_override(sb, "user-1", "quantitative")
    assert res1["methods_override"] == "quantitative"
    assert res1["methods_effective"] == "quantitative"

    res2 = ps.set_methods_override(sb, "user-1", None)
    assert res2["methods_override"] is None

    with pytest.raises(ValueError, match="Invalid methods override"):
        ps.set_methods_override(sb, "user-1", "other")


def test_save_profile_methods_update_failure_returns_unavailable(monkeypatch):
    """When the second update (writing methods suggestion) raises, ai_status is unavailable and core row returned."""
    from findings.ai.methods import MethodsSuggestion

    monkeypatch.setattr(
        ps,
        "suggest_methods",
        lambda _p, **_k: MethodsSuggestion(label="quantitative", reason="Stats"),
    )

    sb = FakeProfilesSupabase()
    # Let first update succeed, make second update fail
    orig_table = sb.table
    call_count = [0]

    def failing_table(name: str):
        query = orig_table(name)
        orig_execute = query.execute

        def wrapped_execute():
            call_count[0] += 1
            if call_count[0] == 2:  # second update
                raise RuntimeError("DB transient connection dropped during methods update")
            return orig_execute()

        query.execute = wrapped_execute
        return query

    monkeypatch.setattr(sb, "table", failing_table)

    form = {"full_name": "Bob", "career_stage": "PhD", "interests": ["Math"]}
    res = ps.save_profile(sb, "user-1", form)
    assert res["ai_status"] == "unavailable"
    assert res["full_name"] == "Bob"
    assert res.get("methods_suggested") is None


def test_save_profile_never_includes_methods_override_in_payload():
    """No update payload sent by save_profile ever contains methods_override."""
    sb = FakeProfilesSupabase()
    form = {
        "full_name": "Carol",
        "career_stage": "Postdoc",
        "interests": ["Physics"],
        "methods_override": "qualitative",  # injected into form
    }
    ps.save_profile(sb, "user-1", form)

    update_payloads = [p for op, p in sb.log if op == "update"]
    for payload in update_payloads:
        assert "methods_override" not in payload

