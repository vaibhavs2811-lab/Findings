import streamlit as st

from findings.core import session
from findings.services import auth_service
from findings.services.auth_service import AuthFailure
from ui.components import brand_html

# The sidebar adds nothing before sign-in; give the page the full width.
st.html("<style>[data-testid='stSidebar'],[data-testid='stSidebarCollapsedControl'],[data-testid='stExpandSidebarButton']{display:none}</style>")

sb = st.session_state["sb"]

left, right = st.columns([1.15, 1], gap="large", vertical_alignment="center")
with left:
    st.html(
        brand_html()
        + '<div style="height:1.4rem"></div>'
        + '<span class="fx-eyebrow">Hinge for researchers</span>'
        + '<div class="fx-display">Find the people you would '
        + '<span class="fx-gradient-text">actually want to work with</span>.</div>'
        + '<div class="fx-lead">Findings matches researchers on topics, methods and goals, '
        + "explains every match, and pairs junior researchers with mentors so both sides gain.</div>"
        + '<div style="height:1rem"></div>'
        + '<div class="fx-feature"><div class="ic">✨</div><div><div class="tt">AI-ranked matches</div>'
        + '<div class="dd">A short, honest reason for every suggestion.</div></div></div>'
        + '<div class="fx-feature"><div class="ic">🎓</div><div><div class="tt">Mentorship both ways</div>'
        + '<div class="dd">Juniors learn how research is done; mentors get skilled help.</div></div></div>'
        + '<div class="fx-feature"><div class="ic">🔒</div><div><div class="tt">Private until you both agree</div>'
        + '<div class="dd">Contact email is revealed only after a request is accepted.</div></div></div>'
    )
with right, st.container(key="fxpanel-signin"):
    st.title("Sign in to Findings")
    st.caption("Welcome back. New here? Create an account in a few seconds.")
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
