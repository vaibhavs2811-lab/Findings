"""Guide chatbot panel (lives in a popover in the top bar)."""

from __future__ import annotations

import streamlit as st

from findings.ai import guide
from findings.repos.profiles import get_own_profile
from findings.services import chat_service, connection_service
from ui.components import completeness

SUGGESTIONS = (
    "How do matches work?",
    "How do I message someone?",
    "What is the difference between qualitative and quantitative?",
)


def _state(sb, user_id: str) -> dict:
    """Non-personal facts only: counts and flags. Never names or emails."""
    state: dict = {}
    try:
        profile = get_own_profile(sb, user_id)
        _pct, missing = completeness(profile)
        state.update(
            profile_complete=bool(profile and profile.get("is_complete")),
            missing=missing,
            seeking=bool((profile or {}).get("seeking_mentor")),
            open=bool((profile or {}).get("open_to_mentoring")),
        )
        state["pending_requests"] = len(connection_service.list_connections(sb, user_id)["received"])
        state["unread"] = chat_service.unread_total(sb, user_id)
    except Exception:
        pass
    return state


def _ask(question: str) -> None:
    ss = st.session_state
    history = ss.setdefault("guide_history", [])
    q = guide.clean_question(question)
    if not q:
        return
    if ss.get("guide_count", 0) >= guide.MAX_QUESTIONS_PER_SESSION:
        history.append({"role": "assistant", "text": "You have reached the guide's limit for this session. "
                        "Refresh the page to start again.", "pages": []})
        return
    ss["guide_count"] = ss.get("guide_count", 0) + 1
    user = ss.get("user") or {}
    reply = guide.ask(q, history, _state(ss["sb"], user.get("id", "")))
    history.append({"role": "user", "text": q})
    history.append({"role": "assistant", "text": reply.text, "pages": reply.pages})
    del history[:-12]


def _on_submit() -> None:
    _ask(st.session_state.get("guide_input", ""))
    st.session_state["guide_input"] = ""


def _clear() -> None:
    st.session_state["guide_history"] = []


def render_guide() -> None:
    """Chat panel: suggestions, history with page links, and an input form."""
    history = st.session_state.get("guide_history", [])
    st.html('<div class="fx-title">Guide</div>')
    st.caption("Ask how anything on Findings works.")

    if not history:
        for i, q in enumerate(SUGGESTIONS):
            st.button(q, key=f"guide_s_{i}", on_click=_ask, args=(q,), use_container_width=True)

    for turn in history:
        is_user = turn["role"] == "user"
        with st.chat_message("user" if is_user else "assistant", avatar=":material/person:" if is_user else ":material/auto_awesome:"):
            st.text(turn["text"])
            for key in turn.get("pages") or []:
                path, label = guide.PAGES[key]
                st.page_link(path, label=label, icon=":material/arrow_forward:")

    with st.form("guide_form", clear_on_submit=False, border=False):
        st.text_input(
            "Ask the guide",
            key="guide_input",
            max_chars=guide.MAX_QUESTION,
            placeholder="e.g. How do I get matched?",
            label_visibility="collapsed",
        )
        st.form_submit_button("Ask", type="primary", on_click=_on_submit, use_container_width=True)
    if history:
        st.button("Clear chat", key="guide_clear", on_click=_clear, type="tertiary")
