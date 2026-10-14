# Lesson 00: Start here (30 min)

**Goal:** run the system, understand the moving parts, and know where everything lives.

## 1. Run it
```bash
python -m agentforge run --sample slugify --auto-approve
```
Read the narrated output top to bottom. Find: the knowledge search, the failed tests on attempt 1, the retry, the
review, the security scan, the approval, the promotion.

## 2. Open it in the dashboard
`python -m agentforge serve`, run the `billing` sample, and find the red **BLOCKED** line in the trace.

## 3. Mental model

| Question | Answer |
|---|---|
| Who decides what happens next? | **Plain Python** in `orchestrator.py`, never the model |
| What do models do? | Produce *content* (a plan, tests, code, a verdict) as JSON |
| How do agents act? | Only through `Toolbox`, which checks policy and logs every call |
| What stops bad output? | `guardrails.py`: deterministic code, not prompt wording |
| How do we know it works? | `evals.py`: tickets with expectations, run repeatedly |

## 4. Exercise
Draw the sequence for the `clamp` ticket on paper from the trace: which agent acted, which guardrail fired, how
many model calls were used. Check against `python -m agentforge trace <run_id>`.

**Break it on purpose:** change `max_attempts` to `1` in `config.py` and re-run `slugify`. Predict the result first.
