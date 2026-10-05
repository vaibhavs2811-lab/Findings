"""AppTest and UI unit tests for views/profile.py and ui/profile_view.py."""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from tests.fakes_profiles import FakeProfilesSupabase

APP = str(Path(__file__).resolve().parent.parent / "app.py")
SECRETS = {"SUPABASE_URL": "https://abc.supabase.co", "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_x"}


def _app_at_profile(sb, user_id="user-1", email="alice@example.com") -> AppTest:
    sb.auth._store(email)
    at = AppTest.from_file(APP, default_timeout=15)
    at.secrets.update(SECRETS)
    at.session_state["sb"] = sb
    at.session_state["user"] = {"id": user_id, "email": email}
    at.run()
    at.switch_page("views/profile.py").run()
    return at


def test_tracer_save_and_read_back():
    """Tracer test: enter name, select PhD, select an interest, click Save -> updates DB and switches to view."""
    sb = FakeProfilesSupabase()
    at = _app_at_profile(sb)
    assert not at.exception
    assert at.title[0].value == "My profile"

    # Fill name
    at.text_input(key="f_name").input("Dr. Alice Smith").run()
    # Select stage
    at.selectbox(key="f_stage").select("PhD").run()
    # Select interest
    at.multiselect(key="f_interests").select("Human-computer interaction").run()

    # Click Save
    at.button(key="profile_save").click().run()
    assert not at.exception

    # Row in fake Supabase should be updated
    assert sb.row["full_name"] == "Dr. Alice Smith"
    assert sb.row["career_stage"] == "PhD"
    assert "Human-computer interaction" in sb.row["interests"]
    assert sb.row["is_complete"] is True

    # Check view mode is shown with heading
    assert any("Dr. Alice Smith" in h.value for h in at.subheader)


def test_career_stage_defaults_toggles():
    """Undergrad turns Seeking on and Open off; Postdoc turns Open on and Seeking off."""
    sb = FakeProfilesSupabase()
    at = _app_at_profile(sb)

    # Pick Undergrad
    at.selectbox(key="f_stage").select("Undergrad").run()
    assert at.toggle(key="f_seeking").value is True
    assert at.toggle(key="f_open").value is False

    # Pick Postdoc
    at.selectbox(key="f_stage").select("Postdoc").run()
    assert at.toggle(key="f_seeking").value is False
    assert at.toggle(key="f_open").value is True

    # Manually turn seeking on as Postdoc
    at.toggle(key="f_seeking").set_value(True).run()
    assert at.toggle(key="f_seeking").value is True

    # Pick PhD -> does not change toggles
    at.selectbox(key="f_stage").select("PhD").run()
    assert at.toggle(key="f_seeking").value is True
    assert at.toggle(key="f_open").value is True


def test_give_need_multiselects_depend_on_toggles():
    """With neither toggle on, no give/need multiselects; Open shows 2; Seeking shows 2; both shows 4."""
    sb = FakeProfilesSupabase()
    at = _app_at_profile(sb)

    # Initial: neither toggle
    at.toggle(key="f_seeking").set_value(False).run()
    at.toggle(key="f_open").set_value(False).run()

    keys = [ms.key for ms in at.multiselect]
    assert "f_offers" not in keys
    assert "f_needs" not in keys
    assert "f_contrib" not in keys
    assert "f_learn" not in keys

    # Turn Open on
    at.toggle(key="f_open").set_value(True).run()
    keys = [ms.key for ms in at.multiselect]
    assert "f_offers" in keys
    assert "f_needs" in keys
    assert "f_contrib" not in keys
    assert "f_learn" not in keys

    # Turn Seeking on as well
    at.toggle(key="f_seeking").set_value(True).run()
    keys = [ms.key for ms in at.multiselect]
    assert "f_offers" in keys
    assert "f_needs" in keys
    assert "f_contrib" in keys
    assert "f_learn" in keys


def test_incomplete_save_stays_in_edit_with_caption():
    """Saving with missing required fields keeps mode in edit with missing-items caption."""
    sb = FakeProfilesSupabase()
    at = _app_at_profile(sb)

    at.text_input(key="f_name").input("Bob").run()
    at.button(key="profile_save").click().run()

    # Still in edit mode with caption
    assert any("Missing for a complete profile" in c.value for c in at.caption)
    assert at.text_input(key="f_name") is not None


def test_complete_profile_opens_in_view_and_edit_cancel():
    """Complete profile opens in view mode. Edit switches to form; Cancel returns to view."""
    complete_row = {
        "id": "user-1",
        "full_name": "Dr. Carol Danvers",
        "career_stage": "Faculty",
        "interests": ["Machine learning"],
        "is_complete": True,
    }
    sb = FakeProfilesSupabase(row=complete_row)
    at = _app_at_profile(sb)

    # Initial mode: view
    assert any("Dr. Carol Danvers" in h.value for h in at.subheader)
    assert at.button(key="profile_edit") is not None

    # Click Edit
    at.button(key="profile_edit").click().run()
    assert at.text_input(key="f_name").value == "Dr. Carol Danvers"
    assert at.button(key="profile_cancel") is not None

    # Click Cancel
    at.button(key="profile_cancel").click().run()
    assert at.button(key="profile_edit") is not None


def _render_runner(data, show_email=False):
    import ui.profile_view

    ui.profile_view.render_profile(data, show_email=show_email)


def test_render_profile_email_privacy():
    """render_profile never exposes email when show_email=False, even if email is present."""
    data = {
        "full_name": "Secret Agent",
        "email": "agent@mi6.gov.uk",
        "career_stage": "Postdoc",
    }
    # Run with show_email=False in an AppTest runner
    at = AppTest.from_function(_render_runner, args=(data,), kwargs={"show_email": False}).run()
    assert not at.exception
    for text_el in at.text:
        assert "agent@mi6.gov.uk" not in text_el.value

    # Run with show_email=True
    at_show = AppTest.from_function(_render_runner, args=(data,), kwargs={"show_email": True}).run()
    assert not at_show.exception
    assert any("agent@mi6.gov.uk" in text_el.value for text_el in at_show.text)


def test_render_profile_markdown_safety():
    """Bio containing markdown links or formatting renders literally via st.text."""
    bio_content = "**bold** [link](https://evil.com) `code`"
    data = {
        "full_name": "Markdown *Injected* Researcher",
        "bio": bio_content,
        "career_stage": "PhD",
    }
    at = AppTest.from_function(_render_runner, args=(data,)).run()
    assert not at.exception
    # Name header is cleaned
    assert "Markdown Injected Researcher" in at.subheader[0].value
    # Bio is rendered via st.text with raw characters intact
    assert any(bio_content in text_el.value for text_el in at.text)


def test_methods_badge_save_ai_suggested(monkeypatch):
    """Saving with methods text calls suggest_methods and renders AI-suggested badge with rationale."""
    import findings.services.profile_service as ps
    from findings.ai.methods import MethodsSuggestion

    monkeypatch.setattr(
        ps,
        "suggest_methods",
        lambda row: MethodsSuggestion(label="quantitative", reason="Heavy focus on statistical genomics"),
    )

    sb = FakeProfilesSupabase()
    at = _app_at_profile(sb)
    at.text_input(key="f_name").input("Alan Turing").run()
    at.selectbox(key="f_stage").select("Faculty").run()
    at.multiselect(key="f_interests").select("Algorithms").run()
    at.button(key="profile_save").click().run()

    assert not at.exception
    assert sb.row["methods_suggested"] == "quantitative"
    assert sb.row["methods_reason"] == "Heavy focus on statistical genomics"
    # Badge rendered in markdown
    assert any("Quantitative" in m.value and "AI-suggested" in m.value for m in at.markdown)
    # Reason rendered in text
    assert any("Heavy focus on statistical genomics" in t.value for t in at.text)


def test_methods_badge_save_ai_unavailable(monkeypatch):
    """When suggest_methods raises AIUnavailable, save succeeds and badge shows Not classified yet."""
    import findings.services.profile_service as ps
    from findings.ai.client import AIUnavailable

    def _fail(row):
        raise AIUnavailable("Simulated quota exhaustion")

    monkeypatch.setattr(ps, "suggest_methods", _fail)

    sb = FakeProfilesSupabase()
    at = _app_at_profile(sb)
    at.text_input(key="f_name").input("Grace Hopper").run()
    at.selectbox(key="f_stage").select("Faculty").run()
    at.multiselect(key="f_interests").select("Compilers").run()
    at.button(key="profile_save").click().run()

    assert not at.exception
    assert sb.row["is_complete"] is True
    # Badge shows unclassified
    assert any("Not classified yet" in m.value for m in at.markdown)
    # Toast flash shows warning
    assert any("AI methods suggestion is unavailable" in t.value for t in at.toast)


def test_methods_save_without_gemini_key_succeeds_offline():
    """Without mocking and with no GEMINI_API_KEY, save completes via the AIUnavailable path."""
    sb = FakeProfilesSupabase()
    at = _app_at_profile(sb)
    at.text_input(key="f_name").input("Ada Lovelace").run()
    at.selectbox(key="f_stage").select("Postdoc").run()
    at.multiselect(key="f_interests").select("Mathematics").run()
    at.button(key="profile_save").click().run()

    assert not at.exception
    assert sb.row["is_complete"] is True
    assert sb.row["methods_suggested"] is None
    assert any("Not classified yet" in m.value for m in at.markdown)


def test_methods_override_segmented_control():
    """Manual override replaces badge label; setting back to auto restores AI suggested."""
    row = {
        "id": "user-1",
        "full_name": "Claude Shannon",
        "career_stage": "Faculty",
        "interests": ["Information theory"],
        "is_complete": True,
        "methods_suggested": "quantitative",
        "methods_reason": "Information entropy formulas",
        "methods_override": None,
        "methods_effective": "quantitative",
    }
    sb = FakeProfilesSupabase(row=row)
    at = _app_at_profile(sb)

    # Initial view state
    assert any("Quantitative" in m.value and "AI-suggested" in m.value for m in at.markdown)
    assert at.segmented_control(key="methods_override_ctl").value == "auto"

    # Set override to mixed
    at.segmented_control(key="methods_override_ctl").set_value("mixed").run()
    assert sb.row["methods_override"] == "mixed"
    assert any("Mixed" in m.value and "set by you" in m.value for m in at.markdown)

    # Reset override to auto
    at.segmented_control(key="methods_override_ctl").set_value("auto").run()
    assert sb.row["methods_override"] is None
    assert any("Quantitative" in m.value and "AI-suggested" in m.value for m in at.markdown)

