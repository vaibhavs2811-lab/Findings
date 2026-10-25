"""Messages: chat between people you are connected with."""

from __future__ import annotations

import streamlit as st

from findings.core.session import current_user
from findings.services import chat_service
from ui.chat import thread_html
from ui.components import avatar_html, empty_state, esc, pill_html

st.html('<span class="fx-eyebrow">Your network</span>')
st.title("Messages")
st.caption("Chat with people who accepted your request. Messages are plain text; times are UTC.")

sb = st.session_state.get("sb")
user = current_user()
user_id = user.get("id") if user else None
if not sb or not user_id:
    st.info("Please sign in to view your messages.")
    st.stop()

try:
    convs = chat_service.conversations(sb, user_id)
except Exception:
    st.warning("Could not load your conversations. Try again in a moment.")
    st.stop()

if not convs:
    empty_state(
        "message",
        "No conversations yet",
        "Once someone accepts your request, you can message each other here. "
        "Connect with researchers on Discover or My Matches to get started.",
    )
    st.page_link("views/discover.py", label="Find researchers", icon=":material/travel_explore:")
    st.stop()

by_id = {str(c["connection_id"]): c for c in convs}
wanted = st.query_params.get("c")
if wanted in by_id:
    st.session_state["chat_with"] = wanted
selected = st.session_state.get("chat_with")
if selected not in by_id:
    selected = next(iter(by_id))
    st.session_state["chat_with"] = selected


# Opening a conversation marks it read, so its "new" badge clears straight away.
chat_service.mark_read(sb, selected)
by_id[selected]["unread_count"] = 0


def _open(cid: str) -> None:
    st.session_state["chat_with"] = cid
    st.query_params["c"] = cid


left, right = st.columns([1, 2], gap="large")

with left:
    for conv in convs:
        cid = str(conv["connection_id"])
        name = conv.get("other_name") or "Unnamed researcher"
        unread = int(conv.get("unread_count") or 0)
        key = f"fxcard-chatsel-{cid}" if cid == selected else f"fxcard-chat-{cid}"
        with st.container(border=True, key=key):
            badge = pill_html(f"{unread} new", "cyan") if unread else ""
            st.html(
                '<div class="fx-row">'
                + avatar_html(name, 40)
                + '<div class="fx-col" style="flex:1">'
                + f'<div class="fx-title" style="font-size:1rem">{esc(name)}</div>'
                + f'<div class="fx-sub">{esc(chat_service.snippet(conv.get("last_body")) or "No messages yet")}</div>'
                + f"</div>{badge}</div>"
            )
            if cid != selected:
                st.button("Open", key=f"chat_open_{cid}", on_click=_open, args=(cid,))

current = by_id[selected]
other_name = current.get("other_name") or "Unnamed researcher"

with right:
    st.html(
        '<div class="fx-row" style="margin-bottom:.4rem">'
        + avatar_html(other_name, 44)
        + '<div class="fx-col"><div class="fx-title">'
        + esc(other_name)
        + '</div><div class="fx-sub">'
        + esc(current.get("other_stage") or "")
        + "</div></div></div>"
    )
    thread_box = st.container()
    text = st.chat_input(f"Message {other_name.split()[0]}", key="chat_input", max_chars=chat_service.MAX_LEN)
    if text:
        try:
            chat_service.send(sb, user_id, selected, text)
        except chat_service.ChatError as err:
            st.error(str(err))

    @st.fragment(run_every="4s")
    def _thread() -> None:
        chat_service.mark_read(sb, selected)
        try:
            msgs = chat_service.thread(sb, selected)
        except Exception:
            st.warning("Could not load this conversation. Try again in a moment.")
            return
        st.html(thread_html(msgs, user_id))

    with thread_box:
        _thread()
