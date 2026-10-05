"""Peer matching service.

Computes shortlist candidates via pgvector similarity and constructs
grounded match explanations with methods complementarity.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from findings.ai import embeddings
from findings.repos import profiles
from findings.repos.mentorship import MENTOR_POOL_SIZE, MENTORSHIP_MODES, mentorship_candidates
from findings.services.mentorship import available_modes, gate_notice
from findings.services.mentorship_fit import cache_hash as mentor_cache_hash
from findings.services.mentorship_fit import shortlist as mentor_shortlist

logger = logging.getLogger(__name__)

SUPPORTED_MODES = ("peer",) + MENTORSHIP_MODES
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
FALLBACK_NOTICE = (
    "AI explanations are unavailable right now, so these matches are ranked by profile similarity."
)
STALE_AI_NOTICE = "Showing your last AI matches. They may not reflect recent profile changes."
EMBEDDING_CACHE_TTL_SECONDS = 600


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
    """Retrieve ranked peer or mentorship matches for a researcher."""
    if mode not in SUPPORTED_MODES:
        raise ValueError(f"Unsupported matching mode: {mode}")

    me = profiles.get_own_profile(sb, user_id)
    if not me or not me.get("is_complete"):
        return MatchResult(items=[], source="embedding", notice=INCOMPLETE_NOTICE)

    # Mentorship gate: viewer must have the right toggle
    if mode in MENTORSHIP_MODES and mode not in available_modes(me):
        return MatchResult(items=[], source="embedding", notice=gate_notice(mode))

    embed_status = ensure_embedding(sb, user_id, me)
    if embed_status == "failed":
        return MatchResult(items=[], source="embedding", notice=EMBED_FAILED_NOTICE)

    from findings.repos import matches as matches_repo

    connected_ids = matches_repo.get_connected_profile_ids(sb, user_id)
    match_key = matches_repo.compute_match_key(me, mode)
    if mode in MENTORSHIP_MODES:
        match_key = mentor_cache_hash(match_key, me, mode)

    force_fallback = os.environ.get("FINDINGS_FORCE_AI_FALLBACK") == "1"

    # Rung 1: Fresh cache check (skip if refresh=True or forced fallback)
    if not refresh and not force_fallback:
        cached = matches_repo.get_cached_matches(sb, user_id, mode)
        if cached:
            c_key = cached.get("profile_hash")
            c_source = cached.get("source") or "embedding"
            c_rows = cached.get("results") or []
            c_created = cached.get("created_at")

            if c_key == match_key:
                fresh_items = [item for item in c_rows if str(item.get("id")) not in connected_ids]
                if c_source == "ai" and fresh_items:
                    return MatchResult(
                        items=fresh_items,
                        source="ai",
                        notice=None,
                        from_cache=True,
                        computed_at=c_created,
                    )
                if c_source == "embedding" and fresh_items and c_created:
                    try:
                        dt = datetime.fromisoformat(str(c_created).replace("Z", "+00:00"))
                        age = (datetime.now(timezone.utc) - dt).total_seconds()
                    except Exception:
                        age = 999999
                    if age <= EMBEDDING_CACHE_TTL_SECONDS:
                        return MatchResult(
                            items=fresh_items,
                            source="embedding",
                            notice=FALLBACK_NOTICE,
                            from_cache=True,
                            computed_at=c_created,
                        )

    # Rung 2: Shortlist from RPC
    exclude = list({user_id} | connected_ids)
    if mode in MENTORSHIP_MODES:
        try:
            rows = mentorship_candidates(
                sb,
                mode=mode,
                match_count=MENTOR_POOL_SIZE,
                exclude_ids=exclude,
            )
        except Exception as exc:
            logger.warning("match_mentorship RPC failed: %s", type(exc).__name__)
            return MatchResult(items=[], source="embedding", notice=UNAVAILABLE_NOTICE)
    else:
        try:
            rows = profiles.match_profiles(
                sb,
                match_count=SHORTLIST_SIZE,
                exclude_ids=exclude,
                mode=mode,
            )
        except Exception as exc:
            logger.warning("match_profiles RPC failed: %s", type(exc).__name__)
            return MatchResult(items=[], source="embedding", notice=UNAVAILABLE_NOTICE)

    if not rows:
        return MatchResult(items=[], source="embedding", notice=NO_MATCHES_NOTICE)

    candidates = [
        row for row in rows
        if str(row.get("id")) != str(user_id) and str(row.get("id")) not in connected_ids
    ]

    if not candidates:
        return MatchResult(items=[], source="embedding", notice=NO_MATCHES_NOTICE)

    if mode in MENTORSHIP_MODES:
        candidates = mentor_shortlist(me, candidates, mode)

    try:
        if mode in MENTORSHIP_MODES:
            from findings.ai import mentorship_prompt

            ai_items = mentorship_prompt.rerank_mentorship(me, candidates, mode)
        else:
            from findings.ai import rerank

            ai_items = rerank.rerank_candidates(me, candidates)
        if not force_fallback:
            matches_repo.upsert_cached_matches(
                sb, user_id, mode, match_key, source="ai", results=ai_items
            )
        return MatchResult(items=ai_items, source="ai", notice=None, from_cache=False)
    except Exception as exc:
        logger.warning("AI rerank failed (%s); checking stale cache or embedding fallback", type(exc).__name__)

    # Rung 3: Stale AI cache fallback (skipped if forced fallback)
    if not force_fallback:
        stale_cached = matches_repo.get_cached_matches(sb, user_id, mode)
        if stale_cached and stale_cached.get("source") == "ai":
            stale_rows = stale_cached.get("results") or []
            stale_items = [item for item in stale_rows if str(item.get("id")) not in connected_ids]
            if stale_items:
                return MatchResult(
                    items=stale_items,
                    source="ai",
                    notice=STALE_AI_NOTICE,
                    from_cache=True,
                    computed_at=stale_cached.get("created_at"),
                )

    # Rung 4: Embedding-only fallback
    if mode in MENTORSHIP_MODES:
        from findings.ai import mentorship_prompt

        emb_items = mentorship_prompt.fallback_items(me, candidates, mode)
    else:
        emb_items = [to_item(row, me) for row in candidates]
    if not force_fallback:
        matches_repo.upsert_cached_matches(
            sb, user_id, mode, match_key, source="embedding", results=emb_items
        )
    return MatchResult(items=emb_items, source="embedding", notice=FALLBACK_NOTICE, from_cache=False)
