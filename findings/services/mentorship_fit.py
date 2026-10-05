"""Two-sided give/need fit for mentorship matches (MENT-02, MENT-03). No Streamlit imports."""

from __future__ import annotations

import hashlib
import json
from typing import Any

MENTOR_PROMPT_VERSION = "mentor-v1"
MENTOR_SHORTLIST_SIZE = 15
EXCHANGE_TEXT_LIMIT = 240


def exchange_labels(mode: str) -> tuple[str, str]:
    """Card labels for the two sides of the exchange."""
    role = "mentor" if mode == "mentor" else "mentee"
    return f"What you get from this {role}", f"What this {role} gets from you"


def _tokens(text: str) -> set[str]:
    cleaned = "".join(c.lower() if c.isalnum() else " " for c in text)
    return {w for w in cleaned.split() if len(w) >= 3}


def _clean(values: Any) -> list[str]:
    return [str(v).strip() for v in (values or []) if str(v).strip()]


def overlap(wanted: Any, offered: Any) -> list[str]:
    """Items in `wanted` that share a meaningful word with any item in `offered`."""
    offered_tokens = [_tokens(o) for o in _clean(offered)]
    hits: list[str] = []
    for item in _clean(wanted):
        toks = _tokens(item)
        if toks and any(toks & o for o in offered_tokens):
            hits.append(item)
    return hits


def exchange_sides(
    viewer: dict[str, Any], cand: dict[str, Any], mode: str
) -> tuple[list[str], list[str]]:
    """Return (what the viewer gets, what the candidate gets) as matched give/need items.

    mode 'mentor': viewer is the junior, candidate is the mentor.
    mode 'mentee': viewer is the mentor, candidate is the junior.
    """
    if mode == "mentor":
        gets = overlap(cand.get("offers"), viewer.get("want_to_learn"))
        gives = overlap(viewer.get("contributable_skills"), cand.get("needs"))
    else:
        gets = overlap(cand.get("contributable_skills"), viewer.get("needs"))
        gives = overlap(viewer.get("offers"), cand.get("want_to_learn"))
    return gets, gives


def fit_score(viewer: dict[str, Any], cand: dict[str, Any], mode: str) -> float:
    """0..1 two-way fit; both directions must contribute for a high score."""
    gets, gives = exchange_sides(viewer, cand, mode)
    return round((min(len(gets), 3) / 3 + min(len(gives), 3) / 3) / 2, 4)


def shortlist(
    viewer: dict[str, Any],
    rows: list[dict[str, Any]],
    mode: str,
    n: int = MENTOR_SHORTLIST_SIZE,
) -> list[dict[str, Any]]:
    """Blend give/need fit (60%) with embedding similarity (40%) and keep the top n."""

    def blended(row: dict[str, Any]) -> float:
        return 0.6 * fit_score(viewer, row, mode) + 0.4 * float(row.get("similarity") or 0.0)

    return sorted(rows, key=blended, reverse=True)[:n]


def _join(items: list[str]) -> str:
    items = items[:3]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def template_exchange(viewer: dict[str, Any], cand: dict[str, Any], mode: str) -> tuple[str, str]:
    """Deterministic they_give_you / you_give_them sentences for the fallback path."""
    gets, gives = exchange_sides(viewer, cand, mode)
    who = "mentor" if mode == "mentor" else "mentee"
    if gets:
        they_give = f"This {who} brings {_join(gets)}, which lines up with what you are after."
    else:
        they_give = f"No direct overlap yet between what this {who} brings and what you are after."
    if gives:
        you_give = f"You can help with {_join(gives)}, which this {who} is looking for."
    else:
        you_give = f"No direct overlap yet between what you bring and what this {who} is looking for."
    return they_give[:EXCHANGE_TEXT_LIMIT], you_give[:EXCHANGE_TEXT_LIMIT]


def cache_hash(base_hash: str, profile: dict[str, Any], mode: str) -> str:
    """Cache key for mentorship modes: peer hash plus give/need lists and prompt version."""
    payload = {
        "base": base_hash,
        "mode": mode,
        "stage": profile.get("career_stage"),
        "lists": [
            _clean(profile.get(k))
            for k in ("offers", "needs", "contributable_skills", "want_to_learn")
        ],
        "v": MENTOR_PROMPT_VERSION,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
