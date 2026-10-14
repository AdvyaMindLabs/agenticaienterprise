# Lesson 04: Guardrails and human-in-the-loop

**Read:** `guardrails.py`, then the `billing` and `clamp` runs.

## The principle
> If a rule matters, enforce it in code the model cannot talk its way around.

| Layer | Enforced by | Demonstrated by |
|---|---|---|
| Path + role permissions | `check_write` | `clamp`: Coder tries to edit tests, blocked |
| Secret scanning | `scan_secrets` | `billing`: hardcoded key blocked before it exists on disk |
| Budgets | `Budget` | Set `max_llm_calls=3` and run any ticket |
| Approval gate | `ApprovalGate` + dashboard | Anything leaving the sandbox needs a human |
| Risk policy | `auto_approver` | Only LOW risk can skip a human |

Blocked output is fed back to the Coder as feedback, so guardrails also *teach* the loop to self-correct.

## Exercise
Add a guardrail that blocks files containing `TODO` or `print(`. Add a test in `tests/test_guardrails.py`, then add a scripted violation to a ticket in `mock_library.py` and watch it get caught in the dashboard.

**Break it on purpose:** loosen the `Hardcoded credential` regex. Run the unit tests and evals, and see which fail. This is what regression tests are for.

## Discuss
What would you add for production? (Think: PII detection, allow-listed dependencies, licence checks, network egress policy, per-team budgets, immutable audit logs.)
