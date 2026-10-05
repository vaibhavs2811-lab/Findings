import streamlit as st

from findings.core import session
from ui.components import avatar_html, esc

user = session.current_user() or {}
st.html('<span class="fx-eyebrow">Settings</span>')
st.title("Account")
st.write(f"Signed in as {user.get('email', '')}")

with st.container(key="fxpanel-account"):
    st.html(
        '<div class="fx-row">' + avatar_html(user.get("email", "?"), 56)
        + f'<div class="fx-col"><div class="fx-title">{esc(user.get("email", ""))}</div>'
        + '<div class="fx-sub">Your account ID (for support)</div></div></div>'
    )
    st.code(user.get("id", ""))
    if st.button("Sign out", type="primary", key="account_sign_out"):
        session.sign_out()
        st.rerun()
