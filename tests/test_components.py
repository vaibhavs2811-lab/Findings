"""Design-system components: escaping, pure helpers and the injected stylesheet."""

from __future__ import annotations

import re

from ui import components as c
from ui.cards import card_header_html, match_header_html
from ui.components import (
    avatar_html,
    chips_html,
    completeness,
    exchange_html,
    initials,
    pill_html,
    ring_html,
)

EVIL = '<script>alert(1)</script><img src=x onerror=alert(2)>"'


def test_initials():
    assert initials("Ada Lovelace") == "AL"
    assert initials("  grace  hopper  ") == "GH"
    assert initials("Cher") == "CH"
    assert initials("Dr. Mary-Jane O'Neil") == "DN"
    assert initials("") == "?"
    assert initials(None) == "?"
    assert initials("<<>>") == "?"


def test_avatar_is_deterministic_and_escaped():
    assert avatar_html("Ada Lovelace") == avatar_html("Ada Lovelace")
    assert "<script" not in avatar_html(EVIL)
    assert avatar_html("Ada Lovelace", 80).count("80px") == 2


def test_all_fragments_escape_user_text():
    fragments = [
        pill_html(EVIL, "violet"),
        chips_html([EVIL, "ok"]),
        exchange_html(EVIL, EVIL, EVIL, EVIL),
        match_header_html({"full_name": EVIL, "career_stage": EVIL, "interests": [EVIL], "strength": EVIL}, 1),
        card_header_html({"full_name": EVIL, "career_stage": "PhD", "interests": [EVIL]}),
    ]
    for html in fragments:
        assert "<script" not in html
        assert "<img" not in html
        assert "onerror=alert" not in html.replace("&quot;", '"') or "&lt;img" in html


def test_unknown_tone_falls_back_to_gray():
    assert "fx-pill gray" in pill_html("x", "not-a-tone")


def test_ring_clamps_score():
    assert "--p:100" in ring_html(250, "Strong match")
    assert "--p:0" in ring_html(-5, None)
    assert "strong" in ring_html(90, "Strong match")
    assert "possible" in ring_html(10, "Possible match")


def test_chips_limit_and_blank_removal():
    html = chips_html(["a", " ", "b", "c", "d", "e"], limit=3)
    assert html.count('class="fx-chip"') == 3
    assert chips_html([]) == ""


def test_completeness():
    assert completeness(None)[0] == 0
    full = {
        "full_name": "A",
        "career_stage": "PhD",
        "institution": "U",
        "interests": ["x"],
        "skills": ["y"],
        "bio": "b",
        "looking_for": "l",
    }
    assert completeness(full) == (100, [])
    pct, missing = completeness({"full_name": "A", "career_stage": "PhD", "interests": ["x"]})
    assert 0 < pct < 100
    assert "bio" in missing and "skills" in missing


def test_stylesheet_is_self_contained():
    css = c._CSS_PATH.read_text(encoding="utf-8")
    assert "</style" not in css.lower()
    urls = re.findall(r"url\(([^)]+)\)", css)
    assert all("fonts.googleapis.com" in u for u in urls)
    assert "javascript:" not in css.lower()
    assert "expression(" not in css.lower()


def test_theme_is_injected_on_every_page():
    from pathlib import Path

    from streamlit.testing.v1 import AppTest

    from tests.fakes_profiles import FakeProfilesSupabase
    from tests.uihelp import html_values  # noqa: F401

    app = str(Path(__file__).resolve().parent.parent / "app.py")
    secrets = {"SUPABASE_URL": "https://abc.supabase.co", "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_x"}
    sb = FakeProfilesSupabase()
    sb.auth._store("a@b.com")
    at = AppTest.from_file(app, default_timeout=20)
    at.secrets.update(secrets)
    at.session_state["sb"] = sb
    at.session_state["user"] = {"id": "user-1", "email": "a@b.com"}
    at.run()
    assert any("--fx-violet" in (e.proto.body or "") for e in at.get("html"))
    assert any("fx-brand-name" in (e.proto.body or "") for e in at.get("html"))


def test_icons_are_css_masks_without_scripts_or_external_urls():
    from ui.icons import _PATHS, icon_css, icon_svg

    assert icon_svg("nope") == ""
    css = icon_css()
    for name in _PATHS:
        el = icon_svg(name, 24)
        assert f"fx-ico-{name}" in el and "width:24px" in el and "<svg" not in el
        assert f".fx-ico-{name}" in css
    assert "<script" not in css.lower() and "javascript:" not in css.lower()
    assert "http%3A" not in css.replace("http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg", "")


def test_pill_accepts_trusted_svg_but_still_escapes_text():
    from ui.icons import icon_svg

    html = pill_html("<b>x</b>", "violet", svg=icon_svg("sparkles", 12))
    assert "fx-ico-sparkles" in html and "<b>" not in html and "&lt;b&gt;" in html


def test_no_emoji_in_ui_source():
    import pathlib

    allowed = set("·–—…→’‘“”é")
    root = pathlib.Path(__file__).resolve().parent.parent
    files = [*root.glob("views/*.py"), *root.glob("ui/*.py"), root / "app.py"]
    offenders = [
        f.name for f in files if any(ord(c) > 127 and c not in allowed for c in f.read_text(encoding="utf-8"))
    ]
    assert offenders == []
