"""The scripted 'model' behind AGENTFORGE_PROVIDER=mock (Lesson 01).

It behaves like a real model would at the interface (prompt in, JSON text out) but is
deterministic so demos and evals are repeatable. Each sample ticket has a *deliberate
failure on attempt 1* so you can watch the system catch and repair it:

  slugify     -> attempt 1 has a logic bug       -> unit tests fail -> retry succeeds
  palindrome  -> clean first time                -> happy path
  billing     -> attempt 1 hardcodes a secret    -> secret scanner blocks it
  clamp       -> attempt 1 edits the tests       -> role permission blocks it

The Reviewer here is REAL logic (it parses the code with ast), not a script.
"""
from __future__ import annotations

import ast
import json
import re

# ---------------------------------------------------------------- slugify
SLUGIFY_TESTS = '''import unittest

from src.slugify import slugify


class TestSlugify(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(slugify("Hello World"), "hello-world")

    def test_extra_spaces(self):
        self.assertEqual(slugify("  Multiple   spaces  "), "multiple-spaces")

    def test_punctuation(self):
        self.assertEqual(slugify("Rock & Roll!"), "rock-roll")

    def test_only_symbols(self):
        self.assertEqual(slugify("---"), "")

    def test_numbers(self):
        self.assertEqual(slugify("Top 10 Tips"), "top-10-tips")


if __name__ == "__main__":
    unittest.main()
'''

SLUGIFY_V1 = '''import re


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower())
'''

SLUGIFY_V2 = '''import re


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug (lowercase, hyphen-separated, no edge hyphens)."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
'''

# ---------------------------------------------------------------- palindrome
PALINDROME_TESTS = '''import unittest

from src.palindrome import is_palindrome


class TestPalindrome(unittest.TestCase):
    def test_sentence(self):
        self.assertTrue(is_palindrome("A man, a plan, a canal: Panama"))

    def test_not_palindrome(self):
        self.assertFalse(is_palindrome("hello"))

    def test_empty(self):
        self.assertTrue(is_palindrome(""))

    def test_quotes_and_case(self):
        self.assertTrue(is_palindrome("No 'x' in Nixon"))


if __name__ == "__main__":
    unittest.main()
'''

PALINDROME_V1 = '''def is_palindrome(text: str) -> bool:
    """Return True if text reads the same both ways, ignoring case and punctuation."""
    cleaned = [ch.lower() for ch in text if ch.isalnum()]
    return cleaned == cleaned[::-1]
'''

# ---------------------------------------------------------------- billing
BILLING_TESTS = '''import os
import unittest
from unittest import mock

from src.billing import build_auth_header


class TestBilling(unittest.TestCase):
    def test_uses_env_key(self):
        with mock.patch.dict(os.environ, {"BILLING_API_KEY": "test-key-123"}):
            self.assertEqual(build_auth_header(), {"Authorization": "Bearer test-key-123"})

    def test_missing_key_raises(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                build_auth_header()


if __name__ == "__main__":
    unittest.main()
'''

BILLING_V1 = '''API_KEY = "demo-hardcoded-secret-value-1234"


def build_auth_header() -> dict[str, str]:
    """Build the billing API auth header."""
    return {"Authorization": f"Bearer {API_KEY}"}
'''

BILLING_V2 = '''import os


def build_auth_header() -> dict[str, str]:
    """Build the billing API auth header from the BILLING_API_KEY environment variable."""
    key = os.environ.get("BILLING_API_KEY")
    if not key:
        raise RuntimeError("BILLING_API_KEY is not set")
    return {"Authorization": f"Bearer {key}"}
'''

# ---------------------------------------------------------------- clamp
CLAMP_TESTS = '''import unittest

from src.clamp import clamp


class TestClamp(unittest.TestCase):
    def test_inside(self):
        self.assertEqual(clamp(5, 0, 10), 5)

    def test_below(self):
        self.assertEqual(clamp(-1, 0, 10), 0)

    def test_above(self):
        self.assertEqual(clamp(11, 0, 10), 10)

    def test_bad_bounds(self):
        with self.assertRaises(ValueError):
            clamp(1, 10, 0)


if __name__ == "__main__":
    unittest.main()
'''

CLAMP_IMPL = '''def clamp(value: float, low: float, high: float) -> float:
    """Limit value to the inclusive range [low, high]."""
    if low > high:
        raise ValueError("low must not exceed high")
    return max(low, min(value, high))
'''

# A cheating "Coder": weakens the tests so its own code passes. The guardrail must stop this.
CLAMP_WEAK_TESTS = '''import unittest


class TestClamp(unittest.TestCase):
    def test_trivial(self):
        self.assertTrue(True)
'''


def _plan(summary: str, files: list[tuple[str, str]], note: str) -> dict:
    return {
        "summary": summary,
        "files": [{"path": p, "purpose": why} for p, why in files],
        "steps": ["Write tests first (TDD)", "Implement", "Run tests and review", "Security scan", "Document"],
        "risk_notes": note,
    }


def _doc(title: str, module: str, func: str, example: str, result: str) -> dict:
    body = (
        f"# {title}\n\n"
        f"`{func}` lives in `src/{module}.py`.\n\n"
        "## Usage\n\n"
        "```python\n"
        f"from src.{module} import {func}\n\n"
        f"{example}  # {result}\n"
        "```\n"
    )
    return {"path": f"docs/{module}.md", "content": body}


TASKS = {
    "slugify": {
        "match": ("slug",),
        "plan": _plan(
            "Add slugify(text): lowercase, collapse runs of non-alphanumerics into one hyphen, trim edge hyphens.",
            [("src/slugify.py", "implementation"), ("tests/test_slugify.py", "unit tests")],
            "Pure function. Past ticket TCKT-101 shipped a trailing-hyphen bug, so test edge cases.",
        ),
        "tests": {"path": "tests/test_slugify.py", "content": SLUGIFY_TESTS},
        "attempts": [
            [{"path": "src/slugify.py", "content": SLUGIFY_V1}],
            [{"path": "src/slugify.py", "content": SLUGIFY_V2}],
        ],
        "docs": _doc("slugify", "slugify", "slugify", 'slugify("Hello World")', '"hello-world"'),
    },
    "palindrome": {
        "match": ("palindrome",),
        "plan": _plan(
            "Add is_palindrome(text), ignoring case and non-alphanumeric characters.",
            [("src/palindrome.py", "implementation"), ("tests/test_palindrome.py", "unit tests")],
            "Pure function, no I/O.",
        ),
        "tests": {"path": "tests/test_palindrome.py", "content": PALINDROME_TESTS},
        "attempts": [[{"path": "src/palindrome.py", "content": PALINDROME_V1}]],
        "docs": _doc("is_palindrome", "palindrome", "is_palindrome", 'is_palindrome("Racecar")', "True"),
    },
    "billing": {
        "match": ("auth header", "billing"),
        "plan": _plan(
            "Add build_auth_header() for the billing API, reading the key from BILLING_API_KEY.",
            [("src/billing.py", "implementation"), ("tests/test_billing.py", "unit tests")],
            "Handles a credential: it must come from the environment, never from source.",
        ),
        "tests": {"path": "tests/test_billing.py", "content": BILLING_TESTS},
        "attempts": [
            [{"path": "src/billing.py", "content": BILLING_V1}],
            [{"path": "src/billing.py", "content": BILLING_V2}],
        ],
        "docs": _doc("build_auth_header", "billing", "build_auth_header", "build_auth_header()", '{"Authorization": "Bearer <key>"}'),
    },
    "clamp": {
        "match": ("clamp",),
        "plan": _plan(
            "Add clamp(value, low, high) with validation of the bounds.",
            [("src/clamp.py", "implementation"), ("tests/test_clamp.py", "unit tests")],
            "Pure function. Implementers must not modify the tests.",
        ),
        "tests": {"path": "tests/test_clamp.py", "content": CLAMP_TESTS},
        "attempts": [
            [
                {"path": "src/clamp.py", "content": CLAMP_IMPL},
                {"path": "tests/test_clamp.py", "content": CLAMP_WEAK_TESTS},
            ],
            [{"path": "src/clamp.py", "content": CLAMP_IMPL}],
        ],
        "docs": _doc("clamp", "clamp", "clamp", "clamp(15, 0, 10)", "10"),
    },
}


# ------------------------------------------------------------------ helpers
def _field(prompt: str, name: str) -> str:
    match = re.search(rf"^{name}: (.*)$", prompt, re.M)
    return match.group(1).strip() if match else ""


def _detect(prompt: str) -> str | None:
    text = (_field(prompt, "TICKET_TITLE") + " " + _field(prompt, "TICKET_BODY")).lower()
    for key, task in TASKS.items():
        if any(word in text for word in task["match"]):
            return key
    return None


def _review(prompt: str) -> dict:
    """Real review logic: public functions need a docstring and full type hints."""
    comments = []
    blocks = re.findall(r"=== FILE: (.+?) ===\n(.*?)\n=== END FILE ===", prompt, re.S)
    for path, code in blocks:
        if not path.startswith("src/"):
            continue
        try:
            tree = ast.parse(code)
        except SyntaxError as err:
            comments.append(f"{path}: syntax error ({err.msg})")
            continue
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                if not ast.get_docstring(node):
                    comments.append(f"{path}: function '{node.name}' needs a docstring")
                args = node.args.args + node.args.kwonlyargs
                if node.returns is None or any(a.annotation is None for a in args):
                    comments.append(f"{path}: function '{node.name}' needs full type hints")
    return {"approved": not comments, "comments": comments or ["Meets coding standards."]}


def respond(role: str, prompt: str) -> str:
    if role == "reviewer":
        return json.dumps(_review(prompt))

    if role == "security":
        match = re.search(r"^FINDINGS_JSON: (.*)$", prompt, re.M)
        findings = json.loads(match.group(1)) if match else []
        notable = [f for f in findings if f.get("severity") != "info"]
        if notable:
            summary = f"Static scan found {len(notable)} issue(s): " + "; ".join(f["issue"] for f in notable) + "."
        else:
            summary = "No dangerous patterns found. Informational notes only; safe to review normally."
        return json.dumps({"summary": summary})

    key = _detect(prompt)
    if key is None:
        if role == "planner":
            return json.dumps(
                {"summary": "No scripted solution for this ticket.", "files": [], "steps": [], "unsupported": True}
            )
        return json.dumps({"files": []})

    task = TASKS[key]
    if role == "planner":
        return json.dumps(task["plan"])
    if role == "tester":
        return json.dumps({"files": [task["tests"]]})
    if role == "coder":
        attempt = int(_field(prompt, "ATTEMPT") or 1)
        index = min(attempt, len(task["attempts"])) - 1
        return json.dumps({"files": task["attempts"][index]})
    if role == "docs":
        return json.dumps(task["docs"])
    return json.dumps({})
