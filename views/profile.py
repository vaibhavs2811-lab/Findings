"""My profile view.

Allows signed-in researchers to edit their profile details, mentoring exchange preferences,
and view their read-only profile card.
"""

from __future__ import annotations

import streamlit as st

from findings.core import session
from findings.core.constants import (
    CAREER_STAGES,
    PRESET_INTERESTS,
    PRESET_NEEDS,
    PRESET_OFFERS,
    PRESET_SKILLS,
)
from findings.repos.profiles import get_own_profile
from findings.services import profile_service as ps
from ui.autofill_panel import render_autofill_panel
from ui.cards import card_header_html
from ui.components import completeness, meter_html
from ui.profile_view import render_profile

# 1. Pop & show flash message from previous action
if "flash" in st.session_state:
    _kind, msg = st.session_state.pop("flash")
    st.toast(msg)

st.title("My profile")

# 2. Authenticated user check
user = session.current_user() or {}
user_id = user.get("id")
if not user_id:
    st.error("You must be signed in to view this page.")
    st.stop()

# 3. Load profile from database
try:
    profile = get_own_profile(st.session_state["sb"], user_id)
except Exception:
    st.warning("Could not load your profile. Try again in a moment.")
    st.stop()

# 4. Mode determination (defaults to view when complete, else edit)
if "profile_mode" not in st.session_state:
    st.session_state["profile_mode"] = "view" if (profile and profile.get("is_complete")) else "edit"


def _seed(row: dict) -> None:
    """Seed widget state once from database row."""
    ss = st.session_state
    ss["f_name"] = row.get("full_name") or ""
    stage = row.get("career_stage")
    ss["f_stage"] = stage if stage in CAREER_STAGES else None
    ss["f_institution"] = row.get("institution") or ""
    ss["f_education"] = row.get("education") or ""
    ss["f_experience"] = row.get("experience") or ""
    ss["f_bio"] = row.get("bio") or ""
    ss["f_looking_for"] = row.get("looking_for") or ""
    ss["f_interests"] = list(row.get("interests") or [])
    ss["f_skills"] = list(row.get("skills") or [])
    ss["f_offers"] = list(row.get("offers") or [])
    ss["f_needs"] = list(row.get("needs") or [])
    ss["f_contrib"] = list(row.get("contributable_skills") or [])
    ss["f_learn"] = list(row.get("want_to_learn") or [])
    ss["f_seeking"] = bool(row.get("seeking_mentor"))
    ss["f_open"] = bool(row.get("open_to_mentoring"))


def _on_stage() -> None:
    """Update mentoring toggles default when career stage is selected."""
    d = ps.mentoring_defaults(st.session_state.get("f_stage"))
    if d is not None:
        st.session_state["f_seeking"], st.session_state["f_open"] = d


def _on_edit() -> None:
    _seed(profile or {})
    st.session_state["profile_mode"] = "edit"


def _on_cancel() -> None:
    st.session_state["profile_mode"] = "view"
    for k in [k for k in st.session_state if k.startswith("f_")]:
        del st.session_state[k]


def _on_override() -> None:
    chosen = st.session_state.get("methods_override_ctl")
    val = None if chosen == "auto" else chosen
    try:
        ps.set_methods_override(st.session_state["sb"], user_id, val)
        st.session_state["flash"] = ("success", "Methods label updated.")
    except Exception:
        st.session_state["flash"] = ("warning", "Could not update methods override.")


if st.session_state["profile_mode"] == "view":
    render_profile(profile, show_email=False)
    suggested_tag = (profile or {}).get("methods_suggested") or "Not classified yet"
    st.segmented_control(
        "Methods orientation",
        options=["auto", "qualitative", "quantitative", "mixed"],
        default=(profile or {}).get("methods_override") or "auto",
        key="methods_override_ctl",
        format_func=lambda v: f"Auto (AI: {suggested_tag})" if v == "auto" else v.title(),
        on_change=_on_override,
    )
    st.button("Edit", key="profile_edit", on_click=_on_edit)
else:
    # Edit mode: seed sentinel check
    if "f_name" not in st.session_state:
        _seed(profile or {})

    main_col, side_col = st.columns([3, 2], gap="large")
    with main_col:
        render_autofill_panel()

        # About you
        st.subheader("About you")
        st.text_input("Full name", key="f_name", max_chars=120)
        st.selectbox(
            "Career stage",
            CAREER_STAGES,
            index=None,
            key="f_stage",
            on_change=_on_stage,
            placeholder="Choose your career stage",
        )
        st.text_input("Institution", key="f_institution", max_chars=2000)
        st.text_area("Education background", key="f_education", max_chars=2000)

        # Research
        st.subheader("Research")
        st.multiselect("Research interests", PRESET_INTERESTS, key="f_interests", accept_new_options=True)
        st.text_area("Research experience", key="f_experience", max_chars=2000)
        st.multiselect("Skills & methods", PRESET_SKILLS, key="f_skills", accept_new_options=True)
        st.text_area("Bio", key="f_bio", max_chars=2000)
        st.text_area("What I'm looking for", key="f_looking_for", max_chars=2000)

        # Mentoring exchange
        st.subheader("Mentoring exchange")
        st.toggle("Seeking a mentor", key="f_seeking")
        st.toggle("Open to mentoring", key="f_open")

        if st.session_state.get("f_open"):
            st.multiselect("What I can offer", PRESET_OFFERS, key="f_offers", accept_new_options=True)
            st.multiselect("What I need help with", PRESET_NEEDS, key="f_needs", accept_new_options=True)

        if st.session_state.get("f_seeking"):
            st.multiselect("Skills I can contribute", PRESET_SKILLS, key="f_contrib", accept_new_options=True)
            st.multiselect("What I want to learn", PRESET_SKILLS, key="f_learn", accept_new_options=True)

        # Build form state for validation / display
        form_data = {
            "full_name": st.session_state.get("f_name"),
            "career_stage": st.session_state.get("f_stage"),
            "institution": st.session_state.get("f_institution"),
            "education": st.session_state.get("f_education"),
            "experience": st.session_state.get("f_experience"),
            "bio": st.session_state.get("f_bio"),
            "looking_for": st.session_state.get("f_looking_for"),
            "interests": st.session_state.get("f_interests", []),
            "skills": st.session_state.get("f_skills", []),
            "seeking_mentor": st.session_state.get("f_seeking", False),
            "open_to_mentoring": st.session_state.get("f_open", False),
            "offers": st.session_state.get("f_offers", []) if st.session_state.get("f_open") else [],
            "needs": st.session_state.get("f_needs", []) if st.session_state.get("f_open") else [],
            "contributable_skills": (
                st.session_state.get("f_contrib", []) if st.session_state.get("f_seeking") else []
            ),
            "want_to_learn": (
                st.session_state.get("f_learn", []) if st.session_state.get("f_seeking") else []
            ),
        }

        missing = ps.missing_for_complete(form_data)
        if missing:
            st.caption("Missing for a complete profile: " + ", ".join(missing) + ".")

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Save", key="profile_save", type="primary"):
                try:
                    with st.spinner("Saving your profile..."):
                        saved = ps.save_profile(st.session_state["sb"], user_id, form_data)

                    ai_status = saved.get("ai_status", "unchanged")
                    if ai_status == "updated":
                        base_msg = "Profile saved. Methods label updated."
                        kind = "success"
                    elif ai_status == "unavailable":
                        base_msg = (
                            "Profile saved. The AI methods suggestion is unavailable right now; "
                            "it will be tried again the next time you save."
                        )
                        kind = "warning"
                    else:
                        base_msg = "Profile saved."
                        kind = "success"

                    if saved.get("is_complete"):
                        st.session_state["flash"] = (kind, base_msg)
                        st.session_state["profile_mode"] = "view"
                    else:
                        missing_labels = ", ".join(ps.missing_for_complete(form_data))
                        full_msg = f"{base_msg} Add {missing_labels} to complete your profile."
                        st.session_state["flash"] = ("info", full_msg)
                        st.session_state["profile_mode"] = "edit"

                    for k in [k for k in st.session_state if k.startswith("f_")]:
                        del st.session_state[k]
                    st.rerun()
                except ps.ProfileSaveError as err:
                    st.error(str(err))

        with col2:
            if profile and profile.get("is_complete"):
                st.button("Cancel", key="profile_cancel", on_click=_on_cancel)

    with side_col, st.container(key="fxpanel-preview"):
        pct, still = completeness(form_data)
        st.html('<span class="fx-eyebrow">Live preview</span>')
        st.html(card_header_html(dict(form_data, methods_effective=(profile or {}).get("methods_effective"))))
        st.html(meter_html(pct))
        st.caption(f"Profile {pct}% complete" + (f" · add: {', '.join(still[:3])}" if still else ""))
