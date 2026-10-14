"""Central settings. Everything tunable lives here so lessons can point at one file."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Settings:
    root: Path = PROJECT_ROOT
    # "mock" = scripted, offline, free, deterministic. "anthropic" = real Claude.
    provider: str = field(default_factory=lambda: os.getenv("AGENTFORGE_PROVIDER", "mock"))
    # Model names change over time: check Anthropic's docs for the current list.
    model: str = field(default_factory=lambda: os.getenv("AGENTFORGE_MODEL", "claude-sonnet-5-5"))
    api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    # Override to point at a gateway/proxy (or a local fake in tests).
    base_url: str = field(default_factory=lambda: os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com"))

    # Guardrail budgets (Lesson 04)
    max_attempts: int = 3            # coder/test/review retries per ticket
    max_llm_calls: int = 40          # hard stop on model calls per run
    max_tokens_total: int = 80_000   # hard stop on tokens per run
    test_timeout_s: int = 20
    approval_timeout_s: int = 3600
    max_file_bytes: int = 50_000

    @property
    def workspace(self) -> Path:
        return self.root / "workspace"

    @property
    def runs_dir(self) -> Path:
        return self.root / "runs"

    @property
    def knowledge_dir(self) -> Path:
        return self.root / "knowledge"

    @property
    def tickets_file(self) -> Path:
        return self.root / "tickets" / "samples.json"
