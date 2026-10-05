"""Connections view: Received, Sent, and Connected collaboration requests."""

from __future__ import annotations

from typing import Any

import streamlit as st

from findings.core.session import current_user
from findings.services import connection_service


def _handle_response(
    sb: Any,
    user_id: str,
    cid: str,
    accept: bool,
) -> None:
    try:
        connection_service.respond(sb, user_id, cid, accept=accept)
        if accept:
            st.session_state["conn_flash"] = ("success", "You're now connected.")
        else:
            st.session_state["conn_flash"] = ("info", "Request declined.")
    except connection_service.ConnectionFailure as err:
        st.session_state["conn_flash"] = ("error", str(err))
    except Exception:
        st.session_state["conn_flash"] = ("error", "Could not answer this request. Try again in a moment.")


def render_connections_page() -> None:
    """Render Connections tabs for incoming, sent, and unlocked connections."""
    st.title("Connections")

    sb = st.session_state.get("sb")
    user = current_user()
    user_id = user.get("id") if user else None

    if not sb or not user_id:
        st.info("Please sign in to view your connections.")
        return

    flash = st.session_state.pop("conn_flash", None)
    if flash:
        lvl, msg = flash
        if lvl == "success":
            st.success(msg)
        elif lvl == "error":
            st.error(msg)
        else:
            st.info(msg)

    try:
        data = connection_service.list_connections(sb, user_id)
    except Exception:
        st.warning("Could not load your connections. Try again in a moment.")
        st.stop()

    received = data.get("received", [])
    sent = data.get("sent", [])
    connected = data.get("accepted", [])

    tab_rec, tab_sent, tab_conn = st.tabs(
        [
            f"Received ({len(received)})",
            f"Sent ({len(sent)})",
            f"Connected ({len(connected)})",
        ]
    )

    with tab_rec:
        if not received:
            st.caption("No incoming connection requests.")
        else:
            for item in received:
                cid = str(item.get("connection_id") or "")
                other_name = item.get("other_name") or "Unnamed researcher"
                other_stage = item.get("other_stage") or ""
                note = item.get("note")

                with st.container(border=True):
                    col_info, col_act = st.columns([3, 1])
                    with col_info:
                        st.subheader(other_name)
                        if other_stage:
                            st.caption(other_stage)
                        if note:
                            st.text(note)
                    with col_act:
                        st.button(
                            "Accept",
                            key=f"accept_{cid}",
                            on_click=_handle_response,
                            args=(sb, user_id, cid, True),
                        )
                        st.button(
                            "Decline",
                            key=f"decline_{cid}",
                            on_click=_handle_response,
                            args=(sb, user_id, cid, False),
                        )

    with tab_sent:
        if not sent:
            st.caption("No sent connection requests.")
        else:
            for item in sent:
                other_name = item.get("other_name") or "Unnamed researcher"
                other_stage = item.get("other_stage") or ""
                note = item.get("note")
                status_raw = item.get("status")
                status_label = "Pending" if status_raw == "pending" else "Not accepted"

                with st.container(border=True):
                    st.subheader(other_name)
                    st.caption(f"{other_stage} · {status_label}")
                    if note:
                        st.text(note)

    with tab_conn:
        if not connected:
            st.caption("No accepted connections yet. Connect with researchers on Discover or My Matches!")
        else:
            for item in connected:
                other_name = item.get("other_name") or "Unnamed researcher"
                other_stage = item.get("other_stage") or ""
                other_email = item.get("other_email") or ""
                is_synth = bool(item.get("other_is_synthetic"))

                with st.container(border=True):
                    st.subheader(other_name)
                    cap_text = f"{other_stage}"
                    if is_synth:
                        cap_text += " · Synthetic · auto-accepted"
                    st.caption(cap_text)

                    st.markdown("**Contact email:**")
                    if other_email:
                        st.code(other_email, language="")
                    else:
                        st.caption("Email unavailable")


render_connections_page()
