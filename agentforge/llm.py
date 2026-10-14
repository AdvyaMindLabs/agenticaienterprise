"""LLM providers (Lesson 01). Agents only know the Provider interface, so swapping the
mock for real Claude changes zero agent code."""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass

from .config import Settings


@dataclass
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class Provider:
    name = "base"

    def complete(self, role: str, system: str, user: str) -> LLMResponse:
        raise NotImplementedError


class MockProvider(Provider):
    """Offline, deterministic, free. See mock_library.py for what it 'knows'."""

    name = "mock"

    def complete(self, role: str, system: str, user: str) -> LLMResponse:
        from .mock_library import respond

        text = respond(role, user)
        return LLMResponse(text, estimate_tokens(system + user), estimate_tokens(text))


class AnthropicProvider(Provider):
    """Real Claude via the Messages API, using only the standard library."""

    name = "anthropic"

    def __init__(self, api_key: str, model: str, base_url: str = "https://api.anthropic.com"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    def complete(self, role: str, system: str, user: str) -> LLMResponse:
        body = json.dumps(
            {
                "model": self.model,
                "max_tokens": 4096,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/v1/messages",
            data=body,
            method="POST",
            headers={
                "content-type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                data = json.load(response)
        except urllib.error.HTTPError as err:
            raise RuntimeError(f"Anthropic API error {err.code}: {err.read().decode()[:300]}") from err
        text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        usage = data.get("usage", {})
        return LLMResponse(text, usage.get("input_tokens", 0), usage.get("output_tokens", 0))


def get_provider(settings: Settings) -> Provider:
    if settings.provider == "anthropic":
        if not settings.api_key:
            raise ValueError("AGENTFORGE_PROVIDER=anthropic needs ANTHROPIC_API_KEY to be set")
        return AnthropicProvider(settings.api_key, settings.model, settings.base_url)
    if settings.provider == "mock":
        return MockProvider()
    raise ValueError(f"unknown provider '{settings.provider}' (use 'mock' or 'anthropic')")


def extract_json(text: str) -> dict:
    """Models wrap JSON in prose or code fences. Be liberal in what you accept,
    but always try the strict parse first (JSON *content* may itself contain code fences)."""
    candidate = text.strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass
    fenced = re.match(r"```(?:json)?\s*(.*?)\s*```\s*$", candidate, re.S)
    if fenced:
        candidate = fenced.group(1)
    start, end = candidate.find("{"), candidate.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object found in model output")
    return json.loads(candidate[start : end + 1])
