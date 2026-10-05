"""Per-browser-session Supabase client and signed-in user accessors."""

from __future__ import annotations

import streamlit as st
from supabase import create_client

from findings.core.config import Settings


def get_client(settings: Settings):
    """Return this browser session's own client (never cached across sessions)."""
    if "sb" not in st.session_state:
        st.session_state["sb"] = create_client(
            settings.supabase_url, settings.supabase_publishable_key
        )
    return st.session_state["sb"]


def current_user() -> dict | None:
    return st.session_state.get("user")


def set_signed_in(user_id: str, email: str) -> None:
    st.session_state["user"] = {"id": user_id, "email": email}


def sign_out(sb) -> None:
    try:
        sb.auth.sign_out()
    except Exception:
        pass
    st.session_state.pop("user", None)
