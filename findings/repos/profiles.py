"""Profiles table access. No streamlit import; the only module that knows the table name."""

from __future__ import annotations

from collections.abc import Sequence

# Explicit column lists: never star, never the embedding column.
PROFILE_SUMMARY_COLUMNS = "id, full_name, career_stage, is_complete, created_at"

PROFILE_COLUMNS = (
    "id, full_name, career_stage, institution, education, experience, bio, looking_for, "
    "interests, skills, offers, needs, contributable_skills, want_to_learn, "
    "seeking_mentor, open_to_mentoring, methods_suggested, methods_override, "
    "methods_effective, stage_tier, is_synthetic, is_complete, created_at, updated_at, "
    "methods_hash, methods_reason"
)


class ProfileWriteError(Exception):
    """Raised when an update to the profiles table affects zero rows (e.g. RLS rejection)."""


def get_own_profile(sb, user_id: str, columns: str = PROFILE_COLUMNS) -> dict | None:
    """Read the signed-in user's own profiles row through RLS, or None if absent."""
    res = sb.table("profiles").select(columns).eq("id", user_id).limit(1).execute()
    rows = res.data or []
    return rows[0] if rows else None


def update_own(sb, user_id: str, payload: dict, columns: str = PROFILE_COLUMNS) -> dict:
    """Update the signed-in user's own profiles row through RLS and return the updated row.

    Raises ProfileWriteError if zero rows were updated (such as when RLS rejects the write).
    """
    res = sb.table("profiles").update(payload).eq("id", user_id).select(columns).execute()
    rows = res.data or []
    if not rows:
        raise ProfileWriteError("Profile write affected zero rows (possible RLS rejection).")
    return rows[0]


CARD_COLUMNS = (
    "id, full_name, career_stage, methods_effective, interests, is_synthetic, "
    "seeking_mentor, open_to_mentoring"
)

EMBED_META_COLUMNS = "embedding_hash, embedding_model, embedded_at"


def get_embedding_meta(sb, user_id: str) -> dict:
    """Fetch only embedding metadata columns for the specified user."""
    res = sb.table("profiles").select(EMBED_META_COLUMNS).eq("id", user_id).limit(1).execute()
    rows = res.data or []
    return rows[0] if rows else {}


PUBLIC_PROFILE_COLUMNS = (
    "id, full_name, career_stage, institution, education, experience, bio, looking_for, "
    "interests, skills, offers, needs, contributable_skills, want_to_learn, "
    "seeking_mentor, open_to_mentoring, methods_suggested, methods_override, "
    "methods_effective, methods_reason, stage_tier, is_synthetic, is_complete"
)

MAX_PUBLIC_ROWS = 300


def list_public(
    sb,
    *,
    methods: Sequence[str] | None = None,
    stages: Sequence[str] | None = None,
    keyword: str | None = None,
    exclude_ids: Sequence[str] = (),
) -> list[dict]:
    """List public profiles for Discover grid.

    Excludes uncompleted profiles and specified IDs (such as own ID and skipped IDs).
    Methods and stages are filtered in PostgREST using indexed columns.
    Keywords are filtered in Python as a case-insensitive substring match across interests.
    """
    from findings.core.constants import CAREER_STAGES, METHODS_LABELS

    query = sb.table("profiles").select(CARD_COLUMNS).eq("is_complete", True)

    clean_methods = [m for m in (methods or []) if m in METHODS_LABELS]
    if clean_methods:
        query = query.in_("methods_effective", clean_methods)

    clean_stages = [s for s in (stages or []) if s in CAREER_STAGES]
    if clean_stages:
        query = query.in_("career_stage", clean_stages)

    res = query.order("is_synthetic").order("full_name").limit(MAX_PUBLIC_ROWS).execute()
    rows = res.data or []

    exclude_set = set(exclude_ids)
    if exclude_set:
        rows = [r for r in rows if r.get("id") not in exclude_set]

    if keyword:
        kw = " ".join(keyword.split()).casefold()[:60]
        if kw:
            rows = [
                r
                for r in rows
                if any(kw in str(item).casefold() for item in (r.get("interests") or []))
            ]

    return rows


def get_public(sb, profile_id: str) -> dict | None:
    """Fetch public profile by ID, returning None if invalid UUID, absent or not public."""
    import uuid

    try:
        parsed_id = str(uuid.UUID(str(profile_id)))
    except (ValueError, TypeError, AttributeError):
        return None

    res = (
        sb.table("profiles")
        .select(PUBLIC_PROFILE_COLUMNS)
        .eq("id", parsed_id)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def match_profiles(
    sb,
    *,
    query_embedding: list[float] | None = None,
    match_count: int = 15,
    exclude_ids: Sequence[str] = (),
    mode: str = "peer",
) -> list[dict]:
    """Call match_profiles RPC to get shortlisted candidate profiles."""
    params: dict = {
        "match_count": match_count,
        "exclude_ids": [str(x) for x in exclude_ids],
        "mode": mode,
    }
    if query_embedding is not None:
        params["query_embedding"] = query_embedding

    res = sb.rpc("match_profiles", params).execute()
    return res.data or []


