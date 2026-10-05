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


def render_profile(profile: dict | None, *, show_email: bool = False) -> None:
    """Render a read-only profile card.

    All user text is rendered safely using st.text to prevent markdown/HTML injection.
    """
    if not profile:
        st.caption("No profile information available.")
        return

    # Heading (sanitised name)
    header_name = _clean_header_name(profile.get("full_name"))
    st.subheader(header_name)

    # Methods orientation badge and AI rationale
    methods_badge(profile)

    # Primary details
    stage = profile.get("career_stage")
    institution = profile.get("institution")
    education = profile.get("education")

    detail_parts = [p for p in [stage, institution] if p]
    if detail_parts:
        st.caption(" · ".join(detail_parts))

    if education:
        st.caption("Education")
        st.text(education)

    # Email display: strictly gated by show_email flag
    if show_email and profile.get("email"):
        st.caption("Contact email")
        st.text(profile["email"])

    # Research section
    interests = profile.get("interests") or []
    if interests:
        st.caption("Research interests")
        st.text(" · ".join(interests))

    skills = profile.get("skills") or []
    if skills:
        st.caption("Skills & methods")
        st.text(" · ".join(skills))

    experience = profile.get("experience")
    if experience:
        st.caption("Research experience")
        st.text(experience)

    bio = profile.get("bio")
    if bio:
        st.caption("Bio")
        st.text(bio)

    looking_for = profile.get("looking_for")
    if looking_for:
        st.caption("What I'm looking for")
        st.text(looking_for)

    # Mentoring exchange section
    seeking = bool(profile.get("seeking_mentor"))
    open_mentor = bool(profile.get("open_to_mentoring"))

    mentoring_roles: list[str] = []
    if seeking:
        mentoring_roles.append("Seeking a mentor")
    if open_mentor:
        mentoring_roles.append("Open to mentoring")

    if mentoring_roles:
        st.caption("Mentoring status")
        st.text(" · ".join(mentoring_roles))

    offers = profile.get("offers") or []
    if offers:
        st.caption("What I can offer")
        st.text(" · ".join(offers))

    needs = profile.get("needs") or []
    if needs:
        st.caption("What I need help with")
        st.text(" · ".join(needs))

    contrib = profile.get("contributable_skills") or []
    if contrib:
        st.caption("Skills I can contribute")
        st.text(" · ".join(contrib))

    learn = profile.get("want_to_learn") or []
    if learn:
        st.caption("What I want to learn")
        st.text(" · ".join(learn))
