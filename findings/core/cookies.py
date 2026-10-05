"""findings_rt cookie: carries ONLY the Supabase refresh token across browser refreshes."""

from __future__ import annotations

import json
import re

import streamlit as st

COOKIE_NAME = "findings_rt"
MAX_AGE_SECONDS = 604800
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_.\-]{8,512}")


def _valid(value) -> bool:
    return isinstance(value, str) and TOKEN_PATTERN.fullmatch(value) is not None


def read_refresh_token() -> str | None:
    try:
        value = st.context.cookies.get(COOKIE_NAME)
    except Exception:
        return None
    return value if _valid(value) else None


def build_cookie_script(value: str | None) -> str:
    if value is not None and not _valid(value):
        raise ValueError("refresh token failed the cookie allowlist")
    want = json.dumps(value)
    return (
        "<script>(function(){"
        f"var want={want};"
        f'var m=document.cookie.match(/(?:^|; ){COOKIE_NAME}=([^;]*)/);'
        "var cur=m?m[1]:null;"
        "if(want===null){"
        f'if(cur!==null){{document.cookie="{COOKIE_NAME}=; Path=/; Max-Age=0; '
        'SameSite=Strict; Secure";}'
        "}else if(cur!==want){"
        f'document.cookie="{COOKIE_NAME}="+want+"; Path=/; Max-Age={MAX_AGE_SECONDS}; '
        'SameSite=Strict; Secure";}'
        "})();</script>"
    )


def sync_cookie(value: str | None) -> None:
    try:
        script = build_cookie_script(value)
    except ValueError:
        script = build_cookie_script(None)
    st.html(script, unsafe_allow_javascript=True)
