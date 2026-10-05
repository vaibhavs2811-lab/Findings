"""Helpers for reading designed (HTML) UI in AppTest. HTML bodies are tag-stripped and unescaped."""

from __future__ import annotations

import html as _html
import re
from types import SimpleNamespace

_TAG = re.compile(r"<style.*?</style>|<[^>]+>", re.DOTALL)


def html_values(at) -> list[str]:
    out = []
    for el in at.get("html"):
        body = getattr(el.proto, "body", "") or ""
        out.append(re.sub(r"\s+", " ", _html.unescape(_TAG.sub(" ", body))).strip())
    return out


def text_like(at) -> list:
    """at.text plus designed HTML blocks, each exposing .value."""
    return list(at.text) + [SimpleNamespace(value=v) for v in html_values(at)]


def markdown_like(at) -> list:
    """at.markdown plus designed HTML blocks, each exposing .value."""
    return list(at.markdown) + [SimpleNamespace(value=v) for v in html_values(at)]
