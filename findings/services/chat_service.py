"""Chat rules between connected researchers. No Streamlit imports."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from findings.repos import messages as repo

logger = logging.getLogger(__name__)

MAX_LEN = 2000


class ChatError(Exception):
    """Carries a user-safe message."""


def clean_body(text: str | None) -> str:
    """Trim, normalise newlines and reject empty or oversized messages."""
    body = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not body:
        raise ChatError("Type a message first.")
    if len(body) > MAX_LEN:
        raise ChatError(f"Messages can be up to {MAX_LEN} characters.")
    return body


def send(sb: Any, user_id: str, connection_id: str, text: str) -> None:
    body = clean_body(text)
    try:
        repo.insert_message(sb, connection_id, user_id, body)
    except Exception as exc:
        detail = str(exc).lower()
        if "too fast" in detail:
            raise ChatError("You are sending messages too fast. Wait a moment and try again.") from None
        if "row-level security" in detail or "policy" in detail:
            raise ChatError("You can only message people you are connected with.") from None
        logger.warning("send failed: %s", type(exc).__name__)
        raise ChatError("Could not send your message. Try again in a moment.") from None


def conversations(sb: Any, user_id: str) -> list[dict[str, Any]]:
    return repo.list_conversations(sb)


def thread(sb: Any, connection_id: str) -> list[dict[str, Any]]:
    return repo.list_messages(sb, connection_id)


def mark_read(sb: Any, connection_id: str) -> None:
    try:
        repo.mark_read(sb, connection_id)
    except Exception as exc:
        logger.warning("mark_read failed: %s", type(exc).__name__)


def unread_total(sb: Any, user_id: str) -> int:
    """Total unread messages across conversations; 0 if anything goes wrong."""
    try:
        return sum(int(c.get("unread_count") or 0) for c in repo.list_conversations(sb))
    except Exception:
        return 0


def snippet(text: str | None, limit: int = 48) -> str:
    one_line = " ".join((text or "").split())
    return one_line if len(one_line) <= limit else one_line[: limit - 1].rstrip() + "…"


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
