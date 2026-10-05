"""findings_rt cookie: carries ONLY the Supabase refresh token across browser refreshes.

Streamlit Community Cloud's proxy strips custom cookies before they reach the
server, so st.context.cookies is empty there. The cookie is therefore read and
written in the browser by a small st.components.v2 bridge, which reports the
value back to Python as component state.
"""

from __future__ import annotations

import re

import streamlit as st

COOKIE_NAME = "findings_rt"
MAX_AGE_SECONDS = 604800
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_.\-]{8,512}")
BRIDGE_KEY = "findings_cookie_bridge"
SEEN_KEY = "_rt_seen"

# `data.want` is allowlist-validated in Python before it reaches the browser.
# The bridge reports the cookie only when it differs from what Python last saw
# (`data.seen`), so a report never loops into another rerun.
_BRIDGE_JS = f"""
export default function(component) {{
  const {{ data, setStateValue }} = component;
  const d = data || {{}};
  const read = () => {{
    const m = document.cookie.match(/(?:^|; ){COOKIE_NAME}=([^;]*)/);
    return m ? m[1] : "";
  }};
  if (d.clear) {{
    document.cookie = "{COOKIE_NAME}=; Path=/; Max-Age=0; SameSite=Lax; Secure";
  }} else if (typeof d.want === "string" && d.want && read() !== d.want) {{
    document.cookie = "{COOKIE_NAME}=" + d.want +
      "; Path=/; Max-Age={MAX_AGE_SECONDS}; SameSite=Lax; Secure";
  }}
  const cur = read();
  if (cur !== d.seen) {{
    setStateValue("rt", cur);
  }}
}}
"""

_bridge = st.components.v2.component("findings_cookie", js=_BRIDGE_JS)


def _valid(value) -> bool:
    return isinstance(value, str) and TOKEN_PATTERN.fullmatch(value) is not None


def _server_cookie() -> str | None:
    """Local runs still send the cookie to the server; Cloud does not."""
    try:
        value = st.context.cookies.get(COOKIE_NAME)
    except Exception:
        return None
    return value if _valid(value) else None


def sync(want: str | None, clear: bool = False) -> str | None:
    """Mount the bridge once per run: write `want` (or clear) and return the browser's token.

    Returns None until the browser has reported (first run of a fresh page load),
    then the validated token, or None when there is no usable cookie.
    """
    if want is not None and not _valid(want):
        want = None
    seen = st.session_state.get(SEEN_KEY)
    try:
        result = _bridge(
            key=BRIDGE_KEY,
            data={"want": want, "clear": bool(clear), "seen": seen},
            default={"rt": None},
            on_rt_change=lambda: None,
            height=0,
        )
        reported = result.get("rt") if hasattr(result, "get") else getattr(result, "rt", None)
    except Exception:
        reported = None
    if isinstance(reported, str):
        st.session_state[SEEN_KEY] = reported
    browser_token = st.session_state.get(SEEN_KEY)
    if isinstance(browser_token, str):
        return browser_token if _valid(browser_token) else None
    return _server_cookie()
