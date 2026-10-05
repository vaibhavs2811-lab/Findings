"""Static analysis tests for Phase 5 connections SQL rules, security constraints, and layering."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_FILE = ROOT / "supabase" / "schema.sql"


def test_schema_section_10_present():
    content = SCHEMA_FILE.read_text(encoding="utf-8")
    assert "-- 10. Phase 5: connections" in content

    # Check it appears after get_contact_email
    pos_email = content.find("get_contact_email")
    pos_sec10 = content.find("-- 10. Phase 5: connections")
    assert pos_email != -1
    assert pos_sec10 > pos_email


def test_my_connections_rpc_security_and_gating():
    content = SCHEMA_FILE.read_text(encoding="utf-8")

    # Match my_connections function body
    match = re.search(
        r"create or replace function public\.my_connections\(\).*?\$\$(.*?)\$\$;",
        content,
        re.DOTALL,
    )
    assert match is not None, "my_connections function not found"
    full_def = match.group(0)
    body = match.group(1)

    assert "security definer" in full_def
    assert "set search_path = ''" in full_def
    assert "auth.uid()" in body
    assert "public.get_contact_email(" in body
    assert "profile_contacts" not in body  # Must NOT directly read private contacts table

    # Permissions
    assert re.search(
        r"revoke execute on function public\.my_connections\(\) from public, anon;",
        content,
    )
    assert re.search(
        r"grant execute on function public\.my_connections\(\) to authenticated;",
        content,
    )


def test_auto_accept_synthetic_trigger_and_permissions():
    content = SCHEMA_FILE.read_text(encoding="utf-8")

    match = re.search(
        r"create or replace function public\.auto_accept_synthetic\(\).*?\$\$(.*?)\$\$;",
        content,
        re.DOTALL,
    )
    assert match is not None, "auto_accept_synthetic function not found"
    full_def = match.group(0)
    body = match.group(1)

    assert "security definer" in full_def
    assert "set search_path = ''" in full_def
    assert "is_synthetic" in body
    assert "status = 'accepted'" in body

    # Trigger attachment
    assert "create trigger auto_accept_synthetic" in content
    assert "after insert on public.connections" in content

    # Trigger execution revoked from all roles
    assert re.search(
        r"revoke execute on function public\.auto_accept_synthetic\(\) from public, anon, authenticated;",
        content,
    )


def test_connections_insert_column_grant_and_phase1_invariants():
    content = SCHEMA_FILE.read_text(encoding="utf-8")

    assert (
        "grant insert (requester_id, recipient_id, note) on public.connections to authenticated;"
        in content
    )
    assert "grant update (status) on public.connections" in content

    # Phase 1 connections_insert policy checks status = 'pending'
    assert "connections_insert" in content
    assert "status = 'pending'" in content

    # No create policy targets private profile_contacts
    assert not re.search(
        r"create policy .*? on public\.profile_contacts",
        content,
        re.IGNORECASE,
    )


def test_connections_layering_and_no_secrets_in_app():
    # 1. No streamlit in connection repo or service
    repo_text = (ROOT / "findings" / "repos" / "connections.py").read_text(encoding="utf-8")
    service_text = (ROOT / "findings" / "services" / "connection_service.py").read_text(encoding="utf-8")
    assert "import streamlit" not in repo_text
    assert "import streamlit" not in service_text

    # 2. No st.cache_data or st.cache_resource on connection files
    btn_text = (ROOT / "ui" / "connect_button.py").read_text(encoding="utf-8")
    view_text = (ROOT / "views" / "connections.py").read_text(encoding="utf-8")
    for txt in (repo_text, service_text, btn_text, view_text):
        assert "@st.cache" not in txt

    # 3. No secret key names or prefixes in app, views, ui, findings
    app_dirs = [ROOT / "app.py", ROOT / "findings", ROOT / "views", ROOT / "ui"]
    for item in app_dirs:
        if item.is_file():
            files = [item]
        else:
            files = list(item.rglob("*.py"))
        for f in files:
            t = f.read_text(encoding="utf-8")
            assert "SUPABASE_SECRET_KEY" not in t, f"Found secret key name in {f}"
            assert "sb_secret_" not in t, f"Found secret key prefix in {f}"
