"""Synthetic researcher profile generation script.

Generates 80 diverse synthetic profiles matching the spec matrix and writes
an atomic, resumable checkpoint to data/seed_profiles.json.

Usage:
    python scripts/seed_generate.py [--offline]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from findings.ai.client import AIUnavailable, configure, generate_structured
from findings.ai.seed_prompt import SEED_SYSTEM_INSTRUCTION, SeedBatchResponse, build_seed_prompt
from findings.core.config import load_local_settings
from findings.services.seed_data import (
    DEMO_PAIRS_META,
    STAGE_QUOTAS,
    build_spec_matrix,
    clean_seed_profile,
    generate_offline_seed_profile,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_generate")

DATA_DIR = ROOT / "data"
OUTPUT_FILE = DATA_DIR / "seed_profiles.json"
BATCH_SIZE = 5
RATE_LIMIT_DELAY_SECONDS = 4.5


def load_checkpoint() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Load existing checkpoint or return blank template.

    Returns (metadata, dict_of_profiles_by_seed_id).
    """
    if not OUTPUT_FILE.exists():
        return {
            "meta": {
                "version": "1.0",
                "count": 0,
                "demo_pairs": DEMO_PAIRS_META,
            },
            "profiles": [],
        }, {}

    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        profiles_by_id = {p["seed_id"]: p for p in data.get("profiles", [])}
        return data, profiles_by_id
    except Exception as err:
        logger.warning("Could not read existing checkpoint (%s), starting fresh", err)
        return {"meta": {"version": "1.0", "demo_pairs": DEMO_PAIRS_META}, "profiles": []}, {}


def save_checkpoint(meta: dict[str, Any], profiles: list[dict[str, Any]]) -> None:
    """Write atomic checkpoint to disk with UTF-8 encoding, handling Windows file locking."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp_file = DATA_DIR / f"seed_profiles.json.{os.getpid()}.tmp"

    payload = {
        "meta": {
            **meta,
            "count": len(profiles),
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "demo_pairs": DEMO_PAIRS_META,
        },
        "profiles": profiles,
    }

    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    for attempt in range(5):
        try:
            os.replace(temp_file, OUTPUT_FILE)
            break
        except PermissionError:
            time.sleep(0.1 * (attempt + 1))
    else:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        try:
            temp_file.unlink(missing_ok=True)
        except Exception:
            pass

    logger.info("Saved checkpoint: %d profiles in %s", len(profiles), OUTPUT_FILE)


def generate_with_gemini(batch_specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Generate batch of profiles using Google Gemini structured output."""
    prompt = build_seed_prompt(batch_specs)
    response: SeedBatchResponse = generate_structured(
        prompt,
        response_schema=SeedBatchResponse,
        system_instruction=SEED_SYSTEM_INSTRUCTION,
    )

    results: list[dict[str, Any]] = []
    spec_map = {s["seed_id"]: s for s in batch_specs}

    for item in response.profiles:
        spec = spec_map.get(item.seed_id)
        if not spec:
            continue
        cleaned = clean_seed_profile(item.model_dump(), spec)
        if cleaned:
            results.append(cleaned)
        else:
            logger.warning("Profile %s failed validation, regenerating offline", item.seed_id)
            results.append(generate_offline_seed_profile(spec))

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate synthetic researcher pool")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Generate synthetic dataset offline deterministically without network calls",
    )
    args = parser.parse_args()

    # Configure Gemini key if present
    gemini_key = None
    try:
        settings = load_local_settings(str(ROOT / ".streamlit" / "secrets.toml"))
        gemini_key = settings.gemini_api_key
    except Exception:
        pass

    use_gemini = False
    if not args.offline and gemini_key:
        try:
            configure(gemini_key)
            use_gemini = True
            logger.info("Configured Gemini for live seed generation")
        except Exception as e:
            logger.warning("Gemini configuration failed (%s), running offline", e)

    if not use_gemini:
        logger.info("Running deterministic offline generation mode")

    specs = build_spec_matrix()
    total_needed = len(specs)
    logger.info("Target dataset: %d specifications", total_needed)

    meta, profiles_by_id = load_checkpoint()
    missing_specs = [s for s in specs if s["seed_id"] not in profiles_by_id]
    logger.info("Profiles existing: %d, missing: %d", len(profiles_by_id), len(missing_specs))

    if not missing_specs:
        logger.info("All %d profiles already present in checkpoint.", total_needed)
    else:
        for i in range(0, len(missing_specs), BATCH_SIZE):
            batch = missing_specs[i : i + BATCH_SIZE]
            batch_ids = [s["seed_id"] for s in batch]
            logger.info("Processing batch [%s]...", ", ".join(batch_ids))

            generated: list[dict[str, Any]] = []
            if use_gemini:
                try:
                    generated = generate_with_gemini(batch)
                    time.sleep(RATE_LIMIT_DELAY_SECONDS)
                except AIUnavailable as e:
                    logger.warning("AI unavailable (%s), falling back to offline generator for batch", e)
                    generated = [generate_offline_seed_profile(s) for s in batch]
                except Exception as exc:
                    logger.warning("Unexpected Gemini batch error (%s), generating offline", exc)
                    generated = [generate_offline_seed_profile(s) for s in batch]
            else:
                generated = [generate_offline_seed_profile(s) for s in batch]

            for p in generated:
                profiles_by_id[p["seed_id"]] = p

            # Save checkpoint after each batch
            ordered_profiles = [profiles_by_id[s["seed_id"]] for s in specs if s["seed_id"] in profiles_by_id]
            save_checkpoint(meta, ordered_profiles)

    # Final verification and report
    final_profiles = [profiles_by_id[s["seed_id"]] for s in specs]
    save_checkpoint(meta, final_profiles)

    stages = Counter(p["career_stage"] for p in final_profiles)
    methods = Counter(p["methods_effective"] for p in final_profiles)
    fields = Counter(p.get("field", "Unknown") for p in specs)

    print("\n" + "=" * 60)
    print("SYNTHETIC RESEARCHER DATASET COMPLETE")
    print("=" * 60)
    print(f"Total profiles: {len(final_profiles)}")
    print(f"Career stages: {dict(stages)}")
    print(f"Methods distribution: {dict(methods)}")
    print(f"Unique fields: {len(fields)}")
    print("Demo pairs:")
    for code, info in DEMO_PAIRS_META.items():
        pair = [p["full_name"] for p in final_profiles if p.get("demo_pair") == code]
        print(f"  [{code}] {info['title']}: {', '.join(pair)}")
    print("=" * 60 + "\n")

    # Assert quotas
    for stage, count in STAGE_QUOTAS.items():
        assert stages[stage] == count, f"Stage {stage} mismatch: {stages[stage]} != {count}"

    return 0


if __name__ == "__main__":
    sys.exit(main())
