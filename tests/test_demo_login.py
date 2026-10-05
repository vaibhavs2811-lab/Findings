"""Demo (password) sign-in and the own-record panel on Home. Uses FakeSupabase subclasses."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from streamlit.testing.v1 import AppTest

from findings.repos.profiles import PROFILE_COLUMNS, get_own_profile
from findings.services import auth_service
from findings.services.auth_service import AuthFailure
from tests.fakes import FakeSupabase

APP = str(Path(__file__).resolve().parent.parent / "app.py")
SECRETS = {"SUPABASE_URL": "https://abc.supabase.co", "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_x"}


class RecordingQuery:
    def __init__(self, rows, log, boom=None):
        self._rows, self._log, self._boom = rows, log, boom

    def select(self, cols):
        self._log.append(("select", cols))
        return self

    def eq(self, col, val):
        self._log.append(("eq", (col, val)))
        return self

    def limit(self, n):
        self._log.append(("limit", n))
        return self

    def execute(self):
        if self._boom:
            raise self._boom
        return SimpleNamespace(data=self._rows)


class ProfileFake(FakeSupabase):
    def __init__(self, rows=None, boom=None):
        super().__init__(rows)
        self.log: list = []
        self.boom = boom

    def table(self, name):
        self.log.append(("table", name))
        return RecordingQuery(self.rows, self.log, self.boom)


def _home(sb):
    sb.auth._store("demo@b.com")
    at = AppTest.from_file(APP, default_timeout=15)
    at.secrets.update(SECRETS)
    at.session_state["sb"] = sb
    at.session_state["user"] = {"id": "user-1", "email": "demo@b.com"}
    return at.run()


def test_sign_in_normalises_email_and_returns_identity():
    sb = FakeSupabase()
    assert auth_service.sign_in(sb, "  Demo@B.com ", "correct-horse") == ("user-1", "demo@b.com")
    assert sb.auth.calls[0][1]["email"] == "demo@b.com"


def test_wrong_password_is_friendly_and_empty_password_skips_supabase():
    sb = FakeSupabase()
    with pytest.raises(AuthFailure, match="Wrong email or password"):
        auth_service.sign_in(sb, "demo@b.com", "nope")
    calls_before = len(sb.auth.calls)
    with pytest.raises(AuthFailure):
        auth_service.sign_in(sb, "demo@b.com", "")
    assert len(sb.auth.calls) == calls_before


def test_get_own_profile_selects_explicit_columns_filtered_by_id():
    row = {"id": "user-1", "full_name": "", "created_at": "2026-10-05T10:00:00+00:00"}
    sb = ProfileFake(rows=[row])
    assert get_own_profile(sb, "user-1") == row
    assert ("table", "profiles") in sb.log
    assert ("select", PROFILE_COLUMNS) in sb.log
    assert ("eq", ("id", "user-1")) in sb.log
    assert "embedding" not in PROFILE_COLUMNS
    assert "*" not in PROFILE_COLUMNS


def test_get_own_profile_returns_none_when_no_row():
    assert get_own_profile(ProfileFake(rows=[]), "user-1") is None


def test_home_incomplete_shows_cta_link():
    row = {"id": "user-1", "is_complete": False, "created_at": "2026-10-05T10:00:00+00:00"}
    at = _home(ProfileFake(rows=[row]))
    assert not at.exception
    assert "Your profile is not complete yet" in at.info[0].value
    links = at.get("page_link")
    assert any(getattr(link, "label", getattr(link.proto, "label", "")) == "Complete your profile" for link in links)


def test_home_without_row_shows_cta_link():
    at = _home(ProfileFake(rows=[]))
    assert not at.exception
    assert not at.error
    assert "Your profile is not complete yet" in at.info[0].value
    links = at.get("page_link")
    assert any(getattr(link, "label", getattr(link.proto, "label", "")) == "Complete your profile" for link in links)


def test_home_complete_shows_success_and_view_link():
    row = {"id": "user-1", "is_complete": True, "created_at": "2026-10-05T10:00:00+00:00"}
    at = _home(ProfileFake(rows=[row]))
    assert not at.exception
    assert "Your profile is complete." in at.success[0].value
    links = at.get("page_link")
    assert any(getattr(link, "label", getattr(link.proto, "label", "")) == "View my profile" for link in links)


def test_home_hides_raw_database_errors():
    at = _home(ProfileFake(boom=RuntimeError("secret internals")))
    assert not at.exception
    assert at.warning[0].value == "Could not load your profile record. Try again in a moment."
    assert "secret internals" not in at.warning[0].value
