"""Live verification script for Phase 4 AI Peer Matching and pgvector RPC.

Credentials: env FINDINGS_DEMO_EMAIL / FINDINGS_DEMO_PASSWORD, else scripts/local.toml
(keys DEMO_EMAIL / DEMO_PASSWORD). Never prints keys, tokens or passwords.
Exit codes: 0 all passed, 1 any failure, 2 demo credentials missing / unconfigured.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from findings.core.config import load_local_settings
from findings.repos import profiles
from findings.services import matching
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
    try:
        settings = load_local_settings(str(ROOT / ".streamlit" / "secrets.toml"))
        url, key = settings.supabase_url, settings.supabase_publishable_key
    except Exception as exc:
        print(f"SKIP: Secrets not configured ({exc})")
        return 2

    # M1: anon rpc match_profiles raises or returns 0 rows
    try:
        anon = create_client(url, key)
        res = anon.rpc("match_profiles", {"mode": "peer"}).execute()
        rows = res.data or []
        report("M1", len(rows) == 0, f"{len(rows)} rows returned to anon")
    except Exception as exc:
        report("M1", True, f"anon access rejected ({type(exc).__name__})")

    email, password = demo_credentials()
    if not (email and password):
        print("SKIP: no demo credentials, M2-M7 not run (set scripts/local.toml or env vars)")
        print(f"{RESULTS['passed']} passed, {RESULTS['failed']} failed")
        return 2

    sb = create_client(url, key)
    try:
        auth_res = sb.auth.sign_in_with_password({"email": email, "password": password})
        demo_id = auth_res.user.id
    except Exception as exc:
        print(f"SKIP: demo sign-in failed ({exc})")
        return 2

    try:
        # M2: demo signs in, and its own profile is complete
        own_prof = profiles.get_own_profile(sb, demo_id)
        is_complete = bool(own_prof and own_prof.get("is_complete"))
        report("M2", is_complete, "demo profile is complete" if is_complete else "FAIL: complete demo profile in app")
        if not is_complete:
            print("\n" + "=" * 40)
            print(f"MATCHING SMOKE: {RESULTS['passed']} passed, {RESULTS['failed']} failed")
            print("=" * 40)
            return 1

        # M3: ensure_embedding returns updated or unchanged, and an immediate second call returns unchanged
        st1 = matching.ensure_embedding(sb, demo_id, own_prof)
        st2 = matching.ensure_embedding(sb, demo_id, own_prof)
        report(
            "M3",
            st1 in ("updated", "unchanged") and st2 == "unchanged",
            f"call 1: {st1}, call 2: {st2}",
        )

        # M4: the raw profiles.match_profiles returns between 5 and 15 rows with non-increasing similarity
        raw_rows = profiles.match_profiles(sb, match_count=15, exclude_ids=[demo_id], mode="peer")
        non_increasing = True
        for i in range(len(raw_rows) - 1):
            if float(raw_rows[i].get("similarity", 0.0)) < float(raw_rows[i + 1].get("similarity", 0.0)):
                non_increasing = False
                break
        report(
            "M4",
            5 <= len(raw_rows) <= 15 and non_increasing,
            f"{len(raw_rows)} rows returned (sorted: {non_increasing})",
        )

        # M5: no row id equals demo id or any connection counterpart
        c_res = sb.table("connections").select("requester_id, recipient_id").execute()
        c_rows = c_res.data or []
        forbidden_ids = {demo_id}
        for r in c_rows:
            if r.get("requester_id"):
                forbidden_ids.add(r["requester_id"])
            if r.get("recipient_id"):
                forbidden_ids.add(r["recipient_id"])

        no_overlap = not any(r.get("id") in forbidden_ids for r in raw_rows)
        report("M5", no_overlap, "No self or connected profiles in shortlist")

        # M6: no returned key contains 'email', and no key equals 'embedding'
        forbidden_keys = False
        for r in raw_rows:
            for k in r:
                if "email" in k or k == "embedding":
                    forbidden_keys = True
                    break
        report("M6", not forbidden_keys, "No private email or vector embedding keys exposed")

        # M7: matching.get_matches returns 5 or more items, each with a non-empty strength and why
        res = matching.get_matches(sb, demo_id, mode="peer")
        m7_ok = len(res.items) >= 5 and all(
            bool(item.get("strength")) and bool(item.get("why")) for item in res.items
        )
        report("M7", m7_ok, f"{len(res.items)} matches with strength and why")

    finally:
        try:
            sb.auth.sign_out()
        except Exception:
            pass

    print("\n" + "=" * 40)
    print(f"MATCHING SMOKE: {RESULTS['passed']} passed, {RESULTS['failed']} failed")
    print("=" * 40)

    return 1 if RESULTS["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
