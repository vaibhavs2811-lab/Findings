"""Connections view: Received, Sent, and Connected collaboration requests."""

from __future__ import annotations

from typing import Any

import streamlit as st

from findings.core.session import current_user
from findings.services import connection_service
from ui.components import avatar_html, empty_state, pill_html
from ui.icons import icon_svg


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
    st.html('<span class="fx-eyebrow">Your network</span>')
    st.title("Connections")
    st.caption("Requests you received, requests you sent, and the people you are connected with.")

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

    def _person_header(name: str, stage: str, pill: str = "") -> None:
        av, info = st.columns([1, 6], vertical_alignment="center")
        with av:
            st.html(avatar_html(name, 48))
        with info:
            st.subheader(name)
            if stage or pill:
                st.html(
                    '<div class="fx-pills">'
                    + (pill_html(stage, "gray") if stage else "")
                    + pill
                    + "</div>"
                )

    with tab_rec:
        if not received:
            empty_state("inbox", "No incoming requests", "When someone wants to connect, their request shows up here.")
        else:
            for item in received:
                cid = str(item.get("connection_id") or "")
                other_name = item.get("other_name") or "Unnamed researcher"
                other_stage = item.get("other_stage") or ""
                note = item.get("note")

                with st.container(border=True, key=f"fxcard-conn-rec-{cid}"):
                    col_info, col_act = st.columns([3, 1])
                    with col_info:
                        _person_header(other_name, other_stage, pill_html("Wants to connect", "violet"))
                        if note:
                            st.text(note)
                    with col_act:
                        st.button(
                            "Accept",
                            key=f"accept_{cid}",
                            type="primary",
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
            empty_state("send", "No sent requests", "Requests you send from Discover or My Matches appear here.")
        else:
            for item in sent:
                other_name = item.get("other_name") or "Unnamed researcher"
                other_stage = item.get("other_stage") or ""
                note = item.get("note")
                status_raw = item.get("status")
                status_label = "Pending" if status_raw == "pending" else "Not accepted"
                tone = "amber" if status_raw == "pending" else "gray"

                with st.container(border=True, key=f"fxcard-conn-sent-{item.get('connection_id')}"):
                    _person_header(other_name, other_stage, pill_html(status_label, tone))
                    st.caption(f"{other_stage} · {status_label}")
                    if note:
                        st.text(note)

    with tab_conn:
        if not connected:
            empty_state(
                "handshake",
                "No connections yet",
                "Connect with researchers on Discover or My Matches. Their email appears here once they accept.",
            )
        else:
            for item in connected:
                other_name = item.get("other_name") or "Unnamed researcher"
                other_stage = item.get("other_stage") or ""
                other_email = item.get("other_email") or ""

                with st.container(border=True, key=f"fxcard-conn-ok-{item.get('connection_id')}"):
                    _person_header(other_name, other_stage, pill_html("Connected", "green"))
                    if other_email:
                        st.html(f'<div class="fx-email">{icon_svg("mail", 18)} Contact email unlocked</div>')
                        st.code(other_email, language="")
                    else:
                        st.html('<div class="fx-email locked">Email unavailable</div>')


render_connections_page()
