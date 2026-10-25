"""Chat table and RPC access. No Streamlit imports."""

from __future__ import annotations

from typing import Any

MESSAGE_COLUMNS = "id, connection_id, sender_id, body, created_at, read_at"
THREAD_LIMIT = 200


def list_conversations(sb: Any) -> list[dict[str, Any]]:
    """Conversations for accepted connections with real people, newest activity first."""
    res = sb.rpc("my_conversations").execute()
    return res.data or []


def list_messages(sb: Any, connection_id: str, limit: int = THREAD_LIMIT) -> list[dict[str, Any]]:
    """Latest messages of a thread, oldest first. RLS limits this to the two participants."""
    res = (
        sb.table("messages")
        .select(MESSAGE_COLUMNS)
        .eq("connection_id", connection_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return list(reversed(res.data or []))


def insert_message(sb: Any, connection_id: str, sender_id: str, body: str) -> None:
    sb.table("messages").insert(
        {"connection_id": connection_id, "sender_id": sender_id, "body": body}
    ).execute()


def mark_read(sb: Any, connection_id: str) -> None:
    sb.rpc("mark_conversation_read", {"p_connection": connection_id}).execute()
