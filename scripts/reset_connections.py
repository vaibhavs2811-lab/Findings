"""Reset connections involving demo and probe test accounts.

Local-only maintenance script. Never imported by the application.
Requires DEMO_EMAIL/PASSWORD, PROBE_EMAIL/PASSWORD and SUPABASE_SECRET_KEY in scripts/local.toml.
Never prints keys, tokens or passwords.
Exit codes: 0 success, 1 error, 2 missing credentials / unconfigured.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import tomllib

from supabase import create_client

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from findings.core.config import load_local_settings


def load_credentials() -> dict[str, str | None]:
    """Load credentials from environment variables or scripts/local.toml."""
    creds: dict[str, str | None] = {
        "demo_email": os.environ.get("FINDINGS_DEMO_EMAIL"),
        "demo_pass": os.environ.get("FINDINGS_DEMO_PASSWORD"),
        "probe_email": os.environ.get("FINDINGS_PROBE_EMAIL"),
        "probe_pass": os.environ.get("FINDINGS_PROBE_PASSWORD"),
        "secret_key": os.environ.get("SUPABASE_SECRET_KEY"),
    }

    local_toml = ROOT / "scripts" / "local.toml"
    if local_toml.exists():
        try:
            with open(local_toml, "rb") as f:
                data = tomllib.load(f)
            creds["demo_email"] = creds["demo_email"] or data.get("DEMO_EMAIL")
            creds["demo_pass"] = creds["demo_pass"] or data.get("DEMO_PASSWORD")
            creds["probe_email"] = creds["probe_email"] or data.get("PROBE_EMAIL")
            creds["probe_pass"] = creds["probe_pass"] or data.get("PROBE_PASSWORD")
            creds["secret_key"] = creds["secret_key"] or data.get("SUPABASE_SECRET_KEY")
        except Exception:
            pass

    return creds


def main() -> int:
    try:
        settings = load_local_settings(str(ROOT / ".streamlit" / "secrets.toml"))
        url, pub_key = settings.supabase_url, settings.supabase_publishable_key
    except Exception as exc:
        print(f"SKIP: Secrets not configured ({exc})")
        return 2

    creds = load_credentials()
    demo_email = creds["demo_email"]
    demo_pass = creds["demo_pass"]
    probe_email = creds["probe_email"]
    probe_pass = creds["probe_pass"]
    secret_key = creds["secret_key"]

    if not (demo_email and demo_pass and probe_email and probe_pass and secret_key):
        print(
            "SKIP: Missing DEMO_EMAIL, PROBE_EMAIL, or SUPABASE_SECRET_KEY in scripts/local.toml or env."
        )
        return 2

    # Secret key prefix verification
    valid_prefixes = ("sb_secret_", "eyJ")
    if not any(secret_key.startswith(p) for p in valid_prefixes):
        print("SKIP: SUPABASE_SECRET_KEY does not start with a valid secret key prefix.")
        return 2

    # Resolve demo and probe user IDs via standard publishable client
    sb_pub = create_client(url, pub_key)
    try:
        demo_auth = sb_pub.auth.sign_in_with_password(
            {"email": demo_email, "password": demo_pass}
        )
        demo_id = str(demo_auth.user.id)
        sb_pub.auth.sign_out()
    except Exception as exc:
        print(f"ERROR: Could not authenticate demo account ({type(exc).__name__})")
        return 1

    try:
        probe_auth = sb_pub.auth.sign_in_with_password(
            {"email": probe_email, "password": probe_pass}
        )
        probe_id = str(probe_auth.user.id)
        sb_pub.auth.sign_out()
    except Exception as exc:
        print(f"ERROR: Could not authenticate probe account ({type(exc).__name__})")
        return 1

    if demo_id == probe_id:
        print("ERROR: Demo and probe accounts resolved to the same user ID.")
        return 1

    # Connect with secret key to delete connections involving only demo and probe
    try:
        sb_admin = create_client(url, secret_key)
        # Delete any rows where requester_id in (demo, probe) or recipient_id in (demo, probe)
        res = (
            sb_admin.table("connections")
            .delete()
            .or_(
                f"requester_id.in.({demo_id},{probe_id}),recipient_id.in.({demo_id},{probe_id})"
            )
            .execute()
        )
        deleted_count = len(res.data or [])
        print(f"deleted {deleted_count} connection rows (demo + probe accounts only)")
        return 0
    except Exception as exc:
        print(f"ERROR: Database deletion failed ({type(exc).__name__})")
        return 1


if __name__ == "__main__":
    sys.exit(main())
