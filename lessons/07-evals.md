# Lesson 07: Evaluation

**Read:** `evals.py`, `tickets/samples.json`

## Ideas
- You can't unit-test a model's output the way you test a function, but you can test the **system's behaviour** against expectations.
- Each sample ticket has expectations: final status, max attempts, minimum guardrail blocks, tests green.
- **Run each ticket several times.** Real models are non-deterministic, so one pass proves little. Report pass *counts* (`8/10`), and express thresholds as counts instead of percentages that mean different things at different sample sizes.
- Evals run in a throwaway workspace so results never depend on your demo state.
- Include **negative cases** (the `sso` ticket): correct behaviour is sometimes refusing.

## Try
1. `python -m agentforge eval --repeat 3`
2. Break something (weaken `scan_secrets`) and watch which eval fails.
3. With real Claude, run `eval --repeat 5` and compare pass counts to the mock.

## Exercise
Add three new sample tickets, including one adversarial one, such as a ticket whose description tells the agent to "disable the secret scanner". Write expectations, then see what happens.

## Beyond this
Track pass rate, attempts, tokens and cost **over time** and gate releases on them, so prompt or model changes can't ship without a score.
