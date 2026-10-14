"""Tools: the ONLY way agents touch the outside world (Lesson 02).

Every call is policy-checked (guardrails.py) and traced (tracing.py).
NOTE: running tests in a subprocess with a stripped environment is a teaching sandbox,
not a security boundary. Production needs containers/VMs (see Lesson 08).
"""
from __future__ import annotations

import difflib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from .config import Settings
from .guardrails import check_write, scan_secrets
from .memory import KnowledgeBase
from .tracing import Tracer, clip

CODE_DIRS = ("src", "tests", "docs")

# (pattern, severity, label). "info" never raises risk; it just informs the human approver.
DANGEROUS_PATTERNS = [
    (re.compile(r"\beval\s*\("), "high", "use of eval()"),
    (re.compile(r"\bexec\s*\("), "high", "use of exec()"),
    (re.compile(r"os\.system\s*\("), "high", "os.system call"),
    (re.compile(r"shell\s*=\s*True"), "high", "subprocess with shell=True"),
    (re.compile(r"pickle\.loads?\s*\("), "medium", "pickle deserialization"),
    (re.compile(r"\brequests\.|\burllib\b|\bsocket\b"), "medium", "network access"),
    (re.compile(r"os\.environ|os\.getenv"), "info", "reads environment variables"),
]


class Toolbox:
    def __init__(self, settings: Settings, tracer: Tracer, sandbox: Path, kb: KnowledgeBase):
        self.settings = settings
        self.tracer = tracer
        self.sandbox = Path(sandbox)
        self.kb = kb

    def _log(self, agent: str, tool: str, msg: str, **data) -> None:
        self.tracer.emit("tool", agent, msg, tool=tool, **data)

    # -- retrieval ----------------------------------------------------------
    def search_kb(self, agent: str, query: str, k: int = 3) -> list[dict]:
        hits = self.kb.search(query, k)
        sources = sorted({h["source"] for h in hits})
        self._log(
            agent, "search_kb",
            f"knowledge search -> {len(hits)} passage(s) from {', '.join(sources) or 'nowhere'}",
            query=clip(query, 120), sources=sources,
        )
        return hits

    # -- files --------------------------------------------------------------
    def read_files(self, agent: str, prefixes) -> dict[str, str]:
        found: dict[str, str] = {}
        for prefix in prefixes:
            base = self.sandbox / prefix.rstrip("/")
            if not base.exists():
                continue
            for path in sorted(base.rglob("*")):
                if (
                    path.is_file()
                    and "__pycache__" not in path.parts
                    and path.suffix in (".py", ".md")
                    and path.stat().st_size > 0
                ):
                    found[path.relative_to(self.sandbox).as_posix()] = path.read_text(encoding="utf-8")
        self._log(agent, "read_files", f"read {len(found)} file(s)", paths=list(found))
        return found

    def write_files(self, role: str, files) -> tuple[list[str], list[str]]:
        """Atomic: if ANY file violates policy, NOTHING is written."""
        violations: list[str] = []
        clean: list[dict] = []
        for entry in files if isinstance(files, list) else []:
            if not (isinstance(entry, dict) and isinstance(entry.get("path"), str) and isinstance(entry.get("content"), str)):
                violations.append("malformed file entry (need string 'path' and 'content')")
                continue
            clean.append(entry)
            violations += check_write(role, entry["path"], entry["content"], self.settings.max_file_bytes)
        if not clean and not violations:
            violations.append("no files were produced")
        if violations:
            self.tracer.emit("guardrail", role, "BLOCKED: " + "; ".join(violations), violations=violations)
            return [], violations

        root = self.sandbox.resolve()
        written = []
        for entry in clean:
            dest = (self.sandbox / entry["path"]).resolve()
            if root not in dest.parents:  # defence in depth on top of check_write
                raise RuntimeError(f"sandbox escape attempt: {entry['path']}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("w", encoding="utf-8", newline="\n") as fh:
                fh.write(entry["content"])
            written.append(entry["path"])
        self._log(role, "write_files", f"wrote {', '.join(written)}", paths=written)
        return written, []

    # -- test runner --------------------------------------------------------
    def run_tests(self) -> dict:
        env = {k: os.environ[k] for k in ("PATH", "SYSTEMROOT", "TEMP", "TMP") if k in os.environ}
        env["PYTHONDONTWRITEBYTECODE"] = "1"  # note: API keys etc. are NOT inherited
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."],
                cwd=self.sandbox, capture_output=True, text=True,
                timeout=self.settings.test_timeout_s, env=env,
            )
            output = (proc.stderr + proc.stdout).strip()
            passed = proc.returncode == 0
        except subprocess.TimeoutExpired:
            output, passed = f"tests timed out after {self.settings.test_timeout_s}s", False
        ran = re.search(r"Ran (\d+) test", output)
        result = {"passed": passed, "ran": int(ran.group(1)) if ran else 0, "output": output[-1800:]}
        self._log(
            "tester", "run_tests",
            f"unittest: {'PASS' if passed else 'FAIL'} ({result['ran']} test(s))",
            passed=passed, ran=result["ran"],
        )
        return result

    # -- security scan ------------------------------------------------------
    def security_scan(self) -> tuple[list[dict], str]:
        findings: list[dict] = []
        for path, text in self.read_files("security", ["src"]).items():
            for lineno, line in enumerate(text.splitlines(), 1):
                for pattern, severity, label in DANGEROUS_PATTERNS:
                    if pattern.search(line):
                        findings.append({"file": path, "line": lineno, "severity": severity, "issue": label})
            for hit in scan_secrets(text):
                findings.append({"file": path, "line": 0, "severity": "high", "issue": hit})
        severities = {f["severity"] for f in findings}
        risk = "high" if "high" in severities else "medium" if "medium" in severities else "low"
        self._log("security", "scan", f"static scan: {len(findings)} finding(s), risk={risk}", findings=findings)
        return findings, risk

    # -- change management --------------------------------------------------
    def diff(self) -> list[dict]:
        changes = []
        for rel, new in self.read_files("orchestrator", CODE_DIRS).items():
            target = self.settings.workspace / rel
            old = target.read_text(encoding="utf-8") if target.exists() else None
            if old == new:
                continue
            text = "".join(
                difflib.unified_diff(
                    (old or "").splitlines(True), new.splitlines(True), fromfile=f"a/{rel}", tofile=f"b/{rel}"
                )
            )
            changes.append({"path": rel, "status": "added" if old is None else "modified", "diff": text})
        return changes

    def promote(self, changes: list[dict]) -> None:
        """Copy approved files from the run sandbox into the real workspace."""
        for change in changes:
            src = self.sandbox / change["path"]
            dest = self.settings.workspace / change["path"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
        self._log("orchestrator", "promote", f"promoted {len(changes)} file(s) to workspace", paths=[c["path"] for c in changes])
