"""Peer matching service.

Computes shortlist candidates via pgvector similarity and constructs
grounded match explanations with methods complementarity.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from findings.ai import embeddings
from findings.repos import profiles

logger = logging.getLogger(__name__)

SUPPORTED_MODES = ("peer",)
SHORTLIST_SIZE = 15

EMBED_STRONG = 0.75
EMBED_GOOD = 0.60
AI_STRONG = 75
AI_GOOD = 50

INCOMPLETE_NOTICE = "Complete your profile first to see personalized peer collaborator matches."
NO_MATCHES_NOTICE = "No matching peer collaborators found yet. Check back soon as more researchers join!"
UNAVAILABLE_NOTICE = (
    "Matching service is currently unavailable. In the meantime, explore researchers on Discover."
)
EMBED_FAILED_NOTICE = (
    "Unable to compute your profile embedding at this time. Please try again shortly or browse Discover."
)


@dataclass
class MatchResult:
    """Result of peer or mentor matching query."""

    items: list[dict[str, Any]]
    source: str  # 'ai' or 'embedding'
    notice: str | None = None
    from_cache: bool = False
    computed_at: str | None = None


def strength_from_similarity(sim: float) -> str:
    """Return coarse match strength from embedding cosine similarity."""
    if sim >= EMBED_STRONG:
        return "Strong match"
    if sim >= EMBED_GOOD:
        return "Good match"
    return "Possible match"


def strength_from_score(score: int) -> str:
    """Return coarse match strength from 0-100 AI rerank score."""
    if score >= AI_STRONG:
        return "Strong match"
    if score >= AI_GOOD:
        return "Good match"
    return "Possible match"


def template_why(me: dict[str, Any], cand: dict[str, Any]) -> str:
    """Construct deterministic 1-2 sentence match explanation.

    Cites shared interests/skills and methods complementarity without LLM calls.
    """
    me_interests = [str(x).strip() for x in (me.get("interests") or []) if str(x).strip()]
    me_skills = [str(x).strip() for x in (me.get("skills") or []) if str(x).strip()]
    me_tokens = {x.casefold() for x in me_interests + me_skills}

    cand_interests = [str(x).strip() for x in (cand.get("interests") or []) if str(x).strip()]
    cand_skills = [str(x).strip() for x in (cand.get("skills") or []) if str(x).strip()]

    # Up to 3 shared interests/skills in candidate's original casing
    shared: list[str] = []
    seen: set[str] = set()
    for token in cand_interests + cand_skills:
        cf = token.casefold()
        if cf in me_tokens and cf not in seen:
            shared.append(token)
            seen.add(cf)
            if len(shared) == 3:
                break

    if shared:
        if len(shared) == 1:
            interests_part = f"You both share interest in {shared[0]}."
        elif len(shared) == 2:
            interests_part = f"You both share interests in {shared[0]} and {shared[1]}."
        else:
            interests_part = f"You both share interests in {shared[0]}, {shared[1]}, and {shared[2]}."
    else:
        cand_sub = cand_interests[:2]
        me_first = me_interests[:1]
        if cand_sub and me_first:
            interests_part = (
                f"They focus on {', '.join(cand_sub)}, connecting with your work in {me_first[0]}."
            )
        elif cand_sub:
            interests_part = f"They focus on {', '.join(cand_sub)}."
        elif me_first:
            interests_part = f"They share research synergy with your work in {me_first[0]}."
        else:
            interests_part = "You have complementary research backgrounds."

    cand_m = cand.get("methods_effective") or "mixed"
    me_m = me.get("methods_effective") or "mixed"
    if cand_m != me_m:
        methods_part = f"Their {cand_m} methods complement your {me_m} approach."
    else:
        methods_part = f"You both take a {me_m} approach."

    return f"{interests_part} {methods_part}"


def to_item(
    row: dict[str, Any],
    me: dict[str, Any],
    *,
    score: int | None = None,
    why: str | None = None,
    why_source: str = "template",
) -> dict[str, Any]:
    """Transform candidate row into standard UI card snapshot."""
    sim = float(row.get("similarity") or 0.0)
    strength = strength_from_score(score) if score is not None else strength_from_similarity(sim)
    explanation = why if why else template_why(me, row)

    return {
        "id": str(row.get("id")),
        "full_name": row.get("full_name"),
        "career_stage": row.get("career_stage"),
        "methods_effective": row.get("methods_effective"),
        "interests": (row.get("interests") or [])[:5],
        "is_synthetic": bool(row.get("is_synthetic")),
        "similarity": sim,
        "score": score,
        "strength": strength,
        "why": explanation,
        "why_source": why_source,
    }


def ensure_embedding(sb: Any, user_id: str, profile: dict[str, Any]) -> str:
    """Ensure user profile has an up-to-date vector embedding in Supabase.

    Returns: 'updated' | 'unchanged' | 'skipped' | 'stale' | 'failed'
    """
    if not profile.get("is_complete"):
        return "skipped"

    meta = profiles.get_embedding_meta(sb, user_id)
    curr_hash = embeddings.profile_hash(profile)
    curr_model = getattr(embeddings, "EMBED_MODEL", getattr(embeddings, "EMBEDDING_MODEL", "gemini-embedding-2"))

    if (
        meta.get("embedding_hash") == curr_hash
        and meta.get("embedding_model") == curr_model
        and meta.get("embedded_at")
    ):
        return "unchanged"

    try:
        text = embeddings.profile_embedding_text(profile)
        vec = embeddings.embed_profile(text)
        now_iso = datetime.now(timezone.utc).isoformat()
        profiles.update_own(
            sb,
            user_id,
            {
                "embedding": vec,
                "embedding_model": curr_model,
                "embedding_hash": curr_hash,
                "embedded_at": now_iso,
            },
        )
        return "updated"
    except Exception as exc:
        logger.warning("ensure_embedding failed: %s", type(exc).__name__)
        if meta.get("embedded_at"):
            return "stale"
        return "failed"


def get_matches(
    sb: Any,
    user_id: str,
    mode: str = "peer",
    refresh: bool = False,
) -> MatchResult:
    """Retrieve ranked peer collaborator matches for a researcher."""
    if mode not in SUPPORTED_MODES:
        raise ValueError(f"Unsupported matching mode: {mode}")

    me = profiles.get_own_profile(sb, user_id)
    if not me or not me.get("is_complete"):
        return MatchResult(items=[], source="embedding", notice=INCOMPLETE_NOTICE)

    embed_status = ensure_embedding(sb, user_id, me)
    if embed_status == "failed":
        return MatchResult(items=[], source="embedding", notice=EMBED_FAILED_NOTICE)

    try:
        rows = profiles.match_profiles(
            sb,
            match_count=SHORTLIST_SIZE,
            exclude_ids=[user_id],
            mode=mode,
        )
    except Exception as exc:
        logger.warning("match_profiles RPC failed: %s", type(exc).__name__)
        return MatchResult(items=[], source="embedding", notice=UNAVAILABLE_NOTICE)

    if not rows:
        return MatchResult(items=[], source="embedding", notice=NO_MATCHES_NOTICE)

    items = [
        to_item(row, me)
        for row in rows
        if str(row.get("id")) != str(user_id)
    ]

    if not items:
        return MatchResult(items=[], source="embedding", notice=NO_MATCHES_NOTICE)

    return MatchResult(items=items, source="embedding", notice=None)
