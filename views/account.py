import streamlit as st

from findings.core import session

user = session.current_user() or {}
st.title("Account")
st.write(f"Signed in as {user.get('email', '')}")
st.code(user.get("id", ""))
if st.button("Sign out", type="primary", key="account_sign_out"):
    session.sign_out()
    st.rerun()
