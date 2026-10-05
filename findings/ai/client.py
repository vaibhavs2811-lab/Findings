"""Shared Gemini client with model chain fallback and structured schema validation.

Streamlit-free; does not access st.secrets or Streamlit session state.
Later phases reuse this module for reranking, autofill, and seed generation.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel

logger = logging.getLogger(__name__)

TEXT_MODELS: tuple[str, ...] = ("gemini-3.5-flash-lite", "gemini-3.1-flash-lite")
REQUEST_TIMEOUT_MS = 15_000

_DISABLED = object()
_configured_state: tuple[Any, Any] | None = None  # (raw_key, client_or_disabled)


class AIUnavailable(Exception):
    """Raised when every model in the chain fails or Gemini is not configured.

    Carries a user-safe message and never contains prompt text or API keys.
    """


def make_client(api_key: str | None, *, httpx_client: Any = None) -> genai.Client:
    """Instantiate a google-genai Client with explicit timeout and no automatic retries."""
    clean_key = (api_key or "").strip()
    if not clean_key:
        raise AIUnavailable("Gemini API key is not configured")
    opts = types.HttpOptions(timeout=REQUEST_TIMEOUT_MS, httpx_client=httpx_client)
    return genai.Client(api_key=clean_key, http_options=opts)


def configure(api_key: str | None, *, httpx_client: Any = None) -> None:
    """Set the module-level default Gemini client or explicitly disable it."""
    global _configured_state
    clean_key = (api_key or "").strip()
    if _configured_state is not None and _configured_state[0] == clean_key:
        return

    if not clean_key:
        _configured_state = (clean_key, _DISABLED)
    else:
        client = make_client(clean_key, httpx_client=httpx_client)
        _configured_state = (clean_key, client)


def _resolve_client(explicit_client: genai.Client | None = None) -> genai.Client:
    """Resolve the active client from explicit argument, configure(), or environment."""
    if explicit_client is not None:
        return explicit_client

    if _configured_state is not None:
        _key, client_or_disabled = _configured_state
        if client_or_disabled is _DISABLED:
            raise AIUnavailable("Gemini API key is not configured")
        return client_or_disabled

    env_key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if not env_key:
        raise AIUnavailable("Gemini API key is not configured")
    return make_client(env_key)


def generate_structured(
    prompt: str,
    schema: type[BaseModel],
    *,
    parts: list[Any] | None = None,
    system: str | None = None,
    client: genai.Client | None = None,
    models: tuple[str, ...] = TEXT_MODELS,
) -> BaseModel:
    """Generate structured output against a Pydantic schema using model chain fallback.

    Uses LOW thinking level and default sampling parameters. On model failure, falls
    back to the next model in models. If all models fail, raises AIUnavailable.
    """
    resolved_client = _resolve_client(client)

    cfg_kwargs: dict[str, Any] = {
        "response_mime_type": "application/json",
        "response_schema": schema,
        "thinking_config": types.ThinkingConfig(thinking_level=types.ThinkingLevel.LOW),
    }
    if system:
        cfg_kwargs["system_instruction"] = system

    cfg = types.GenerateContentConfig(**cfg_kwargs)

    contents: list[Any] | str
    if parts:
        contents = list(parts) + [prompt]
    else:
        contents = prompt

    last_error: Exception | None = None
    for model in models:
        try:
            resp = resolved_client.models.generate_content(
                model=model,
                contents=contents,
                config=cfg,
            )
            if not resp.text:
                raise ValueError("Empty response from model")
            return schema.model_validate_json(resp.text)
        except Exception as exc:
            last_error = exc
            logger.warning("gemini model %s failed: %s", model, type(exc).__name__)

    raise AIUnavailable("AI suggestion unavailable") from last_error
