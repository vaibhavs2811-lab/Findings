from pathlib import Path

import streamlit as st

from findings.ai.client import configure
from findings.core import cookies, session
from findings.core.config import ConfigError, load_settings
from findings.services import chat_service
from ui.components import inject_theme
from ui.guide import render_guide

st.set_page_config(page_title="Findings", page_icon=":material/hub:", layout="wide")

try:
    settings = load_settings(st.secrets)
except (ConfigError, FileNotFoundError, KeyError, st.errors.StreamlitSecretNotFoundError):
    st.error(
        "App is not configured. Copy .streamlit/secrets.toml.example to "
        ".streamlit/secrets.toml and fill in SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY."
    )
    st.stop()

configure(settings.gemini_api_key)
inject_theme()

session.get_client(settings)
session.refresh_if_needed()
token = cookies.sync(session.cookie_value(), clear=st.session_state.pop("clear_cookie", False))
if session.restore_from_cookie(token):
    st.rerun()

user = session.current_user()
if user:
    _unread = chat_service.unread_total(st.session_state["sb"], user["id"])
    messages_title = f"Messages ({_unread})" if _unread else "Messages"
    pages = [
        st.Page("views/home.py", title="Home", icon=":material/home:", default=True),
        st.Page("views/discover.py", title="Discover", icon=":material/travel_explore:"),
        st.Page("views/matches.py", title="My Matches", icon=":material/handshake:"),
        st.Page("views/connections.py", title="Connections", icon=":material/group:"),
        st.Page("views/messages.py", title=messages_title, icon=":material/chat:"),
        st.Page("views/profile.py", title="My profile", icon=":material/badge:"),
        st.Page("views/account.py", title="Account", icon=":material/settings:"),
        st.Page("views/researcher.py", title="Researcher profile", visibility="hidden"),
    ]
else:
    pages = [st.Page("views/login.py", title="Sign in", icon=":material/login:", default=True)]

st.logo(str(Path(__file__).resolve().parent / "ui" / "logo.svg"), size="large")
nav = st.navigation(pages, position="top")

if user:
    # Guide and account menus, top right of every page ("sign out from any page" lives here).
    _spacer, _guide, _menu = st.columns([4, 1, 1], vertical_alignment="center")
    with _guide.popover("Guide", icon=":material/help:"):
        render_guide()
    with _menu.popover(user["email"].split("@")[0], icon=":material/account_circle:"):
        st.caption(user["email"])
        st.button("Sign out", key="sidebar_sign_out", on_click=session.sign_out, use_container_width=True)

nav.run()
