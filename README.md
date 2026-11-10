# AgentForge

A free, hands-on learning lab for an **individual learner** who wants to understand agentic AI by building and breaking a working multi-agent software engineering system. Learn the ideas behind enterprise agentic AI without needing a paid model, cloud account, or API key.

Give AgentForge a software ticket. Its agents plan the work, write tests first, implement code, review it, scan it for security issues, document it, and then **wait for your approval** before promoting changes from the sandbox. Follow the traces to understand every decision, experiment with guardrails, and use the eval suite to measure behavior.

**Start at $0.** The default scripted model runs offline using Python's standard library: no dependencies, no tokens, no usage limits, and no account required. The optional real-model integration is not needed to complete the learning path. If you later choose a provider's free tier, check its current limits and terms first; do not enter payment details or enable paid usage if you cannot afford it.

## 60-second start

> On a Mac, use `python3` instead of `python` in the commands below.

```bash
python -m agentforge serve          # open http://127.0.0.1:8765
```

In the dashboard, choose a sample ticket and click **Run agents**. Watch the pipeline, inspect the trace, and approve the change when the approval panel appears. Everything works locally in mock mode.

Prefer the terminal?

```bash
python -m agentforge run --sample slugify --auto-approve   # narrated run
python -m agentforge eval --repeat 3                        # scorecard
python -m unittest discover -s tests -t .                   # run framework tests
python -m agentforge reset --yes                            # clean slate
```

## What you will learn by building

```text
 ticket -> Planner -> Tester -> Coder -> tests -> Reviewer -> Security -> Docs
             |          |         |                         |               |
         RAG/context  tests first  bounded writes       guardrails     human approval
```

| Concept | Where to explore | What you will learn |
|---|---|---|
| Agent roles and orchestration | `agentforge/agents.py`, `agentforge/orchestrator.py` | How agents have narrow jobs and how ordinary Python controls the workflow |
| Tools and safe actions | `agentforge/tools.py` | How to limit what an agent can do and record each action |
| Memory and retrieval | `agentforge/memory.py`, `knowledge/` | How an agent finds relevant reference material |
| Guardrails and human oversight | `agentforge/guardrails.py` | Permissions, secret scanning, budgets, and approval gates |
| Tracing and evaluation | `agentforge/tracing.py`, `agentforge/evals.py` | How to inspect and measure agent behavior rather than trust a demo |
| Local app and API | `agentforge/server.py`, `agentforge/dashboard.html` | How to run the learning lab on your own computer |

## Learn in order

Work through `lessons/` as a self-paced course (about 30–45 minutes per lesson). Each lesson includes a hands-on exercise; many ask you to break something deliberately and observe what happens. You can complete the entire course using the offline mock model—no paid API or free-tier signup is required. Start with [`lessons/00-start-here.md`](lessons/00-start-here.md).

The sample tickets demonstrate a clean success, a test-driven repair, a blocked hard-coded secret, a permissions check, and a safe refusal when a request is outside the mock model's abilities.

## Optional: try a real model later

AgentForge can optionally connect to a real model provider. This is **not required** for learning or running the examples. Provider free tiers, availability, and limits can change, and may require an account or payment method; verify the terms directly with the provider before opting in. Never assume a free tier cannot incur charges. Keep mock mode if you need to guarantee zero model spend, and use synthetic data only with any external provider.

## VS Code (optional)

Open the folder (`code .`), accept the recommended extensions if you want them, then use **Run and Debug** to run the server, sample tickets, evals, and tests. VS Code is optional; the command-line instructions above are enough to learn the project.

## Honest limits

This is a teaching and demo system, not production software. The mock model is scripted, the test sandbox is a subprocess rather than a security boundary, and the API has no authentication. Do not use it with real company code, secrets, or sensitive data. See `lessons/08-from-demo-to-production.md` for the limitations and the security work required before any production use.
