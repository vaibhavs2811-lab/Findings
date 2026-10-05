"""Methods orientation classifier and hashing utilities.

Extracts signal from research text fields, hashes inputs to avoid repeat calls,
and classifies profiles into qualitative, quantitative, or mixed orientation.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from findings.ai.client import TEXT_MODELS, generate_structured
from findings.ai.prompts import METHODS_SYSTEM, methods_prompt

METHODS_FIELDS: tuple[str, ...] = (
    "interests",
    "skills",
    "experience",
    "bio",
    "education",
    "looking_for",
)
PROMPT_VERSION = "m1"
REASON_MAX_CHARS = 140
TEXT_INPUT_MAX_CHARS = 1500
LIST_INPUT_MAX_ITEMS = 15


class MethodsSuggestion(BaseModel):
    """Structured response model for Gemini methods classification."""

    label: Literal["qualitative", "quantitative", "mixed"]
    reason: str = Field(description="One short sentence (max 140 characters) naming the methods mentioned.")


def methods_input(profile: dict[str, Any]) -> dict[str, Any]:
    """Extract and bound only the methods-driving fields from a profile.

    Prohibition: Excludes full_name, institution, career_stage, mentoring toggles, and email.
    """
    cleaned: dict[str, Any] = {}
    for field in METHODS_FIELDS:
        val = profile.get(field)
        if isinstance(val, (list, tuple, set)):
            items = [str(x).strip() for x in val if x and str(x).strip()]
            cleaned[field] = items[:LIST_INPUT_MAX_ITEMS]
        elif val is not None:
            text = str(val).strip()
            cleaned[field] = text[:TEXT_INPUT_MAX_CHARS] if text else ""
        else:
            cleaned[field] = ""
    return cleaned


def has_signal(profile: dict[str, Any]) -> bool:
    """Return True if any of the methods-driving fields contain non-empty data."""
    extracted = methods_input(profile)
    for val in extracted.values():
        if val:
            return True
    return False


def methods_hash(profile: dict[str, Any]) -> str:
    """Compute stable SHA256 over methods fields.

    Insensitive to list item order, case, and surrounding whitespace.
    Includes PROMPT_VERSION to bust hash when prompt evolves.
    """
    extracted = methods_input(profile)
    normalized: dict[str, Any] = {"version": PROMPT_VERSION}

    for field in METHODS_FIELDS:
        val = extracted.get(field)
        if isinstance(val, list):
            normalized[field] = sorted({item.casefold() for item in val})
        else:
            normalized[field] = (val or "").strip()

    serialized = json.dumps(normalized, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def needs_classification(
    new_hash: str,
    stored_hash: str | None,
    stored_suggested: str | None,
) -> bool:
    """True if profile has never been classified or methods input has changed."""
    return stored_suggested is None or stored_hash != new_hash


def suggest_methods(
    profile: dict[str, Any],
    *,
    client: Any = None,
    models: tuple[str, ...] = TEXT_MODELS,
) -> MethodsSuggestion:
    """Classify methods orientation and return suggestion with reason capped to 140 chars."""
    prompt = methods_prompt(methods_input(profile))
    suggestion: MethodsSuggestion = generate_structured(
        prompt,
        MethodsSuggestion,
        system=METHODS_SYSTEM,
        client=client,
        models=models,
    )  # type: ignore[assignment]

    cleaned_reason = suggestion.reason.strip()[:REASON_MAX_CHARS]
    return MethodsSuggestion(label=suggestion.label, reason=cleaned_reason)
