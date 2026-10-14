"""The agent team (Lesson 01). Each agent = a role, a system prompt, and a narrow job.

Agents never touch files or run code directly. They ask the model and return structured
data; the orchestrator and Toolbox do the acting under guardrails.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from .config import Settings
from .guardrails import Budget
from .llm import Provider, extract_json
from .memory import KnowledgeBase
from .tools import Toolbox
from .tracing import Tracer, clip


@dataclass
class RunContext:
    settings: Settings
    llm: Provider
    tracer: Tracer
    budget: Budget
    tools: Toolbox
    kb: KnowledgeBase
    ticket: dict


def files_block(files: dict[str, str]) -> str:
    if not files:
        return "(none)"
    return "\n".join(f"=== FILE: {p} ===\n{c}\n=== END FILE ===" for p, c in files.items())


class Agent:
    role = "agent"
    system = ""

    def __init__(self, ctx: RunContext):
        self.ctx = ctx

    # Shared ticket header. The mock provider parses these exact field names.
    def _ticket(self) -> str:
        t = self.ctx.ticket
        body = " ".join(str(t.get("description", "")).split())
        return f"TICKET_TITLE: {t.get('title', '')}\nTICKET_BODY: {body}"

    def ask(self, user: str) -> dict:
        ctx = self.ctx
        for _ in range(2):  # one repair attempt if the model returns bad JSON
            ctx.tracer.emit("llm", self.role, f"{self.role} -> {ctx.llm.name} model (prompt {len(user)} chars)")
            response = ctx.llm.complete(self.role, self.system, user)
            ctx.budget.charge(response.input_tokens + response.output_tokens)
            ctx.tracer.emit(
                "llm", self.role, f"{ctx.llm.name} model -> {self.role} ({response.output_tokens} tokens)",
                input_tokens=response.input_tokens, output_tokens=response.output_tokens,
                preview=clip(response.text, 400),
            )
            try:
                return extract_json(response.text)
            except ValueError:
                user += "\n\nYour previous reply was not valid JSON. Reply with a single JSON object only."
        raise ValueError(f"{self.role}: model did not return valid JSON")


class Planner(Agent):
    role = "planner"
    system = (
        "You are the Planner on a software engineering team. Read the ticket and the team standards, then reply "
        "with ONLY a JSON object: {\"summary\": str, \"files\": [{\"path\": str, \"purpose\": str}], "
        "\"steps\": [str], \"risk_notes\": str}. Rules: Python 3.10+ standard library only. Implementation files "
        "live in src/, tests in tests/, imported as `from src.<module> import <name>`. If the ticket cannot be "
        "done within these constraints, return {\"summary\": str, \"files\": [], \"steps\": [], \"unsupported\": true}."
    )

    def run(self) -> dict:
        t = self.ctx.ticket
        hits = self.ctx.tools.search_kb(self.role, f"{t.get('title', '')} {t.get('description', '')}")
        standards = "\n\n".join(f"[{h['source']}] {h['text']}" for h in hits) or "(none found)"
        return self.ask(f"{self._ticket()}\n\nRELEVANT STANDARDS AND HISTORY:\n{standards}\n\nProduce the plan.")


class Tester(Agent):
    role = "tester"
    system = (
        "You are the Tester. Write unittest files BEFORE the implementation exists (test-driven development). "
        "Reply with ONLY JSON: {\"files\": [{\"path\": \"tests/test_<name>.py\", \"content\": str}]}. Cover normal "
        "and edge cases. You may write only under tests/."
    )

    def run(self, plan: dict) -> list[dict]:
        hits = self.ctx.tools.search_kb(self.role, "testing standards unittest edge cases")
        standards = "\n\n".join(f"[{h['source']}] {h['text']}" for h in hits)
        result = self.ask(f"{self._ticket()}\n\nPLAN: {json.dumps(plan)}\n\nSTANDARDS:\n{standards}\n\nWrite the tests.")
        return result.get("files", [])


class Coder(Agent):
    role = "coder"
    system = (
        "You are the Coder. Implement the plan so the existing tests pass. Reply with ONLY JSON: "
        "{\"files\": [{\"path\": \"src/<name>.py\", \"content\": str}]}. You may write only under src/. Follow the "
        "team standards: docstrings and type hints on public functions, no hardcoded secrets (read them from "
        "environment variables), no eval/exec. If FEEDBACK is present, fix exactly what it reports."
    )

    def run(self, plan: dict, attempt: int, feedback: str, tests: dict[str, str]) -> list[dict]:
        hits = self.ctx.tools.search_kb(self.role, "coding standards security secrets docstrings type hints")
        standards = "\n\n".join(f"[{h['source']}] {h['text']}" for h in hits)
        user = (
            f"{self._ticket()}\nATTEMPT: {attempt}\n\nPLAN: {json.dumps(plan)}\n\n"
            f"TESTS THAT MUST PASS:\n{files_block(tests)}\n\nSTANDARDS:\n{standards}\n\n"
            f"FEEDBACK FROM LAST ATTEMPT:\n{feedback or '(none: first attempt)'}\n\nWrite the implementation."
        )
        return self.ask(user).get("files", [])


class Reviewer(Agent):
    role = "reviewer"
    system = (
        "You are the Reviewer. Check the source files against the team standards. Reply with ONLY JSON: "
        "{\"approved\": bool, \"comments\": [str]}. Reject if public functions lack docstrings or type hints."
    )

    def run(self, sources: dict[str, str]) -> dict:
        hits = self.ctx.tools.search_kb(self.role, "code review standards docstrings type hints")
        standards = "\n\n".join(f"[{h['source']}] {h['text']}" for h in hits)
        result = self.ask(f"{self._ticket()}\n\nSTANDARDS:\n{standards}\n\nFILES TO REVIEW:\n{files_block(sources)}")
        return {"approved": bool(result.get("approved")), "comments": [str(c) for c in result.get("comments", [])]}


class SecurityAgent(Agent):
    role = "security"
    system = (
        "You are the Security agent. You receive findings from a static scanner. Reply with ONLY JSON: "
        "{\"summary\": str}, a two-sentence plain-English assessment for a human approver."
    )

    def run(self) -> dict:
        findings, risk = self.ctx.tools.security_scan()  # deterministic: the scanner decides risk, not the LLM
        result = self.ask(f"{self._ticket()}\nFINDINGS_JSON: {json.dumps(findings)}")
        return {"risk": risk, "findings": findings, "summary": str(result.get("summary", ""))}


class DocsAgent(Agent):
    role = "docs"
    system = (
        "You are the Docs agent. Write a short markdown doc for the new code. Reply with ONLY JSON: "
        "{\"path\": \"docs/<name>.md\", \"content\": str}. You may write only under docs/."
    )

    def run(self, plan: dict, sources: dict[str, str]) -> list[dict]:
        result = self.ask(f"{self._ticket()}\n\nPLAN: {json.dumps(plan)}\n\nCODE:\n{files_block(sources)}")
        return [{"path": result.get("path", ""), "content": result.get("content", "")}]
