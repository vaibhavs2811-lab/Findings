"""Seed embedding and database loader script.

Computes 768-dim embeddings for all 80 synthetic profiles with caching in data/seed_embeddings.json,
calculates vector diversity metrics (pairwise cosines, nearest neighbors, near-duplicates),
and upserts them into Supabase via admin service-role key if available.

Usage:
    python scripts/seed_load.py [--dry-run] [--offline]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tomllib

from findings.ai.client import AIUnavailable, configure
from findings.ai.embeddings import (
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
    embed_profile,
    mock_embedding,
    profile_embedding_text,
    profile_hash,
)
from findings.core.config import load_local_settings
from findings.repos.seed_admin import seed_uuid, upsert_seed_profiles
from supabase import create_client


def get_admin_client(supabase_url: str, supabase_secret_key: str):
    """Create Supabase client using secret service-role key."""
    clean_key = (supabase_secret_key or "").strip()
    if not clean_key.startswith("sb_secret_"):
        raise ValueError("Admin secret key must start with 'sb_secret_'")
    return create_client(supabase_url, clean_key)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_load")

DATA_DIR = ROOT / "data"
SEED_PROFILES_FILE = DATA_DIR / "seed_profiles.json"
CACHE_FILE = DATA_DIR / "seed_embeddings.json"


def load_embeddings_cache() -> dict[str, dict[str, Any]]:
    """Load cached embeddings keyed by seed_id."""
    if not CACHE_FILE.exists():
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as err:
        logger.warning("Could not read embeddings cache (%s), starting fresh", err)
        return {}


def save_embeddings_cache(cache: dict[str, dict[str, Any]]) -> None:
    """Save embeddings cache to disk atomically."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp_file = DATA_DIR / f"seed_embeddings.json.{os.getpid()}.tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)
    for attempt in range(5):
        try:
            os.replace(temp_file, CACHE_FILE)
            break
        except PermissionError:
            time.sleep(0.1 * (attempt + 1))
    else:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
        try:
            temp_file.unlink(missing_ok=True)
        except Exception:
            pass


def get_secret_key() -> str | None:
    """Read SUPABASE_SECRET_KEY exclusively from scripts/local.toml."""
    local_toml = ROOT / "scripts" / "local.toml"
    if not local_toml.exists():
        return None
    try:
        with open(local_toml, "rb") as f:
            data = tomllib.load(f)
        return data.get("SUPABASE_SECRET_KEY")
    except Exception:
        return None


def calculate_diversity_metrics(profiles: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate pairwise cosine similarities and nearest-neighbor statistics."""
    n = len(profiles)
    if n < 2:
        return {"mean_pairwise": 0.0, "max_pairwise": 0.0, "near_duplicates": []}

    vectors = [p["embedding"] for p in profiles]
    pairwise_similarities: list[float] = []
    nearest_neighbors: list[float] = []
    near_duplicates: list[tuple[str, str, float]] = []

    for i in range(n):
        v1 = vectors[i]
        id1 = profiles[i]["seed_id"]
        max_sim = -1.0

        for j in range(n):
            if i == j:
                continue
            v2 = vectors[j]
            id2 = profiles[j]["seed_id"]
            # Cosine similarity for unit-normalized vectors is dot product
            dot = sum(a * b for a, b in zip(v1, v2))

            if j > i:
                pairwise_similarities.append(dot)
                if dot >= 0.95:
                    near_duplicates.append((id1, id2, round(dot, 4)))

            max_sim = max(max_sim, dot)

        nearest_neighbors.append(max_sim)

    mean_pairwise = sum(pairwise_similarities) / len(pairwise_similarities)
    max_pairwise = max(pairwise_similarities) if pairwise_similarities else 0.0
    mean_nn = sum(nearest_neighbors) / len(nearest_neighbors)

    return {
        "mean_pairwise": round(mean_pairwise, 4),
        "max_pairwise": round(max_pairwise, 4),
        "mean_nearest_neighbor": round(mean_nn, 4),
        "near_duplicates": near_duplicates,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Embed and load synthetic researcher pool")
    parser.add_argument("--dry-run", action="store_true", help="Calculate embeddings and diversity without database write")
    parser.add_argument("--offline", action="store_true", help="Generate mock embeddings deterministically without Gemini API")
    args = parser.parse_args()

    if not SEED_PROFILES_FILE.exists():
        logger.error("seed_profiles.json missing. Run scripts/seed_generate.py first.")
        return 1

    with open(SEED_PROFILES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    profiles = data.get("profiles", [])
    logger.info("Loaded %d profiles from %s", len(profiles), SEED_PROFILES_FILE)

    # Configure Gemini if possible
    use_gemini = False
    if not args.offline:
        try:
            settings = load_local_settings(str(ROOT / ".streamlit" / "secrets.toml"))
            if settings.gemini_api_key:
                configure(settings.gemini_api_key)
                use_gemini = True
                logger.info("Configured Gemini for live embedding generation")
        except Exception:
            pass

    if not use_gemini:
        logger.info("Running embedding generation in deterministic offline mock mode")

    cache = load_embeddings_cache()
    now_stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    for idx, p in enumerate(profiles, 1):
        sid = p["seed_id"]
        text = profile_embedding_text(p)
        ehash = profile_hash(text)

        if sid in cache and cache[sid].get("hash") == ehash and len(cache[sid].get("vector", [])) == EMBEDDING_DIM:
            p["embedding"] = cache[sid]["vector"]
        else:
            logger.info("[%d/%d] Generating embedding for %s (%s)...", idx, len(profiles), sid, p["full_name"])
            if use_gemini:
                try:
                    vec = embed_profile(text)
                    time.sleep(1.0)  # Pacing for rate limits
                except AIUnavailable as exc:
                    logger.warning("Gemini unavailable (%s), using mock vector for %s", exc, sid)
                    vec = mock_embedding(text)
            else:
                vec = mock_embedding(text)

            p["embedding"] = vec
            cache[sid] = {"hash": ehash, "vector": vec, "updated_at": now_stamp}

        p["embedding_hash"] = ehash
        p["embedding_model"] = EMBEDDING_MODEL
        p["embedded_at"] = now_stamp

    save_embeddings_cache(cache)
    logger.info("Embeddings cached: %d entries in %s", len(cache), CACHE_FILE)

    # Calculate diversity
    metrics = calculate_diversity_metrics(profiles)
    print("\n" + "=" * 60)
    print("VECTOR DIVERSITY REPORT (gemini-embedding-2 / 768 dims)")
    print("=" * 60)
    print(f"Total profiles embedded: {len(profiles)}")
    print(f"Mean pairwise cosine similarity: {metrics['mean_pairwise']}")
    print(f"Max pairwise cosine similarity: {metrics['max_pairwise']}")
    print(f"Mean nearest-neighbor cosine similarity: {metrics['mean_nearest_neighbor']}")
    print(f"Near-duplicates (cosine >= 0.95): {len(metrics['near_duplicates'])}")
    if metrics["near_duplicates"]:
        for id1, id2, sim in metrics["near_duplicates"]:
            print(f"  - {id1} <-> {id2}: cosine {sim}")

    if metrics["mean_pairwise"] > 0.8:
        print("WARNING: Mean pairwise cosine similarity > 0.8. Profiles share high text overlap.")
    else:
        print("Vector space distribution: BALANCED (mean cosine <= 0.8)")
    print("=" * 60 + "\n")

    secret_key = get_secret_key()
    if args.dry_run or not secret_key:
        print("Notice: Dry run or SUPABASE_SECRET_KEY missing in scripts/local.toml. Database writes skipped.")
        return 0

    # Live Database Upsert
    try:
        settings = load_local_settings(str(ROOT / ".streamlit" / "secrets.toml"))
        sb_admin = get_admin_client(settings.supabase_url, secret_key)

        # Integrity check: verify seed UUIDs do not collide with non-synthetic rows
        seed_ids = [seed_uuid(p["seed_id"]) for p in profiles]
        res = sb_admin.table("profiles").select("id, is_synthetic").in_("id", seed_ids).execute()
        existing = res.data or []
        for row in existing:
            if not row.get("is_synthetic"):
                logger.error("Seed ID %s collides with a non-synthetic profile! Aborting.", row["id"])
                return 1

        prof_count, cont_count = upsert_seed_profiles(sb_admin, profiles)
        print(f"Database upsert SUCCESS: {prof_count} profiles, {cont_count} contacts.")
        return 0
    except Exception as err:
        logger.error("Database seeding failed: %s", err)
        return 1


if __name__ == "__main__":
    sys.exit(main())
