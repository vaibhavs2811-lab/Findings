"""Reachability probe of the live Supabase Auth settings (stdlib only, never prints the key)."""

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from findings.core.config import load_local_settings


def main() -> int:
    s = load_local_settings()
    req = urllib.request.Request(
        f"{s.supabase_url}/auth/v1/settings", headers={"apikey": s.supabase_publishable_key}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            status, body = resp.status, json.load(resp)
    except urllib.error.HTTPError as err:
        print(f"FAIL: HTTP {err.code} from /auth/v1/settings")
        return 1
    except Exception as err:
        print(f"FAIL: could not reach Supabase ({type(err).__name__})")
        return 1
    fails = 0
    for ok, label in [
        (status == 200, "HTTP 200"),
        (body.get("external", {}).get("email") is True, "email provider enabled"),
        (body.get("disable_signup") is False, "signups allowed"),
    ]:
        print(("PASS: " if ok else "FAIL: ") + label)
        fails += not ok
    print(
        f"INFO: mailer_autoconfirm = {body.get('mailer_autoconfirm')} "
        "(must be true for instant sign-up after Create account)"
    )
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
