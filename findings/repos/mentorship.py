"""Repository for match_mentorship RPC. No Streamlit imports."""

from __future__ import annotations

from typing import Any

MENTORSHIP_MODES = ("mentor", "mentee")
MENTOR_POOL_SIZE = 40


def mentorship_candidates(
    sb: Any,
    *,
    mode: str,
    match_count: int = MENTOR_POOL_SIZE,
    exclude_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Call match_mentorship RPC for mentor or mentee candidates."""
    if mode not in MENTORSHIP_MODES:
        raise ValueError(f"Invalid mentorship mode: {mode}")

    res = sb.rpc(
        "match_mentorship",
        {
            "match_count": match_count,
            "exclude_ids": [str(i) for i in (exclude_ids or [])],
            "mode": mode,
        },
    ).execute()
    return res.data or []
