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
from findings.repos.profiles import (
    PROFILE_COLUMNS,
    ProfileWriteError,
    get_own_profile,
    update_own,
)
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


def probe_credentials() -> tuple[str | None, str | None]:
    email = os.environ.get("FINDINGS_PROBE_EMAIL")
    password = os.environ.get("FINDINGS_PROBE_PASSWORD")
    if email and password:
        return email, password
    path = ROOT / "scripts" / "local.toml"
    if path.exists():
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
        return data.get("PROBE_EMAIL"), data.get("PROBE_PASSWORD")
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
    orig_interests = []
    try:
        own_row = get_own_profile(sb, user_id, columns=PROFILE_COLUMNS)
        report("D11", own_row is not None and "interests" in own_row)
        orig_interests = list(own_row.get("interests") or []) if own_row else []
    except Exception as err:
        report("D11", False, f"error {type(err).__name__}")
    try:
        test_interests = orig_interests + ["Findings live check"]
        updated_row = update_own(
            sb, user_id, {"interests": test_interests}, columns=PROFILE_COLUMNS
        )
        report("D12", "Findings live check" in (updated_row.get("interests") or []))
    except Exception as err:
        report("D12", False, f"error {type(err).__name__}")
    finally:
        try:
            restored = update_own(
                sb, user_id, {"interests": orig_interests}, columns=PROFILE_COLUMNS
            )
            report("D13", (restored.get("interests") or []) == orig_interests)
        except Exception as err:
            report("D13", False, f"error {type(err).__name__}")
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


def run_probe(
    url: str,
    key: str,
    demo_email: str,
    demo_password: str,
    probe_email: str,
    probe_password: str,
) -> None:
    demo_client = create_client(url, key)
    probe_client = create_client(url, key)

    try:
        demo_res = demo_client.auth.sign_in_with_password(
            {"email": demo_email, "password": demo_password}
        )
        demo_id = demo_res.user.id
    except Exception as err:
        report("P0-demo-signin", False, f"error {type(err).__name__}")
        return

    try:
        probe_res = probe_client.auth.sign_in_with_password(
            {"email": probe_email, "password": probe_password}
        )
        probe_id = probe_res.user.id
        report("P1", True)
    except Exception as err:
        report("P1", False, f"error {type(err).__name__}")
        return

    try:
        # P2: probe updates its own row
        p2_row = update_own(
            probe_client,
            probe_id,
            {
                "full_name": "RLS probe",
                "career_stage": "PhD",
                "interests": ["RLS probe"],
                "is_complete": True,
            },
        )
        report(
            "P2",
            p2_row is not None
            and p2_row.get("full_name") == "RLS probe"
            and p2_row.get("interests") == ["RLS probe"],
        )

        # P3: demo selects probe row
        rows = demo_client.table("profiles").select("id").eq("id", probe_id).execute().data or []
        report("P3", len(rows) == 1, f"{len(rows)} rows")

        # P4: demo raw update of probe row yields 0 rows
        p4_rows = (
            demo_client.table("profiles")
            .update({"full_name": "hijacked"})
            .eq("id", probe_id)
            .execute()
            .data
            or []
        )
        report("P4", len(p4_rows) == 0, f"{len(p4_rows)} rows")

        # P5: update_own from demo client on probe id raises ProfileWriteError
        try:
            update_own(demo_client, probe_id, {"full_name": "hijacked"})
            report("P5", False, "no error raised")
        except ProfileWriteError:
            report("P5", True)
        except Exception as exc:
            report("P5", False, f"unexpected error {type(exc).__name__}")

        # P6: probe re-reads own row -> still "RLS probe"
        p6_row = get_own_profile(probe_client, probe_id)
        report("P6", p6_row is not None and p6_row.get("full_name") == "RLS probe")

        # P7: updating generated ungranted column raises
        ok, detail = raises(
            lambda: demo_client.table("profiles")
            .update({"methods_effective": "quantitative"})
            .eq("id", demo_id)
            .execute()
        )
        report("P7", ok, detail)

        # P8: inserting random profile raises
        ok, detail = raises(
            lambda: demo_client.table("profiles")
            .insert({"id": str(uuid.uuid4()), "full_name": "attacker"})
            .execute()
        )
        report("P8", ok, detail)

    finally:
        # P9: reset probe is_complete to False
        try:
            p9_row = update_own(probe_client, probe_id, {"is_complete": False})
            report("P9", p9_row is not None and p9_row.get("is_complete") is False)
        except Exception as exc:
            report("P9", False, f"error {type(exc).__name__}")

        try:
            demo_client.auth.sign_out()
        except Exception:
            pass
        try:
            probe_client.auth.sign_out()
        except Exception:
            pass


def run_connections(
    url: str,
    key: str,
    demo_email: str,
    demo_pass: str,
    probe_email: str,
    probe_pass: str,
) -> None:
    demo_client = create_client(url, key)
    probe_client = create_client(url, key)
    try:
        d_auth = demo_client.auth.sign_in_with_password(
            {"email": demo_email, "password": demo_pass}
        )
        demo_id = str(d_auth.user.id)
        p_auth = probe_client.auth.sign_in_with_password(
            {"email": probe_email, "password": probe_pass}
        )
        probe_id = str(p_auth.user.id)
    except Exception as exc:
        print(f"SKIP C0-C14: auth failed ({type(exc).__name__})")
        return

    try:
        # C0: no connections row exists between demo and probe
        c0_res = (
            demo_client.table("connections")
            .select("id")
            .or_(
                f"and(requester_id.eq.{demo_id},recipient_id.eq.{probe_id}),and(requester_id.eq.{probe_id},recipient_id.eq.{demo_id})"
            )
            .execute()
        )
        c0_rows = c0_res.data or []
        if c0_rows:
            report("C0", False, "run scripts/reset_connections.py first")
            return
        report("C0", True)

        # C1: anon rpc my_connections raises
        anon = create_client(url, key)
        ok, detail = raises(lambda: anon.rpc("my_connections").execute())
        report("C1", ok, detail)

        # C2: demo get_contact_email(probe id) is null
        c2_res = demo_client.rpc("get_contact_email", {"other_id": probe_id}).execute()
        report("C2", c2_res.data is None, f"got {c2_res.data}")

        # C3: demo inserts requester demo, recipient probe, note 'probe' -> 1 row pending
        c3_res = (
            demo_client.table("connections")
            .insert({"requester_id": demo_id, "recipient_id": probe_id, "note": "probe"})
            .execute()
        )
        c3_rows = c3_res.data or []
        conn_id = c3_rows[0]["id"] if c3_rows else None
        c3_ok = len(c3_rows) == 1 and c3_rows[0].get("status") == "pending"
        report("C3", c3_ok, f"{len(c3_rows)} rows")

        # C4: demo inserting same pair again raises with code 23505
        try:
            demo_client.table("connections").insert(
                {"requester_id": demo_id, "recipient_id": probe_id, "note": "dup"}
            ).execute()
            report("C4", False, "no error raised")
        except Exception as exc:
            report("C4", getattr(exc, "code", None) == "23505", f"code {getattr(exc, 'code', None)}")

        # C5: probe inserting reverse pair raises with code 23505
        try:
            probe_client.table("connections").insert(
                {"requester_id": probe_id, "recipient_id": demo_id, "note": "rev"}
            ).execute()
            report("C5", False, "no error raised")
        except Exception as exc:
            report("C5", getattr(exc, "code", None) == "23505", f"code {getattr(exc, 'code', None)}")

        # C6: demo inserting with requester_id = probe id raises with code 42501
        try:
            demo_client.table("connections").insert(
                {"requester_id": probe_id, "recipient_id": str(uuid.uuid4())}
            ).execute()
            report("C6", False, "no error raised")
        except Exception as exc:
            report("C6", getattr(exc, "code", None) == "42501", f"code {getattr(exc, 'code', None)}")

        # C7: demo inserting with explicit status accepted raises with code 42501
        try:
            demo_client.table("connections").insert(
                {"requester_id": demo_id, "recipient_id": str(uuid.uuid4()), "status": "accepted"}
            ).execute()
            report("C7", False, "no error raised")
        except Exception as exc:
            report("C7", getattr(exc, "code", None) == "42501", f"code {getattr(exc, 'code', None)}")

        # C8: while pending, get_contact_email is null in both directions
        d_c8 = demo_client.rpc("get_contact_email", {"other_id": probe_id}).execute()
        p_c8 = probe_client.rpc("get_contact_email", {"other_id": demo_id}).execute()
        report("C8", d_c8.data is None and p_c8.data is None)

        # C9: while pending, check my_connections direction and email null
        d_mine = demo_client.rpc("my_connections").execute().data or []
        p_mine = probe_client.rpc("my_connections").execute().data or []
        d_p = next((r for r in d_mine if str(r.get("other_id")) == probe_id), None)
        p_d = next((r for r in p_mine if str(r.get("other_id")) == demo_id), None)
        c9_ok = (
            d_p is not None
            and d_p.get("direction") == "sent"
            and d_p.get("status") == "pending"
            and d_p.get("other_email") is None
            and p_d is not None
            and p_d.get("direction") == "received"
            and p_d.get("other_email") is None
        )
        report("C9", c9_ok)

        # C10: demo updating its own request to accepted returns 0 rows
        c10_res = (
            demo_client.table("connections")
            .update({"status": "accepted"})
            .eq("id", conn_id)
            .execute()
        )
        c10_rows = c10_res.data or []
        c10_read = (
            demo_client.table("connections")
            .select("status")
            .eq("id", conn_id)
            .execute()
            .data
            or []
        )
        report(
            "C10",
            len(c10_rows) == 0 and len(c10_read) == 1 and c10_read[0].get("status") == "pending",
        )

        # C11: probe updating to accepted returns 1 row with status accepted and responded_at
        c11_res = (
            probe_client.table("connections")
            .update({"status": "accepted"})
            .eq("id", conn_id)
            .eq("recipient_id", probe_id)
            .execute()
        )
        c11_rows = c11_res.data or []
        c11_ok = (
            len(c11_rows) == 1
            and c11_rows[0].get("status") == "accepted"
            and c11_rows[0].get("responded_at") is not None
        )
        report("C11", c11_ok)

        # C12: after accept, get_contact_email matches on both sides
        d_c12 = demo_client.rpc("get_contact_email", {"other_id": probe_id}).execute()
        p_c12 = probe_client.rpc("get_contact_email", {"other_id": demo_id}).execute()
        d_mine_12 = demo_client.rpc("my_connections").execute().data or []
        p_mine_12 = probe_client.rpc("my_connections").execute().data or []
        d_row_12 = next((r for r in d_mine_12 if str(r.get("other_id")) == probe_id), None)
        p_row_12 = next((r for r in p_mine_12 if str(r.get("other_id")) == demo_id), None)
        c12_ok = (
            str(d_c12.data or "").lower() == probe_email.lower()
            and str(p_c12.data or "").lower() == demo_email.lower()
            and d_row_12 is not None
            and str(d_row_12.get("other_email") or "").lower() == probe_email.lower()
            and p_row_12 is not None
            and str(p_row_12.get("other_email") or "").lower() == demo_email.lower()
        )
        report("C12", c12_ok)

        # C13: probe changing accepted row to declined raises
        ok, detail = raises(
            lambda: probe_client.table("connections")
            .update({"status": "declined"})
            .eq("id", conn_id)
            .execute()
        )
        report("C13", ok, detail)

        # C14: synthetic recipient auto-accepted
        synth_res = (
            probe_client.table("profiles")
            .select("id")
            .eq("is_synthetic", True)
            .limit(50)
            .execute()
        )
        synth_ids = [str(r["id"]) for r in (synth_res.data or [])]
        if not synth_ids:
            report("C14", False, "no synthetic profiles - load Phase 3 seed")
        else:
            p_existing = {str(r.get("other_id")) for r in p_mine_12}
            pick_id = next((sid for sid in synth_ids if sid not in p_existing), synth_ids[0])
            ins_synth = (
                probe_client.table("connections")
                .insert({"requester_id": probe_id, "recipient_id": pick_id, "note": "synth probe"})
                .execute()
            )
            s_rows = ins_synth.data or []
            s_cid = s_rows[0]["id"] if s_rows else None
            s_read = (
                probe_client.table("connections")
                .select("status, responded_at")
                .eq("id", s_cid)
                .execute()
                .data
                or []
            )
            s_email = str(
                probe_client.rpc("get_contact_email", {"other_id": pick_id}).execute().data or ""
            )
            p_mine_synth = probe_client.rpc("my_connections").execute().data or []
            s_mine_row = next((r for r in p_mine_synth if str(r.get("other_id")) == pick_id), None)
            c14_ok = (
                len(s_read) == 1
                and s_read[0].get("status") == "accepted"
                and s_read[0].get("responded_at") is not None
                and s_email.endswith("@example.org")
                and s_mine_row is not None
                and s_mine_row.get("other_is_synthetic") is True
            )
            report("C14", c14_ok)
    finally:
        try:
            demo_client.auth.sign_out()
        except Exception:
            pass
        try:
            probe_client.auth.sign_out()
        except Exception:
            pass


def main() -> int:
    settings = load_local_settings(str(ROOT / ".streamlit" / "secrets.toml"))
    url, key = settings.supabase_url, settings.supabase_publishable_key
    run_anon(url, key)
    email, password = demo_credentials()
    if not (email and password):
        print("SKIP: no demo credentials, D1-D10 not run (set scripts/local.toml or env vars)")
        print(f"{RESULTS['passed']} passed, {RESULTS['failed']} failed")
        return 2
    run_demo(url, key, email, password)

    probe_email, probe_password = probe_credentials()
    if not (probe_email and probe_password):
        print("SKIP: no probe credentials, P1-P9 and C0-C14 not run (set scripts/local.toml or env vars)")
        print(f"{RESULTS['passed']} passed, {RESULTS['failed']} failed")
        return 2 if not RESULTS["failed"] else 1

    run_probe(url, key, email, password, probe_email, probe_password)
    run_connections(url, key, email, password, probe_email, probe_password)
    print(f"{RESULTS['passed']} passed, {RESULTS['failed']} failed")
    return 1 if RESULTS["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())


