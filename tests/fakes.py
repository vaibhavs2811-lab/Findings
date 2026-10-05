"""FakeSupabase shared by Phase 1 tests. Later plans subclass it; do not edit per-plan."""

from __future__ import annotations

from types import SimpleNamespace

from supabase import AuthApiError

FAR_FUTURE = 4_102_444_800


def make_user(user_id: str, email: str, identities=None):
    return SimpleNamespace(
        id=user_id, email=email, identities=[object()] if identities is None else identities
    )


def make_session(user):
    return SimpleNamespace(
        access_token=f"access-{user.id}",
        refresh_token=f"refresh-{user.id}",
        expires_at=FAR_FUTURE,
        user=user,
    )


class FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def select(self, *_a, **_k):
        return self

    def update(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def execute(self):
        return SimpleNamespace(data=self._rows)


class FakeAuth:
    def __init__(self):
        self.calls: list[tuple[str, object]] = []
        self.valid_password = "correct-horse"
        self.user_id = "user-1"
        self.known_emails: set[str] = set()
        self.sign_up_session = True  # False simulates "Confirm email" being on
        self.raise_on: dict[str, Exception] = {}
        self.refresh_error: Exception | None = None
        self._session = None

    def _maybe_raise(self, name):
        if name in self.raise_on:
            raise self.raise_on[name]

    def _store(self, email):
        user = make_user(self.user_id, email)
        self._session = make_session(user)
        return SimpleNamespace(user=user, session=self._session)

    def sign_in_with_password(self, credentials):
        self.calls.append(("sign_in_with_password", credentials))
        self._maybe_raise("sign_in_with_password")
        if credentials["password"] != self.valid_password:
            raise AuthApiError("Invalid login credentials", 400, "invalid_credentials")
        return self._store(credentials["email"])

    def sign_up(self, credentials):
        self.calls.append(("sign_up", credentials))
        self._maybe_raise("sign_up")
        email = credentials["email"]
        if email in self.known_emails:
            user = make_user(self.user_id, email, identities=[])
            return SimpleNamespace(user=user, session=None)
        self.known_emails.add(email)
        if not self.sign_up_session:
            return SimpleNamespace(user=make_user(self.user_id, email), session=None)
        return self._store(email)

    def refresh_session(self, refresh_token=None):
        self.calls.append(("refresh_session", refresh_token))
        if self.refresh_error:
            raise self.refresh_error
        email = self._session.user.email if self._session else "refreshed@example.com"
        return self._store(email)

    def get_session(self):
        self.calls.append(("get_session", None))
        return self._session

    def sign_out(self, options=None):
        self.calls.append(("sign_out", options))
        self._session = None


class FakeSupabase:
    def __init__(self, rows=None):
        self.auth = FakeAuth()
        self.rows = rows if rows is not None else []

    def table(self, _name):
        return FakeQuery(self.rows)
