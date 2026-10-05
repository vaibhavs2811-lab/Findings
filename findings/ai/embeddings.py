"""Shared Gemini vector embedding pipeline for profile matching and discovery.

Uses gemini-embedding-2 with 768 dimensions, L2 normalization, and symmetric prefixes.
Excludes names, institutions, and education to mitigate prestige and identity bias.
"""

from __future__ import annotations

import hashlib
import math
import random
from collections.abc import Sequence
from typing import Any

from google.genai import types

from findings.ai.client import AIUnavailable, _resolve_client

EMBEDDING_MODEL = "gemini-embedding-2"
EMBED_MODEL = EMBEDDING_MODEL
EMBEDDING_DIM = 768
TEXT_VERSION = "v1"
EMBEDDING_PREFIX = "task: sentence similarity | query: "


def normalize_vector(vec: Sequence[float]) -> list[float]:
    """L2-normalize a floating point vector to unit length."""
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0.0:
        return [0.0] * len(vec)
    return [float(x / norm) for x in vec]


def profile_embedding_text(profile: dict[str, Any]) -> str:
    """Assemble text payload for semantic embedding from a profile record.

    Excludes name, institution, education, and email to mitigate bias.
    """
    sections: list[str] = []

    stage = profile.get("career_stage")
    if stage:
        sections.append(f"Career stage: {stage}")

    methods = (
        profile.get("methods_effective")
        or profile.get("methods_override")
        or profile.get("methods_suggested")
    )
    if methods:
        sections.append(f"Methods orientation: {methods}")

    interests = profile.get("interests") or []
    if interests:
        clean_ints = [str(x).strip() for x in interests if str(x).strip()]
        if clean_ints:
            sections.append(f"Research interests: {', '.join(clean_ints)}")

    skills = profile.get("skills") or []
    if skills:
        clean_skills = [str(x).strip() for x in skills if str(x).strip()]
        if clean_skills:
            sections.append(f"Skills and methodologies: {', '.join(clean_skills)}")

    experience = str(profile.get("experience") or "").strip()
    if experience:
        sections.append(f"Research experience: {experience}")

    looking_for = str(profile.get("looking_for") or "").strip()
    if looking_for:
        sections.append(f"Looking for: {looking_for}")

    offers = profile.get("offers") or []
    if offers:
        clean_offers = [str(x).strip() for x in offers if str(x).strip()]
        if clean_offers:
            sections.append(f"Mentoring offers: {', '.join(clean_offers)}")

    needs = profile.get("needs") or []
    if needs:
        clean_needs = [str(x).strip() for x in needs if str(x).strip()]
        if clean_needs:
            sections.append(f"Mentoring needs: {', '.join(clean_needs)}")

    contrib = profile.get("contributable_skills") or []
    if contrib:
        clean_contrib = [str(x).strip() for x in contrib if str(x).strip()]
        if clean_contrib:
            sections.append(f"Contributable skills: {', '.join(clean_contrib)}")

    learn = profile.get("want_to_learn") or []
    if learn:
        clean_learn = [str(x).strip() for x in learn if str(x).strip()]
        if clean_learn:
            sections.append(f"Want to learn: {', '.join(clean_learn)}")

    bio = str(profile.get("bio") or "").strip()
    if bio:
        sections.append(f"Bio: {bio}")

    body = "\n\n".join(sections)
    return f"{EMBEDDING_PREFIX}{body}"


def profile_hash(target: str | dict[str, Any]) -> str:
    """Compute sha256 input hash over embedding model, dimension, version and text."""
    text = profile_embedding_text(target) if isinstance(target, dict) else str(target)
    payload = f"{EMBEDDING_MODEL}:{EMBEDDING_DIM}:{TEXT_VERSION}:{text}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()



def mock_embedding(text: str) -> list[float]:
    """Generate deterministic pseudo-random unit vector for offline testing."""
    h = hashlib.sha256(text.encode("utf-8")).digest()
    seed_int = int.from_bytes(h[:8], "big")
    rng = random.Random(seed_int)
    raw = [rng.gauss(0.0, 1.0) for _ in range(EMBEDDING_DIM)]
    return normalize_vector(raw)


def embed_profile(text: str, *, client: Any = None) -> list[float]:
    """Call gemini-embedding-2 to produce a 768-dimensional L2-normalized vector."""
    resolved = _resolve_client(client)
    try:
        cfg = types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIM)
        res = resolved.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text,
            config=cfg,
        )
        embeds = getattr(res, "embeddings", None)
        if not embeds:
            raise ValueError("Empty embeddings response")
        values = embeds[0].values
        if len(values) != EMBEDDING_DIM:
            raise ValueError(f"Expected {EMBEDDING_DIM} dimensions, got {len(values)}")
        return normalize_vector(values)
    except Exception as exc:
        raise AIUnavailable(f"Embedding generation failed: {type(exc).__name__}") from exc
