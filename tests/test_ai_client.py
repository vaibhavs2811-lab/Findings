"""Tests for findings.ai.client using httpx.MockTransport with the real SDK."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from google.genai import types
from pydantic import BaseModel

from findings.ai import client as ai_client
from findings.ai.client import (
    TEXT_MODELS,
    AIUnavailable,
    configure,
    generate_structured,
    make_client,
)
from findings.core.config import load_settings


class SampleSchema(BaseModel):
    label: str
    reason: str


def _make_gemini_response(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": json.dumps(payload)}],
                    "role": "model",
                },
                "finishReason": "STOP",
            }
        ]
    }


@pytest.fixture(autouse=True)
def _reset_client_config():
    yield
    ai_client._configured_state = None


def test_make_client_blank_key_raises_ai_unavailable():
    with pytest.raises(AIUnavailable, match="not configured"):
        make_client(None)
    with pytest.raises(AIUnavailable, match="not configured"):
        make_client("   ")


def test_configure_none_disables_even_with_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "real-key-in-env")
    configure(None)
    with pytest.raises(AIUnavailable, match="not configured"):
        generate_structured("prompt", SampleSchema)


def test_first_model_success():
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        resp_data = _make_gemini_response({"label": "mixed", "reason": "Uses surveys and interviews."})
        return httpx.Response(200, json=resp_data)

    mock_http = httpx.Client(transport=httpx.MockTransport(handler))
    client = make_client("fake-key", httpx_client=mock_http)

    res = generate_structured("test prompt", SampleSchema, client=client)
    assert isinstance(res, SampleSchema)
    assert res.label == "mixed"
    assert len(calls) == 1
    assert TEXT_MODELS[0] in calls[0]


def test_fallback_on_429():
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        calls.append(url_str)
        if TEXT_MODELS[0] in url_str:
            return httpx.Response(429, json={"error": {"code": 429, "message": "Resource exhausted", "status": "RESOURCE_EXHAUSTED"}})
        resp_data = _make_gemini_response({"label": "qualitative", "reason": "Interviews only."})
        return httpx.Response(200, json=resp_data)

    mock_http = httpx.Client(transport=httpx.MockTransport(handler))
    client = make_client("fake-key", httpx_client=mock_http)

    res = generate_structured("test prompt", SampleSchema, client=client)
    assert res.label == "qualitative"
    assert len(calls) == 2
    assert TEXT_MODELS[0] in calls[0]
    assert TEXT_MODELS[1] in calls[1]


def test_all_models_fail_raises_ai_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": {"code": 500, "message": "Server error"}})

    mock_http = httpx.Client(transport=httpx.MockTransport(handler))
    client = make_client("fake-key", httpx_client=mock_http)

    with pytest.raises(AIUnavailable, match="AI suggestion unavailable"):
        generate_structured("test prompt", SampleSchema, client=client)


def test_captured_request_body_and_schema():
    captured_body: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_body
        captured_body = json.loads(request.content.decode("utf-8"))
        resp_data = _make_gemini_response({"label": "quantitative", "reason": "Regression."})
        return httpx.Response(200, json=resp_data)

    mock_http = httpx.Client(transport=httpx.MockTransport(handler))
    client = make_client("fake-key", httpx_client=mock_http)

    from findings.ai.methods import MethodsSuggestion
    from findings.ai.prompts import METHODS_SYSTEM

    generate_structured("test prompt", MethodsSuggestion, system=METHODS_SYSTEM, client=client)

    # Thinking config LOW
    gen_config = captured_body.get("generationConfig", {})
    thinking_cfg = gen_config.get("thinkingConfig", {})
    assert thinking_cfg.get("thinking_level") == "LOW" or thinking_cfg.get("thinkingLevel") == "LOW"
    # No temperature
    assert "temperature" not in gen_config

    # Response schema check
    schema = gen_config.get("responseSchema", {})
    label_prop = schema.get("properties", {}).get("label", {})
    assert set(label_prop.get("enum", [])) == {"qualitative", "quantitative", "mixed"}
    # No max_length or maxLength in schema
    schema_dump = json.dumps(schema)
    assert "max_length" not in schema_dump
    assert "maxLength" not in schema_dump

    # System instruction present
    sys_inst = captured_body.get("systemInstruction", {})
    parts = sys_inst.get("parts", [])
    assert any("qualitative" in p.get("text", "") for p in parts)


def test_parts_payload():
    captured_body: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_body
        captured_body = json.loads(request.content.decode("utf-8"))
        resp_data = _make_gemini_response({"label": "mixed", "reason": "PDF analysis."})
        return httpx.Response(200, json=resp_data)

    mock_http = httpx.Client(transport=httpx.MockTransport(handler))
    client = make_client("fake-key", httpx_client=mock_http)

    part = types.Part.from_bytes(data=b"%PDF-1.4 test", mime_type="application/pdf")
    generate_structured("prompt text", SampleSchema, parts=[part], client=client)

    contents = captured_body.get("contents", [])
    assert len(contents) >= 1
    content_parts = contents[0].get("parts", [])
    assert len(content_parts) == 2
    assert "inlineData" in content_parts[0]
    assert content_parts[1].get("text") == "prompt text"


def test_settings_gemini_api_key():
    base = {"SUPABASE_URL": "https://abc.supabase.co", "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_x"}
    s1 = load_settings(base)
    assert s1.gemini_api_key is None

    s2 = load_settings({**base, "GEMINI_API_KEY": "  ai-key-123  "})
    assert s2.gemini_api_key == "ai-key-123"

    s3 = load_settings({**base, "GEMINI_API_KEY": "   "})
    assert s3.gemini_api_key is None
