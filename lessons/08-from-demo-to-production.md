# Lesson 08: From demo to production

**Read:** `server.py`, then be honest about what's missing.

## What the API gives you
Submit tickets, watch progress, approve or reject, run evals. A human decision is required to promote changes.

## Gap list (what you'd build next)

| Area | Today | Production |
|---|---|---|
| AuthN/AuthZ | None, localhost only | SSO, per-team roles, who may approve what |
| Execution | Background threads | Job queue, workers, retries, idempotency |
| Sandbox | Subprocess, stripped env | Containers/microVMs, no network, CPU/mem limits |
| Storage | JSON files | Database + object store, retention, immutable audit log |
| Secrets | Env var | Secret manager, short-lived credentials |
| Model access | Direct API | Approved gateway, per-team budgets, data-handling policy |
| Source control | Local files | Open real PRs, branch protection, CODEOWNERS |
| Tools | A handful, hand-written | Governed registry (e.g. MCP servers) with review + versioning |
| Data | Synthetic | Classification, PII redaction, residency |
| Evals | Local CLI | CI gate on every prompt/model change; drift monitoring |
| Cost | Token estimate | Metering, quotas, alerts |

## Swapping in a real model
Set `AGENTFORGE_PROVIDER=anthropic`. Expect: more varied outputs, occasional invalid JSON (handled by one repair retry), and new failure modes worth turning into eval tickets. Keep model names in config, and check the provider's docs for current ones.

## Aligning with your organisation
Before connecting to real repos, data, or internal tools, check your company's AI usage, security and data-handling policies, and use the approved agent/skill/MCP registries and model gateways instead of rebuilding them. Verify specifics with your platform and security teams.

## Capstone
Pick one row from the table and implement it (the easiest wins: authentication on the API; opening a real GitHub PR on approval). Add tests and an eval for it.
