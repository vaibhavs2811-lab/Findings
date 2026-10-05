"""Stateful multi-user ConnectionsFake and ConnectionStore for Phase 5 tests.

Subclasses tests.fakes.FakeSupabase without modifying existing fake infrastructure.
Imitates PostgreSQL / Supabase RLS and trigger semantics for connections.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

from postgrest.exceptions import APIError as PostgrestAPIError

from tests.fakes import FakeSupabase


class ConnectionStore:
    """In-memory database store shared across simulated user sessions."""

    def __init__(self) -> None:
        self.profiles: dict[str, dict[str, Any]] = {}
        self.contacts: dict[str, str] = {}
        self.connections: list[dict[str, Any]] = []

    def add_profile(
        self,
        pid: str,
        full_name: str,
        career_stage: str = "PhD",
        email: str = "",
        is_synthetic: bool = False,
        is_complete: bool = True,
    ) -> None:
        """Register profile and contact record in shared store."""
        self.profiles[str(pid)] = {
            "id": str(pid),
            "full_name": full_name,
            "career_stage": career_stage,
            "is_synthetic": is_synthetic,
            "is_complete": is_complete,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if email:
            self.contacts[str(pid)] = email


class FakeConnectionsTable:
    """Table mock enforcing connections RLS policies and trigger transitions."""

    def __init__(self, fake: ConnectionsFake, name: str) -> None:
        self.fake = fake
        self.store = fake.store
        self.name = name
        self.filters: list[tuple[str, str, Any]] = []
        self.limit_val: int | None = None
        self.selected_cols: list[str] | None = None
        self.pending_insert: dict[str, Any] | None = None
        self.pending_update: dict[str, Any] | None = None

    def select(self, cols: str = "*") -> FakeConnectionsTable:
        if cols != "*":
            self.selected_cols = [c.strip() for c in cols.split(",")]
        return self

    def eq(self, col: str, val: Any) -> FakeConnectionsTable:
        self.filters.append(("eq", col, val))
        return self

    def limit(self, n: int) -> FakeConnectionsTable:
        self.limit_val = n
        return self

    def insert(self, payload: dict[str, Any]) -> FakeConnectionsTable:
        self.pending_insert = dict(payload)
        return self

    def update(self, payload: dict[str, Any]) -> FakeConnectionsTable:
        self.pending_update = dict(payload)
        return self

    def execute(self) -> SimpleNamespace:
        now_iso = datetime.now(timezone.utc).isoformat()

        if self.name == "connections":
            if self.pending_insert is not None:
                p = self.pending_insert
                req = str(p.get("requester_id") or "")
                rec = str(p.get("recipient_id") or "")

                # 1. RLS policy: requester must be bound authenticated user
                if req != str(self.fake.user_id):
                    raise PostgrestAPIError(
                        {"message": "violates row-level security policy", "code": "42501"}
                    )

                # 2. Status insert grant: cannot insert non-pending status
                if "status" in p and p["status"] != "pending":
                    raise PostgrestAPIError(
                        {"message": "column grant error: status", "code": "42501"}
                    )

                # 3. Unique unordered pair index
                pair = tuple(sorted([req, rec]))
                for r in self.store.connections:
                    existing_pair = tuple(sorted([str(r["requester_id"]), str(r["recipient_id"])]))
                    if pair == existing_pair:
                        raise PostgrestAPIError(
                            {"message": "duplicate key value violates unique constraint", "code": "23505"}
                        )

                cid = str(uuid.uuid4())
                rec_prof = self.store.profiles.get(rec, {})
                is_synthetic_rec = bool(rec_prof.get("is_synthetic"))

                # In SQL RETURNING, row shows status 'pending' before after-insert trigger
                returning_row = {
                    "id": cid,
                    "requester_id": req,
                    "recipient_id": rec,
                    "note": p.get("note"),
                    "status": "pending",
                    "created_at": now_iso,
                    "responded_at": None,
                }

                # Trigger auto_accept_synthetic flips stored state if recipient is synthetic
                stored_row = dict(returning_row)
                if is_synthetic_rec:
                    stored_row["status"] = "accepted"
                    stored_row["responded_at"] = now_iso

                self.store.connections.append(stored_row)
                return SimpleNamespace(data=[returning_row])

            if self.pending_update is not None:
                cid = None
                rec_id = None
                for op, col, val in self.filters:
                    if op == "eq" and col == "id":
                        cid = str(val)
                    if op == "eq" and col == "recipient_id":
                        rec_id = str(val)

                # Find targeted row
                found = None
                for r in self.store.connections:
                    if r["id"] == cid:
                        found = r
                        break

                if not found:
                    return SimpleNamespace(data=[])

                # Guard trigger: can only update pending rows
                if found["status"] != "pending":
                    raise PostgrestAPIError(
                        {"message": "connection already answered", "code": "P0001"}
                    )

                # RLS: only recipient can update
                if str(self.fake.user_id) != str(found["recipient_id"]) or (
                    rec_id and rec_id != str(found["recipient_id"])
                ):
                    return SimpleNamespace(data=[])

                new_status = self.pending_update.get("status")
                if new_status:
                    found["status"] = new_status
                    found["responded_at"] = now_iso

                return SimpleNamespace(data=[dict(found)])

            # SELECT on connections: RLS restricts to rows caller is party to
            matched: list[dict[str, Any]] = []
            for r in self.store.connections:
                is_party = (
                    str(r["requester_id"]) == str(self.fake.user_id)
                    or str(r["recipient_id"]) == str(self.fake.user_id)
                )
                if not is_party:
                    continue

                filter_ok = True
                for op, col, val in self.filters:
                    if op == "eq" and str(r.get(col)) != str(val):
                        filter_ok = False
                        break
                if filter_ok:
                    if self.selected_cols:
                        matched.append({k: r.get(k) for k in self.selected_cols})
                    else:
                        matched.append(dict(r))

            if self.limit_val is not None:
                matched = matched[: self.limit_val]
            return SimpleNamespace(data=matched)

        if self.name == "profiles":
            matched_profs = []
            for p in self.store.profiles.values():
                filter_ok = True
                for op, col, val in self.filters:
                    if op == "eq" and str(p.get(col)) != str(val):
                        filter_ok = False
                        break
                if filter_ok:
                    matched_profs.append(dict(p))
            if self.limit_val is not None:
                matched_profs = matched_profs[: self.limit_val]
            return SimpleNamespace(data=matched_profs)

        return SimpleNamespace(data=[])


class ConnectionsFake(FakeSupabase):
    """Supabase test double maintaining multi-user connection state and RPCs."""

    def __init__(self, user_id: str, store: ConnectionStore | None = None) -> None:
        super().__init__()
        self.user_id = str(user_id)
        self.auth.user_id = str(user_id)
        self.auth._store(f"{user_id}@example.org")
        self.store = store if store is not None else ConnectionStore()
        self.rpc_calls: list[str] = []

    def for_user(self, other_id: str) -> ConnectionsFake:
        """Create client bound to another user sharing the same backing database."""
        client = ConnectionsFake(user_id=other_id, store=self.store)
        client.auth._store(f"{other_id}@example.org")
        return client

    def table(self, name: str) -> FakeConnectionsTable:
        return FakeConnectionsTable(self, name)

    def rpc(self, name: str, params: dict[str, Any] | None = None) -> Any:
        self.rpc_calls.append(name)
        p = dict(params or {})

        class _RpcCall:
            def __init__(inner, fake: ConnectionsFake) -> None:
                inner.fake = fake

            def execute(inner) -> SimpleNamespace:
                if name == "my_connections":
                    rows: list[dict[str, Any]] = []
                    uid = inner.fake.user_id
                    for r in sorted(
                        inner.fake.store.connections,
                        key=lambda x: str(x.get("created_at") or ""),
                        reverse=True,
                    ):
                        req = str(r["requester_id"])
                        rec = str(r["recipient_id"])
                        if uid != req and uid != rec:
                            continue

                        direction = "sent" if uid == req else "received"
                        other_id = rec if uid == req else req
                        other_prof = inner.fake.store.profiles.get(other_id, {})
                        other_name = other_prof.get("full_name") or "Unnamed researcher"
                        other_stage = other_prof.get("career_stage") or ""
                        other_synth = bool(other_prof.get("is_synthetic"))

                        # Email strictly gated on status == 'accepted'
                        other_email = None
                        if r["status"] == "accepted":
                            other_email = inner.fake.store.contacts.get(other_id)

                        rows.append(
                            {
                                "connection_id": r["id"],
                                "direction": direction,
                                "status": r["status"],
                                "note": r.get("note"),
                                "created_at": r.get("created_at"),
                                "responded_at": r.get("responded_at"),
                                "other_id": other_id,
                                "other_name": other_name,
                                "other_stage": other_stage,
                                "other_is_synthetic": other_synth,
                                "other_email": other_email,
                            }
                        )
                    return SimpleNamespace(data=rows)

                if name == "get_contact_email":
                    target = str(p.get("p_profile") or p.get("other_id") or "")
                    uid = inner.fake.user_id
                    if target == uid:
                        return SimpleNamespace(data=inner.fake.store.contacts.get(uid))
                    # Check accepted connection
                    for r in inner.fake.store.connections:
                        if r["status"] == "accepted":
                            parties = {str(r["requester_id"]), str(r["recipient_id"])}
                            if uid in parties and target in parties:
                                return SimpleNamespace(data=inner.fake.store.contacts.get(target))
                    return SimpleNamespace(data=None)

                return SimpleNamespace(data=[])

        return _RpcCall(self)
