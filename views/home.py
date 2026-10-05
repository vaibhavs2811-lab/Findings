import streamlit as st

from findings.core import session

user = session.current_user() or {}
st.title("Welcome to Findings")
st.write(f"Signed in as {user.get('email', '')}")
if st.button("Sign out"):
    session.sign_out(st.session_state["sb"])
    st.rerun()
