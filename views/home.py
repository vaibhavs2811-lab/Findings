import streamlit as st

from findings.core import session
from findings.repos.profiles import get_own_profile
from findings.services import connection_service

user = session.current_user() or {}
st.title("Welcome to Findings")
st.write(f"Signed in as {user.get('email', '')}")
st.caption("Findings matches researchers who want to collaborate, and pairs juniors with mentors.")

sb = st.session_state["sb"]
try:
    profile = get_own_profile(sb, user.get("id", ""))
except Exception:
    st.warning("Could not load your profile record. Try again in a moment.")
    st.stop()

complete = bool(profile and profile.get("is_complete"))

if not complete:
    with st.container(border=True):
        st.subheader("Step 1: build your profile")
        st.info(
            "Your profile is not complete yet. Add your name, career stage and at least "
            "one research interest so other researchers can find you."
        )
        st.progress(0.33, text="Profile 1 of 3 steps: name, career stage, interests")
        st.page_link(
            "views/profile.py", label="Complete your profile", icon=":material/badge:"
        )
else:
    pending = 0
    try:
        pending = len(connection_service.list_connections(sb, user["id"])["received"])
    except Exception:
        pending = 0

    st.success("Your profile is complete.")
    c1, c2, c3 = st.columns(3)
    with c1.container(border=True):
        st.markdown("#### :material/handshake: My Matches")
        st.caption("AI-ranked collaborators and mentors, with a reason for each.")
        st.page_link("views/matches.py", label="See my matches")
    with c2.container(border=True):
        st.markdown("#### :material/travel_explore: Discover")
        st.caption("Browse, filter and search researchers across fields.")
        st.page_link("views/discover.py", label="Browse researchers")
    with c3.container(border=True):
        st.markdown("#### :material/group: Connections")
        st.caption(
            f"{pending} request(s) waiting for you." if pending else "Requests you sent and received."
        )
        st.page_link("views/connections.py", label="Open connections")
    st.page_link("views/profile.py", label="View my profile", icon=":material/badge:")
