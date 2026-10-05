"""My Matches view: AI and pgvector peer collaborator matches."""

from __future__ import annotations

from typing import Any

import streamlit as st

from findings.core.session import current_user
from findings.services import matching
from ui.cards import METHOD_TITLES


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


def _render_match(item: dict[str, Any], rank: int) -> None:
    """Render single match card. Single hook for Phase 5 Connect button."""
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

        st.page_link(
            "views/researcher.py",
            label="View profile",
            icon=":material/person:",
            query_params={"id": item["id"]},
        )


def render_matches_page() -> None:
    """Render My Matches page with shortlisted peer collaborators."""
    st.title("My Matches")

    sb = st.session_state.get("sb")
    user = current_user()
    user_id = user.get("id") if user else None

    if not sb or not user_id:
        st.info("Please sign in to view your matches.")
        return

    with st.spinner("Finding peer collaborators..."):
        result = matching.get_matches(sb, user_id, mode="peer")

    if result.notice:
        st.info(result.notice)
        if result.notice == matching.INCOMPLETE_NOTICE:
            st.page_link("views/profile.py", label="Complete your profile", icon=":material/edit:")
        return

    caption_text = "AI-ranked" if result.source == "ai" else "Ranked by profile similarity"
    st.caption(caption_text)

    if not result.items:
        st.info(matching.NO_MATCHES_NOTICE)
        return

    for idx, item in enumerate(result.items, start=1):
        _render_match(item, idx)


render_matches_page()
