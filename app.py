import streamlit as st

from findings.core import cookies, session
from findings.core.config import ConfigError, load_settings

st.set_page_config(page_title="Findings")

try:
    settings = load_settings(st.secrets)
except (ConfigError, FileNotFoundError, KeyError, st.errors.StreamlitSecretNotFoundError):
    st.error(
        "App is not configured. Copy .streamlit/secrets.toml.example to "
        ".streamlit/secrets.toml and fill in SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY."
    )
    st.stop()

session.get_client(settings)
session.restore_once()
session.refresh_if_needed()

user = session.current_user()
if user:
    pages = [
        st.Page("views/home.py", title="Home", default=True),
        st.Page("views/account.py", title="Account"),
    ]
else:
    pages = [st.Page("views/login.py", title="Sign in", default=True)]

nav = st.navigation(pages)

if user:
    with st.sidebar:
        st.caption(user["email"])
        st.button("Sign out", key="sidebar_sign_out", on_click=session.sign_out)

cookies.sync_cookie(session.cookie_value())
nav.run()
