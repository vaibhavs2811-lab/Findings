"""My Matches view: AI and pgvector peer collaborator matches."""

from __future__ import annotations

import time
from typing import Any

import streamlit as st

from findings.core.session import current_user
from findings.services import connection_service, matching
from ui.cards import METHOD_TITLES
from ui.connect_button import connect_button


def match_badge_markdown(item: dict[str, Any]) -> str:
    """Format markdown badges for match strength, methods, and synthetic status."""
    badges: list[str] = []

    # 1. Match strength badge
    strength = item.get("strength") or "Possible match"
    if strength == "Strong match":
        badges.append(":green-badge[:material/auto_awesome: Strong match]")
    elif strength == "Good match":
        badges.append(":blue-badge[Good match]")
    else:
        badges.append(":gray-badge[Possible match]")

    # 2. Methods badge
    methods = item.get("methods_effective")
    if methods in METHOD_TITLES:
        badges.append(f":violet-badge[{METHOD_TITLES[methods]}]")

    # 3. Synthetic profile badge
    if item.get("is_synthetic") is True:
        badges.append(":orange-badge[:material/smart_toy: Synthetic]")

    return " ".join(badges)


def _render_match(
    item: dict[str, Any],
    rank: int,
    sb: Any = None,
    user_id: str | None = None,
    states: dict[str, dict[str, Any]] | None = None,
) -> None:
    """Render single match card with View profile and Connect actions."""
    with st.container(border=True):
        name = item.get("full_name") or "Unnamed researcher"
        st.text(f"#{rank}  {name}")
        st.markdown(match_badge_markdown(item))

        stage = item.get("career_stage")
        if stage:
            st.text(f"Stage: {stage}")

        interests = item.get("interests") or []
        clean_ints = [str(x).strip() for x in interests if str(x).strip()]
        if clean_ints:
            st.text(" · ".join(clean_ints))

        why = item.get("why")
        if why:
            st.text(why)

        col1, col2 = st.columns([1, 1])
        with col1:
            st.page_link(
                "views/researcher.py",
                label="View profile",
                icon=":material/person:",
                query_params={"id": item["id"]},
            )
        with col2:
            if sb and user_id and "id" in item:
                connect_button(
                    sb,
                    user_id=user_id,
                    profile_id=str(item["id"]),
                    key=f"match_{item['id']}",
                    name=item.get("full_name") or "",
                    is_synthetic=bool(item.get("is_synthetic")),
                    states=states,
                )


def _on_refresh_click() -> None:
    now = time.time()
    last = st.session_state.get("matches_last_refreshed", 0.0)
    if now - last < 60:
        wait_secs = int(60 - (now - last))
        st.toast(f"Please wait {wait_secs}s before refreshing matches.", icon="⏳")
    else:
        st.session_state["matches_last_refreshed"] = now
        st.session_state["matches_force_refresh"] = True
        st.rerun()


def render_matches_page() -> None:
    """Render My Matches page with shortlisted peer collaborators."""
    st.title("My Matches")

    sb = st.session_state.get("sb")
    user = current_user()
    user_id = user.get("id") if user else None

    if not sb or not user_id:
        st.info("Please sign in to view your matches.")
        return

    force_refresh = st.session_state.pop("matches_force_refresh", False)

    with st.spinner("Finding peer collaborators..."):
        result = matching.get_matches(sb, user_id, mode="peer", refresh=force_refresh)

    if result.notice:
        st.info(result.notice)
        if result.notice == matching.INCOMPLETE_NOTICE:
            st.page_link("views/profile.py", label="Complete your profile", icon=":material/edit:")
        if not result.items:
            return

    col_cap, col_ref = st.columns([4, 1])
    with col_cap:
        caption_text = "AI-ranked" if result.source == "ai" else "Ranked by profile similarity"
        if result.from_cache:
            caption_text += " (cached)"
        st.caption(caption_text)
    with col_ref:
        st.button(
            "Refresh matches",
            key="btn_refresh_matches",
            on_click=_on_refresh_click,
            help="Recompute matches and bypass cache (60s cooldown)",
        )

    conn_states: dict[str, Any] = {}
    try:
        conn_states = connection_service.connection_states(sb, user_id)
    except Exception:
        conn_states = {}

    # Filter out anyone who currently has a connection with user (D-12)
    visible_items = [
        item for item in result.items
        if str(item.get("id")) not in conn_states
    ]

    if not visible_items:
        st.info(matching.NO_MATCHES_NOTICE)
        return

    for idx, item in enumerate(visible_items, start=1):
        _render_match(item, idx, sb=sb, user_id=user_id, states=conn_states)


render_matches_page()
