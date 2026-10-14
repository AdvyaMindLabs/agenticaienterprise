"""Guardrails: the rules agents cannot talk their way around (Lesson 04).

Four layers, all deterministic code (never "please be careful" in a prompt):
  1. Path + role permissions  - who may write where
  2. Secret scanning          - nothing credential-shaped gets written
  3. Budgets                  - hard caps on model calls and tokens
  4. Approval gate            - a human decides before anything leaves the sandbox
"""
from __future__ import annotations

import re
import threading
from pathlib import PurePosixPath


class BudgetExceeded(Exception):
    pass


# ---- 2. Secret scanning ---------------------------------------------------
SECRET_PATTERNS = {
    "AWS access key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "Private key block": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "Hardcoded credential": re.compile(
        r"""(?i)(?:api[_-]?key|secret|token|passwd|password)\w*\s*[=:]\s*['"][^'"\s]{12,}['"]"""
    ),
}


def scan_secrets(text: str) -> list[str]:
    hits = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for name, pattern in SECRET_PATTERNS.items():
            if pattern.search(line):
                hits.append(f"{name} on line {lineno}")
    return hits


# ---- 1. Path + role permissions -------------------------------------------
# Least privilege: the Coder can never edit tests, the Tester can never edit src.
ROLE_WRITE_PREFIXES = {
    "tester": ("tests/",),
    "coder": ("src/",),
    "docs": ("docs/",),
}


def check_write(role: str, rel_path: str, content: str, max_bytes: int = 50_000) -> list[str]:
    """Return a list of violations (empty list = allowed)."""
    normalized = rel_path.replace("\\", "/")
    parts = PurePosixPath(normalized).parts
    if (
        normalized.startswith(("/", "~"))
        or (len(normalized) > 1 and normalized[1] == ":")
        or ".." in parts
        or not normalized.strip()
    ):
        return [f"path '{rel_path}' escapes the sandbox"]

    problems = []
    allowed = ROLE_WRITE_PREFIXES.get(role, ())
    if not any(normalized.startswith(prefix) for prefix in allowed):
        problems.append(
            f"role '{role}' may not write '{rel_path}' (allowed: {', '.join(allowed) or 'nothing'})"
        )
    if len(content.encode("utf-8")) > max_bytes:
        problems.append(f"'{rel_path}' exceeds the {max_bytes}-byte file limit")
    for hit in scan_secrets(content):
        problems.append(f"secret detected in '{rel_path}': {hit}")
    return problems


# ---- 3. Budgets ------------------------------------------------------------
class Budget:
    def __init__(self, max_calls: int, max_tokens: int):
        self.max_calls = max_calls
        self.max_tokens = max_tokens
        self.calls = 0
        self.tokens = 0

    def charge(self, tokens: int) -> None:
        self.calls += 1
        self.tokens += tokens
        if self.calls > self.max_calls:
            raise BudgetExceeded(f"model-call budget exceeded ({self.max_calls})")
        if self.tokens > self.max_tokens:
            raise BudgetExceeded(f"token budget exceeded ({self.max_tokens})")


# ---- 4. Approval gate -------------------------------------------------------
class ApprovalGate:
    """Blocks a run thread until a human decides (used by the web dashboard)."""

    def __init__(self) -> None:
        self._event = threading.Event()
        self._decision: dict | None = None

    def decide(self, approved: bool, by: str = "human", note: str = "") -> None:
        self._decision = {"approved": bool(approved), "by": by, "note": note}
        self._event.set()

    def wait(self, timeout: float) -> dict:
        if self._event.wait(timeout) and self._decision:
            return self._decision
        return {"approved": False, "by": "system", "note": "approval timed out"}
