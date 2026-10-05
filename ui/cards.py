"""Researcher card rendering and badge components for Discover grid.

Follows strict markdown safety: user-written text (full name, interests) is rendered
only with st.text; markdown badges are constructed exclusively from whitelisted enums.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import streamlit as st

from findings.core.constants import CAREER_STAGES

SYNTHETIC_LABEL = "Synthetic profile"

METHOD_TITLES = {
    "qualitative": "Qualitative",
    "quantitative": "Quantitative",
    "mixed": "Mixed methods",
}


def top_interests(profile: dict | None, n: int = 3) -> list[str]:
    """Extract first n non-empty interests from profile."""
    if not profile:
        return []
    items = profile.get("interests") or []
    return [str(item).strip() for item in items if str(item).strip()][:n]


def mentoring_role_label(profile: dict | None) -> str | None:
    """Return friendly label for mentoring exchange status or None if neither."""
    if not profile:
        return None
    seeking = bool(profile.get("seeking_mentor"))
    open_to = bool(profile.get("open_to_mentoring"))
    if seeking and open_to:
        return "Seeking a mentor · Open to mentoring"
    if seeking:
        return "Seeking a mentor"
    if open_to:
        return "Open to mentoring"
    return None


def badge_markdown(profile: dict | None) -> str:
    """Construct a single markdown line containing whitelisted badge directives.

    Uses Streamlit's native :color-badge[...] syntax. Never interpolates unverified user strings.
    """
    if not profile:
        return ":gray-badge[Methods not set]"

    badges: list[str] = []

    # 1. Career stage badge
    stage = profile.get("career_stage")
    if stage in CAREER_STAGES:
        badges.append(f":gray-badge[{stage}]")

    # 2. Methods orientation badge
    methods = profile.get("methods_effective")
    if methods in METHOD_TITLES:
        badges.append(f":blue-badge[{METHOD_TITLES[methods]}]")
    else:
        badges.append(":gray-badge[Methods not set]")

    # 3. Synthetic profile badge
    if profile.get("is_synthetic") is True:
        badges.append(f":orange-badge[:material/smart_toy: {SYNTHETIC_LABEL}]")

    return " ".join(badges)


def synthetic_badge(profile: dict | None) -> None:
    """Render a standalone orange badge if profile is synthetic."""
    if profile and profile.get("is_synthetic") is True:
        st.badge(SYNTHETIC_LABEL, color="orange", icon=":material/smart_toy:")


def render_card(profile: dict[str, Any], *, on_skip: Callable[[str], None] | None = None) -> None:
    """Render an individual researcher card inside a bordered container."""
    with st.container(border=True):
        st.text(profile.get("full_name") or "Unnamed researcher")
        st.markdown(badge_markdown(profile))

        role = mentoring_role_label(profile)
        if role:
            st.caption(role)

        interests = top_interests(profile)
        if interests:
            st.text("Interests: " + " · ".join(interests))

        col1, col2 = st.columns([1, 1])
        with col1:
            st.page_link(
                "views/researcher.py",
                label="View profile",
                icon=":material/person:",
                query_params={"id": profile["id"]},
            )
        with col2:
            if on_skip is not None and "id" in profile:
                st.button(
                    "Skip",
                    key=f"skip_{profile['id']}",
                    on_click=on_skip,
                    args=(profile["id"],),
                )
