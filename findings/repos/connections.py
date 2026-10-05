"""Repository for connections table and my_connections RPC.

No Streamlit imports; safe for headless services, scripts, and tests.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

CONNECTION_COLUMNS = "id, requester_id, recipient_id, note, status, created_at, responded_at"


def insert_request(
    sb: Any,
    requester_id: str,
    recipient_id: str,
    note: str | None = None,
) -> dict[str, Any]:
    """Insert a new pending connection request with only allowed client columns."""
    clean_note = note.strip() if note and note.strip() else None
    payload: dict[str, Any] = {
        "requester_id": requester_id,
        "recipient_id": recipient_id,
        "note": clean_note,
    }
    res = sb.table("connections").insert(payload).execute()
    rows = res.data or []
    return rows[0] if rows else {}


def get_by_id(sb: Any, connection_id: str) -> dict[str, Any] | None:
    """Fetch a single connection row by id, selecting only non-private columns."""
    res = (
        sb.table("connections")
        .select(CONNECTION_COLUMNS)
        .eq("id", connection_id)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def set_status(
    sb: Any,
    connection_id: str,
    recipient_id: str,
    status: str,
) -> list[dict[str, Any]]:
    """Update connection status (accepted/declined) scoped strictly to recipient."""
    res = (
        sb.table("connections")
        .update({"status": status})
        .eq("id", connection_id)
        .eq("recipient_id", recipient_id)
        .execute()
    )
    return res.data or []


def list_mine(sb: Any) -> list[dict[str, Any]]:
    """Call my_connections security-definer RPC to retrieve caller's connections."""
    res = sb.rpc("my_connections").execute()
    return res.data or []
