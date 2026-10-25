"""Chat thread rendering. Every dynamic string is HTML-escaped; messages are plain text."""

from __future__ import annotations

from typing import Any

from findings.services.chat_service import parse_time
from ui.components import esc


def thread_html(messages: list[dict[str, Any]], me_id: str) -> str:
    """Bubbles for a thread, oldest first, with date dividers (times are UTC)."""
    if not messages:
        return '<div class="fx-thread-empty">No messages yet. Say hello.</div>'
    parts: list[str] = []
    last_day = None
    for m in messages:
        dt = parse_time(m.get("created_at"))
        day = dt.strftime("%b %d, %Y") if dt else ""
        if day and day != last_day:
            parts.append(f'<div class="fx-day">{esc(day)}</div>')
            last_day = day
        mine = str(m.get("sender_id")) == str(me_id)
        stamp = dt.strftime("%H:%M") if dt else ""
        receipt = " · Read" if mine and m.get("read_at") else ""
        side = "me" if mine else "them"
        parts.append(
            f'<div class="fx-msgrow {side}"><div class="fx-bubble">{esc(m.get("body"))}</div>'
            f'<div class="fx-time">{esc(stamp)}{receipt}</div></div>'
        )
    return '<div class="fx-thread-scroll"><div class="fx-thread">' + "".join(parts) + "</div></div>"
