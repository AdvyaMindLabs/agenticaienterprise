"""HTTP API + dashboard, standard library only (Lesson 08).

  GET  /                         dashboard
  GET  /api/info                 provider/model/version
  GET  /api/samples              sample tickets
  GET  /api/runs                 run summaries
  GET  /api/runs/<id>            full run record + trace
  POST /api/tickets              {title, description} -> {run_id}
  POST /api/runs/<id>/decision   {approved, note}     (human-in-the-loop)
  GET  /api/evals                latest eval report + running flag
  POST /api/evals                start the eval suite in the background

Deliberately missing (see Lesson 08): authentication, authorization, rate limiting, a
job queue, a real database, TLS. It binds to localhost only; do not expose it as-is.
"""
from __future__ import annotations

import copy
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import __version__
from .config import Settings
from .evals import run_evals
from .guardrails import ApprovalGate
from .orchestrator import TERMINAL, Orchestrator, new_run_id
from .tracing import load_trace


class AppState:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.runs: dict[str, dict] = {}
        self.gates: dict[str, ApprovalGate] = {}
        self.lock = threading.Lock()
        self.eval_running = False
        self._load_existing()

    def _load_existing(self) -> None:
        for path in sorted(self.settings.runs_dir.glob("*/run.json")):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if record.get("status") not in TERMINAL:
                record["status"], record["error"] = "failed", "server restarted while this run was in progress"
            self.runs[record["id"]] = record

    def update(self, record: dict) -> None:
        with self.lock:
            self.runs[record["id"]] = copy.deepcopy(record)

    def submit(self, ticket: dict) -> str:
        run_id = new_run_id()
        gate = ApprovalGate()
        with self.lock:
            self.gates[run_id] = gate
            self.runs[run_id] = {
                "id": run_id, "ticket": ticket, "status": "running", "stage": "queued",
                "attempts": 0, "guardrail_blocks": 0, "started": time.time(), "usage": {"llm_calls": 0, "tokens": 0},
            }

        def worker() -> None:
            try:
                Orchestrator(self.settings).run(
                    ticket, run_id=run_id, on_update=self.update,
                    approver=lambda _record: gate.wait(self.settings.approval_timeout_s),
                )
            except Exception as err:  # e.g. provider misconfiguration
                with self.lock:
                    self.runs[run_id].update(status="failed", error=f"{type(err).__name__}: {err}", finished=time.time())

        threading.Thread(target=worker, daemon=True).start()
        return run_id

    def start_evals(self) -> bool:
        with self.lock:
            if self.eval_running:
                return False
            self.eval_running = True

        def worker() -> None:
            try:
                run_evals(self.settings, repeat=1, log=lambda _line: None)
            finally:
                self.eval_running = False

        threading.Thread(target=worker, daemon=True).start()
        return True


def make_handler(state: AppState):
    settings = state.settings
    dashboard = Path(__file__).with_name("dashboard.html")

    class Handler(BaseHTTPRequestHandler):
        server_version = f"AgentForge/{__version__}"

        def log_message(self, fmt, *args):  # keep the console quiet
            pass

        def _send(self, code: int, body: bytes, ctype: str = "application/json") -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj, code: int = 200) -> None:
            self._send(code, json.dumps(obj, default=str).encode("utf-8"))

        def _body(self) -> dict:
            # Requiring application/json blocks cross-site form posts (a basic CSRF defence).
            if "application/json" not in (self.headers.get("Content-Type") or ""):
                raise ValueError("Content-Type must be application/json")
            length = int(self.headers.get("Content-Length") or 0)
            if length > 1_000_000:
                raise ValueError("request body too large")
            return json.loads(self.rfile.read(length) or b"{}")

        def do_GET(self) -> None:
            try:
                path = self.path.split("?")[0].rstrip("/") or "/"
                if path == "/":
                    return self._send(200, dashboard.read_bytes(), "text/html; charset=utf-8")
                if path == "/api/info":
                    return self._json({"version": __version__, "provider": settings.provider,
                                       "model": settings.model if settings.provider == "anthropic" else "scripted-mock"})
                if path == "/api/samples":
                    return self._json(json.loads(settings.tickets_file.read_text(encoding="utf-8")))
                if path == "/api/runs":
                    with state.lock:
                        rows = [
                            {"id": r["id"], "title": r["ticket"].get("title", ""), "status": r["status"],
                             "stage": r.get("stage"), "started": r.get("started")}
                            for r in state.runs.values()
                        ]
                    rows.sort(key=lambda r: r["started"] or 0, reverse=True)
                    return self._json({"runs": rows})
                if path.startswith("/api/runs/"):
                    run_id = path.split("/")[3]
                    with state.lock:
                        record = copy.deepcopy(state.runs.get(run_id))
                    if not record:
                        return self._json({"error": "run not found"}, 404)
                    return self._json({"run": record, "trace": load_trace(settings.runs_dir / run_id / "trace.jsonl")})
                if path == "/api/evals":
                    latest = settings.runs_dir / "evals_latest.json"
                    report = json.loads(latest.read_text(encoding="utf-8")) if latest.exists() else None
                    return self._json({"running": state.eval_running, "latest": report})
                self._json({"error": "not found"}, 404)
            except Exception as err:
                self._json({"error": str(err)}, 500)

        def do_POST(self) -> None:
            try:
                path = self.path.split("?")[0].rstrip("/")
                body = self._body()
                if path == "/api/tickets":
                    title = str(body.get("title", "")).strip()
                    description = str(body.get("description", "")).strip()
                    if not title or len(title) > 200 or len(description) > 4000:
                        return self._json({"error": "title is required (<=200 chars); description <=4000 chars"}, 400)
                    return self._json({"run_id": state.submit({"title": title, "description": description})}, 202)
                if path.startswith("/api/runs/") and path.endswith("/decision"):
                    run_id = path.split("/")[3]
                    with state.lock:
                        record, gate = state.runs.get(run_id), state.gates.get(run_id)
                    if not record or not gate:
                        return self._json({"error": "run not found"}, 404)
                    if record["status"] != "awaiting_approval":
                        return self._json({"error": f"run is '{record['status']}', not awaiting approval"}, 409)
                    gate.decide(bool(body.get("approved")), by="dashboard-user", note=str(body.get("note", ""))[:500])
                    return self._json({"ok": True})
                if path == "/api/evals":
                    return self._json({"started": state.start_evals()}, 202)
                self._json({"error": "not found"}, 404)
            except ValueError as err:
                self._json({"error": str(err)}, 400)
            except Exception as err:
                self._json({"error": str(err)}, 500)

    return Handler


def serve(settings: Settings, host: str = "127.0.0.1", port: int = 8765) -> None:
    state = AppState(settings)
    httpd = ThreadingHTTPServer((host, port), make_handler(state))
    print(f"AgentForge {__version__}  provider={settings.provider}")
    print(f"Dashboard: http://{host}:{port}   (Ctrl+C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
    finally:
        httpd.server_close()
