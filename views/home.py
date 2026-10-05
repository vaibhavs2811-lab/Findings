import streamlit as st

from findings.core import session
from findings.repos.profiles import get_own_profile

user = session.current_user() or {}
st.title("Welcome to Findings")
st.write(f"Signed in as {user.get('email', '')}")

try:
    profile = get_own_profile(st.session_state["sb"], user.get("id", ""))
except Exception:
    st.warning("Could not load your profile record. Try again in a moment.")
else:
    if profile is None or not profile.get("is_complete"):
        st.info(
            "Your profile is not complete yet. Add your name, career stage and at least "
            "one research interest so other researchers can find you."
        )
        st.page_link("views/profile.py", label="Complete your profile")
    else:
        st.success("Your profile is complete.")
        st.page_link("views/profile.py", label="View my profile")
