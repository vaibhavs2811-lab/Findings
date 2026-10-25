"""In-memory chat database shared by simulated user sessions. Mirrors the SQL rules in schema.sql:
only participants of an accepted connection with a real (non-synthetic) person can read or write,
inserts are sender-bound, bodies are trimmed, and a rate limit applies."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

from tests.fakes import FakeSupabase


class ChatStore:
    def __init__(self) -> None:
        self.profiles: dict[str, dict[str, Any]] = {}
        self.connections: dict[str, dict[str, Any]] = {}
        self.messages: list[dict[str, Any]] = []
        self.clock = datetime(2026, 10, 6, 9, 0, tzinfo=timezone.utc)

    def add_profile(self, pid: str, name: str, stage: str = "PhD", synthetic: bool = False) -> None:
        self.profiles[pid] = {"id": pid, "full_name": name, "career_stage": stage, "is_synthetic": synthetic}

    def connect(self, cid: str, a: str, b: str, status: str = "accepted") -> None:
        self.connections[cid] = {"id": cid, "requester_id": a, "recipient_id": b, "status": status}

    def other(self, cid: str, me: str) -> str:
        c = self.connections[cid]
        return c["recipient_id"] if c["requester_id"] == me else c["requester_id"]

    def can_chat(self, cid: str, me: str) -> bool:
        c = self.connections.get(cid)
        if not c or c["status"] != "accepted" or me not in (c["requester_id"], c["recipient_id"]):
            return False
        return not self.profiles[self.other(cid, me)]["is_synthetic"]

    def tick(self) -> str:
        self.clock += timedelta(seconds=30)
        return self.clock.isoformat()


class _Query:
    def __init__(self, fake: ChatFake) -> None:
        self.fake = fake
        self.cid: str | None = None
        self.desc = False
        self.max: int | None = None
        self.payload: dict[str, Any] | None = None

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        if col == "connection_id":
            self.cid = val
        return self

    def order(self, _col, desc=False, **_k):
        self.desc = desc
        return self

    def limit(self, n):
        self.max = n
        return self

    def insert(self, payload):
        self.payload = payload
        return self

    def execute(self):
        f, s = self.fake, self.fake.store
        if self.payload is not None:
            p = self.payload
            if p["sender_id"] != f.user_id or not s.can_chat(p["connection_id"], f.user_id):
                raise RuntimeError('new row violates row-level security policy for table "messages"')
            recent = [m for m in s.messages if m["sender_id"] == f.user_id]
            if len(recent) >= f.rate_limit:
                raise RuntimeError("You are sending messages too fast. Wait a moment and try again.")
            row = {
                "id": f"m{len(s.messages) + 1}",
                "connection_id": p["connection_id"],
                "sender_id": p["sender_id"],
                "body": p["body"].strip(),
                "created_at": s.tick(),
                "read_at": None,
            }
            s.messages.append(row)
            return SimpleNamespace(data=[row])
        rows = [m for m in s.messages if m["connection_id"] == self.cid and s.can_chat(self.cid, f.user_id)]
        rows.sort(key=lambda m: m["created_at"], reverse=self.desc)
        if self.max:
            rows = rows[: self.max]
        return SimpleNamespace(data=[dict(r) for r in rows])


class _Rpc:
    def __init__(self, fake: ChatFake, name: str, params: dict[str, Any] | None) -> None:
        self.fake, self.name, self.params = fake, name, params or {}

    def execute(self):
        f, s = self.fake, self.fake.store
        if self.name == "mark_conversation_read":
            cid = self.params["p_connection"]
            if s.can_chat(cid, f.user_id):
                for m in s.messages:
                    if m["connection_id"] == cid and m["sender_id"] != f.user_id and not m["read_at"]:
                        m["read_at"] = s.tick()
            return SimpleNamespace(data=None)
        if self.name == "my_conversations":
            out = []
            for cid in s.connections:
                if not s.can_chat(cid, f.user_id):
                    continue
                other = s.profiles[s.other(cid, f.user_id)]
                msgs = [m for m in s.messages if m["connection_id"] == cid]
                last = msgs[-1] if msgs else None
                out.append(
                    {
                        "connection_id": cid,
                        "other_id": other["id"],
                        "other_name": other["full_name"],
                        "other_stage": other["career_stage"],
                        "last_body": last["body"] if last else None,
                        "last_at": last["created_at"] if last else None,
                        "last_sender_id": last["sender_id"] if last else None,
                        "unread_count": sum(1 for m in msgs if m["sender_id"] != f.user_id and not m["read_at"]),
                    }
                )
            return SimpleNamespace(data=out)
        return SimpleNamespace(data=[])


class ChatFake(FakeSupabase):
    def __init__(self, user_id: str, store: ChatStore) -> None:
        super().__init__()
        self.user_id = user_id
        self.store = store
        self.rate_limit = 20
        self.auth.user_id = user_id

    def for_user(self, user_id: str) -> ChatFake:
        other = ChatFake(user_id, self.store)
        other.rate_limit = self.rate_limit
        return other

    def table(self, name: str):
        if name == "messages":
            return _Query(self)
        return super().table(name)

    def rpc(self, name: str, params: dict[str, Any] | None = None):
        return _Rpc(self, name, params)
