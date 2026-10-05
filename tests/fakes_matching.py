"""Fake Supabase client with table queries and match_profiles RPC support for Phase 4 tests.

Subclasses tests.fakes.FakeSupabase without modifying existing fake infrastructure.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from tests.fakes import FakeSupabase


class FakeTable:
    """In-memory chainable table mock supporting CRUD, projections and filters."""

    def __init__(self, parent: FakeMatchingSupabase, name: str):
        self.parent = parent
        self.name = name
        self.selected_cols: list[str] | None = None
        self.filters: list[tuple[str, str, Any]] = []
        self.limit_val: int | None = None
        self.pending_update: dict[str, Any] | None = None
        self.pending_upsert: dict[str, Any] | None = None
        self.on_conflict: str | None = None
        self.is_delete = False

    def select(self, cols: str = "*"):
        self.parent.log.append((self.name, "select", cols))
        if cols != "*":
            self.selected_cols = [c.strip() for c in cols.split(",")]
        return self

    def eq(self, col: str, val: Any):
        self.parent.log.append((self.name, "eq", (col, val)))
        self.filters.append(("eq", col, val))
        return self

    def in_(self, col: str, vals: Any):
        self.parent.log.append((self.name, "in_", (col, vals)))
        self.filters.append(("in_", col, list(vals)))
        return self

    def limit(self, n: int):
        self.parent.log.append((self.name, "limit", n))
        self.limit_val = n
        return self

    def order(self, col: str, **kwargs):
        self.parent.log.append((self.name, "order", col))
        return self

    def update(self, payload: dict[str, Any]):
        self.parent.log.append((self.name, "update", payload))
        self.pending_update = dict(payload)
        return self

    def upsert(self, payload: dict[str, Any], on_conflict: str | None = None):
        self.parent.log.append((self.name, "upsert", payload))
        self.pending_upsert = dict(payload)
        self.on_conflict = on_conflict
        return self

    def delete(self):
        self.parent.log.append((self.name, "delete", None))
        self.is_delete = True
        return self

    def _match(self, row: dict[str, Any]) -> bool:
        for op, col, val in self.filters:
            if op == "eq":
                if row.get(col) != val:
                    return False
            elif op == "in_" and row.get(col) not in val:
                return False
        return True

    def _project(self, row: dict[str, Any]) -> dict[str, Any]:
        if not self.selected_cols:
            return dict(row)
        return {k: row.get(k) for k in self.selected_cols}

    def execute(self):
        if self.name in self.parent.table_errors:
            raise self.parent.table_errors[self.name]

        table_rows = self.parent.tables.setdefault(self.name, [])

        if self.pending_upsert is not None:
            conflict = self.on_conflict
            if not conflict:
                conflict = "id" if self.name == "profiles" else "user_id,mode"
            keys = [k.strip() for k in conflict.split(",")]

            found_idx = None
            for idx, r in enumerate(table_rows):
                if all(r.get(k) == self.pending_upsert.get(k) for k in keys):
                    found_idx = idx
                    break

            if found_idx is not None:
                table_rows[found_idx].update(self.pending_upsert)
                ret = [dict(table_rows[found_idx])]
            else:
                table_rows.append(dict(self.pending_upsert))
                ret = [dict(self.pending_upsert)]
            return SimpleNamespace(data=ret)

        if self.pending_update is not None:
            updated = []
            for r in table_rows:
                if self._match(r):
                    r.update(self.pending_update)
                    updated.append(self._project(r))
            return SimpleNamespace(data=updated)

        if self.is_delete:
            remaining = []
            deleted = []
            for r in table_rows:
                if self._match(r):
                    deleted.append(r)
                else:
                    remaining.append(r)
            self.parent.tables[self.name] = remaining
            return SimpleNamespace(data=deleted)

        matched = [self._project(r) for r in table_rows if self._match(r)]
        if self.limit_val is not None:
            matched = matched[: self.limit_val]
        return SimpleNamespace(data=matched)


class FakeMatchingSupabase(FakeSupabase):
    """Fake Supabase client with in-memory tables and match_profiles RPC support."""

    def __init__(self, initial_profile: dict[str, Any] | None = None):
        super().__init__()
        self.tables: dict[str, list[dict[str, Any]]] = {
            "profiles": [dict(initial_profile)] if initial_profile else [],
            "match_cache": [],
            "connections": [],
        }
        self.rpc_rows: list[dict[str, Any]] = []
        self.rpc_error: Exception | None = None
        self.rpc_calls: list[tuple[str, dict[str, Any]]] = []
        self.log: list[tuple[str, str, Any]] = []
        self.table_errors: dict[str, Exception] = {}

    def table(self, name: str) -> FakeTable:
        return FakeTable(self, name)

    def rpc(self, name: str, params: dict[str, Any] | None = None):
        p = dict(params or {})
        self.rpc_calls.append((name, p))

        class _RpcCall:
            def __init__(inner):
                inner.parent = self

            def execute(inner):
                if inner.parent.rpc_error is not None:
                    raise inner.parent.rpc_error
                return SimpleNamespace(data=list(inner.parent.rpc_rows))

        return _RpcCall()
