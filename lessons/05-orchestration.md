# Lesson 05: Orchestration patterns

**Read:** `orchestrator.py`

## Ideas
- This is a **state machine with a bounded retry loop**: `plan -> tests -> [code -> verify -> review] x N -> security -> docs -> approval -> promote`.
- **Deterministic control flow, probabilistic content.** The model never chooses the next step, which makes behaviour testable and auditable.
- **Test-first:** the Tester writes tests before the Coder exists, and the Coder cannot edit them. The requirement is fixed independently of the implementation.
- **Feedback loop:** every failure (guardrail, test, review) becomes text for the next attempt.
- **Fail closed:** unknown ticket, exhausted retries, budget exceeded, security `high`, approval timeout all end in a *safe* terminal state (`failed` or `rejected`) with nothing promoted.

## Try
1. List every way a run can end and which line produces it.
2. Run `slugify` and count model calls. Where could you save calls without losing safety?
3. Set a breakpoint on `stage("verify")` and inspect `record` as it evolves.

## Exercise
Add a `max_cost_usd` budget. Estimate cost from tokens, with prices as config, and fail the run when exceeded. Add a test.

**Break it on purpose:** swap the order of `security` and `review`. Do all tests still pass? Which conversation would you have with the team about why order matters?

## Going further
Compare with other patterns: supervisor/worker (this), peer-to-peer debate, parallel fan-out/fan-in, and graph frameworks. When is a framework worth it over 150 lines of Python?
