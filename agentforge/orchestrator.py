"""The orchestrator: a state machine that routes work between agents (Lesson 05).

plan -> tests -> [code -> verify -> review]x(max_attempts) -> security -> docs -> approval -> promote

Key idea: the LLM never decides control flow. Plain Python does, so behaviour is
predictable, testable and auditable. Models only fill in the *content* of each step.
"""
from __future__ import annotations

import json
import shutil
import time
import uuid
from pathlib import Path
from typing import Callable

from .agents import Coder, DocsAgent, Planner, Reviewer, RunContext, SecurityAgent, Tester
from .config import Settings
from .guardrails import Budget, BudgetExceeded
from .llm import Provider, get_provider
from .memory import KnowledgeBase
from .tools import Toolbox
from .tracing import Tracer

STAGES = ["plan", "tests", "code", "verify", "review", "security", "docs", "approval", "promote"]
TERMINAL = {"completed", "rejected", "failed"}


class RunFailed(Exception):
    pass


def new_run_id() -> str:
    return time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:5]


def auto_approver(record: dict) -> dict:
    """Policy approver: only LOW-risk changes may skip a human."""
    risk = (record.get("security") or {}).get("risk", "high")
    if risk == "low":
        return {"approved": True, "by": "policy:auto-approve-low-risk", "note": ""}
    return {"approved": False, "by": "policy", "note": f"risk={risk} requires a human reviewer"}


class Orchestrator:
    def __init__(self, settings: Settings | None = None, provider: Provider | None = None):
        self.settings = settings or Settings()
        self.provider = provider or get_provider(self.settings)

    def run(
        self,
        ticket: dict,
        run_id: str | None = None,
        approver: Callable[[dict], dict] | None = None,
        on_update: Callable[[dict], None] | None = None,
        on_event: Callable[[dict], None] | None = None,
    ) -> dict:
        s = self.settings
        run_id = run_id or new_run_id()
        run_dir = s.runs_dir / run_id
        sandbox = run_dir / "sandbox"
        if run_dir.exists():
            shutil.rmtree(run_dir)
        shutil.copytree(s.workspace, sandbox, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

        tracer = Tracer(run_dir / "trace.jsonl", run_id, on_event)
        kb = KnowledgeBase(s.knowledge_dir)
        budget = Budget(s.max_llm_calls, s.max_tokens_total)
        tools = Toolbox(s, tracer, sandbox, kb)
        ctx = RunContext(s, self.provider, tracer, budget, tools, kb, ticket)

        record: dict = {
            "id": run_id, "ticket": ticket, "status": "running", "stage": "queued",
            "provider": self.provider.name, "model": s.model if self.provider.name == "anthropic" else "scripted-mock",
            "attempts": 0, "guardrail_blocks": 0, "plan": None, "tests": None, "review": None,
            "security": None, "changes": [], "approval": None, "error": None,
            "started": time.time(), "finished": None, "usage": {"llm_calls": 0, "tokens": 0},
        }

        def save() -> None:
            record["usage"] = {"llm_calls": budget.calls, "tokens": budget.tokens}
            (run_dir / "run.json").write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")
            if on_update:
                on_update(record)

        def stage(name: str) -> None:
            record["stage"] = name
            tracer.emit("stage", "orchestrator", f"stage: {name}", stage=name)
            save()

        tracer.emit("run", "orchestrator", f"run {run_id}: {ticket.get('title', '')}")
        save()
        try:
            # 1. PLAN ---------------------------------------------------------
            stage("plan")
            plan = Planner(ctx).run()
            record["plan"] = plan
            if plan.get("unsupported") or not plan.get("files"):
                raise RunFailed(
                    "The Planner could not produce an actionable plan. The mock provider only has scripted "
                    "solutions for the sample tickets; set AGENTFORGE_PROVIDER=anthropic for arbitrary tickets."
                )

            # 2. TESTS FIRST (TDD) ---------------------------------------------
            stage("tests")
            _, violations = tools.write_files("tester", Tester(ctx).run(plan))
            if violations:
                raise RunFailed("Tester blocked by guardrails: " + "; ".join(violations))
            tests = tools.read_files("coder", ["tests"])

            # 3. IMPLEMENT / VERIFY / REVIEW LOOP ------------------------------
            feedback, success = "", False
            for attempt in range(1, s.max_attempts + 1):
                record["attempts"] = attempt
                tracer.emit("attempt", "orchestrator", f"attempt {attempt}/{s.max_attempts}", attempt=attempt)

                stage("code")
                _, violations = tools.write_files("coder", Coder(ctx).run(plan, attempt, feedback, tests))
                if violations:
                    record["guardrail_blocks"] += 1
                    feedback = "Guardrails blocked your last output:\n- " + "\n- ".join(violations)
                    continue

                stage("verify")
                record["tests"] = tools.run_tests()
                if not record["tests"]["passed"]:
                    feedback = "The tests failed:\n" + record["tests"]["output"]
                    continue

                stage("review")
                record["review"] = Reviewer(ctx).run(tools.read_files("reviewer", ["src"]))
                if not record["review"]["approved"]:
                    feedback = "The reviewer rejected the change:\n- " + "\n- ".join(record["review"]["comments"])
                    continue
                success = True
                break
            if not success:
                raise RunFailed(f"No passing, compliant implementation after {s.max_attempts} attempts. Last feedback: {feedback[:300]}")

            # 4. SECURITY GATE -------------------------------------------------
            stage("security")
            record["security"] = SecurityAgent(ctx).run()
            if record["security"]["risk"] == "high":
                raise RunFailed("Blocked by security gate: " + record["security"]["summary"])

            # 5. DOCS ----------------------------------------------------------
            stage("docs")
            sources = tools.read_files("docs", ["src"])
            _, violations = tools.write_files("docs", DocsAgent(ctx).run(plan, sources))
            if violations:
                raise RunFailed("Docs agent blocked by guardrails: " + "; ".join(violations))

            # 6. HUMAN APPROVAL ------------------------------------------------
            stage("approval")
            record["changes"] = tools.diff()
            record["status"] = "awaiting_approval"
            tracer.emit("approval", "orchestrator", f"awaiting approval: {len(record['changes'])} file change(s), risk={record['security']['risk']}")
            save()
            decision = approver(record) if approver else {"approved": False, "by": "system", "note": "no approver configured"}
            record["approval"] = decision
            record["status"] = "running"
            tracer.emit("approval", decision.get("by", "human"), f"{'APPROVED' if decision['approved'] else 'REJECTED'} by {decision.get('by')}: {decision.get('note') or 'no note'}")

            # 7. PROMOTE -------------------------------------------------------
            if decision["approved"]:
                stage("promote")
                tools.promote(record["changes"])
                record["status"] = "completed"
            else:
                record["status"] = "rejected"

        except (RunFailed, BudgetExceeded) as err:
            record["status"], record["error"] = "failed", str(err)
            tracer.emit("error", "orchestrator", f"FAILED: {err}")
        except Exception as err:  # unexpected: still leave a trace
            record["status"], record["error"] = "failed", f"{type(err).__name__}: {err}"
            tracer.emit("error", "orchestrator", f"FAILED: {type(err).__name__}: {err}")
        finally:
            record["finished"] = time.time()
            tracer.emit("run", "orchestrator", f"run finished: {record['status']}", status=record["status"])
            save()
        return record
