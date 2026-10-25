"""Live read-only check of the chat database objects, using the demo account and the publishable key.

Reports whether the `messages` table and the `my_conversations` / `can_chat` functions exist and are
callable. Never prints keys, tokens or the password. Exit codes: 0 all passed, 1 a check failed,
2 demo credentials missing.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from findings.core.config import load_local_settings
from scripts.check_live import demo_credentials, report
from supabase import create_client


def _why(exc: Exception) -> str:
    return f"{type(exc).__name__}: {str(exc)[:240]}"


def main() -> int:
    email, password = demo_credentials()
    if not email or not password:
        print("SKIP: demo credentials missing")
        return 2
    settings = load_local_settings(str(ROOT / ".streamlit" / "secrets.toml"))
    sb = create_client(settings.supabase_url, settings.supabase_publishable_key)
    sb.auth.sign_in_with_password({"email": email, "password": password})
    ok = True

    try:
        rows = sb.rpc("my_conversations").execute().data or []
        report("C1", True, f"my_conversations returned {len(rows)} conversation(s)")
    except Exception as exc:
        ok = False
        report("C1", False, _why(exc))

    try:
        sb.table("messages").select("id").limit(1).execute()
        report("C2", True, "messages table is readable")
    except Exception as exc:
        ok = False
        report("C2", False, _why(exc))

    try:
        sb.rpc("can_chat", {"p_connection": "00000000-0000-0000-0000-000000000000"}).execute()
        report("C3", True, "can_chat is callable")
    except Exception as exc:
        ok = False
        report("C3", False, _why(exc))

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
