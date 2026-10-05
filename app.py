import platform

import streamlit as st

from findings.ai.client import configure
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

configure(settings.gemini_api_key)

session.get_client(settings)
session.refresh_if_needed()
token = cookies.sync(session.cookie_value(), clear=st.session_state.pop("clear_cookie", False))
if session.restore_from_cookie(token):
    st.rerun()

user = session.current_user()
if user:
    pages = [
        st.Page("views/home.py", title="Home", default=True),
        st.Page("views/profile.py", title="My profile"),
        st.Page("views/discover.py", title="Discover", icon=":material/travel_explore:"),
        st.Page("views/matches.py", title="My Matches", icon=":material/handshake:"),
        st.Page("views/connections.py", title="Connections", icon=":material/group:"),
        st.Page("views/account.py", title="Account"),
        st.Page("views/researcher.py", title="Researcher profile", visibility="hidden"),
    ]
else:
    pages = [st.Page("views/login.py", title="Sign in", default=True)]

nav = st.navigation(pages)

with st.sidebar:
    st.caption(f"Findings · Python {platform.python_version()}")

if user:
    with st.sidebar:
        st.caption(user["email"])
        st.button("Sign out", key="sidebar_sign_out", on_click=session.sign_out)

nav.run()
