"""Researcher card rendering and badge components for Discover grid.

Follows strict markdown safety: user-written text (full name, interests) is rendered
only with st.text; markdown badges are constructed exclusively from whitelisted enums.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import streamlit as st

from findings.core.constants import CAREER_STAGES

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

    return " ".join(badges)


def render_card(
    profile: dict[str, Any],
    *,
    on_skip: Callable[[str], None] | None = None,
    sb: Any = None,
    user_id: str | None = None,
    states: dict[str, dict[str, Any]] | None = None,
) -> None:
    """Render an individual researcher card inside a bordered container."""
    with st.container(border=True, key=f"fxcard-disc-{profile.get('id', 'x')}"):
        st.html(card_header_html(profile))

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

        if sb and user_id and "id" in profile:
            from ui.connect_button import connect_button

            connect_button(
                sb,
                user_id=user_id,
                profile_id=str(profile["id"]),
                key=f"card_{profile['id']}",
                name=profile.get("full_name") or "",
                is_synthetic=bool(profile.get("is_synthetic")),
                states=states,
            )


# ---------------------------------------------------------------------------
# Designed card headers (static HTML, every dynamic string escaped)
# ---------------------------------------------------------------------------

METHOD_TONE = {"qualitative": "cyan", "quantitative": "green", "mixed": "violet"}


def _methods_pill(profile: dict | None) -> str:
    from ui.components import pill_html

    m = (profile or {}).get("methods_effective")
    if m in METHOD_TITLES:
        return pill_html(METHOD_TITLES[m], METHOD_TONE[m])
    return pill_html("Methods not set", "gray")


def mentoring_pills(profile: dict | None) -> str:
    from ui.components import pill_html

    out = ""
    if (profile or {}).get("seeking_mentor"):
        out += pill_html("Seeking a mentor", "cyan")
    if (profile or {}).get("open_to_mentoring"):
        out += pill_html("Open to mentoring", "pink")
    return out


def match_header_html(item: dict, rank: int) -> str:
    """Header for a My Matches card: avatar, name, stage, pills and score ring."""
    from ui.components import avatar_html, chips_html, esc, pill_html, ring_html

    name = item.get("full_name") or "Unnamed researcher"
    strength = item.get("strength") or "Possible match"
    tone = {"Strong match": "green", "Good match": "cyan"}.get(strength, "amber")
    stage = item.get("career_stage") or ""
    ai = pill_html("AI explained", "violet", "✨") if item.get("why_source") == "ai" else ""
    score = item.get("score")
    if score is None:
        score = round(float(item.get("similarity") or 0) * 100)
    return (
        '<div class="fx-row">'
        + avatar_html(name, 54)
        + '<div class="fx-col" style="flex:1">'
        + f'<div class="fx-title">#{rank} · {esc(name)}</div>'
        + f'<div class="fx-sub">{esc(stage)}</div>'
        + f'<div class="fx-pills" style="margin-top:.35rem">{pill_html(strength, tone)}'
        + f"{_methods_pill(item)}{ai}</div></div>"
        + ring_html(score, strength)
        + "</div>"
        + chips_html(item.get("interests"), limit=5)
    )


def card_header_html(profile: dict) -> str:
    """Header for a Discover card: avatar, name, stage and pills."""
    from ui.components import avatar_html, chips_html, esc, pill_html

    name = profile.get("full_name") or "Unnamed researcher"
    stage = profile.get("career_stage")
    stage_pill = pill_html(stage, "gray") if stage in CAREER_STAGES else ""
    return (
        '<div class="fx-row">'
        + avatar_html(name, 52)
        + '<div class="fx-col" style="flex:1">'
        + f'<div class="fx-title">{esc(name)}</div>'
        + f'<div class="fx-pills" style="margin-top:.3rem">{stage_pill}{_methods_pill(profile)}</div>'
        + "</div></div>"
        + f'<div class="fx-pills" style="margin-top:.5rem">{mentoring_pills(profile)}</div>'
        + chips_html(top_interests(profile, 4), limit=4)
    )
