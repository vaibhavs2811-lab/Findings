import streamlit as st

from findings.core import session
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

if session.current_user():
    pages = [st.Page("views/home.py", title="Home", default=True)]
else:
    pages = [st.Page("views/login.py", title="Sign in", default=True)]

st.navigation(pages).run()
