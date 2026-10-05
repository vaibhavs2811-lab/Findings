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
def synced(monkeypatch):
    calls = []
    monkeypatch.setattr(cookies, "sync_cookie", lambda v: calls.append(v))
    return calls


def _app(sb, token):
    at = AppTest.from_file(APP, default_timeout=15)
    at.secrets.update(SECRETS)
    at.session_state["sb"] = sb
    return at


def _count(sb, name):
    return len([c for c in sb.auth.calls if c[0] == name])


def test_build_script_sets_cookie_with_flags():
    s = cookies.build_cookie_script("abc123_-.XYZ")
    for part in ("findings_rt", "Path=/", "Max-Age=604800", "SameSite=Strict", "Secure"):
        assert part in s
    assert "cur!==want" in s  # only writes when the value differs
    assert '"abc123_-.XYZ"' in s


def test_build_script_none_expires_cookie():
    assert "Max-Age=0" in cookies.build_cookie_script(None)


@pytest.mark.parametrize(
    "bad", ['ab"cdefgh', "abcd<efgh", "abcd;efgh", "abcd efgh", "a" * 513, "short", ""]
)
def test_build_script_rejects_unsafe_values(bad):
    with pytest.raises(ValueError):
        cookies.build_cookie_script(bad)


def test_sync_cookie_never_embeds_invalid_value(monkeypatch):
    out = []
    monkeypatch.setattr(cookies.st, "html", lambda body, **k: out.append(body))
    cookies.sync_cookie('x"; alert(1)//')
    assert "alert" not in out[0]
    assert "Max-Age=0" in out[0]


def test_read_refresh_token_handles_missing_and_bad(monkeypatch):
    def ctx(cookie_dict):
        return SimpleNamespace(cookies=cookie_dict)

    monkeypatch.setattr(cookies.st, "context", ctx({}), raising=False)
    assert cookies.read_refresh_token() is None
    monkeypatch.setattr(cookies.st, "context", ctx({"findings_rt": 'bad"value'}), raising=False)
    assert cookies.read_refresh_token() is None
    monkeypatch.setattr(cookies.st, "context", ctx({"findings_rt": "good_token-1"}), raising=False)
    assert cookies.read_refresh_token() == "good_token-1"
    monkeypatch.setattr(cookies.st, "context", object(), raising=False)
    assert cookies.read_refresh_token() is None


def test_restore_signs_in_once_and_syncs_rotated_token(monkeypatch, synced):
    monkeypatch.setattr(cookies, "read_refresh_token", lambda: "rt_old_token")
    sb = _fake()
    at = _app(sb, None).run()
    assert not at.exception
    assert at.title[0].value == "Welcome to Findings"
    assert "restored@b.com" in at.markdown[0].value
    at.run()
    assert _count(sb, "refresh_session") == 1
    assert synced[-1] == "rt_new_token"


def test_restore_with_reused_token_shows_sign_in(monkeypatch, synced):
    monkeypatch.setattr(cookies, "read_refresh_token", lambda: "rt_old_token")
    sb = _fake()
    sb.auth.refresh_error = AuthApiError(
        "Already Used", 400, "refresh_token_already_used"
    )
    at = _app(sb, None).run()
    assert not at.exception
    assert at.title[0].value == "Sign in to Findings"
    assert synced[-1] is None


def test_no_cookie_means_sign_in_and_no_refresh(monkeypatch, synced):
    monkeypatch.setattr(cookies, "read_refresh_token", lambda: None)
    sb = _fake()
    at = _app(sb, None).run()
    assert at.title[0].value == "Sign in to Findings"
    assert _count(sb, "refresh_session") == 0


def test_rotated_session_is_synced(monkeypatch, synced):
    monkeypatch.setattr(cookies, "read_refresh_token", lambda: None)
    sb = _fake()
    user = make_user("user-1", "me@b.com")
    sb.auth._session = SimpleNamespace(
        access_token="a", refresh_token="rt_rotated", expires_at=4_102_444_800, user=user
    )
    at = _app(sb, None)
    at.session_state["user"] = {"id": "user-1", "email": "me@b.com"}
    at.run()
    assert not at.exception
    assert synced[-1] == "rt_rotated"


def test_get_session_error_signs_user_out(monkeypatch, synced):
    monkeypatch.setattr(cookies, "read_refresh_token", lambda: None)
    sb = _fake()

    def boom():
        raise AuthApiError("expired", 400, "refresh_token_not_found")

    sb.auth.get_session = boom
    at = _app(sb, None)
    at.session_state["user"] = {"id": "user-1", "email": "me@b.com"}
    at.run()
    assert not at.exception
    assert at.title[0].value == "Sign in to Findings"
    assert synced[-1] is None
