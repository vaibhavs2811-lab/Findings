"""Smoke verification script for Discover queries and public profile projections.

Runs verification checks against the Supabase database using only the publishable key.
Exit codes: 0 all passed, 1 any failure, 2 unconfigured.
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from findings.core.config import load_local_settings
from findings.repos.profiles import CARD_COLUMNS, PUBLIC_PROFILE_COLUMNS, get_public, list_public
from supabase import create_client

RESULTS = {"passed": 0, "failed": 0}


def report(check_id: str, ok: bool, detail: str = "") -> None:
    RESULTS["passed" if ok else "failed"] += 1
    print(f"{'PASS' if ok else 'FAIL'} {check_id}" + (f" - {detail}" if detail else ""))


def demo_credentials() -> tuple[str | None, str | None]:
    email = os.environ.get("FINDINGS_DEMO_EMAIL")
    password = os.environ.get("FINDINGS_DEMO_PASSWORD")
    if email and password:
        return email, password
    path = ROOT / "scripts" / "local.toml"
    if path.exists():
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
        return data.get("DEMO_EMAIL"), data.get("DEMO_PASSWORD")
    return None, None


def main() -> int:
    # C5: CARD_COLUMNS & PUBLIC_PROFILE_COLUMNS contain no star or email (offline check)
    c_tokens = [c.strip() for c in CARD_COLUMNS.split(",")]
    p_tokens = [c.strip() for c in PUBLIC_PROFILE_COLUMNS.split(",")]
    ok_cols = (
        "*" not in c_tokens
        and "*" not in p_tokens
        and not any("email" in t for t in c_tokens)
        and not any("email" in t for t in p_tokens)
    )
    report("C5", ok_cols, "Column constants are explicit and free of private fields")

    # C3: SQL Injection defense on get_public (offline UUID check)
    try:
        res = get_public(None, "1; drop table profiles;")
        report("C3", res is None, "SQL injection safely rejected by UUID validator")
    except Exception as exc:
        report("C3", False, f"error {type(exc).__name__}")

    try:
        settings = load_local_settings(str(ROOT / ".streamlit" / "secrets.toml"))
        url, key = settings.supabase_url, settings.supabase_publishable_key
    except Exception as exc:
        print(f"SKIP: Secrets not configured ({exc})")
        return 2

    email, password = demo_credentials()
    if not (email and password):
        print("SKIP: no demo credentials, live queries (C1, C2, C4) not run (set scripts/local.toml or env vars)")
        print(f"{RESULTS['passed']} passed, {RESULTS['failed']} failed")
        return 2

    sb = create_client(url, key)
    try:
        sb.auth.sign_in_with_password({"email": email, "password": password})
    except Exception as exc:
        print(f"SKIP: demo sign-in failed ({exc})")
        return 2

    try:
        # C1: List public profiles
        try:
            profiles = list_public(sb)
            report("C1", isinstance(profiles, list), f"{len(profiles)} profiles returned")
        except Exception as exc:
            report("C1", False, f"error {type(exc).__name__}")
            profiles = []

        # C2: Column hygiene on returned profiles
        try:
            forbidden = False
            for p in profiles:
                for k in ("email", "embedding", "embedding_hash", "methods_hash"):
                    if k in p:
                        forbidden = True
                        break
            report("C2", not forbidden, "No private/heavy columns exposed in list_public")
        except Exception as exc:
            report("C2", False, f"error {type(exc).__name__}")

        # C4: Random non-existent UUID returns None
        try:
            res = get_public(sb, str(uuid.uuid4()))
            report("C4", res is None, "Random UUID returned None")
        except Exception as exc:
            report("C4", False, f"error {type(exc).__name__}")
    finally:
        try:
            sb.auth.sign_out()
        except Exception:
            pass

    print("\n" + "=" * 40)
    print(f"DISCOVER SMOKE: {RESULTS['passed']} passed, {RESULTS['failed']} failed")
    print("=" * 40)

    return 1 if RESULTS["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
