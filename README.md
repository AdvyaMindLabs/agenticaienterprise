# AgentForge

A working, end-to-end **multi-agent software engineering team** you can run, trace, and break, built to learn
how enterprise agentic AI really works and to demo it.

Give it a ticket. A team of agents plans it, writes the tests first, writes the code, reviews it, scans it for
security issues, documents it, and then **waits for a human to approve** before anything leaves the sandbox.
Every decision is traced. Guardrails are enforced in code, not in prompts. An eval suite scores the whole system.

**Zero dependencies.** Python 3.10+ and the standard library. It runs **offline with a scripted mock model** (free,
deterministic, demo-safe) and switches to real Claude with two environment variables.

## 60-second start

> **On a Mac, type `python3` instead of `python`** in every command below.

```bash
python -m agentforge serve          # open http://127.0.0.1:8765
```

In the dashboard: click a sample ticket, then **Run agents**. Watch the pipeline, read the trace, and approve
the change when the approval panel appears.

Prefer the terminal?

```bash
python -m agentforge run --sample slugify --auto-approve   # narrated run
python -m agentforge eval --repeat 3                        # scorecard
python -m unittest discover -s tests -t .                   # 32 framework tests
python -m agentforge reset --yes                            # clean slate before a demo
```

## What happens to a ticket

```
            +--------+   +--------+   +-------------------------------+   +----------+   +------+
 ticket --> |Planner |-->| Tester |-->|  Coder -> run tests -> Review |-->| Security |-->| Docs |
            +--------+   +--------+   |  (retry up to 3x on feedback) |   +----------+   +------+
              RAG over    writes      +-------------------------------+                      |
              standards   tests FIRST        guardrails on every write                       v
                                                                                   HUMAN APPROVAL GATE
                                                                                           |
                                                                          promote sandbox -> workspace/
```

| Layer | Where | What you learn |
|---|---|---|
| Orchestration | `agentforge/orchestrator.py` | Control flow is plain Python, models only fill in content |
| Agents | `agentforge/agents.py` | Role + prompt + narrow job, structured JSON in and out |
| Tools | `agentforge/tools.py` | The only way agents touch the world; policy-checked and traced |
| Memory / RAG | `agentforge/memory.py`, `knowledge/` | Retrieval over standards and past tickets |
| Guardrails | `agentforge/guardrails.py` | Role permissions, secret scan, budgets, approval gate |
| Observability | `agentforge/tracing.py` | One JSON line per decision; dashboard timeline |
| Evaluation | `agentforge/evals.py`, `tickets/samples.json` | Testing a non-deterministic system |
| Serving | `agentforge/server.py`, `dashboard.html` | API, human-in-the-loop UI, and what's missing for production |

## The sample tickets (each demonstrates one idea)

| Ticket | What goes wrong on attempt 1 | What catches it |
|---|---|---|
| `slugify` | A logic bug (edge hyphens) | The unit tests written *before* the code |
| `palindrome` | Nothing: the happy path | n/a |
| `billing` | Coder hardcodes an API key | Secret scanner blocks the write |
| `clamp` | Coder edits the tests to cheat | Role permissions: Coder may only write `src/` |
| `sso` | Out of scope for the mock | Planner declines; run fails safely instead of guessing |

## Use real Claude

```bash
cp .env.example .env          # add your key; .env is git-ignored
# macOS/Linux
export AGENTFORGE_PROVIDER=anthropic ANTHROPIC_API_KEY=... && python -m agentforge serve
```

Windows PowerShell: `$env:AGENTFORGE_PROVIDER="anthropic"; $env:ANTHROPIC_API_KEY="..."`.
Or use the **"serve with real Claude"** launch config in VS Code. Check Anthropic's docs for current model
names and set `AGENTFORGE_MODEL`. Real models vary run to run, so use `eval --repeat 3` or more.

Use synthetic data only and an approved key, and follow your organisation's AI-usage and security policies
before pointing this at anything real.

## VS Code

Open the folder (`code .`), accept the recommended extensions, then **Run and Debug** has five ready configs
(serve, run a sample, evals, unit tests, real Claude). Set a breakpoint in `orchestrator.py` and step through a
run. `api.http` lets you call the API from the editor (REST Client extension). A dev container is included.

## Learn

Work through `lessons/` in order (about 30 to 45 minutes each). Every lesson ends with a **break it on purpose**
exercise. To present this to someone, use `SHOWCASE.md`.

## Honest limits

This is a teaching and demo system, not production software. The mock model is scripted. The test "sandbox" is a
subprocess, not a container. The API has no authentication. See `lessons/08-from-demo-to-production.md` for the
full gap list and what to build next.
