"""Live RLS / privacy probe using only the publishable key (anon + demo user).

Credentials: env FINDINGS_DEMO_EMAIL / FINDINGS_DEMO_PASSWORD, else scripts/local.toml
(keys DEMO_EMAIL / DEMO_PASSWORD). Never prints keys, tokens or the password.
Exit codes: 0 all passed, 1 any failure, 2 demo credentials missing.
"""

import os
import sys
import uuid
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from findings.core.config import load_local_settings
from supabase import create_client

RESULTS = {"passed": 0, "failed": 0}


def report(check_id: str, ok: bool, detail: str = "") -> None:
    RESULTS["passed" if ok else "failed"] += 1
    print(f"{'PASS' if ok else 'FAIL'} {check_id}" + (f" - {detail}" if detail else ""))


def denied_or_empty(fn) -> tuple[bool, str]:
    """True when the call raises (permission error) or returns no rows."""
    try:
        res = fn()
    except Exception as err:
        return True, f"error {type(err).__name__}"
    rows = res.data or []
    return len(rows) == 0, f"{len(rows)} rows"


def raises(fn) -> tuple[bool, str]:
    try:
        fn()
    except Exception as err:
        return True, f"error {type(err).__name__}"
    return False, "no error raised"


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


def run_anon(url: str, key: str) -> None:
    anon = create_client(url, key)
    try:
        rows = anon.table("keepalive").select("*").execute().data or []
        report("A1", len(rows) == 1, f"{len(rows)} rows")
    except Exception as err:
        report("A1", False, f"error {type(err).__name__}")
    ok, detail = denied_or_empty(lambda: anon.table("profiles").select("id").execute())
    report("A2", ok, detail)
    ok, detail = denied_or_empty(lambda: anon.table("profile_contacts").select("*").execute())
    report("A3", ok, detail)
    ok, detail = raises(
        lambda: anon.rpc("get_contact_email", {"p_profile": str(uuid.uuid4())}).execute()
    )
    report("A4", ok, detail)


def run_demo(url: str, key: str, email: str, password: str) -> None:
    sb = create_client(url, key)
    try:
        res = sb.auth.sign_in_with_password({"email": email, "password": password})
        user_id = res.user.id
        report("D1", True)
    except Exception as err:
        report("D1", False, f"error {type(err).__name__}")
        return
    try:
        rows = sb.table("profiles").select("id").eq("id", user_id).execute().data or []
        report("D2", len(rows) == 1, f"{len(rows)} rows")
    except Exception as err:
        report("D2", False, f"error {type(err).__name__}")
    try:
        stamp = "2026-01-01T00:00:00+00:00"
        rows = sb.table("profiles").update({"updated_at": stamp}).eq("id", user_id).execute().data
        report("D3", len(rows or []) == 1, f"{len(rows or [])} rows")
    except Exception as err:
        report("D3", False, f"error {type(err).__name__}")
    try:
        other = str(uuid.uuid4())
        rows = sb.table("profiles").update({"full_name": "x"}).eq("id", other).execute().data
        report("D4", len(rows or []) == 0, f"{len(rows or [])} rows")
    except Exception as err:
        report("D4", False, f"error {type(err).__name__}")
    ok, detail = raises(
        lambda: sb.table("profiles").update({"is_synthetic": True}).eq("id", user_id).execute()
    )
    report("D5", ok, detail)
    ok, detail = denied_or_empty(lambda: sb.table("profile_contacts").select("*").execute())
    report("D6", ok, detail)
    try:
        got = sb.rpc("get_contact_email", {"p_profile": user_id}).execute().data
        report("D7", isinstance(got, str) and got.lower() == email.lower())
    except Exception as err:
        report("D7", False, f"error {type(err).__name__}")
    try:
        got = sb.rpc("get_contact_email", {"p_profile": str(uuid.uuid4())}).execute().data
        report("D8", got is None, "null" if got is None else "returned a value")
    except Exception as err:
        report("D8", False, f"error {type(err).__name__}")
    try:
        rows = sb.table("connections").select("id").execute().data or []
        report("D9", len(rows) == 0, f"{len(rows)} rows")
    except Exception as err:
        report("D9", False, f"error {type(err).__name__}")
    try:
        sb.auth.sign_out()
        report("D10", True)
    except Exception as err:
        report("D10", False, f"error {type(err).__name__}")


def main() -> int:
    settings = load_local_settings(str(ROOT / ".streamlit" / "secrets.toml"))
    url, key = settings.supabase_url, settings.supabase_publishable_key
    run_anon(url, key)
    email, password = demo_credentials()
    if not (email and password):
        print("SKIP D1-D10: demo credentials missing (set scripts/local.toml or env vars)")
        print(f"{RESULTS['passed']} passed, {RESULTS['failed']} failed")
        return 2
    run_demo(url, key, email, password)
    print(f"{RESULTS['passed']} passed, {RESULTS['failed']} failed")
    return 1 if RESULTS["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
