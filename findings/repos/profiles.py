"""Profiles table access. No streamlit import; the only module that knows the table name."""

from __future__ import annotations

# Explicit column list: never star, never the embedding column.
PROFILE_SUMMARY_COLUMNS = "id, full_name, career_stage, is_complete, created_at"


def get_own_profile(sb, user_id: str) -> dict | None:
    """Read the signed-in user's own profiles row through RLS, or None if absent."""
    res = sb.table("profiles").select(PROFILE_SUMMARY_COLUMNS).eq("id", user_id).limit(1).execute()
    rows = res.data or []
    return rows[0] if rows else None
