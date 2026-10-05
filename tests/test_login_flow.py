from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from tests.fakes import FakeSupabase

APP = str(Path(__file__).resolve().parent.parent / "app.py")

SECRETS = {
    "SUPABASE_URL": "https://abc.supabase.co",
    "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_x",
}


def _app(sb=None):
    at = AppTest.from_file(APP, default_timeout=15)
    at.secrets.update(SECRETS)
    at.session_state["sb"] = sb or FakeSupabase()
    return at


def _fill(at, key, value):
    next(w for w in at.text_input if w.key == key).set_value(value)


def _submit(at, label):
    next(b for b in at.button if b.label == label).click()


def test_signed_out_shows_sign_in_page():
    at = _app().run()
    assert not at.exception
    assert at.title[0].value == "Sign in to Findings"
    assert [t.label for t in at.tabs] == ["Sign in", "Create account"]


def test_sign_in_shows_home_with_email():
    at = _app().run()
    _fill(at, "signin_email", "me@b.com")
    _fill(at, "signin_password", "correct-horse")
    _submit(at, "Sign in")
    at.run()
    assert not at.exception
    assert at.title[0].value == "Welcome to Findings"
    assert "me@b.com" in at.markdown[0].value


def test_wrong_password_shows_friendly_error():
    at = _app().run()
    _fill(at, "signin_email", "me@b.com")
    _fill(at, "signin_password", "wrong")
    _submit(at, "Sign in")
    at.run()
    assert at.error[0].value == "Wrong email or password."
    assert at.title[0].value == "Sign in to Findings"


def test_create_account_signs_in_straight_away():
    at = _app().run()
    _fill(at, "signup_email", "new@b.com")
    _fill(at, "signup_password", "secret1")
    _fill(at, "signup_confirm", "secret1")
    _submit(at, "Create account")
    at.run()
    assert at.title[0].value == "Welcome to Findings"
    assert "new@b.com" in at.markdown[0].value


@pytest.mark.parametrize(
    ("pw", "confirm", "msg"),
    [("12345", "12345", "at least 6"), ("secret1", "secret2", "do not match")],
)
def test_create_account_validation_errors(pw, confirm, msg):
    at = _app().run()
    _fill(at, "signup_email", "new@b.com")
    _fill(at, "signup_password", pw)
    _fill(at, "signup_confirm", confirm)
    _submit(at, "Create account")
    at.run()
    assert msg in at.error[0].value


def test_create_account_existing_email_error():
    sb = FakeSupabase()
    sb.auth.known_emails.add("dup@b.com")
    at = _app(sb).run()
    _fill(at, "signup_email", "dup@b.com")
    _fill(at, "signup_password", "secret1")
    _fill(at, "signup_confirm", "secret1")
    _submit(at, "Create account")
    at.run()
    assert "already exists" in at.error[0].value


def test_each_session_gets_its_own_client():
    from findings.core.config import load_settings

    a = AppTest.from_file(APP, default_timeout=15)
    b = AppTest.from_file(APP, default_timeout=15)
    for at in (a, b):
        at.secrets.update(SECRETS)
        at.run()
    assert a.session_state["sb"] is not b.session_state["sb"]
    assert load_settings(SECRETS)
