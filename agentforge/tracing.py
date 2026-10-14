"""Structured tracing: every decision an agent makes becomes one JSON line (Lesson 06)."""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Callable


def clip(text: object, limit: int = 300) -> str:
    text = str(text)
    return text if len(text) <= limit else text[:limit] + f"... (+{len(text) - limit} chars)"


class Tracer:
    """Append-only JSONL log. One file per run: runs/<run_id>/trace.jsonl."""

    def __init__(self, path: Path, run_id: str, on_event: Callable[[dict], None] | None = None):
        self.path = Path(path)
        self.run_id = run_id
        self.on_event = on_event
        self._lock = threading.Lock()
        self._seq = 0
        self._t0 = time.time()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("", encoding="utf-8")

    def emit(self, type: str, agent: str | None = None, msg: str = "", **data) -> dict:
        with self._lock:
            self._seq += 1
            event = {
                "seq": self._seq,
                "t": round(time.time() - self._t0, 2),
                "type": type,
                "agent": agent,
                "msg": msg,
                "data": data,
            }
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(event, default=str) + "\n")
        if self.on_event:
            self.on_event(event)
        return event


def load_trace(path: Path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return events
