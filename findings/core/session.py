"""Per-browser-session Supabase client and signed-in user accessors."""

from __future__ import annotations

import logging

import streamlit as st

from findings.core import cookies
from findings.core.config import Settings
from supabase import AuthError, ClientOptions, create_client

log = logging.getLogger(__name__)


def get_client(settings: Settings):
    """Return this browser session's own client (never cached across sessions)."""
    if "sb" not in st.session_state:
        st.session_state["sb"] = create_client(
            settings.supabase_url,
            settings.supabase_publishable_key,
            options=ClientOptions(auto_refresh_token=False),
        )
    return st.session_state["sb"]


def current_user() -> dict | None:
    return st.session_state.get("user")


def set_signed_in(user_id: str, email: str) -> None:
    st.session_state["user"] = {"id": user_id, "email": email}


def restore_once() -> None:
    """Try the refresh-token cookie once per browser session."""
    if st.session_state.get("restore_attempted"):
        return
    st.session_state["restore_attempted"] = True
    if current_user():
        return
    token = cookies.read_refresh_token()
    if not token:
        return
    try:
        res = st.session_state["sb"].auth.refresh_session(token)
        set_signed_in(res.user.id, res.user.email)
    except AuthError:
        log.warning("cookie restore failed; showing sign in")
    except Exception:
        log.warning("cookie restore failed unexpectedly; showing sign in")


def _clear_signed_in() -> None:
    st.session_state.pop("user", None)


def refresh_if_needed() -> None:
    """get_session refreshes an expiring session itself; drop sign-in if that fails."""
    if not current_user():
        return
    try:
        sess = st.session_state["sb"].auth.get_session()
    except AuthError:
        sess = None
    if sess is None:
        _clear_signed_in()


def cookie_value() -> str | None:
    """Refresh token of the live session (what the cookie should hold), or None."""
    if not current_user():
        return None
    try:
        sess = st.session_state["sb"].auth.get_session()
    except AuthError:
        return None
    return getattr(sess, "refresh_token", None) if sess else None


def sign_out() -> None:
    """Revoke this session only (local scope), then drop all per-session auth state."""
    sb = st.session_state.get("sb")
    if sb is not None:
        try:
            sb.auth.sign_out({"scope": "local"})
        except AuthError:
            log.warning("sign-out request failed; cleared local state anyway")
    for key in [k for k in st.session_state if k in ("user", "sb") or k.startswith("otp_")]:
        del st.session_state[key]
