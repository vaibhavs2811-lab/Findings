"""Repository for match_cache table and connections invalidation.

No Streamlit imports; safe for headless services, scripts, and tests.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

from findings.ai.rerank import RERANK_PROMPT_VERSION, sanitize_profile_for_ai

logger = logging.getLogger(__name__)

CACHE_COLUMNS = "user_id, mode, profile_hash, source, results, created_at"


def compute_match_key(profile: dict[str, Any], mode: str) -> str:
    """Compute sha256 cache key from canonical sanitized profile, mode, and prompt version."""
    clean = sanitize_profile_for_ai(profile)
    payload = f"{json.dumps(clean, sort_keys=True)}:{mode}:{RERANK_PROMPT_VERSION}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def get_cached_matches(sb: Any, user_id: str, mode: str) -> dict[str, Any] | None:
    """Retrieve cached matches row for user and mode, or None if absent."""
    try:
        res = (
            sb.table("match_cache")
            .select(CACHE_COLUMNS)
            .eq("user_id", user_id)
            .eq("mode", mode)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        return rows[0] if rows else None
    except Exception as exc:
        logger.warning("get_cached_matches failed: %s", type(exc).__name__)
        return None


def upsert_cached_matches(
    sb: Any,
    user_id: str,
    mode: str,
    profile_hash: str,
    source: str,
    results: list[dict[str, Any]],
) -> None:
    """Save or update matches cache row."""
    now_iso = datetime.now(timezone.utc).isoformat()
    payload = {
        "user_id": user_id,
        "mode": mode,
        "profile_hash": profile_hash,
        "source": source,
        "results": results,
        "created_at": now_iso,
    }
    try:
        sb.table("match_cache").upsert(payload, on_conflict="user_id,mode").execute()
    except Exception as exc:
        logger.warning("upsert_cached_matches failed: %s", type(exc).__name__)


def get_connected_profile_ids(sb: Any, user_id: str) -> set[str]:
    """Fetch IDs of all profiles that currently have an active or pending connection with user."""
    try:
        req_res = (
            sb.table("connections").select("recipient_id").eq("requester_id", user_id).execute()
        )
        rec_res = (
            sb.table("connections").select("requester_id").eq("recipient_id", user_id).execute()
        )
        connected: set[str] = set()
        for r in req_res.data or []:
            rec = str(r.get("recipient_id") or "")
            if rec and rec != user_id:
                connected.add(rec)
        for r in rec_res.data or []:
            req = str(r.get("requester_id") or "")
            if req and req != user_id:
                connected.add(req)
        return connected
    except Exception as exc:
        logger.warning("get_connected_profile_ids failed: %s", type(exc).__name__)
        return set()
