"""Fake Supabase client with profiles table mutation support for Phase 2 tests.

Subclasses FakeSupabase; never edit tests/fakes.py directly.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from tests.fakes import FakeSupabase


class ProfilesQuery:
    def __init__(self, parent: FakeProfilesSupabase, table_name: str):
        self.parent = parent
        self.table_name = table_name
        self.pending_update: dict[str, Any] | None = None
        self.eq_filter: tuple[str, Any] | None = None
        self.selected_cols: str | None = None

    def select(self, cols: str = "*"):
        self.selected_cols = cols
        self.parent.log.append(("select", cols))
        return self

    def eq(self, col: str, val: Any):
        self.eq_filter = (col, val)
        self.parent.log.append(("eq", (col, val)))
        return self

    def limit(self, n: int):
        self.parent.log.append(("limit", n))
        return self

    def update(self, payload: dict[str, Any]):
        self.pending_update = dict(payload)
        self.parent.log.append(("update", payload))
        return self

    def execute(self):
        if self.parent.boom:
            raise self.parent.boom
        if self.parent.zero_rows:
            return SimpleNamespace(data=[])

        if self.table_name == "profiles":
            if self.pending_update is not None:
                if self.eq_filter:
                    col, val = self.eq_filter
                    if self.parent.row.get(col) == val:
                        self.parent.row.update(self.pending_update)
                        override = self.parent.row.get("methods_override")
                        suggested = self.parent.row.get("methods_suggested")
                        self.parent.row["methods_effective"] = override or suggested
                        return SimpleNamespace(data=[dict(self.parent.row)])
                    return SimpleNamespace(data=[])
                self.parent.row.update(self.pending_update)
                return SimpleNamespace(data=[dict(self.parent.row)])

            if self.eq_filter:
                col, val = self.eq_filter
                if self.parent.row.get(col) == val:
                    return SimpleNamespace(data=[dict(self.parent.row)])
                return SimpleNamespace(data=[])

            return SimpleNamespace(data=[dict(self.parent.row)])

        return SimpleNamespace(data=[])


class FakeProfilesSupabase(FakeSupabase):
    def __init__(
        self,
        row: dict[str, Any] | None = None,
        boom: Exception | None = None,
        zero_rows: bool = False,
    ):
        super().__init__()
        self.log: list[tuple[str, Any]] = []
        self.boom = boom
        self.zero_rows = zero_rows

        default_row = {
            "id": "user-1",
            "full_name": "",
            "career_stage": None,
            "institution": None,
            "education": None,
            "experience": None,
            "bio": None,
            "looking_for": None,
            "interests": [],
            "skills": [],
            "offers": [],
            "needs": [],
            "contributable_skills": [],
            "want_to_learn": [],
            "seeking_mentor": False,
            "open_to_mentoring": False,
            "methods_suggested": None,
            "methods_override": None,
            "methods_effective": None,
            "stage_tier": None,
            "is_synthetic": False,
            "is_complete": False,
            "methods_hash": None,
            "methods_reason": None,
            "created_at": "2026-10-05T10:00:00+00:00",
            "updated_at": "2026-10-05T10:00:00+00:00",
        }
        if row is not None:
            default_row.update(row)
        self.row = default_row

    def table(self, name: str):
        self.log.append(("table", name))
        return ProfilesQuery(self, name)
