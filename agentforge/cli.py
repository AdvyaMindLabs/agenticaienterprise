"""Command line interface: python -m agentforge <command>"""
from __future__ import annotations

import argparse
import json
import shutil
import sys

from .config import Settings
from .evals import run_evals
from .orchestrator import Orchestrator, auto_approver
from .tracing import load_trace


def _print_event(ev: dict) -> None:
    tag = {"stage": ">>", "guardrail": "!!", "error": "XX", "approval": "??", "attempt": "<>"}.get(ev["type"], "  ")
    print(f"[{ev['t']:6.2f}s] {ev['agent'] or '':<13} {tag} {ev['msg']}")


def _cli_approver(record: dict) -> dict:
    risk = record["security"]["risk"]
    print("\n===== APPROVAL REQUIRED =====")
    print(f"Security risk: {risk}. {record['security']['summary']}")
    for change in record["changes"]:
        print(f"  {change['status']:<9} {change['path']}")
    if not sys.stdin.isatty():
        return {"approved": False, "by": "cli", "note": "non-interactive session; re-run with --auto-approve"}
    answer = input("Approve and promote these changes to workspace/? [y/N] ").strip().lower()
    return {"approved": answer == "y", "by": "cli-user", "note": ""}


def cmd_run(args, settings: Settings) -> int:
    if args.sample:
        samples = {s["id"]: s for s in json.loads(settings.tickets_file.read_text(encoding="utf-8"))}
        if args.sample not in samples:
            print(f"Unknown sample '{args.sample}'. Choose from: {', '.join(samples)}")
            return 2
        ticket = samples[args.sample]
    elif args.title:
        ticket = {"title": args.title, "description": args.description or ""}
    else:
        print("Provide --sample <id> or --title '...' [--description '...']")
        return 2
    approver = auto_approver if args.auto_approve else _cli_approver
    record = Orchestrator(settings).run(ticket, approver=approver, on_event=_print_event)
    print("\n===== RESULT =====")
    print(f"status:   {record['status']}" + (f"  ({record['error']})" if record["error"] else ""))
    print(f"attempts: {record['attempts']}   guardrail blocks: {record['guardrail_blocks']}")
    print(f"usage:    {record['usage']['llm_calls']} model calls, ~{record['usage']['tokens']} tokens")
    print(f"trace:    python -m agentforge trace {record['id']}")
    return 0 if record["status"] in ("completed", "rejected") else 1


def cmd_eval(args, settings: Settings) -> int:
    print(f"Running eval suite (provider={settings.provider}, repeat={args.repeat})")
    report = run_evals(settings, repeat=args.repeat, only=args.only)
    s = report["summary"]
    print(f"\nSCORE: {s['passed']}/{s['total']} runs passed   (avg {s['avg_tokens']} tokens/run)")
    for ticket_id, entry in s["by_ticket"].items():
        print(f"  {ticket_id:<11} {entry['passed']}/{entry['runs']}")
    return 0 if s["passed"] == s["total"] else 1


def cmd_trace(args, settings: Settings) -> int:
    events = load_trace(settings.runs_dir / args.run_id / "trace.jsonl")
    if not events:
        print(f"No trace found for run '{args.run_id}'")
        return 2
    for ev in events:
        _print_event(ev)
    return 0


def cmd_serve(args, settings: Settings) -> int:
    from .server import serve

    serve(settings, args.host, args.port)
    return 0


def cmd_reset(args, settings: Settings) -> int:
    if not args.yes and input("Delete runs/ and generated files in workspace/? [y/N] ").strip().lower() != "y":
        return 1
    shutil.rmtree(settings.runs_dir, ignore_errors=True)
    keep = {"__init__.py"}
    for sub in ("src", "tests", "docs"):
        folder = settings.workspace / sub
        if not folder.exists():
            continue
        for path in folder.iterdir():
            if path.name in keep:
                continue
            shutil.rmtree(path) if path.is_dir() else path.unlink()
    print("Demo state reset.")
    return 0


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass
    parser = argparse.ArgumentParser(prog="agentforge", description="A multi-agent engineering team you can run, trace and break.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("run", help="run one ticket through the agent team")
    p.add_argument("--sample", help="id from tickets/samples.json")
    p.add_argument("--title")
    p.add_argument("--description")
    p.add_argument("--auto-approve", action="store_true", help="auto-approve LOW-risk changes (policy approver)")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("serve", help="start the API + dashboard")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.set_defaults(func=cmd_serve)

    p = sub.add_parser("eval", help="run the evaluation suite")
    p.add_argument("--repeat", type=int, default=1, help="runs per ticket (use >1 with a real model)")
    p.add_argument("--only", help="run a single ticket id")
    p.set_defaults(func=cmd_eval)

    p = sub.add_parser("trace", help="print the trace of a past run")
    p.add_argument("run_id")
    p.set_defaults(func=cmd_trace)

    p = sub.add_parser("reset", help="clear runs and generated workspace files (demo reset)")
    p.add_argument("--yes", action="store_true")
    p.set_defaults(func=cmd_reset)

    args = parser.parse_args(argv)
    settings = Settings()
    try:
        return args.func(args, settings)
    except ValueError as err:
        print(f"Configuration error: {err}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
