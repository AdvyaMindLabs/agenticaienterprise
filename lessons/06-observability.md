# Lesson 06: Observability and tracing

**Read:** `tracing.py`, then a `runs/<id>/trace.jsonl` file.

## Ideas
- Agent systems fail in *interesting* ways. Without traces you're guessing.
- Each event is one JSON line: sequence, time, type (`stage`, `llm`, `tool`, `guardrail`, `approval`, `error`), agent, and message.
- Traces answer: **What did the agent see? What did it decide? What did the guardrails do? How many tokens did it cost? Who approved?**
- The dashboard timeline and `python -m agentforge trace <id>` read the same file.

## Try
1. `python -m agentforge trace <run_id>` for a failed run. Find the first point where things went wrong.
2. Use `grep '"guardrail"' runs/*/trace.jsonl` to count blocked actions across all runs.
3. Sum `output_tokens` per agent from a trace with a few lines of Python. Which agent is most expensive?

## Exercise
Add a `latency_ms` field to each `llm` event and show the slowest call per run in the dashboard stats.

## Production notes
Ship traces to a real backend (OpenTelemetry, your logging platform). Redact secrets and PII *before* writing. Keep approval records immutable, because they're your audit trail.
