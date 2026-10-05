"""Tests for supabase/schema.sql structure, security grants, and Phase 2 additions."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "supabase" / "schema.sql"


def test_schema_sql_grants_and_phase2_section():
    content = SCHEMA_PATH.read_text(encoding="utf-8")

    # 1. Find all update grants on profiles to authenticated
    pattern = r"grant\s+update\s*\(([^)]+)\)\s*on\s+public\.profiles\s+to\s+authenticated;"
    matches = list(re.finditer(pattern, content, re.DOTALL | re.IGNORECASE))
    assert len(matches) >= 2, f"Expected at least 2 grant update blocks, found {len(matches)}"

    # First grant (section 8)
    sec8_cols = {c.strip() for c in matches[0].group(1).split(",")}
    forbidden = {"methods_effective", "stage_tier", "id", "is_synthetic", "created_at"}
    for col in forbidden:
        assert col not in sec8_cols, f"Forbidden column {col} found in section 8 grant list"

    # Second grant (section 10 / Phase 2)
    phase2_cols = {c.strip() for c in matches[1].group(1).split(",")}
    assert phase2_cols == {"methods_hash", "methods_reason"}

    # Offset assertions
    revoke_offset = content.find("revoke update on public.profiles from authenticated")
    assert revoke_offset != -1
    assert matches[1].start() > revoke_offset

    # Check ALTER table statements
    assert "alter table public.profiles add column if not exists methods_hash text;" in content
    assert (
        "alter table public.profiles add column if not exists methods_reason text check (char_length(methods_reason) <= 300);"
        in content
    )

    # Check profiles_update policy
    assert "using (id = (select auth.uid()))" in content
    assert "is_synthetic = false" in content

    # Check notify pgrst after phase 2 grant
    notify_offset = content.rfind("notify pgrst, 'reload schema';")
    assert notify_offset > matches[1].start()
