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
    if profile is None:
        st.info("No profile record yet.")
    else:
        created = str(profile.get("created_at") or "")[:10]
        state = "complete" if profile.get("is_complete") else "not complete yet"
        st.success(f"Profile record found (created {created}). Profile is {state}.")
