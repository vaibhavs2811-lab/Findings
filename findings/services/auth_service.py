"""Streamlit-free email + password auth with user-safe error messages."""

from __future__ import annotations

import re

from supabase import AuthApiError, AuthError

MIN_PASSWORD_LEN = 6
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_GENERIC = "Something went wrong. Please try again."


class AuthFailure(Exception):
    """Carries a message that is safe to show to the user."""


def _normalise_email(email: str) -> str:
    email = (email or "").strip().lower()
    if len(email) > 254 or not _EMAIL_RE.match(email):
        raise AuthFailure("Enter a valid email address.")
    return email


def friendly_message(err: Exception) -> str:
    code = getattr(err, "code", None)
    status = getattr(err, "status", None)
    if code in ("invalid_credentials", "invalid_login_credentials"):
        return "Wrong email or password."
    if code == "email_not_confirmed":
        return "Please confirm your email first, then sign in."
    if code in ("user_already_exists", "email_exists"):
        return "An account with this email already exists. Use the Sign in tab."
    if code == "weak_password":
        return f"Password must be at least {MIN_PASSWORD_LEN} characters."
    if status == 429 or code in ("over_email_send_rate_limit", "over_request_rate_limit"):
        return "Too many attempts. Wait a minute and try again."
    return _GENERIC


def sign_in(sb, email: str, password: str) -> tuple[str, str]:
    email = _normalise_email(email)
    if not password:
        raise AuthFailure("Enter your password.")
    try:
        res = sb.auth.sign_in_with_password({"email": email, "password": password})
    except (AuthApiError, AuthError) as err:
        raise AuthFailure(friendly_message(err)) from None
    except Exception:
        raise AuthFailure(_GENERIC) from None
    if res is None or res.user is None:
        raise AuthFailure(_GENERIC)
    return res.user.id, res.user.email or email


def sign_up(sb, email: str, password: str, confirm: str) -> tuple[str, str]:
    """Create an account and return (user_id, email) when signed in straight away."""
    email = _normalise_email(email)
    if len(password or "") < MIN_PASSWORD_LEN:
        raise AuthFailure(f"Password must be at least {MIN_PASSWORD_LEN} characters.")
    if password != confirm:
        raise AuthFailure("Passwords do not match.")
    try:
        res = sb.auth.sign_up({"email": email, "password": password})
    except (AuthApiError, AuthError) as err:
        raise AuthFailure(friendly_message(err)) from None
    except Exception:
        raise AuthFailure(_GENERIC) from None
    user = getattr(res, "user", None)
    if user is None:
        raise AuthFailure(_GENERIC)
    # Supabase hides existing accounts by returning a user with no identities.
    if getattr(user, "identities", None) == []:
        raise AuthFailure("An account with this email already exists. Use the Sign in tab.")
    if getattr(res, "session", None) is None:
        raise AuthFailure(
            "Account created, but email confirmation is still required. "
            "Confirm via the email we sent, then sign in."
        )
    return user.id, user.email or email
