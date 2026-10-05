"""Reusable read-only profile rendering component.

Never executes markdown on untrusted user strings; uses st.text for safe rendering.
Email is displayed only if show_email=True and an email key is present.
"""

from __future__ import annotations

import re

import streamlit as st


def _clean_header_name(name: str | None) -> str:
    """Strip markdown control characters from name heading to avoid injection."""
    if not name:
        return "Unnamed researcher"
    cleaned = re.sub(r"[\\`*_\[\](){}\#<>|\$~:]", "", str(name)).strip()
    return cleaned if cleaned else "Unnamed researcher"


def methods_badge(profile: dict | None) -> None:
    """Render qualitative/quantitative/mixed orientation badge with source indicator and rationale."""
    if not profile:
        st.badge("Not classified yet", color="gray")
        return

    effective = (
        profile.get("methods_effective")
        or profile.get("methods_override")
        or profile.get("methods_suggested")
    )
    if not effective or effective not in ("qualitative", "quantitative", "mixed"):
        st.badge("Not classified yet", color="gray")
        return

    is_override = bool(profile.get("methods_override"))
    source_tag = "set by you" if is_override else "AI-suggested"
    badge_label = f"{effective.title()} · {source_tag}"

    if effective == "quantitative":
        st.badge(badge_label, icon=":material/analytics:", color="green")
    elif effective == "qualitative":
        st.badge(badge_label, icon=":material/psychology:", color="blue")
    else:  # mixed
        st.badge(badge_label, icon=":material/merge:", color="violet")

    if not is_override and profile.get("methods_reason"):
        st.text(profile["methods_reason"])


def _chips(label: str, items: list[str] | None, limit: int = 12) -> None:
    from ui.components import chips_html

    html = chips_html(items, limit=limit)
    if html:
        st.caption(label)
        st.html(html)


def render_profile(profile: dict | None, *, show_email: bool = False) -> None:
    """Render a read-only profile as a designed page.

    The name and all long free text use native elements (safe, plain text); short list values
    are shown as escaped chips. Email appears only if show_email=True and an email key exists.
    """
    from ui.cards import mentoring_pills
    from ui.components import avatar_html

    if not profile:
        st.caption("No profile information available.")
        return

    header_name = _clean_header_name(profile.get("full_name"))
    stage = profile.get("career_stage")
    institution = profile.get("institution")

    with st.container(key="fxhero-profile"):
        av, info = st.columns([1, 5], vertical_alignment="center")
        with av:
            st.html(avatar_html(header_name, 92))
        with info:
            st.subheader(header_name)
            detail_parts = [p for p in [stage, institution] if p]
            if detail_parts:
                st.caption(" · ".join(detail_parts))
            methods_badge(profile)
            roles = mentoring_pills(profile)
            if roles:
                st.html(f'<div class="fx-pills" style="margin-top:.4rem">{roles}</div>')

    left, right = st.columns([3, 2], gap="medium")

    with left, st.container(key="fxpanel-p-about"):
        st.html('<div class="fx-tile-title">About</div>')
        bio = profile.get("bio")
        if bio:
            st.caption("Bio")
            st.text(bio)
        looking_for = profile.get("looking_for")
        if looking_for:
            st.caption("What I'm looking for")
            st.text(looking_for)
        experience = profile.get("experience")
        if experience:
            st.caption("Research experience")
            st.text(experience)
        education = profile.get("education")
        if education:
            st.caption("Education")
            st.text(education)
        if not any([bio, looking_for, experience, education]):
            st.caption("Nothing here yet.")

    with right, st.container(key="fxpanel-p-research"):
        st.html('<div class="fx-tile-title">Research</div>')
        _chips("Research interests", profile.get("interests"))
        _chips("Skills & methods", profile.get("skills"))
        if show_email and profile.get("email"):
            st.caption("Contact email")
            st.text(profile["email"])

    give_need = [
        ("What I can offer", profile.get("offers")),
        ("What I need help with", profile.get("needs")),
        ("Skills I can contribute", profile.get("contributable_skills")),
        ("What I want to learn", profile.get("want_to_learn")),
    ]
    roles_present = bool(profile.get("seeking_mentor") or profile.get("open_to_mentoring"))
    if roles_present or any(items for _, items in give_need):
        with st.container(key="fxpanel-p-exchange"):
            st.html('<div class="fx-tile-title">Mentoring exchange</div>')
            seeking = bool(profile.get("seeking_mentor"))
            open_mentor = bool(profile.get("open_to_mentoring"))
            status = [t for t, on in (("Seeking a mentor", seeking), ("Open to mentoring", open_mentor)) if on]
            if status:
                st.caption("Mentoring status")
                st.text(" · ".join(status))
            cols = st.columns(2)
            for idx, (label, items) in enumerate(give_need):
                if items:
                    with cols[idx % 2]:
                        _chips(label, items)
