"""Mentorship give/need fit and two-sided rerank (MENT-01..04). No network."""

from __future__ import annotations

import pytest

from findings.ai import mentorship_prompt as mp
from findings.ai.client import AIUnavailable
from findings.services import mentorship_fit as fit

JUNIOR = {
    "career_stage": "Master's",
    "interests": ["maternal health"],
    "want_to_learn": ["thematic analysis", "grant writing"],
    "contributable_skills": ["transcription", "literature review"],
    "seeking_mentor": True,
}
MENTOR_A = {
    "id": "a",
    "full_name": "Mentor A",
    "career_stage": "Faculty",
    "interests": ["maternal health"],
    "offers": ["Thematic analysis training"],
    "needs": ["Interview transcription"],
    "similarity": 0.7,
    "open_to_mentoring": True,
}
MENTOR_B = {
    "id": "b",
    "full_name": "Mentor B",
    "career_stage": "Postdoc",
    "interests": ["machine learning"],
    "offers": ["Deep learning"],
    "needs": ["GPU time"],
    "similarity": 0.8,
    "open_to_mentoring": True,
}


def test_exchange_sides_mentor_mode():
    gets, gives = fit.exchange_sides(JUNIOR, MENTOR_A, "mentor")
    assert gets == ["Thematic analysis training"]
    assert gives == ["transcription"]


def test_exchange_sides_mentee_mode_swaps_roles():
    mentor_viewer = {"offers": ["Thematic analysis"], "needs": ["Transcription help"]}
    junior_cand = {"want_to_learn": ["thematic analysis"], "contributable_skills": ["transcription"]}
    gets, gives = fit.exchange_sides(mentor_viewer, junior_cand, "mentee")
    assert gets == ["transcription"]
    assert gives == ["thematic analysis"] or gives == ["Thematic analysis"]


def test_fit_needs_both_directions_for_high_score():
    one_way = {"offers": ["Thematic analysis"], "needs": ["Quantum computing"]}
    assert fit.fit_score(JUNIOR, MENTOR_A, "mentor") > fit.fit_score(JUNIOR, one_way, "mentor")
    assert fit.fit_score(JUNIOR, MENTOR_B, "mentor") == 0


def test_shortlist_prefers_give_need_fit_over_similarity():
    ranked = fit.shortlist(JUNIOR, [MENTOR_B, MENTOR_A], "mentor")
    assert [r["id"] for r in ranked] == ["a", "b"]


def test_template_exchange_names_overlap_and_gaps():
    give, get = fit.template_exchange(JUNIOR, MENTOR_A, "mentor")
    assert "Thematic analysis" in give
    assert "transcription" in get
    give_b, get_b = fit.template_exchange(JUNIOR, MENTOR_B, "mentor")
    assert "No direct overlap" in give_b and "No direct overlap" in get_b


def test_labels_per_mode():
    assert fit.exchange_labels("mentor") == (
        "What you get from this mentor",
        "What this mentor gets from you",
    )
    assert fit.exchange_labels("mentee")[0] == "What you get from this mentee"


def test_cache_hash_changes_with_give_need_and_mode():
    base = "abc"
    h1 = fit.cache_hash(base, JUNIOR, "mentor")
    assert h1 == fit.cache_hash(base, dict(JUNIOR), "mentor")
    changed = dict(JUNIOR, want_to_learn=["something else"])
    assert fit.cache_hash(base, changed, "mentor") != h1
    assert fit.cache_hash(base, JUNIOR, "mentee") != h1


def test_prompt_has_ids_lists_no_names_and_delimiters():
    prompt = mp.build_mentorship_prompt(JUNIOR, [MENTOR_A, MENTOR_B], "mentor")
    assert 'id="c1"' in prompt and 'id="c2"' in prompt
    assert "Thematic analysis training" in prompt
    assert "Mentor A" not in prompt and "Mentor B" not in prompt
    assert "untrusted" in prompt.lower()
    assert "MENTOR" in prompt
    assert "MENTEES" in mp.build_mentorship_prompt(MENTOR_A, [JUNIOR], "mentee")


def _fake(monkeypatch, matches):
    calls = []

    def fake(prompt, schema, **kw):
        calls.append(prompt)
        return mp.MentorRerankResponse(matches=matches)

    monkeypatch.setattr(mp, "generate_structured", fake)
    return calls


def _m(cid, score, give="They teach thematic analysis.", get="You transcribe interviews."):
    return mp.MentorMatchItem(
        candidate_id=cid,
        score=score,
        why="Their thematic analysis training fits your maternal health work.",
        they_give_you=give,
        you_give_them=get,
    )


def test_rerank_orders_clamps_drops_unknown_and_appends_missing(monkeypatch):
    calls = _fake(monkeypatch, [_m("c1", 140), _m("c99", 90)])
    items = mp.rerank_mentorship(JUNIOR, [MENTOR_A, MENTOR_B], "mentor")
    assert len(calls) == 1
    assert [i["id"] for i in items] == ["a", "b"]
    assert items[0]["score"] == 100
    assert items[0]["they_give_you"] and items[0]["you_give_them"]
    assert items[1]["why_source"] == "template"
    assert items[1]["they_give_you"]


def test_rerank_truncates_exchange_text(monkeypatch):
    _fake(monkeypatch, [_m("c1", 80, give="x" * 500, get="y" * 500)])
    item = mp.rerank_mentorship(JUNIOR, [MENTOR_A], "mentor")[0]
    assert len(item["they_give_you"]) == fit.EXCHANGE_TEXT_LIMIT
    assert len(item["you_give_them"]) == fit.EXCHANGE_TEXT_LIMIT


def test_rerank_empty_exchange_falls_back_to_template(monkeypatch):
    _fake(monkeypatch, [_m("c1", 80, give="", get="")])
    item = mp.rerank_mentorship(JUNIOR, [MENTOR_A], "mentor")[0]
    assert "Thematic analysis" in item["they_give_you"]


def test_rerank_raises_when_gemini_fails(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("down")

    monkeypatch.setattr(mp, "generate_structured", boom)
    with pytest.raises(AIUnavailable):
        mp.rerank_mentorship(JUNIOR, [MENTOR_A], "mentor")


def test_rerank_raises_when_nothing_valid(monkeypatch):
    _fake(monkeypatch, [_m("c42", 50)])
    with pytest.raises(AIUnavailable):
        mp.rerank_mentorship(JUNIOR, [MENTOR_A], "mentor")


def test_forced_fallback_env(monkeypatch):
    monkeypatch.setenv("FINDINGS_FORCE_AI_FALLBACK", "1")
    with pytest.raises(AIUnavailable):
        mp.rerank_mentorship(JUNIOR, [MENTOR_A], "mentor")


def test_fallback_items_carry_both_sides():
    items = mp.fallback_items(JUNIOR, [MENTOR_A, MENTOR_B], "mentor")
    assert all(i["they_give_you"] and i["you_give_them"] for i in items)
    assert items[0]["why_source"] == "template"


# ---------------------------------------------------------------------------
# Integration: get_matches in mentor mode and the card on My Matches
# ---------------------------------------------------------------------------

def _mentor_fixtures():
    from tests.fakes_matching import FakeMatchingSupabase

    me = {
        "id": "00000000-0000-0000-0000-000000000001",
        "full_name": "Junior User",
        "career_stage": "Master's",
        "methods_effective": "qualitative",
        "interests": ["maternal health"],
        "skills": ["Python"],
        "want_to_learn": ["thematic analysis"],
        "contributable_skills": ["transcription"],
        "seeking_mentor": True,
        "open_to_mentoring": False,
        "is_complete": True,
        "is_synthetic": False,
        "embedding_hash": "x",
        "embedding_model": "gemini-embedding-2",
        "embedded_at": "2026-10-05T00:00:00+00:00",
    }
    sb = FakeMatchingSupabase(initial_profile=me)
    sb.rpc_rows = [dict(MENTOR_A, id="00000000-0000-0000-0000-0000000000a1")]
    return sb, me


def test_get_matches_mentor_mode_ai_path_carries_both_sides(monkeypatch):
    from findings.services import matching

    sb, me = _mentor_fixtures()
    monkeypatch.setattr(matching.embeddings, "profile_hash", lambda p: "x")
    _fake(monkeypatch, [_m("c1", 88)])
    res = matching.get_matches(sb, me["id"], mode="mentor")
    assert res.source == "ai"
    assert res.items[0]["they_give_you"] and res.items[0]["you_give_them"]
    assert sb.rpc_calls[0][0] == "match_mentorship"


def test_get_matches_mentor_mode_falls_back_with_both_sides(monkeypatch):
    from findings.services import matching

    sb, me = _mentor_fixtures()
    monkeypatch.setattr(matching.embeddings, "profile_hash", lambda p: "x")

    def boom(*a, **k):
        raise RuntimeError("down")

    monkeypatch.setattr(mp, "generate_structured", boom)
    res = matching.get_matches(sb, me["id"], mode="mentor")
    assert res.source == "embedding"
    assert res.notice == matching.FALLBACK_NOTICE
    assert res.items[0]["they_give_you"] and res.items[0]["you_give_them"]


def test_mentor_card_shows_both_labels_and_peer_card_does_not(monkeypatch):
    from pathlib import Path

    from streamlit.testing.v1 import AppTest

    from findings.services import matching

    app = str(Path(__file__).resolve().parent.parent / "app.py")
    secrets = {
        "SUPABASE_URL": "https://abc.supabase.co",
        "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_x",
    }
    sb, me = _mentor_fixtures()
    monkeypatch.setattr(matching.embeddings, "profile_hash", lambda p: "x")
    _fake(monkeypatch, [_m("c1", 88)])
    sb.auth._store("junior@example.org")
    at = AppTest.from_file(app, default_timeout=20)
    at.secrets.update(secrets)
    at.session_state["sb"] = sb
    at.session_state["user"] = {"id": me["id"], "email": "junior@example.org"}
    at.run()
    at.switch_page("views/matches.py").run()
    at.segmented_control(key="match_view").set_value("Mentorship").run()
    assert not at.exception
    text = " ".join(m.value for m in at.markdown)
    assert "What you get from this mentor" in text
    assert "What this mentor gets from you" in text
