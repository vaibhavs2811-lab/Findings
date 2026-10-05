"""Discover view: browse, filter, search and skip researchers in the community."""

from __future__ import annotations

from typing import Any

import streamlit as st

from findings.core import session
from findings.core.constants import CAREER_STAGES, METHODS_LABELS
from findings.repos.profiles import list_public
from findings.services import connection_service
from ui.cards import METHOD_TITLES, render_card

st.html('<span class="fx-eyebrow">Community</span>')
st.title("Discover")
st.caption("Browse researchers across fields, filter by methods and stage, or search an interest.")

# Authenticated user check
user = session.current_user() or {}
user_id = user.get("id")
if not user_id:
    st.error("You must be signed in to view this page.")
    st.stop()

# Ensure skip state is isolated to current signed-in account
if st.session_state.get("skipped_owner") != user_id:
    st.session_state["skipped_owner"] = user_id
    st.session_state["skipped_ids"] = []


def _skip(pid: str) -> None:
    if pid not in st.session_state["skipped_ids"]:
        st.session_state["skipped_ids"].append(pid)


def _unskip_all() -> None:
    st.session_state["skipped_ids"] = []


def _clear_filters() -> None:
    st.session_state["disc_methods"] = []
    st.session_state["disc_stages"] = []
    st.session_state["disc_keyword"] = ""


# Filter row
filter_panel = st.container(key="fxpanel-filters")
with filter_panel:
    col_methods, col_stages, col_keyword = st.columns(3)
    with col_methods:
        st.pills(
            "Methods",
            METHODS_LABELS,
            selection_mode="multi",
            format_func=lambda m: METHOD_TITLES.get(m, m.title()),
            key="disc_methods",
        )
    with col_stages:
        st.multiselect(
            "Career stage",
            CAREER_STAGES,
            key="disc_stages",
            placeholder="Any stage",
        )
    with col_keyword:
        st.text_input(
            "Interest keyword",
            key="disc_keyword",
            max_chars=60,
            placeholder="e.g. ethnography",
        )

skipped_ids = list(st.session_state.get("skipped_ids", []))
action_cols = st.columns([1, 1, 4])
with action_cols[0]:
    st.button("Clear filters", key="disc_clear", on_click=_clear_filters, icon=":material/filter_alt_off:")
with action_cols[1]:
    if skipped_ids:
        st.button(f"Show skipped ({len(skipped_ids)})", key="disc_unskip", on_click=_unskip_all)

# Fetch public profiles
selected_methods = st.session_state.get("disc_methods")
selected_stages = st.session_state.get("disc_stages")
keyword = st.session_state.get("disc_keyword")
exclude_ids = [user_id, *skipped_ids]

try:
    profiles = list_public(
        st.session_state["sb"],
        methods=selected_methods,
        stages=selected_stages,
        keyword=keyword,
        exclude_ids=exclude_ids,
    )
except Exception:
    st.warning("Could not load researchers. Try again in a moment.")
    st.stop()

has_filters = bool(selected_methods or selected_stages or (keyword and keyword.strip()))

sb = st.session_state.get("sb")
conn_states: dict[str, Any] | None = None
if sb and user_id:
    try:
        conn_states = connection_service.connection_states(sb, user_id)
    except Exception:
        conn_states = {}

if not profiles:
    if has_filters:
        st.info("No researchers match these filters.")
    else:
        st.info("No researchers to show yet.")
else:
    st.caption(f"Showing {len(profiles)} researchers")
    cols = st.columns(3)
    for idx, p in enumerate(profiles):
        with cols[idx % 3]:
            render_card(p, on_skip=_skip, sb=sb, user_id=user_id, states=conn_states)
