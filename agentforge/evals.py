"""Evaluation harness (Lesson 07): how you test a non-deterministic system.

Each sample ticket carries expectations. We run every ticket N times (real models vary
run to run, so one pass proves little) and report pass counts, not just percentages.
Runs happen in a throwaway copy of the project so evals never pollute your workspace.
"""
from __future__ import annotations

import dataclasses
import json
import shutil
import tempfile
import time
from pathlib import Path
from typing import Callable

from .config import Settings
from .orchestrator import Orchestrator, auto_approver


def _check(name: str, ok: bool, detail: str = "") -> dict:
    return {"name": name, "ok": bool(ok), "detail": detail}


def evaluate(sample: dict, record: dict) -> list[dict]:
    expect = sample.get("expect", {})
    checks = [_check("status", record["status"] == expect.get("status", "completed"),
                     f"got {record['status']}, expected {expect.get('status', 'completed')}")]
    if expect.get("status", "completed") == "completed":
        checks.append(_check("tests_passed", bool(record.get("tests") and record["tests"]["passed"]), "unit tests green"))
    checks.append(_check("attempts", record["attempts"] <= expect.get("attempts_max", 3),
                         f"{record['attempts']} attempt(s), max {expect.get('attempts_max', 3)}"))
    checks.append(_check("guardrails", record["guardrail_blocks"] >= expect.get("guardrail_blocks_min", 0),
                         f"{record['guardrail_blocks']} block(s), min {expect.get('guardrail_blocks_min', 0)}"))
    return checks


def run_evals(
    settings: Settings, repeat: int = 1, log: Callable[[str], None] = print, only: str | None = None
) -> dict:
    samples = json.loads(settings.tickets_file.read_text(encoding="utf-8"))
    if settings.provider != "mock":
        samples = [s for s in samples if not s.get("mock_only")]
    if only:
        samples = [s for s in samples if s["id"] == only]

    results = []
    for sample in samples:
        for i in range(1, repeat + 1):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                shutil.copytree(settings.knowledge_dir, root / "knowledge")
                for package in ("src", "tests"):  # pristine workspace: demo leftovers must not skew scores
                    (root / "workspace" / package).mkdir(parents=True)
                    (root / "workspace" / package / "__init__.py").write_text("")
                local = dataclasses.replace(settings, root=root)
                record = Orchestrator(local).run(
                    {"title": sample["title"], "description": sample["description"]}, approver=auto_approver
                )
            checks = evaluate(sample, record)
            passed = all(c["ok"] for c in checks)
            results.append({
                "ticket_id": sample["id"], "run": i, "passed": passed, "checks": checks,
                "status": record["status"], "attempts": record["attempts"],
                "llm_calls": record["usage"]["llm_calls"], "tokens": record["usage"]["tokens"],
            })
            log(f"  {'PASS' if passed else 'FAIL'}  {sample['id']:<11} run {i}/{repeat}  "
                f"status={record['status']:<9} attempts={record['attempts']} "
                f"calls={record['usage']['llm_calls']} tokens={record['usage']['tokens']}")

    by_ticket: dict[str, dict] = {}
    for r in results:
        entry = by_ticket.setdefault(r["ticket_id"], {"passed": 0, "runs": 0})
        entry["runs"] += 1
        entry["passed"] += int(r["passed"])
    summary = {
        "passed": sum(e["passed"] for e in by_ticket.values()),
        "total": sum(e["runs"] for e in by_ticket.values()),
        "by_ticket": by_ticket,
        "avg_tokens": round(sum(r["tokens"] for r in results) / len(results)) if results else 0,
    }
    report = {"provider": settings.provider, "finished": time.time(), "repeat": repeat, "summary": summary, "results": results}
    settings.runs_dir.mkdir(parents=True, exist_ok=True)
    (settings.runs_dir / "evals_latest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
