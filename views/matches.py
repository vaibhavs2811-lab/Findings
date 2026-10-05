"""My Matches view: AI and pgvector peer collaborator and mentorship matches."""

from __future__ import annotations

import time
from typing import Any

import streamlit as st

from findings.core.session import current_user
from findings.repos import profiles
from findings.services import connection_service, matching
from findings.services.mentorship import (
    available_modes,
    direction_label,
    own_give_need_empty,
)
from findings.services.mentorship_fit import exchange_labels
from ui.cards import METHOD_TITLES, match_header_html
from ui.components import esc, exchange_html
from ui.connect_button import connect_button


def match_badge_markdown(item: dict[str, Any]) -> str:
    """Format markdown badges for match strength, and methods orientation."""
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

    return " ".join(badges)


def _render_match(
    item: dict[str, Any],
    rank: int,
    sb: Any = None,
    user_id: str | None = None,
    states: dict[str, dict[str, Any]] | None = None,
    mode: str = "peer",
) -> None:
    """Render single match card with View profile and Connect actions."""
    with st.container(border=True, key=f"fxcard-{mode}-{item.get('id')}"):
        st.html(match_header_html(item, rank))

        why = item.get("why")
        if why:
            st.html(f'<div class="fx-why">{esc(why)}</div>')

        if mode in ("mentor", "mentee") and (item.get("they_give_you") or item.get("you_give_them")):
            get_label, give_label = exchange_labels(mode)
            st.html(
                exchange_html(
                    get_label,
                    item.get("they_give_you") or "",
                    give_label,
                    item.get("you_give_them") or "",
                )
            )

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
                    key=f"{mode}_match_{item['id']}",
                    name=item.get("full_name") or "",
                    is_synthetic=bool(item.get("is_synthetic")),
                    states=states,
                )


def _on_refresh_click(mode: str = "peer") -> None:
    now = time.time()
    key = f"matches_last_refreshed_{mode}"
    last = st.session_state.get(key, 0.0)
    if now - last < 60:
        wait_secs = int(60 - (now - last))
        st.toast(f"Please wait {wait_secs}s before refreshing matches.", icon=":material/schedule:")
    else:
        st.session_state[key] = now
        st.session_state["matches_force_refresh"] = True
        st.rerun()


def _render_results(
    sb: Any,
    user_id: str,
    mode: str,
    force_refresh: bool,
) -> None:
    """Fetch and render match results for a given mode."""
    if mode == "peer":
        spinner_text = "Finding peer collaborators..."
    elif mode == "mentor":
        spinner_text = "Finding mentors..."
    else:
        spinner_text = "Finding mentees..."

    with st.spinner(spinner_text):
        result = matching.get_matches(sb, user_id, mode=mode, refresh=force_refresh)

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
            key=f"btn_refresh_{mode}",
            on_click=_on_refresh_click,
            args=(mode,),
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
        if mode == "mentor":
            st.info("Nobody at a later career stage is open to mentoring yet.")
        elif mode == "mentee":
            st.info("Nobody at an earlier career stage is looking for a mentor yet.")
        else:
            st.info(matching.NO_MATCHES_NOTICE)
        return

    for idx, item in enumerate(visible_items, start=1):
        _render_match(item, idx, sb=sb, user_id=user_id, states=conn_states, mode=mode)


def render_matches_page() -> None:
    """Render My Matches page with peer collaborator and mentorship matches."""
    st.title("My Matches")

    sb = st.session_state.get("sb")
    user = current_user()
    user_id = user.get("id") if user else None

    if not sb or not user_id:
        st.info("Please sign in to view your matches.")
        return

    force_refresh = st.session_state.pop("matches_force_refresh", False)

    # Load viewer profile for toggle checks
    me = profiles.get_own_profile(sb, user_id)

    # Match type: Peers vs Mentorship
    match_view = st.segmented_control(
        "Match type",
        options=["Peers", "Mentorship"],
        default="Peers",
        key="match_view",
    )
    if not match_view:
        match_view = "Peers"

    if match_view == "Peers":
        _render_results(sb, user_id, "peer", force_refresh)
    else:
        # Mentorship
        modes = available_modes(me) if me else []
        if not modes:
            st.info(
                "Mentorship matches need 'Seeking a mentor' or 'Open to mentoring' turned on."
            )
            st.page_link("views/profile.py", label="Go to My profile", icon=":material/edit:")
            return

        if len(modes) == 1:
            active_mode = modes[0]
        else:
            labels = [direction_label(m) for m in modes]
            selected = st.segmented_control(
                "Direction",
                options=labels,
                default=labels[0],
                key="mentor_direction",
            )
            if not selected:
                selected = labels[0]
            active_mode = modes[labels.index(selected)]

        if active_mode == "mentor":
            st.subheader("Mentors for you")
            st.caption("People at a later career stage who are open to mentoring.")
        else:
            st.subheader("Mentees for you")
            st.caption("People at an earlier career stage who are looking for a mentor.")

        # D-12: thin-profile hint
        if me and own_give_need_empty(me, active_mode):
            if active_mode == "mentor":
                st.info("Add what you want to learn and what you can contribute on My profile to get sharper mentor matches.")
            else:
                st.info("Add what you offer and what you need on My profile to get sharper mentee matches.")
            st.page_link("views/profile.py", label="Go to My profile", icon=":material/edit:")

        _render_results(sb, user_id, active_mode, force_refresh)


render_matches_page()
