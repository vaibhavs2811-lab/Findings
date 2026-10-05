"""Profile domain service.

Validates, normalises, and builds payloads for user profile updates.
No Streamlit imports; safe for headless testing and CLI use.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from findings.ai.client import AIUnavailable
from findings.ai.methods import (
    has_signal,
    methods_hash,
    needs_classification,
    suggest_methods,
)
from findings.core.constants import (
    CAREER_STAGES,
    LIST_ITEM_MAX_LEN,
    LIST_MAX_ITEMS,
    METHODS_LABELS,
    STAGE_MENTORING_DEFAULTS,
    TEXT_LIMITS,
)
from findings.repos.profiles import update_own

logger = logging.getLogger(__name__)

FORM_KEYS: dict[str, str] = {
    "full_name": "f_name",
    "career_stage": "f_stage",
    "institution": "f_institution",
    "education": "f_education",
    "experience": "f_experience",
    "bio": "f_bio",
    "looking_for": "f_looking_for",
    "interests": "f_interests",
    "skills": "f_skills",
    "offers": "f_offers",
    "needs": "f_needs",
    "contributable_skills": "f_contrib",
    "want_to_learn": "f_learn",
    "seeking_mentor": "f_seeking",
    "open_to_mentoring": "f_open",
}


class ProfileSaveError(Exception):
    """Raised when profile save fails, carrying a user-safe error message."""


def mentoring_defaults(stage: str | None) -> tuple[bool, bool] | None:
    """Return (seeking_mentor, open_to_mentoring) defaults for a career stage, or None if unmanaged."""
    if not stage:
        return None
    return STAGE_MENTORING_DEFAULTS.get(stage)


def normalise_text(value: Any, max_len: int) -> str | None:
    """Trim string and truncate to max_len; return None if empty or whitespace-only."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:max_len]


def normalise_list(items: Any) -> list[str]:
    """Collapse inner whitespace, trim, truncate each to LIST_ITEM_MAX_LEN.

    Drops empty items and case-insensitive duplicates while preserving original order.
    Caps resulting list at LIST_MAX_ITEMS.
    """
    if not items or not isinstance(items, (list, tuple, set)):
        return []

    seen: set[str] = set()
    result: list[str] = []

    for item in items:
        if item is None:
            continue
        cleaned = re.sub(r"\s+", " ", str(item)).strip()
        if not cleaned:
            continue
        truncated = cleaned[:LIST_ITEM_MAX_LEN]
        key = truncated.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(truncated)
        if len(result) >= LIST_MAX_ITEMS:
            break

    return result


def is_complete(form: dict[str, Any]) -> bool:
    """True only if full_name is non-blank, career_stage in CAREER_STAGES, and >=1 interest."""
    name = str(form.get("full_name") or "").strip()
    stage = form.get("career_stage")
    interests = normalise_list(form.get("interests"))
    return bool(name and stage in CAREER_STAGES and len(interests) > 0)


def missing_for_complete(form: dict[str, Any]) -> list[str]:
    """Return human labels for missing required profile fields."""
    missing: list[str] = []
    name = str(form.get("full_name") or "").strip()
    if not name:
        missing.append("your name")
    stage = form.get("career_stage")
    if stage not in CAREER_STAGES:
        missing.append("a career stage")
    interests = normalise_list(form.get("interests"))
    if not interests:
        missing.append("at least one research interest")
    return missing


def build_payload(form: dict[str, Any]) -> dict[str, Any]:
    """Construct an allow-listed payload dict for profile update."""
    raw_name = str(form.get("full_name") or "").strip()
    full_name = raw_name[: TEXT_LIMITS["full_name"]]

    raw_stage = form.get("career_stage")
    career_stage = raw_stage if raw_stage in CAREER_STAGES else None

    seeking_mentor = bool(form.get("seeking_mentor", False))
    open_to_mentoring = bool(form.get("open_to_mentoring", False))

    offers = normalise_list(form.get("offers")) if open_to_mentoring else []
    needs = normalise_list(form.get("needs")) if open_to_mentoring else []
    contributable_skills = normalise_list(form.get("contributable_skills")) if seeking_mentor else []
    want_to_learn = normalise_list(form.get("want_to_learn")) if seeking_mentor else []

    payload: dict[str, Any] = {
        "full_name": full_name,
        "career_stage": career_stage,
        "institution": normalise_text(form.get("institution"), TEXT_LIMITS["institution"]),
        "education": normalise_text(form.get("education"), TEXT_LIMITS["education"]),
        "experience": normalise_text(form.get("experience"), TEXT_LIMITS["experience"]),
        "bio": normalise_text(form.get("bio"), TEXT_LIMITS["bio"]),
        "looking_for": normalise_text(form.get("looking_for"), TEXT_LIMITS["looking_for"]),
        "interests": normalise_list(form.get("interests")),
        "skills": normalise_list(form.get("skills")),
        "offers": offers,
        "needs": needs,
        "contributable_skills": contributable_skills,
        "want_to_learn": want_to_learn,
        "seeking_mentor": seeking_mentor,
        "open_to_mentoring": open_to_mentoring,
        "is_complete": is_complete(form),
    }

    return payload


def save_profile(sb, user_id: str, form: dict[str, Any]) -> dict[str, Any]:
    """Validate, build payload, and save profile to database via update_own.

    Triggers hash-gated methods classification if research fields changed.
    Returns the updated row dict augmented with ai_status ('updated' | 'unchanged' | 'skipped' | 'unavailable').
    """
    payload = build_payload(form)
    try:
        saved_row = update_own(sb, user_id, payload)
    except Exception as err:
        logger.warning("save_profile core write failed: %s", type(err).__name__)
        raise ProfileSaveError("Could not save your profile. Try again in a moment.") from None

    ai_status = "unchanged"
    if not has_signal(saved_row):
        ai_status = "skipped"
    else:
        new_hash = methods_hash(saved_row)
        if not needs_classification(
            new_hash, saved_row.get("methods_hash"), saved_row.get("methods_suggested")
        ):
            ai_status = "unchanged"
        else:
            try:
                suggestion = suggest_methods(saved_row)
                methods_payload = {
                    "methods_suggested": suggestion.label,
                    "methods_reason": suggestion.reason,
                    "methods_hash": new_hash,
                }
                saved_row = update_own(sb, user_id, methods_payload)
                ai_status = "updated"
            except AIUnavailable:
                ai_status = "unavailable"
            except Exception as exc:
                logger.warning("save_profile methods update failed: %s", type(exc).__name__)
                ai_status = "unavailable"

    embedding_status = "skipped"
    try:
        from findings.services import matching
        embedding_status = matching.ensure_embedding(sb, user_id, saved_row)
    except Exception as exc:
        logger.warning("save_profile embedding update failed: %s", type(exc).__name__)
        embedding_status = "failed"

    result = dict(saved_row)
    result["ai_status"] = ai_status
    result["embedding_status"] = embedding_status
    return result


def set_methods_override(sb, user_id: str, value: str | None) -> dict[str, Any]:
    """Set or clear manual methods orientation override ('qualitative' | 'quantitative' | 'mixed' | None)."""
    if value is not None and value not in METHODS_LABELS:
        raise ValueError(
            f"Invalid methods override: {value!r}. Must be one of {METHODS_LABELS} or None."
        )
    try:
        return update_own(sb, user_id, {"methods_override": value})
    except Exception as err:
        logger.warning("set_methods_override failed: %s", type(err).__name__)
        raise ProfileSaveError(
            "Could not update methods override. Try again in a moment."
        ) from None
