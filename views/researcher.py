"""Public researcher profile view.

Displays read-only information for a selected researcher without exposing contact details.
Accessible via query param ?id=<uuid>.
"""

from __future__ import annotations

import streamlit as st

from findings.repos.profiles import get_public
from ui.cards import synthetic_badge
from ui.profile_view import render_profile

raw_id = st.query_params.get("id")

if not raw_id:
    st.info("Pick a researcher on Discover to see their profile.")
    st.page_link("views/discover.py", label="Back to Discover", icon=":material/arrow_back:")
    st.stop()

try:
    profile = get_public(st.session_state["sb"], raw_id)
except Exception:
    st.warning("Could not load this profile. Try again in a moment.")
    st.page_link("views/discover.py", label="Back to Discover", icon=":material/arrow_back:")
    st.stop()

if not profile:
    st.info("Researcher not found or their profile is not public.")
    st.page_link("views/discover.py", label="Back to Discover", icon=":material/arrow_back:")
    st.stop()

synthetic_badge(profile)
render_profile(profile, show_email=False)
st.page_link("views/discover.py", label="Back to Discover", icon=":material/arrow_back:")
