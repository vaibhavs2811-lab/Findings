"""Settings loading. No streamlit import so scripts and tests can reuse it."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import tomllib


class ConfigError(Exception):
    """Raised when required settings are missing or unsafe."""


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    supabase_publishable_key: str


def load_settings(source: Mapping) -> Settings:
    try:
        url = str(source["SUPABASE_URL"]).strip()
        key = str(source["SUPABASE_PUBLISHABLE_KEY"]).strip()
    except KeyError as exc:
        raise ConfigError(f"Missing setting: {exc.args[0]}") from None
    local = url.startswith(("http://localhost", "http://127.0.0.1"))
    if not (url.startswith("https://") or local):
        raise ConfigError("SUPABASE_URL must start with https://")
    if not key.startswith("sb_publishable_"):
        raise ConfigError(
            "SUPABASE_PUBLISHABLE_KEY must be a publishable key starting with "
            "sb_publishable_. Secret and service_role keys are never allowed in the app."
        )
    return Settings(supabase_url=url, supabase_publishable_key=key)


def load_local_settings(path: str = ".streamlit/secrets.toml") -> Settings:
    with open(path, "rb") as fh:
        return load_settings(tomllib.load(fh))
