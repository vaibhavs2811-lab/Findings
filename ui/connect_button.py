"""Reusable Connect button and note dialog component for Findings.

Used on researcher profile pages, Discover cards, and My Matches entries.
No Streamlit caching decorators (per D-06; connection state is per-user).
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from findings.services import connection_service


def show_connect_flash() -> None:
    """Display pending connect action toast notification if present."""
    flash = st.session_state.pop("connect_flash", None)
    if flash:
        st.toast(flash, icon="✉️")


def _close(*args: Any, **kwargs: Any) -> None:
    """Clear open dialog identifier from session state."""
    st.session_state.pop("connect_dialog", None)


def _open(key: str) -> None:
    """Open connect dialog for specific component key."""
    st.session_state["connect_dialog"] = key


@st.dialog("Send a connection request", on_dismiss=_close)
def _request_dialog(
    sb: Any,
    user_id: str,
    profile_id: str,
    key: str,
    name: str = "",
    is_synthetic: bool = False,
) -> None:
    """Render modal dialog with note input and submit button."""
    st.text(f"To: {name or 'this researcher'}")

    note_val = st.text_area(
        "Note (optional)",
        key=f"connect_note_{key}",
        max_chars=500,
        placeholder="Say why you'd like to collaborate",
    )

    if st.button("Send request", key=f"connect_send_{key}"):
        try:
            res = connection_service.send_request(
                sb,
                user_id=user_id,
                recipient_id=profile_id,
                note=note_val,
            )
            st.session_state.pop("connect_dialog", None)
            st.session_state.pop(f"connect_note_{key}", None)
            if res.get("status") == "accepted" or is_synthetic:
                st.session_state["connect_flash"] = "Connected! Email unlocked on Connections page."
            else:
                st.session_state["connect_flash"] = f"Request sent to {name or 'this researcher'}."
            st.rerun()
        except connection_service.ConnectionFailure as err:
            st.error(str(err))


def connect_button(
    sb: Any,
    user_id: str,
    profile_id: str,
    key: str,
    *,
    name: str = "",
    is_synthetic: bool = False,
    states: dict[str, dict[str, Any]] | None = None,
) -> None:
    """Render connect button, active status chip, or modal dialog."""
    show_connect_flash()

    if not user_id or str(profile_id) == str(user_id):
        return

    curr_states = states
    if curr_states is None:
        try:
            curr_states = connection_service.connection_states(sb, user_id)
        except Exception:
            st.caption("Connection status unavailable right now.")
            return

    target_key = str(profile_id)
    if target_key in curr_states:
        info = curr_states[target_key]
        state = info.get("state")
        if state == "sent":
            st.caption("Request sent · waiting for their answer")
        elif state == "connected":
            st.caption("Connected · email on your Connections page")
        elif state == "declined":
            st.caption("Not available")
        elif state == "received":
            cid = info.get("connection_id")
            if cid:
                if st.button("Accept their request", key=f"accept_req_{key}", type="primary"):
                    try:
                        connection_service.respond(sb, user_id, cid, accept=True)
                        st.session_state["connect_flash"] = (
                            f"Connected with {name or 'this researcher'}! Email unlocked on Connections page."
                        )
                        st.rerun()
                    except connection_service.ConnectionFailure as err:
                        st.error(str(err))
            else:
                st.caption("They sent you a request · answer it on your Connections page")
        return

    st.button(
        "Connect",
        key=f"connect_{key}",
        on_click=_open,
        args=(key,),
        type="primary",
        icon=":material/person_add:",
    )

    if st.session_state.get("connect_dialog") == key:
        _request_dialog(sb, user_id, profile_id, key, name, is_synthetic)
