from pathlib import Path
from types import SimpleNamespace

import pytest
from streamlit.testing.v1 import AppTest

from findings.core import cookies
from supabase import AuthApiError
from tests.fakes import FakeAuth, FakeSupabase, make_user

APP = str(Path(__file__).resolve().parent.parent / "app.py")
SECRETS = {
    "SUPABASE_URL": "https://example.supabase.co",
    "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_dummy",
}


class RotatingAuth(FakeAuth):
    def refresh_session(self, refresh_token=None):
        self.calls.append(("refresh_session", refresh_token))
        if self.refresh_error:
            raise self.refresh_error
        user = make_user("user-1", "restored@b.com")
        self._session = SimpleNamespace(
            access_token="a", refresh_token="rt_new_token", expires_at=4_102_444_800, user=user
        )
        return SimpleNamespace(user=user, session=self._session)


def _fake():
    sb = FakeSupabase()
    sb.auth = RotatingAuth()
    return sb


@pytest.fixture
def browser(monkeypatch):
    """Fake the browser bridge: `token` is what the browser reports, `calls` what Python sent."""
    state = SimpleNamespace(token=None, calls=[])

    def fake_sync(want, clear=False):
        state.calls.append((want, clear))
        if clear:
            state.token = None
        return state.token

    monkeypatch.setattr(cookies, "sync", fake_sync)
    return state


def _app(sb, token):
    at = AppTest.from_file(APP, default_timeout=15)
    at.secrets.update(SECRETS)
    at.session_state["sb"] = sb
    return at


def _count(sb, name):
    return len([c for c in sb.auth.calls if c[0] == name])


def test_bridge_js_writes_and_reports_cookie_with_flags():
    js = cookies._BRIDGE_JS
    for part in ("findings_rt", "Path=/", "Max-Age=604800", "Max-Age=0", "SameSite=Lax", "Secure"):
        assert part in js
    assert "setStateValue" in js
    assert "cur !== d.seen" in js  # reports only changes, so no rerun loop


class _Bridge:
    def __init__(self, reported=None):
        self.reported = reported
        self.data = None

    def __call__(self, **kwargs):
        self.data = kwargs["data"]
        return {"rt": self.reported}


@pytest.fixture
def no_server_cookie(monkeypatch):
    monkeypatch.setattr(cookies.st, "context", SimpleNamespace(cookies={}), raising=False)


@pytest.mark.parametrize(
    "bad", ['ab"cdefgh', "abcd<efgh", "abcd;efgh", "abcd efgh", "a" * 513, "short", ""]
)
def test_sync_never_sends_unsafe_want_to_browser(monkeypatch, no_server_cookie, bad):
    bridge = _Bridge()
    monkeypatch.setattr(cookies, "_bridge", bridge)
    monkeypatch.setattr(cookies.st, "session_state", {})
    cookies.sync(bad)
    assert bridge.data["want"] is None


def test_sync_returns_validated_browser_token(monkeypatch, no_server_cookie):
    monkeypatch.setattr(cookies.st, "session_state", {})
    monkeypatch.setattr(cookies, "_bridge", _Bridge("good_token-1"))
    assert cookies.sync(None) == "good_token-1"
    monkeypatch.setattr(cookies, "_bridge", _Bridge('bad"value'))
    assert cookies.sync(None) is None
    monkeypatch.setattr(cookies, "_bridge", _Bridge(""))
    assert cookies.sync(None) is None


def test_sync_falls_back_to_server_cookie_only_before_browser_reports(monkeypatch):
    monkeypatch.setattr(cookies.st, "session_state", {})
    monkeypatch.setattr(
        cookies.st, "context", SimpleNamespace(cookies={"findings_rt": "server_tok1"}), raising=False
    )
    monkeypatch.setattr(cookies, "_bridge", _Bridge(None))
    assert cookies.sync(None) == "server_tok1"
    monkeypatch.setattr(cookies, "_bridge", _Bridge(""))
    assert cookies.sync(None) is None


def test_restore_signs_in_once_and_syncs_rotated_token(browser):
    browser.token = "rt_old_token"
    sb = _fake()
    at = _app(sb, None).run()
    assert not at.exception
    assert at.title[0].value == "Welcome to Findings"
    assert "restored@b.com" in at.markdown[0].value
    at.run()
    assert _count(sb, "refresh_session") == 1
    assert browser.calls[-1] == ("rt_new_token", False)


def test_restore_with_reused_token_shows_sign_in(browser):
    browser.token = "rt_old_token"
    sb = _fake()
    sb.auth.refresh_error = AuthApiError(
        "Already Used", 400, "refresh_token_already_used"
    )
    at = _app(sb, None).run()
    assert not at.exception
    assert at.title[0].value == "Sign in to Findings"
    assert _count(sb, "refresh_session") == 1


def test_no_cookie_means_sign_in_and_no_refresh(browser):
    sb = _fake()
    at = _app(sb, None).run()
    assert at.title[0].value == "Sign in to Findings"
    assert _count(sb, "refresh_session") == 0


def test_rotated_session_is_synced(browser):
    sb = _fake()
    user = make_user("user-1", "me@b.com")
    sb.auth._session = SimpleNamespace(
        access_token="a", refresh_token="rt_rotated", expires_at=4_102_444_800, user=user
    )
    at = _app(sb, None)
    at.session_state["user"] = {"id": "user-1", "email": "me@b.com"}
    at.run()
    assert not at.exception
    assert browser.calls[-1] == ("rt_rotated", False)


def test_get_session_error_signs_user_out(browser):
    sb = _fake()

    def boom():
        raise AuthApiError("expired", 400, "refresh_token_not_found")

    sb.auth.get_session = boom
    at = _app(sb, None)
    at.session_state["user"] = {"id": "user-1", "email": "me@b.com"}
    at.run()
    assert not at.exception
    assert at.title[0].value == "Sign in to Findings"
    assert browser.calls[-1] == (None, False)


def test_sign_out_clears_browser_cookie(browser):
    sb = _fake()
    user = make_user("user-1", "me@b.com")
    sb.auth._session = SimpleNamespace(
        access_token="a", refresh_token="rt_live", expires_at=4_102_444_800, user=user
    )
    at = _app(sb, None)
    at.session_state["user"] = {"id": "user-1", "email": "me@b.com"}
    at.run()
    next(b for b in at.sidebar.button if b.label == "Sign out").click()
    at.run()
    assert not at.exception
    assert browser.calls[-1] == (None, True)
    assert at.title[0].value == "Sign in to Findings"
