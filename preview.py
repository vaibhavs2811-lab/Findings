"""Design preview: runs the real app against an in-memory fake database.

Dev-only. Lets every signed-in page be viewed and screenshotted without a login or a live
Supabase project. Run with:  streamlit run preview.py --server.port 8502
Environment: PREVIEW_AI=1 uses real Gemini for explanations (default is the embedding fallback).
"""

from __future__ import annotations

import json
import os
import runpy
from pathlib import Path
from types import SimpleNamespace

import streamlit as st

from findings.ai import embeddings
from findings.repos.seed_admin import seed_uuid

ROOT = Path(__file__).resolve().parent
ME_ID = "00000000-0000-4000-8000-000000000001"

if os.environ.get("PREVIEW_AI") != "1":
    os.environ["FINDINGS_FORCE_AI_FALLBACK"] = "1"


def _rank(stage: str | None) -> int:
    return {"Undergrad": 1, "Master's": 2, "PhD": 3, "Postdoc": 4, "Industry researcher": 4, "Faculty": 5}.get(
        stage or "", 0
    )


def _tokens(profile: dict) -> set[str]:
    words: set[str] = set()
    for key in ("interests", "skills"):
        for item in profile.get(key) or []:
            words |= {w.lower() for w in str(item).replace("/", " ").split() if len(w) > 3}
    return words


def _stage_tier(stage: str | None) -> str | None:
    if stage in ("Undergrad", "Master's", "PhD"):
        return "junior"
    if stage:
        return "senior"
    return None


def _build_rows() -> list[dict]:
    seeds = json.loads((ROOT / "data" / "seed_profiles.json").read_text(encoding="utf-8"))["profiles"]
    rows = []
    for p in seeds:
        row = dict(p)
        row["id"] = seed_uuid(p["seed_id"])
        row["stage_tier"] = _stage_tier(p["career_stage"])
        rows.append(row)
    me = {
        "id": ME_ID,
        "full_name": "Jordan Rivera",
        "career_stage": "PhD",
        "institution": "Northbridge University",
        "education": "BA Sociology; MSc Social Research Methods",
        "experience": "Two years of fieldwork on urban housing, interviews and survey design.",
        "bio": "Third-year PhD student studying how housing policy shapes everyday community life.",
        "looking_for": "Collaborators who can add quantitative modelling to qualitative housing studies.",
        "interests": ["Urban housing", "Community health", "Qualitative methods", "Survey design"],
        "skills": ["NVivo", "R", "Interviewing", "Thematic analysis"],
        "offers": ["Interview training", "Qualitative coding"],
        "needs": ["Statistical modelling"],
        "contributable_skills": ["Transcription", "Literature review", "Interviewing"],
        "want_to_learn": ["Causal inference", "Grant writing"],
        "seeking_mentor": True,
        "open_to_mentoring": True,
        "methods_suggested": "qualitative",
        "methods_override": None,
        "methods_effective": "qualitative",
        "methods_reason": "Centres on interviews, thematic analysis and fieldwork.",
        "is_synthetic": False,
        "is_complete": True,
        "stage_tier": "junior",
    }
    me["embedding_hash"] = embeddings.profile_hash(me)
    me["embedding_model"] = embeddings.EMBEDDING_MODEL
    me["embedded_at"] = "2026-10-05T00:00:00+00:00"
    rows.append(me)
    return rows


class _Result(SimpleNamespace):
    pass


class _Query:
    def __init__(self, fake, name):
        self.fake, self.name = fake, name
        self.filters: list = []
        self.orders: list[str] = []
        self.max = None
        self.mode = "select"
        self.payload = None

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self.filters.append(lambda r: r.get(col) == val)
        return self

    def in_(self, col, vals):
        self.filters.append(lambda r: r.get(col) in vals)
        return self

    def order(self, col, **_k):
        self.orders.append(col)
        return self

    def limit(self, n):
        self.max = n
        return self

    def update(self, payload):
        self.mode, self.payload = "update", payload
        return self

    def insert(self, payload):
        self.mode, self.payload = "insert", payload
        return self

    def upsert(self, payload, **_k):
        self.mode, self.payload = "upsert", payload
        return self

    def execute(self):
        table = self.fake.tables.setdefault(self.name, [])
        if self.mode == "insert":
            row = dict(self.payload, id=f"conn-{len(table) + 1}")
            table.append(row)
            return _Result(data=[row])
        if self.mode == "upsert":
            table.append(dict(self.payload))
            return _Result(data=[self.payload])
        rows = [r for r in table if all(f(r) for f in self.filters)]
        if self.mode == "update":
            for r in rows:
                r.update(self.payload)
            return _Result(data=[dict(r) for r in rows])
        for col in reversed(self.orders):
            rows.sort(key=lambda r: str(r.get(col)))
        if self.max:
            rows = rows[: self.max]
        return _Result(data=[dict(r) for r in rows])


class _Rpc:
    def __init__(self, fake, name, params):
        self.fake, self.name, self.params = fake, name, params or {}

    def execute(self):
        f = self.fake
        me = next(r for r in f.tables["profiles"] if r["id"] == ME_ID)
        exclude = set(self.params.get("exclude_ids") or [])
        pool = [r for r in f.tables["profiles"] if r["id"] != ME_ID and r.get("is_complete") and r["id"] not in exclude]
        if self.name == "match_mentorship":
            mode = self.params.get("mode")
            if mode == "mentor":
                pool = [r for r in pool if r.get("open_to_mentoring") and _rank(r["career_stage"]) > _rank(me["career_stage"])]
            else:
                pool = [r for r in pool if r.get("seeking_mentor") and _rank(r["career_stage"]) < _rank(me["career_stage"])]
        elif self.name == "my_connections":
            return _Result(data=f.connections())
        elif self.name == "get_contact_email":
            return _Result(data=None)
        mine = _tokens(me)
        scored = []
        for r in pool:
            overlap = len(mine & _tokens(r))
            sim = min(0.93, 0.52 + 0.06 * overlap + (hash(r["id"]) % 100) / 1000)
            scored.append(dict(r, similarity=round(sim, 3)))
        scored.sort(key=lambda r: r["similarity"], reverse=True)
        return _Result(data=scored[: int(self.params.get("match_count") or 15)])


class _Auth:
    def get_session(self):
        return SimpleNamespace(refresh_token="preview", access_token="preview")

    def sign_out(self, *_a, **_k):
        return None


class PreviewSupabase:
    def __init__(self):
        self.tables = {"profiles": _build_rows(), "connections": [], "match_cache": []}
        self.auth = _Auth()
        by_name = {r["full_name"]: r for r in self.tables["profiles"]}
        self.seeded = []
        names = list(by_name)
        # a pending incoming request, one accepted connection, one sent request
        self.seeded.append(("received", "pending", names[3], "Loved your work on community housing, want to compare notes?"))
        self.seeded.append(("sent", "accepted", names[10], "Would love to collaborate on a mixed-methods study."))
        self.seeded.append(("sent", "pending", names[20], "Hi! Your methods training sounds like a great fit."))

    def connections(self):
        by_name = {r["full_name"]: r for r in self.tables["profiles"]}
        out = []
        for i, (direction, status, name, note) in enumerate(self.seeded):
            o = by_name[name]
            out.append(
                {
                    "connection_id": f"seed-{i}",
                    "direction": direction,
                    "status": status,
                    "note": note,
                    "created_at": "2026-10-05T09:00:00+00:00",
                    "responded_at": None,
                    "other_id": o["id"],
                    "other_name": o["full_name"],
                    "other_stage": o["career_stage"],
                    "other_is_synthetic": False,
                    "other_email": o.get("email") if status == "accepted" else None,
                }
            )
        for row in self.tables["connections"]:
            o = next((r for r in self.tables["profiles"] if r["id"] == row.get("recipient_id")), None)
            if o:
                out.append(
                    {
                        "connection_id": row["id"],
                        "direction": "sent",
                        "status": "accepted",
                        "note": row.get("note"),
                        "created_at": "2026-10-05T10:00:00+00:00",
                        "responded_at": None,
                        "other_id": o["id"],
                        "other_name": o["full_name"],
                        "other_stage": o["career_stage"],
                        "other_is_synthetic": False,
                        "other_email": o.get("email"),
                    }
                )
        return out

    def table(self, name):
        return _Query(self, name)

    def rpc(self, name, params=None):
        return _Rpc(self, name, params)


if "sb" not in st.session_state:
    st.session_state["sb"] = PreviewSupabase()
    st.session_state["user"] = {"id": ME_ID, "email": "jordan@preview.example"}

runpy.run_path(str(ROOT / "app.py"), run_name="__main__")
