"""Service for researcher connection requests, responses, and connection states.

No Streamlit imports; safe for headless services, scripts, and tests.
"""

from __future__ import annotations

import logging
from typing import Any

from postgrest.exceptions import APIError as PostgrestAPIError

from findings.repos import connections as connections_repo

logger = logging.getLogger(__name__)

NOTE_MAX = 500


class ConnectionFailure(Exception):
    """User-safe exception indicating connection action failure."""


def send_request(
    sb: Any,
    user_id: str,
    recipient_id: str,
    note: str | None = None,
) -> dict[str, Any]:
    """Send connection request with optional note (max 500 chars)."""
    if not user_id:
        raise ConnectionFailure("Sign in again to send requests.")

    if str(user_id) == str(recipient_id):
        raise ConnectionFailure("You can't send a request to yourself.")

    clean_note = (note or "").strip()
    if len(clean_note) > NOTE_MAX:
        raise ConnectionFailure("Keep the note under 500 characters.")

    try:
        inserted = connections_repo.insert_request(
            sb,
            requester_id=user_id,
            recipient_id=recipient_id,
            note=clean_note or None,
        )
        cid = inserted.get("id")
        if not cid:
            return inserted

        # Re-read to observe server-side trigger effects (e.g. auto_accept_synthetic)
        fresh = connections_repo.get_by_id(sb, cid)
        return fresh if fresh is not None else inserted
    except PostgrestAPIError as exc:
        code = getattr(exc, "code", None)
        logger.warning("send_request API error code=%s: %s", code, type(exc).__name__)
        if str(code) == "23505":
            raise ConnectionFailure("You've already connected with this researcher or sent a request.") from None
        raise ConnectionFailure("Could not send the request. Try again in a moment.") from None
    except Exception as exc:
        logger.warning("send_request failed: %s", type(exc).__name__)
        raise ConnectionFailure("Could not send the request. Try again in a moment.") from None


def respond(
    sb: Any,
    user_id: str,
    connection_id: str,
    accept: bool,
) -> dict[str, Any]:
    """Respond to pending request as recipient (accept or decline)."""
    status = "accepted" if accept else "declined"
    try:
        rows = connections_repo.set_status(sb, connection_id, user_id, status)
        if not rows:
            raise ConnectionFailure("Only the person who received this request can answer it.")
        return rows[0]
    except ConnectionFailure:
        raise
    except PostgrestAPIError as exc:
        logger.warning("respond API error code=%s: %s", getattr(exc, "code", None), type(exc).__name__)
        raise ConnectionFailure("This request was already answered.") from None
    except Exception as exc:
        logger.warning("respond failed: %s", type(exc).__name__)
        raise ConnectionFailure("Could not answer this request. Try again in a moment.") from None


def list_connections(sb: Any, user_id: str) -> dict[str, list[dict[str, Any]]]:
    """Fetch connections for user categorized into sent, received, and accepted."""
    rows = connections_repo.list_mine(sb)
    sent: list[dict[str, Any]] = []
    received: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []

    for r in rows:
        direction = r.get("direction")
        status = r.get("status")

        if status == "accepted":
            accepted.append(r)
        elif direction == "received" and status == "pending":
            received.append(r)
        elif direction == "sent" and status in ("pending", "declined"):
            sent.append(r)

    return {
        "sent": sent,
        "received": received,
        "accepted": accepted,
    }


def connection_states(sb: Any, user_id: str) -> dict[str, dict[str, Any]]:
    """Map other_id to current connection status chip information."""
    rows = connections_repo.list_mine(sb)
    states: dict[str, dict[str, Any]] = {}

    for r in rows:
        other_id = str(r.get("other_id") or "")
        if not other_id:
            continue

        direction = r.get("direction")
        status = r.get("status")
        cid = str(r.get("connection_id") or "")
        is_synthetic = bool(r.get("other_is_synthetic"))

        if status == "accepted":
            state = "connected"
        elif status == "declined":
            state = "declined"
        elif status == "pending":
            state = "sent" if direction == "sent" else "received"
        else:
            state = "unknown"

        states[other_id] = {
            "state": state,
            "connection_id": cid,
            "is_synthetic": is_synthetic,
        }

    return states
