"""Admin database repository for seeding synthetic researcher profiles using service-role access.

Never imported by Streamlit app code; used exclusively by scripts/seed_load.py.
"""

from __future__ import annotations

import uuid
from typing import Any

FINDINGS_SEED_NAMESPACE = uuid.UUID("f14d1965-7e5d-4f01-9a3b-28f804564c7e")


def seed_uuid(seed_id: str) -> str:
    """Generate deterministic UUID5 identifier for a given seed_id."""
    return str(uuid.uuid5(FINDINGS_SEED_NAMESPACE, seed_id))


def upsert_seed_profiles(sb_admin: Any, profiles: list[dict[str, Any]]) -> tuple[int, int]:
    """Upsert synthetic profiles and private contacts into database using admin privileges.

    Returns (profiles_upserted, contacts_upserted).
    """
    profile_rows: list[dict[str, Any]] = []
    contact_rows: list[dict[str, Any]] = []

    for p in profiles:
        uid = seed_uuid(p["seed_id"])

        row = {
            "id": uid,
            "full_name": p["full_name"],
            "career_stage": p["career_stage"],
            "institution": p["institution"],
            "education": p.get("education", ""),
            "experience": p.get("experience", ""),
            "bio": p.get("bio", ""),
            "looking_for": p.get("looking_for", ""),
            "interests": p.get("interests", []),
            "skills": p.get("skills", []),
            "offers": p.get("offers", []),
            "needs": p.get("needs", []),
            "contributable_skills": p.get("contributable_skills", []),
            "want_to_learn": p.get("want_to_learn", []),
            "seeking_mentor": bool(p.get("seeking_mentor")),
            "open_to_mentoring": bool(p.get("open_to_mentoring")),
            "methods_suggested": p.get("methods_effective"),
            "methods_override": None,
            "methods_reason": p.get(
                "methods_reason", "Synthetic profile: methods label set by the seed spec"
            ),
            "is_synthetic": True,
            "is_complete": True,
        }

        if "embedding" in p:
            row["embedding"] = p["embedding"]
            row["embedding_hash"] = p.get("embedding_hash")
            row["embedding_model"] = p.get("embedding_model")
            row["embedded_at"] = p.get("embedded_at")

        profile_rows.append(row)

        if "email" in p:
            contact_rows.append({
                "id": uid,
                "contact_email": p["email"],
            })

    # Upsert profiles in batches of 50
    for i in range(0, len(profile_rows), 50):
        batch = profile_rows[i : i + 50]
        sb_admin.table("profiles").upsert(batch, on_conflict="id").execute()

    # Upsert contacts in batches of 50
    for i in range(0, len(contact_rows), 50):
        batch = contact_rows[i : i + 50]
        sb_admin.table("profile_contacts").upsert(batch, on_conflict="id").execute()

    return len(profile_rows), len(contact_rows)
