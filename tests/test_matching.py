"""Tests for peer matching service, repo RPC wrapper, template explanations, schema and UI."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
from streamlit.testing.v1 import AppTest

from findings.repos.profiles import match_profiles
from findings.services.matching import (
    INCOMPLETE_NOTICE,
    UNAVAILABLE_NOTICE,
    get_matches,
    strength_from_similarity,
    template_why,
)
from tests.fakes_matching import FakeMatchingSupabase

APP = str(Path(__file__).resolve().parent.parent / "app.py")
ROOT = Path(__file__).resolve().parent.parent
SECRETS = {
    "SUPABASE_URL": "https://abc.supabase.co",
    "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_x",
}

USER_ID = "00000000-0000-0000-0000-000000000001"
CAND1_ID = "00000000-0000-0000-0000-000000000002"
CAND2_ID = "00000000-0000-0000-0000-000000000003"
CAND3_ID = "00000000-0000-0000-0000-000000000004"


def _make_own_profile(complete: bool = True, methods: str = "qualitative") -> dict[str, Any]:
    return {
        "id": USER_ID,
        "full_name": "Test User",
        "career_stage": "PhD",
        "methods_effective": methods,
        "interests": ["Robotics", "Computer Vision"],
        "skills": ["PyTorch", "SLAM"],
        "is_complete": complete,
        "is_synthetic": False,
        "embedding_hash": "dummy_hash",
        "embedding_model": "gemini-embedding-2",
        "embedded_at": "2026-10-05T00:00:00+00:00",
    }


def _make_rpc_rows() -> list[dict[str, Any]]:
    return [
        {
            "id": CAND1_ID,
            "full_name": "Dr. Alice Smith",
            "career_stage": "Postdoc",
            "methods_effective": "quantitative",
            "interests": ["Robotics", "Reinforcement Learning"],
            "skills": ["Python", "ROS"],
            "is_synthetic": False,
            "similarity": 0.82,
        },
        {
            "id": CAND2_ID,
            "full_name": "Bob Synth",
            "career_stage": "PhD",
            "methods_effective": "qualitative",
            "interests": ["HCI", "Accessibility"],
            "skills": ["Interviews", "Thematic analysis"],
            "is_synthetic": True,
            "similarity": 0.66,
        },
        {
            "id": CAND3_ID,
            "full_name": "Charlie Low",
            "career_stage": "Master's",
            "methods_effective": "mixed",
            "interests": ["Bioinformatics"],
            "skills": ["R"],
            "is_synthetic": False,
            "similarity": 0.41,
        },
    ]


def test_strength_from_similarity():
    assert strength_from_similarity(0.82) == "Strong match"
    assert strength_from_similarity(0.66) == "Good match"
    assert strength_from_similarity(0.41) == "Possible match"


def test_template_why_shared_interest_and_methods_complement():
    me = {"interests": ["Robotics", "AI"], "skills": ["Python"], "methods_effective": "qualitative"}
    cand = {
        "interests": ["robotics", "Bio"],
        "skills": ["C++"],
        "methods_effective": "quantitative",
    }
    why = template_why(me, cand)
    assert "robotics" in why or "Robotics" in why
    assert "Their quantitative methods complement your qualitative approach." in why


def test_template_why_equal_methods():
    me = {"interests": ["HCI"], "skills": [], "methods_effective": "mixed"}
    cand = {"interests": ["UX"], "skills": [], "methods_effective": "mixed"}
    why = template_why(me, cand)
    assert "You both take a mixed approach." in why
    assert len(why) > 0


def test_template_why_never_empty():
    me = {"interests": [], "skills": [], "methods_effective": None}
    cand = {"interests": [], "skills": [], "methods_effective": None}
    why = template_why(me, cand)
    assert len(why) > 10


def test_match_profiles_repo_call():
    fake = FakeMatchingSupabase()
    fake.rpc_rows = [{"id": CAND1_ID, "similarity": 0.8}]
    res = match_profiles(fake, match_count=15, exclude_ids=[USER_ID], mode="peer")
    assert len(res) == 1
    assert len(fake.rpc_calls) == 1
    name, params = fake.rpc_calls[0]
    assert name == "match_profiles"
    assert params["match_count"] == 15
    assert params["exclude_ids"] == [USER_ID]
    assert params["mode"] == "peer"
    assert "query_embedding" not in params


def test_get_matches_preserves_order_and_strengths():
    fake = FakeMatchingSupabase(initial_profile=_make_own_profile(complete=True))
    fake.rpc_rows = _make_rpc_rows()

    res = get_matches(fake, USER_ID, mode="peer")
    assert res.notice is None
    assert res.source == "embedding"
    assert len(res.items) == 3

    assert res.items[0]["id"] == CAND1_ID
    assert res.items[0]["strength"] == "Strong match"
    assert res.items[1]["id"] == CAND2_ID
    assert res.items[1]["strength"] == "Good match"
    assert res.items[2]["id"] == CAND3_ID
    assert res.items[2]["strength"] == "Possible match"


def test_get_matches_drops_self():
    fake = FakeMatchingSupabase(initial_profile=_make_own_profile(complete=True))
    fake.rpc_rows = [{"id": USER_ID, "similarity": 1.0}] + _make_rpc_rows()

    res = get_matches(fake, USER_ID, mode="peer")
    assert len(res.items) == 3
    assert not any(item["id"] == USER_ID for item in res.items)


def test_get_matches_incomplete_profile():
    fake = FakeMatchingSupabase(initial_profile=_make_own_profile(complete=False))
    fake.rpc_rows = _make_rpc_rows()

    res = get_matches(fake, USER_ID, mode="peer")
    assert res.notice == INCOMPLETE_NOTICE
    assert len(res.items) == 0
    assert len(fake.rpc_calls) == 0


def test_get_matches_rpc_error_handled_gracefully():
    fake = FakeMatchingSupabase(initial_profile=_make_own_profile(complete=True))
    fake.rpc_error = RuntimeError("Database timeout")

    res = get_matches(fake, USER_ID, mode="peer")
    assert res.notice == UNAVAILABLE_NOTICE
    assert len(res.items) == 0


def test_get_matches_invalid_mode_raises():
    fake = FakeMatchingSupabase(initial_profile=_make_own_profile(complete=True))
    with pytest.raises(ValueError, match="Unsupported matching mode"):
        get_matches(fake, USER_ID, mode="mentor")


def test_match_profiles_sql_schema_static_guarantees():
    schema_path = ROOT / "supabase" / "schema.sql"
    content = schema_path.read_text(encoding="utf-8")

    # Extract match_profiles section
    match = re.search(
        r"create or replace function public\.match_profiles.*?\$\$(.*?)\$\$;",
        content,
        re.DOTALL,
    )
    assert match is not None, "match_profiles function definition not found in schema.sql"
    body = match.group(0)

    # Static assurances
    assert "security invoker" in body
    assert "auth.uid()" in body
    assert "public.connections" in body
    assert "is_complete" in body
    assert "least(" in body

    # Negative security assurances
    assert "security definer" not in body
    assert "email" not in body
    assert "profile_contacts" not in body

    # Returns table check: returns table segment must not contain embedding column
    returns_table_match = re.search(
        r"returns table\s*\((.*?)\)\s*language",
        body,
        re.DOTALL | re.IGNORECASE,
    )
    assert returns_table_match is not None
    returns_cols = returns_table_match.group(1)
    assert "embedding" not in returns_cols

    # Permissions
    assert re.search(
        r"grant execute on function public\.match_profiles.*?to authenticated",
        content,
    )
    assert re.search(
        r"revoke execute on function public\.match_profiles.*?from public, anon",
        content,
    )


def test_app_test_my_matches_view():
    fake = FakeMatchingSupabase(initial_profile=_make_own_profile(complete=True))
    fake.rpc_rows = _make_rpc_rows()

    fake.auth._store("test@example.org")
    at = AppTest.from_file(APP, default_timeout=15)
    at.secrets.update(SECRETS)
    at.session_state["sb"] = fake
    at.session_state["user"] = {"id": USER_ID, "email": "test@example.org"}
    at.run()
    at.switch_page("views/matches.py").run()

    assert not at.exception

    text_values = [t.value for t in at.text]
    # Candidate names in st.text
    assert any("Dr. Alice Smith" in t for t in text_values)
    assert any("Bob Synth" in t for t in text_values)
    # Why text rendered in st.text
    assert any("methods complement" in t or "complementary" in t or "approach" in t for t in text_values)

    markdown_values = [m.value for m in at.markdown]
    # Strong match and Synthetic badges in markdown
    assert any("Strong match" in m for m in markdown_values)
    assert any("Synthetic" in m for m in markdown_values)

    caption_values = [c.value for c in at.caption]
    assert any("Ranked by profile similarity" in c for c in caption_values)
