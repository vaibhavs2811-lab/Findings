import pytest
from supabase import AuthApiError

from findings.core.config import ConfigError, load_settings
from findings.services import auth_service
from findings.services.auth_service import AuthFailure
from tests.fakes import FakeSupabase

URL = "https://abc.supabase.co"


def test_settings_reject_secret_key():
    with pytest.raises(ConfigError):
        load_settings({"SUPABASE_URL": URL, "SUPABASE_PUBLISHABLE_KEY": "sb_secret_abc"})


def test_settings_reject_legacy_jwt_key():
    with pytest.raises(ConfigError):
        load_settings({"SUPABASE_URL": URL, "SUPABASE_PUBLISHABLE_KEY": "eyJhbGciOi"})


def test_settings_accept_publishable_key():
    s = load_settings({"SUPABASE_URL": URL, "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_x"})
    assert s.supabase_url == URL


def test_settings_reject_http_url():
    with pytest.raises(ConfigError):
        load_settings(
            {"SUPABASE_URL": "http://evil.example", "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_x"}
        )


def test_sign_in_success_normalises_email():
    sb = FakeSupabase()
    uid, email = auth_service.sign_in(sb, " A@B.com ", "correct-horse")
    assert (uid, email) == ("user-1", "a@b.com")


def test_sign_in_invalid_email_skips_supabase():
    sb = FakeSupabase()
    with pytest.raises(AuthFailure, match="Enter a valid email address."):
        auth_service.sign_in(sb, "not-an-email", "x")
    assert sb.auth.calls == []


def test_sign_in_wrong_password_friendly():
    sb = FakeSupabase()
    with pytest.raises(AuthFailure, match="Wrong email or password."):
        auth_service.sign_in(sb, "a@b.com", "nope")


def test_sign_in_rate_limit_friendly():
    sb = FakeSupabase()
    sb.auth.raise_on["sign_in_with_password"] = AuthApiError("slow down", 429, None)
    with pytest.raises(AuthFailure, match="Too many attempts"):
        auth_service.sign_in(sb, "a@b.com", "x")


def test_sign_in_unknown_error_hides_original_message():
    sb = FakeSupabase()
    sb.auth.raise_on["sign_in_with_password"] = RuntimeError("secret internals")
    with pytest.raises(AuthFailure) as exc:
        auth_service.sign_in(sb, "a@b.com", "x")
    assert "secret internals" not in str(exc.value)


def test_sign_up_success_returns_user():
    sb = FakeSupabase()
    uid, email = auth_service.sign_up(sb, "New@b.com", "secret1", "secret1")
    assert (uid, email) == ("user-1", "new@b.com")


def test_sign_up_short_password_skips_supabase():
    sb = FakeSupabase()
    with pytest.raises(AuthFailure, match="at least 6"):
        auth_service.sign_up(sb, "a@b.com", "12345", "12345")
    assert sb.auth.calls == []


def test_sign_up_mismatch_skips_supabase():
    sb = FakeSupabase()
    with pytest.raises(AuthFailure, match="do not match"):
        auth_service.sign_up(sb, "a@b.com", "secret1", "secret2")
    assert sb.auth.calls == []


def test_sign_up_existing_email_by_empty_identities():
    sb = FakeSupabase()
    sb.auth.known_emails.add("a@b.com")
    with pytest.raises(AuthFailure, match="already exists"):
        auth_service.sign_up(sb, "a@b.com", "secret1", "secret1")


def test_sign_up_existing_email_by_error_code():
    sb = FakeSupabase()
    sb.auth.raise_on["sign_up"] = AuthApiError("exists", 422, "user_already_exists")
    with pytest.raises(AuthFailure, match="already exists"):
        auth_service.sign_up(sb, "a@b.com", "secret1", "secret1")


def test_sign_up_confirmation_required_message():
    sb = FakeSupabase()
    sb.auth.sign_up_session = False
    with pytest.raises(AuthFailure, match="confirmation"):
        auth_service.sign_up(sb, "a@b.com", "secret1", "secret1")
