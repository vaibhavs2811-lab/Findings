import streamlit as st

from findings.core import session
from findings.services import auth_service
from findings.services.auth_service import AuthFailure

st.title("Sign in to Findings")
sb = st.session_state["sb"]

tab_in, tab_up = st.tabs(["Sign in", "Create account"])

with tab_in:
    with st.form("signin_form"):
        email = st.text_input("Email", key="signin_email")
        password = st.text_input("Password", type="password", key="signin_password")
        submitted = st.form_submit_button("Sign in")
    if submitted:
        try:
            user_id, user_email = auth_service.sign_in(sb, email, password)
        except AuthFailure as err:
            st.error(str(err))
        else:
            session.set_signed_in(user_id, user_email)
            st.rerun()

with tab_up:
    with st.form("signup_form"):
        new_email = st.text_input("Email", key="signup_email")
        new_password = st.text_input(
            "Password (at least 6 characters)", type="password", key="signup_password"
        )
        confirm = st.text_input("Confirm password", type="password", key="signup_confirm")
        created = st.form_submit_button("Create account")
    if created:
        try:
            user_id, user_email = auth_service.sign_up(sb, new_email, new_password, confirm)
        except AuthFailure as err:
            st.error(str(err))
        else:
            session.set_signed_in(user_id, user_email)
            st.rerun()
