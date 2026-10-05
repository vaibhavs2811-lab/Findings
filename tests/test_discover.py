"""Unit tests and AppTests for Discover page and Researcher public profile view."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

from streamlit.testing.v1 import AppTest

from findings.repos.profiles import CARD_COLUMNS, PUBLIC_PROFILE_COLUMNS, get_public, list_public
from tests.fakes import FakeSupabase
from ui.cards import SYNTHETIC_LABEL, badge_markdown

APP = str(Path(__file__).resolve().parent.parent / "app.py")
SECRETS = {
    "SUPABASE_URL": "https://abc.supabase.co",
    "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_x",
}

VIEWER_ID = "00000000-0000-0000-0000-000000000001"
REAL_QUANT_ID = "00000000-0000-0000-0000-000000000002"
SYNTH_PHD_ID = "00000000-0000-0000-0000-000000000003"
SYNTH_FACULTY_ID = "00000000-0000-0000-0000-000000000004"
SYNTH_MASTERS_ID = "00000000-0000-0000-0000-000000000005"
SYNTH_INDUSTRY_ID = "00000000-0000-0000-0000-000000000006"
INCOMPLETE_ID = "00000000-0000-0000-0000-000000000007"


def _make_fixture_rows() -> list[dict[str, Any]]:
    return [
        {
            "id": VIEWER_ID,
            "full_name": "Viewer Researcher",
            "career_stage": "Faculty",
            "methods_effective": "mixed",
            "interests": ["Robotics", "AI"],
            "is_synthetic": False,
            "is_complete": True,
            "embedding": "[0.1, 0.2]",
            "email": "leak@example.org",
        },
        {
            "id": REAL_QUANT_ID,
            "full_name": "Dr. Real Quantitative",
            "career_stage": "Postdoc",
            "methods_effective": "quantitative",
            "interests": ["Statistics", "Bioinformatics"],
            "is_synthetic": False,
            "is_complete": True,
            "embedding": "[0.1, 0.2]",
            "email": "leak@example.org",
        },
        {
            "id": SYNTH_PHD_ID,
            "full_name": "Zoë Müller",
            "career_stage": "PhD",
            "methods_effective": "qualitative",
            "interests": ["Ethnography of migration", "Oral history"],
            "is_synthetic": True,
            "is_complete": True,
            "bio": "Cultural anthropologist studying diaspora communities.",
            "embedding": "[0.1, 0.2]",
            "email": "leak@example.org",
        },
        {
            "id": SYNTH_FACULTY_ID,
            "full_name": "Prof. Mixed Methods",
            "career_stage": "Faculty",
            "methods_effective": "mixed",
            "interests": ["Mixed methods", "Public health"],
            "is_synthetic": True,
            "is_complete": True,
            "open_to_mentoring": True,
            "embedding": "[0.1, 0.2]",
            "email": "leak@example.org",
        },
        {
            "id": SYNTH_MASTERS_ID,
            "full_name": "Master Quant",
            "career_stage": "Master's",
            "methods_effective": "quantitative",
            "interests": ["Data science", "Machine learning"],
            "is_synthetic": True,
            "is_complete": True,
            "seeking_mentor": True,
            "embedding": "[0.1, 0.2]",
            "email": "leak@example.org",
        },
        {
            "id": SYNTH_INDUSTRY_ID,
            "full_name": "Industry Qual",
            "career_stage": "Industry researcher",
            "methods_effective": "qualitative",
            "interests": ["User research", "UX anthropology"],
            "is_synthetic": True,
            "is_complete": True,
            "embedding": "[0.1, 0.2]",
            "email": "leak@example.org",
        },
        {
            "id": INCOMPLETE_ID,
            "full_name": "Incomplete User",
            "career_stage": "PhD",
            "methods_effective": "qualitative",
            "interests": ["Draft work"],
            "is_synthetic": False,
            "is_complete": False,
            "embedding": "[0.1, 0.2]",
            "email": "leak@example.org",
        },
    ]


class PublicProfilesQuery:
    def __init__(self, parent: PublicProfilesFake, table_name: str):
        self.parent = parent
        self.table_name = table_name
        self.selected_cols: str = "*"
        self.eq_filters: list[tuple[str, Any]] = []
        self.in_filters: list[tuple[str, list[Any]]] = []
        self.orders: list[tuple[str, bool]] = []
        self.limit_val: int | None = None

    def select(self, cols: str = "*"):
        self.selected_cols = cols
        self.parent.log.append(("select", cols))
        return self

    def eq(self, col: str, val: Any):
        self.eq_filters.append((col, val))
        self.parent.log.append(("eq", (col, val)))
        return self

    def in_(self, col: str, vals: list[Any]):
        self.in_filters.append((col, list(vals)))
        self.parent.log.append(("in_", (col, list(vals))))
        return self

    def order(self, col: str, desc: bool = False):
        self.orders.append((col, desc))
        self.parent.log.append(("order", (col, desc)))
        return self

    def limit(self, n: int):
        self.limit_val = n
        self.parent.log.append(("limit", n))
        return self

    def execute(self):
        if self.parent.boom:
            raise self.parent.boom

        if self.table_name != "profiles":
            return SimpleNamespace(data=[])

        rows = list(self.parent.rows)

        # Apply eq filters
        for col, val in self.eq_filters:
            rows = [r for r in rows if r.get(col) == val]

        # Apply in filters
        for col, vals in self.in_filters:
            rows = [r for r in rows if r.get(col) in vals]

        # Apply orders (stable multi-key sort in python: execute in reverse order)
        for col, desc in reversed(self.orders):
            rows.sort(key=lambda r: (r.get(col) is None, r.get(col)), reverse=desc)

        # Apply limit
        if self.limit_val is not None:
            rows = rows[: self.limit_val]

        # Project columns
        col_names = [c.strip() for c in self.selected_cols.split(",") if c.strip()]
        projected = []
        for r in rows:
            projected.append({k: r.get(k) for k in col_names if k in r})

        return SimpleNamespace(data=projected)


class PublicProfilesFake(FakeSupabase):
    def __init__(self, rows: list[dict[str, Any]] | None = None, boom: Exception | None = None):
        super().__init__()
        self.rows = rows if rows is not None else _make_fixture_rows()
        self.boom = boom
        self.log: list[tuple[str, Any]] = []

    def table(self, name: str):
        self.log.append(("table", name))
        return PublicProfilesQuery(self, name)

    def rpc(self, fn: str, params: dict | None = None):
        self.log.append(("rpc", (fn, params)))
        if fn == "my_connections":
            return SimpleNamespace(execute=lambda: SimpleNamespace(data=[]))
        raise AssertionError(f"RPC {fn} called unexpectedly on Discover/Researcher path")


def _app_at_discover(sb: PublicProfilesFake, user_id=VIEWER_ID, email="viewer@example.org") -> AppTest:
    sb.auth._store(email)
    at = AppTest.from_file(APP, default_timeout=15)
    at.secrets.update(SECRETS)
    at.session_state["sb"] = sb
    at.session_state["user"] = {"id": user_id, "email": email}
    at.run()
    at.switch_page("views/discover.py").run()
    return at


def _all_rendered_text(at: AppTest) -> list[str]:
    """Collect all rendered text values in main across headings, body, markdown and captions."""
    collected = []
    for bucket in (
        at.main.title,
        at.main.header,
        at.main.subheader,
        at.main.text,
        at.main.markdown,
        at.main.caption,
        at.main.info,
        at.main.warning,
    ):
        for el in bucket:
            if hasattr(el, "value") and el.value:
                collected.append(str(el.value))
    return collected


def test_card_columns_are_explicit_and_private_free():
    tokens = [c.strip() for c in CARD_COLUMNS.split(",")]
    assert "*" not in tokens
    for t in tokens:
        assert "embedding" not in t
        assert "email" not in t
        assert "hash" not in t


def test_public_profile_columns_are_explicit_and_private_free():
    tokens = [c.strip() for c in PUBLIC_PROFILE_COLUMNS.split(",")]
    assert "*" not in tokens
    for t in tokens:
        assert "embedding" not in t
        assert "email" not in t
        assert "hash" not in t


def test_list_public_reads_complete_profiles_excluding_viewer():
    fake = PublicProfilesFake()
    res = list_public(fake, exclude_ids=[VIEWER_ID])
    ids = [r["id"] for r in res]

    # Viewer excluded
    assert VIEWER_ID not in ids
    # Incomplete excluded
    assert INCOMPLETE_ID not in ids
    # Real user comes first before synthetic
    assert ids[0] == REAL_QUANT_ID
    assert res[0]["is_synthetic"] is False
    assert all(r["is_synthetic"] is True for r in res[1:])

    # Check query log
    ops = [op for op, _ in fake.log]
    assert "select" in ops
    assert ("eq", ("is_complete", True)) in fake.log


def test_list_public_filter_methods():
    fake = PublicProfilesFake()
    res = list_public(fake, methods=["quantitative"], exclude_ids=[VIEWER_ID])
    assert ("in_", ("methods_effective", ["quantitative"])) in fake.log
    assert len(res) == 2
    assert all(r["methods_effective"] == "quantitative" for r in res)


def test_list_public_filter_stages():
    fake = PublicProfilesFake()
    res = list_public(
        fake,
        stages=["Industry researcher", "Master's"],
        exclude_ids=[VIEWER_ID],
    )
    assert ("in_", ("career_stage", ["Industry researcher", "Master's"])) in fake.log
    assert len(res) == 2
    assert {r["career_stage"] for r in res} == {"Industry researcher", "Master's"}


def test_list_public_filter_keyword():
    fake = PublicProfilesFake()
    res = list_public(fake, keyword="  ETHNO ", exclude_ids=[VIEWER_ID])
    assert len(res) == 1
    assert res[0]["full_name"] == "Zoë Müller"


def test_list_public_drops_unknown_filters():
    fake = PublicProfilesFake()
    res = list_public(
        fake,
        methods=["alien_methods"],
        stages=["Space cadet"],
        exclude_ids=[VIEWER_ID],
    )
    in_ops = [val for op, val in fake.log if op == "in_"]
    assert in_ops == []
    assert len(res) == 5


def test_get_public_sql_injection_defense():
    fake = PublicProfilesFake()
    res = get_public(fake, "1; drop table profiles;")
    assert res is None
    # No query was executed against the database
    assert [op for op, _ in fake.log] == []


def test_get_public_returns_projected_row():
    fake = PublicProfilesFake()
    row = get_public(fake, SYNTH_PHD_ID)
    assert row is not None
    assert row["full_name"] == "Zoë Müller"
    assert row["career_stage"] == "PhD"
    assert "embedding" not in row
    assert "email" not in row


def test_badge_markdown_whitelists_values():
    injected_profile = {
        "career_stage": "<script>alert(1)</script>",
        "methods_effective": "unclassified_random_string",
        "is_synthetic": True,
    }
    rendered = badge_markdown(injected_profile)
    assert "<script>" not in rendered
    assert "Methods not set" in rendered
    assert SYNTHETIC_LABEL in rendered


def test_synthetic_badge_renders_only_when_synthetic():
    def _runner(p):
        from ui.cards import synthetic_badge

        synthetic_badge(p)

    at_synth = AppTest.from_function(_runner, args=({"is_synthetic": True},)).run()
    assert not at_synth.exception
    assert any(SYNTHETIC_LABEL in m.value for m in at_synth.markdown)

    at_real = AppTest.from_function(_runner, args=({"is_synthetic": False},)).run()
    assert not at_real.exception
    assert not any(SYNTHETIC_LABEL in m.value for m in at_real.markdown)


def test_discover_page_shows_cards_with_synthetic_label():
    fake = PublicProfilesFake()
    at = _app_at_discover(fake)
    assert not at.exception

    all_texts = _all_rendered_text(at)
    # Visible complete candidates shown
    assert any("Dr. Real Quantitative" in t for t in all_texts)
    assert any("Zoë Müller" in t for t in all_texts)
    # Viewer and incomplete candidates absent
    assert not any("Viewer Researcher" in t for t in all_texts)
    assert not any("Incomplete User" in t for t in all_texts)

    # Synthetic label count matches synthetic profiles count (4)
    synth_badges = [m.value for m in at.markdown if SYNTHETIC_LABEL in m.value]
    assert len(synth_badges) == 4

    # No email leaked anywhere
    for t in all_texts:
        assert "@" not in t or "@example.org" not in t


def test_discover_filters_and_keyword_combination():
    fake = PublicProfilesFake()
    at = _app_at_discover(fake)

    # Filter qualitative + PhD
    at.pills(key="disc_methods").set_value(["qualitative"]).run()
    at.multiselect(key="disc_stages").select("PhD").run()

    texts = _all_rendered_text(at)
    assert any("Zoë Müller" in t for t in texts)
    assert not any("Dr. Real Quantitative" in t for t in texts)
    assert not any("Prof. Mixed Methods" in t for t in texts)

    # Add matching keyword
    at.text_input(key="disc_keyword").input("oral").run()
    texts = _all_rendered_text(at)
    assert any("Zoë Müller" in t for t in texts)

    # Change to non-matching keyword
    at.text_input(key="disc_keyword").input("zzz").run()
    assert any("No researchers match these filters." in i.value for i in at.info)


def test_discover_skip_and_unskip():
    fake = PublicProfilesFake()
    at = _app_at_discover(fake)

    # Initial: Zoë is visible
    assert any("Zoë Müller" in t.value for t in at.text)

    # Click Skip on Zoë
    at.button(key=f"skip_{SYNTH_PHD_ID}").click().run()
    assert not any("Zoë Müller" in t.value for t in at.text)

    # Switch away to Home and back to Discover: still skipped
    at.switch_page("views/home.py").run()
    at.switch_page("views/discover.py").run()
    assert not any("Zoë Müller" in t.value for t in at.text)

    # Click Show skipped (1)
    assert at.button(key="disc_unskip") is not None
    at.button(key="disc_unskip").click().run()
    assert any("Zoë Müller" in t.value for t in at.text)


def test_discover_skipped_owner_isolation():
    fake = PublicProfilesFake()
    at = _app_at_discover(fake)
    # Simulate session state left over by another user
    at.session_state["skipped_owner"] = "other-user-999"
    at.session_state["skipped_ids"] = [SYNTH_PHD_ID]
    at.run()

    # Discover resets skips because owner != current user
    assert at.session_state["skipped_owner"] == VIEWER_ID
    assert at.session_state["skipped_ids"] == []
    assert any("Zoë Müller" in t.value for t in at.text)


def test_discover_load_failure_shows_friendly_warning():
    fake = PublicProfilesFake(boom=RuntimeError("Database connection timed out"))
    at = _app_at_discover(fake)
    assert not at.exception
    assert any("Could not load researchers" in w.value for w in at.warning)


def test_researcher_page_displays_profile_safely():
    fake = PublicProfilesFake()
    sb = fake
    sb.auth._store("viewer@example.org")
    at = AppTest.from_file(APP, default_timeout=15)
    at.secrets.update(SECRETS)
    at.session_state["sb"] = sb
    at.session_state["user"] = {"id": VIEWER_ID, "email": "viewer@example.org"}
    at.query_params["id"] = SYNTH_PHD_ID
    at.run()
    at.switch_page("views/researcher.py").run()

    assert not at.exception
    texts = _all_rendered_text(at)
    assert any("Zoë Müller" in t for t in texts)
    assert any("Cultural anthropologist studying diaspora communities." in t for t in texts)
    # Synthetic badge appears exactly once in markdown
    synth_badges = [m.value for m in at.markdown if SYNTHETIC_LABEL in m.value]
    assert len(synth_badges) == 1

    # No email leaked
    for t in texts:
        assert "leak@example.org" not in t

    # Fake log touched only table "profiles", and at most my_connections RPC for connect button
    tables = [val for op, val in fake.log if op == "table"]
    assert all(tbl == "profiles" for tbl in tables)
    rpcs = [val[0] for op, val in fake.log if op == "rpc"]
    assert all(fn == "my_connections" for fn in rpcs)


def test_researcher_page_real_profile_no_synthetic_badge():
    fake = PublicProfilesFake()
    fake.auth._store("viewer@example.org")
    at = AppTest.from_file(APP, default_timeout=15)
    at.secrets.update(SECRETS)
    at.session_state["sb"] = fake
    at.session_state["user"] = {"id": VIEWER_ID, "email": "viewer@example.org"}
    at.query_params["id"] = REAL_QUANT_ID
    at.run()
    at.switch_page("views/researcher.py").run()

    assert not at.exception
    texts = _all_rendered_text(at)
    assert any("Dr. Real Quantitative" in t for t in texts)
    assert not any(SYNTHETIC_LABEL in m.value for m in at.markdown)


def test_researcher_page_invalid_or_missing_id():
    fake = PublicProfilesFake()
    fake.auth._store("viewer@example.org")

    # 1. Missing id
    at1 = AppTest.from_file(APP, default_timeout=15)
    at1.secrets.update(SECRETS)
    at1.session_state["sb"] = fake
    at1.session_state["user"] = {"id": VIEWER_ID, "email": "viewer@example.org"}
    at1.run()
    at1.switch_page("views/researcher.py").run()
    assert not at1.exception
    assert any("Pick a researcher on Discover" in i.value for i in at1.info)

    # 2. Non-UUID string
    at2 = AppTest.from_file(APP, default_timeout=15)
    at2.secrets.update(SECRETS)
    at2.session_state["sb"] = fake
    at2.session_state["user"] = {"id": VIEWER_ID, "email": "viewer@example.org"}
    at2.query_params["id"] = "not-a-uuid"
    at2.run()
    at2.switch_page("views/researcher.py").run()
    assert not at2.exception
    assert any("Researcher not found" in i.value for i in at2.info)
