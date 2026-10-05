import ast
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest
from supabase import AuthApiError

from tests.fakes import FakeSupabase

ROOT = Path(__file__).resolve().parent.parent
APP = str(ROOT / "app.py")

SECRETS = {
    "SUPABASE_URL": "https://example.supabase.co",
    "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_dummy",
}


def _signed_in(sb=None):
    sb = sb or FakeSupabase()
    sb.auth._store("me@b.com")
    at = AppTest.from_file(APP, default_timeout=15)
    at.secrets.update(SECRETS)
    at.session_state["sb"] = sb
    at.session_state["user"] = {"id": "user-1", "email": "me@b.com"}
    return at, sb


def _sidebar_button(at):
    return next(b for b in at.sidebar.button if b.label == "Sign out")


def test_home_sidebar_shows_email_and_sign_out():
    at, _ = _signed_in()
    at.run()
    assert not at.exception
    assert at.title[0].value == "Welcome to Findings"
    assert at.sidebar.caption[0].value == "me@b.com"
    assert _sidebar_button(at)


def test_account_page_shows_email_id_and_sign_out():
    at, _ = _signed_in()
    at.run()
    at.switch_page("views/account.py").run()
    assert not at.exception
    assert at.title[0].value == "Account"
    assert "me@b.com" in at.markdown[0].value
    assert at.code[0].value == "user-1"
    assert _sidebar_button(at)


@pytest.mark.parametrize("page", [None, "views/account.py"])
def test_sign_out_from_any_page(page):
    at, sb = _signed_in()
    at.run()
    if page:
        at.switch_page(page).run()
    _sidebar_button(at).click()
    at.run()
    assert not at.exception
    sign_outs = [c for c in sb.auth.calls if c[0] == "sign_out"]
    assert sign_outs == [("sign_out", {"scope": "local"})]
    assert "user" not in at.session_state
    assert at.session_state["restore_attempted"] is True
    assert at.title[0].value == "Sign in to Findings"


def test_account_page_sign_out_button():
    at, sb = _signed_in()
    at.run()
    at.switch_page("views/account.py").run()
    next(b for b in at.button if b.key == "account_sign_out").click()
    at.run()
    assert not at.exception
    assert at.title[0].value == "Sign in to Findings"
    assert len([c for c in sb.auth.calls if c[0] == "sign_out"]) == 1


def test_sign_out_error_still_clears_local_state():
    sb = FakeSupabase()
    sb.auth.sign_out = lambda options=None: (_ for _ in ()).throw(
        AuthApiError("boom", 500, "unexpected_failure")
    )
    at, _ = _signed_in(sb)
    at.run()
    _sidebar_button(at).click()
    at.run()
    assert not at.exception
    assert "user" not in at.session_state
    assert at.title[0].value == "Sign in to Findings"


def test_two_sessions_get_distinct_real_clients():
    sessions = []
    for _ in range(2):
        at = AppTest.from_file(APP, default_timeout=15)
        at.secrets.update(SECRETS)
        at.run()
        assert not at.exception
        sessions.append(at.session_state["sb"])
    assert sessions[0] is not sessions[1]


def _py_files():
    files = [ROOT / "app.py"]
    for folder in ("findings", "views"):
        files += (ROOT / folder).rglob("*.py")
    return files


def test_no_cache_decorators_and_no_stray_create_client():
    bad = []
    for path in _py_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for dec in node.decorator_list:
                    target = dec.func if isinstance(dec, ast.Call) else dec
                    name = target.attr if isinstance(target, ast.Attribute) else getattr(
                        target, "id", ""
                    )
                    if name in ("cache_resource", "cache_data", "cache"):
                        bad.append(f"{path.name}:{node.name} cache decorator")
            if isinstance(node, ast.Call):
                fn = node.func
                fname = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
                if fname == "create_client":
                    bad.append(f"{path.name}:{node.lineno} create_client")
    # exactly one create_client call allowed: get_client in session.py
    allowed = [b for b in bad if b.startswith("session.py") and "create_client" in b]
    assert len(allowed) == 1
    assert [b for b in bad if b not in allowed] == []
