"""Chat between connections: SQL rules, service, thread rendering and the Messages page."""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from findings.services import chat_service
from tests.fakes_chat import ChatFake, ChatStore
from tests.uihelp import html_values
from ui.chat import thread_html

ROOT = Path(__file__).resolve().parent.parent
APP = str(ROOT / "app.py")
SECRETS = {"SUPABASE_URL": "https://abc.supabase.co", "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_x"}
ALICE, BOB, CARA, SAM = "u-alice", "u-bob", "u-cara", "u-sam"


def _store() -> ChatStore:
    s = ChatStore()
    s.add_profile(ALICE, "Alice Park")
    s.add_profile(BOB, "Bob Lee")
    s.add_profile(CARA, "Cara Diaz")
    s.add_profile(SAM, "Sam Sample", synthetic=True)
    s.connect("c-ab", ALICE, BOB)  # accepted, real
    s.connect("c-ac", ALICE, CARA, status="pending")
    s.connect("c-as", ALICE, SAM)  # accepted but with a sample profile
    return s


def _app(sb, uid, email):
    sb.auth._store(email)
    at = AppTest.from_file(APP, default_timeout=20)
    at.secrets.update(SECRETS)
    at.session_state["sb"] = sb
    at.session_state["user"] = {"id": uid, "email": email}
    return at


# ---------- SQL ----------

@pytest.fixture(scope="module")
def sql() -> str:
    return (ROOT / "supabase" / "schema.sql").read_text(encoding="utf-8").lower()


def test_sql_rls_and_grants(sql):
    section = sql[sql.index("12. chat between connections"):]
    assert "alter table public.messages enable row level security" in section
    assert "revoke all on public.messages from anon" in section
    assert "grant insert (connection_id, sender_id, body) on public.messages" in section
    # clients can never update or delete messages
    assert "grant update" not in section and "grant delete" not in section
    assert "for delete" not in section and "for update" not in section
    assert "sender_id = (select auth.uid()) and public.can_chat(connection_id)" in section
    assert "using (public.can_chat(connection_id))" in section


def test_sql_chat_gate_requires_accepted_real_person(sql):
    body = sql[sql.index("function public.can_chat"):sql.index("alter table public.messages enable")]
    assert "c.status = 'accepted'" in body
    assert "not o.is_synthetic" in body
    assert "security definer" in body and "set search_path = ''" in body


def test_sql_rate_limit_and_length(sql):
    assert "between 1 and 2000" in sql
    assert "interval '1 minute'" in sql and ">= 20" in sql
    assert "create trigger messages_guard" in sql


def test_sql_rpcs_are_not_callable_by_anon(sql):
    for fn in ("my_conversations()", "mark_conversation_read(uuid)", "can_chat(uuid)"):
        assert f"revoke execute on function public.{fn} from public, anon" in sql
        assert f"grant execute on function public.{fn} to authenticated" in sql


# ---------- service ----------

def test_clean_body_rules():
    assert chat_service.clean_body("  hi \r\n there ") == "hi \n there"
    with pytest.raises(chat_service.ChatError):
        chat_service.clean_body("   ")
    with pytest.raises(chat_service.ChatError):
        chat_service.clean_body("x" * (chat_service.MAX_LEN + 1))
    assert len(chat_service.clean_body("x" * chat_service.MAX_LEN)) == chat_service.MAX_LEN


def test_send_and_read_between_connections():
    store = _store()
    a, b = ChatFake(ALICE, store), ChatFake(BOB, store)
    chat_service.send(a, ALICE, "c-ab", "  Hello Bob  ")
    assert [m["body"] for m in chat_service.thread(b, "c-ab")] == ["Hello Bob"]
    assert chat_service.unread_total(b, BOB) == 1
    chat_service.mark_read(b, "c-ab")
    assert chat_service.unread_total(b, BOB) == 0
    assert chat_service.thread(a, "c-ab")[0]["read_at"] is not None


def test_cannot_chat_without_accepted_connection_or_with_sample_profiles():
    store = _store()
    a, c = ChatFake(ALICE, store), ChatFake(CARA, store)
    with pytest.raises(chat_service.ChatError, match="connected"):
        chat_service.send(a, ALICE, "c-ac", "hi")  # pending
    with pytest.raises(chat_service.ChatError, match="connected"):
        chat_service.send(a, ALICE, "c-as", "hi")  # sample profile
    with pytest.raises(chat_service.ChatError, match="connected"):
        chat_service.send(c, CARA, "c-ab", "let me in")  # not a participant
    assert chat_service.thread(c, "c-ab") == []


def test_cannot_send_as_someone_else():
    store = _store()
    b = ChatFake(BOB, store)
    with pytest.raises(chat_service.ChatError):
        chat_service.send(b, ALICE, "c-ab", "spoofed")


def test_rate_limit_message_is_friendly():
    store = _store()
    a = ChatFake(ALICE, store)
    a.rate_limit = 2
    chat_service.send(a, ALICE, "c-ab", "1")
    chat_service.send(a, ALICE, "c-ab", "2")
    with pytest.raises(chat_service.ChatError, match="too fast"):
        chat_service.send(a, ALICE, "c-ab", "3")


def test_conversations_exclude_pending_and_sample_profiles():
    store = _store()
    names = [c["other_name"] for c in chat_service.conversations(ChatFake(ALICE, store), ALICE)]
    assert names == ["Bob Lee"]


def test_unread_total_never_raises():
    class Broken:
        def rpc(self, *_a, **_k):
            raise RuntimeError("down")

    assert chat_service.unread_total(Broken(), "x") == 0


def test_snippet():
    assert chat_service.snippet("a  b\nc") == "a b c"
    assert chat_service.snippet("x" * 100).endswith("…") and len(chat_service.snippet("x" * 100)) == 48


# ---------- rendering ----------

def test_thread_html_escapes_and_orders():
    evil = '<script>alert(1)</script><img src=x onerror=alert(2)>'
    msgs = [
        {"sender_id": ALICE, "body": evil, "created_at": "2026-10-06T09:00:00+00:00", "read_at": "2026-10-06T09:01:00+00:00"},
        {"sender_id": BOB, "body": "line1\nline2", "created_at": "2026-10-07T10:30:00+00:00", "read_at": None},
    ]
    html = thread_html(msgs, ALICE)
    assert "<script" not in html and "<img" not in html and "&lt;script&gt;" in html
    assert html.index("fx-msgrow me") < html.index("fx-msgrow them")
    assert "Oct 06, 2026" in html and "Oct 07, 2026" in html and "Read" in html
    assert html.count("fx-day") == 2


def test_thread_html_empty():
    assert "No messages yet" in thread_html([], ALICE)


# ---------- page ----------

def test_messages_page_empty_state():
    store = ChatStore()
    store.add_profile(ALICE, "Alice Park")
    at = _app(ChatFake(ALICE, store), ALICE, "alice@x.org")
    at.run()
    at.switch_page("views/messages.py").run()
    assert not at.exception
    assert any("No conversations yet" in v for v in html_values(at))


def test_messages_page_send_and_receive():
    store = _store()
    a_at = _app(ChatFake(ALICE, store), ALICE, "alice@x.org")
    a_at.run()
    a_at.switch_page("views/messages.py").run()
    assert not a_at.exception
    assert any("Bob Lee" in v for v in html_values(a_at))
    assert not any("Sam Sample" in v for v in html_values(a_at))  # sample profile has no chat
    a_at.chat_input[0].set_value("Hi Bob, loved your talk").run()
    assert not a_at.exception
    assert [m["body"] for m in store.messages] == ["Hi Bob, loved your talk"]
    assert any("Hi Bob, loved your talk" in v for v in html_values(a_at))

    b_at = _app(ChatFake(BOB, store), BOB, "bob@x.org")
    b_at.run()
    b_at.switch_page("views/messages.py").run()
    assert any("Hi Bob, loved your talk" in v for v in html_values(b_at))
    assert store.messages[0]["read_at"] is not None  # opening the thread marks it read


def test_messages_page_rejects_empty_and_reports_errors():
    store = _store()
    sb = ChatFake(ALICE, store)
    sb.rate_limit = 0
    at = _app(sb, ALICE, "alice@x.org")
    at.run()
    at.switch_page("views/messages.py").run()
    at.chat_input[0].set_value("hello").run()
    assert any("too fast" in e.value for e in at.error)
    assert store.messages == []


def test_messages_page_explains_missing_database_objects():
    class NoChatTables(ChatFake):
        def rpc(self, name, params=None):
            raise RuntimeError("Could not find the function public.my_conversations in the schema cache")

    store = _store()
    at = _app(NoChatTables(ALICE, store), ALICE, "alice@x.org")
    at.run()
    at.switch_page("views/messages.py").run()
    assert not at.exception
    assert any("not set up on the database" in w.value for w in at.warning)
