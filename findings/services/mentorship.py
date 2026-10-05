"""Mentorship mode rules and utilities. Pure functions, no Streamlit dependency."""

from __future__ import annotations

from typing import Any


def available_modes(profile: dict[str, Any]) -> list[str]:
    """Return mentorship modes available based on profile toggles."""
    modes: list[str] = []
    if profile.get("seeking_mentor"):
        modes.append("mentor")
    if profile.get("open_to_mentoring"):
        modes.append("mentee")
    return modes


def direction_label(mode: str) -> str:
    """Human-readable label for mentorship direction."""
    if mode == "mentor":
        return "Find a mentor"
    if mode == "mentee":
        return "Find a mentee"
    return mode


def gate_notice(mode: str) -> str:
    """Notice for a viewer who lacks the required toggle."""
    if mode == "mentor":
        return "Turn on 'Seeking a mentor' on My profile to see mentors."
    return "Turn on 'Open to mentoring' on My profile to see mentees."


def own_give_need_empty(profile: dict[str, Any], mode: str) -> bool:
    """Check if viewer's give/need fields for the active direction are both empty."""
    if mode == "mentor":
        wl = profile.get("want_to_learn") or []
        cs = profile.get("contributable_skills") or []
        return not wl and not cs
    # mentee
    offers = profile.get("offers") or []
    needs = profile.get("needs") or []
    return not offers and not needs
