"""Design-system building blocks. Static markup only: every dynamic string is HTML-escaped.

User-written text (names, bios, notes) should still be shown with native elements such as
st.text where it appears as body content; these helpers only escape and style short labels.
"""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

import streamlit as st

from ui.icons import icon_css, icon_svg

_CSS_PATH = Path(__file__).with_name("theme.css")

_AVATAR_GRADIENTS = (
    ("#7c5cff", "#22d3ee"),
    ("#ff4d9d", "#ffb84d"),
    ("#22d3ee", "#34d399"),
    ("#ffb84d", "#ff7849"),
    ("#9b7bff", "#ff4d9d"),
    ("#34d399", "#7c5cff"),
    ("#fb7185", "#9b7bff"),
    ("#38bdf8", "#7c5cff"),
)

TONES = {"violet", "cyan", "green", "amber", "pink", "gray"}


def esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def inject_theme() -> None:
    """Inject the stylesheet. Call once per script run, before the page renders."""
    try:
        css = _CSS_PATH.read_text(encoding="utf-8")
    except OSError:
        return
    st.html(f"<style>{css}{icon_css()}</style>")


# ---------- Pure helpers ----------

def initials(name: str | None) -> str:
    words = [w for w in "".join(c if c.isalpha() or c.isspace() else " " for c in (name or "")).split() if w]
    if not words:
        return "?"
    if len(words) == 1:
        return words[0][:2].upper()
    return (words[0][0] + words[-1][0]).upper()


def _gradient_for(name: str | None) -> tuple[str, str]:
    h = 0
    for ch in name or "?":
        h = (h * 31 + ord(ch)) % 997
    return _AVATAR_GRADIENTS[h % len(_AVATAR_GRADIENTS)]


def completeness(profile: dict | None) -> tuple[int, list[str]]:
    """Return (percent complete, labels of missing items) for the profile meter."""
    p = profile or {}
    checks = [
        ("name", bool((p.get("full_name") or "").strip())),
        ("career stage", bool(p.get("career_stage"))),
        ("institution", bool((p.get("institution") or "").strip())),
        ("research interests", bool(p.get("interests"))),
        ("skills", bool(p.get("skills"))),
        ("bio", bool((p.get("bio") or "").strip())),
        ("what you are looking for", bool((p.get("looking_for") or "").strip())),
    ]
    done = sum(1 for _, ok in checks if ok)
    return round(100 * done / len(checks)), [label for label, ok in checks if not ok]


def strength_tone(strength: str | None) -> str:
    return {"Strong match": "strong", "Good match": "good"}.get(strength or "", "possible")


# ---------- HTML fragments (return strings) ----------

def avatar_html(name: str | None, size: int = 46) -> str:
    c1, c2 = _gradient_for(name)
    font = max(12, round(size * 0.38))
    return (
        f'<span class="fx-avatar" style="width:{size}px;height:{size}px;font-size:{font}px;'
        f'background:linear-gradient(135deg,{c1},{c2})">{esc(initials(name))}</span>'
    )


def pill_html(text: str, tone: str = "gray", icon: str = "", *, svg: str = "") -> str:
    """Pill badge. `svg` is trusted inline markup from ui.icons; `icon` is escaped text."""
    tone = tone if tone in TONES else "gray"
    lead = svg or esc(icon)
    return f'<span class="fx-pill {tone}">{lead}{" " if lead else ""}{esc(text)}</span>'


def pills_html(pills: list[tuple[str, str]]) -> str:
    return '<div class="fx-pills">' + "".join(pill_html(t, tone) for t, tone in pills) + "</div>"


def chips_html(items: list[str] | None, limit: int = 4) -> str:
    clean = [str(i).strip() for i in (items or []) if str(i).strip()][:limit]
    if not clean:
        return ""
    return '<div class="fx-chips">' + "".join(f'<span class="fx-chip">{esc(i)}</span>' for i in clean) + "</div>"


def ring_html(score: int | None, strength: str | None) -> str:
    pct = max(0, min(100, int(score or 0)))
    return f'<div class="fx-ring {strength_tone(strength)}" style="--p:{pct}"><span>{pct}</span></div>'


def exchange_html(get_label: str, get_text: str, give_label: str, give_text: str) -> str:
    return (
        '<div class="fx-exchange">'
        f'<div class="fx-ex get"><div class="h">{esc(get_label)}</div><div class="b">{esc(get_text)}</div></div>'
        f'<div class="fx-ex give"><div class="h">{esc(give_label)}</div><div class="b">{esc(give_text)}</div></div>'
        "</div>"
    )


def meter_html(pct: int) -> str:
    return f'<div class="fx-meter"><i style="width:{max(0, min(100, int(pct)))}%"></i></div>'


# ---------- Renderers (write to the page) ----------

def section_header(title: str, subtitle: str | None = None) -> None:
    sub = f'<div class="s">{esc(subtitle)}</div>' if subtitle else ""
    st.html(f'<div class="fx-section"><div class="t">{esc(title)}</div>{sub}</div>')


def empty_state(icon: str, title: str, body: str) -> None:
    """`icon` is a name from ui.icons."""
    st.html(
        f'<div class="fx-empty"><div class="i">{icon_svg(icon, 28)}</div>'
        f'<div class="t">{esc(title)}</div><div class="b">{esc(body)}</div></div>'
    )


def banner(text: str, tone: str = "warn", icon: str = "") -> None:
    cls = {"ok": " ok", "info": " info"}.get(tone, "")
    st.html(f'<div class="fx-banner{cls}"><span>{esc(icon)}</span><span>{esc(text)}</span></div>')


def brand_html() -> str:
    return (
        '<div class="fx-brand"><div class="fx-logo">F</div><div>'
        '<div class="fx-brand-name">Findings</div>'
        '<div class="fx-brand-tag">Find your research people</div></div></div>'
    )
