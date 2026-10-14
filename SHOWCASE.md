# Showcase script: AgentForge for Pahlguna Yadhlapati

A 10 minute demo plus 5 minutes of discussion. Everything runs offline with the mock model, so there is no
network, key or cost risk on the day.

## Before you start (2 minutes)
```bash
python -m agentforge reset --yes
python -m unittest discover -s tests -t .      # expect: OK (32 tests)
python -m agentforge serve                      # open http://127.0.0.1:8765
```
Optional: have the real-Claude config ready (`.env`) as a "live model" encore, but only if you have an approved key
and a stable connection. Use synthetic data only.

## The one-sentence pitch
"A team of AI agents that takes an engineering ticket to a reviewed, tested, security-scanned, documented change,
with guardrails enforced in code and a human approving before anything ships."

## Talk track

| Min | Do | Say |
|---|---|---|
| 0-1 | Show the dashboard header and the README diagram | "Six specialist agents. The orchestrator is plain Python: models write content, they never decide control flow." |
| 1-3 | Click `palindrome`, **Run agents** | "Happy path. Plan, tests written first, code, review, security scan, docs. It stops at the approval gate. Nothing has left the sandbox." Click **Approve**. |
| 3-5 | Click `slugify`, run it | "First attempt had a bug. The tests, written before the code, caught it. The coder got the failure as feedback and fixed it. No human involved." Point at attempts = 2 in the stats. |
| 5-7 | Click `billing`, run it, open the trace | "The coder hardcoded an API key. The secret scanner blocked the write before it touched disk." Point at the red BLOCKED line. |
| 7-8 | Click `clamp`, run it | "The coder tried to weaken the tests to cheat. Role permissions blocked it: the coder can only write `src/`." |
| 8-9 | Click `sso` | "Out of scope. The system fails safely rather than guessing." |
| 9-10 | **Run eval suite**, then show the scorecard | "Behaviour is measured, not assumed: 5/5 scenarios, tokens per run, repeatable on every change." |

## Why it matters (for the discussion)
- **Guardrails in code, not prompts.** Four layers: permissions, secret scan, budgets, human approval.
- **Observable.** Every tool call, retry and decision is in the trace, which is the audit story.
- **Measurable.** The eval suite is the release gate, and the same suite works against a real model with `--repeat`.
- **Model-agnostic.** One environment variable swaps the scripted model for real Claude. Agents don't change.

## Be upfront about (builds credibility)
- The mock model is **scripted**, which is what makes the demo deterministic. Real-model behaviour needs real evals.
- The sandbox is a subprocess, **not** a security boundary. Production needs containers/microVMs.
- The API has **no authentication**. It is localhost-only by design.
- It operates on a toy workspace. Connecting to real repos, data and internal tools is the next phase and needs
  security and platform review.

## Likely questions

| Question | Answer |
|---|---|
| Is it really using AI? | The architecture is real and the provider is swappable. Set `AGENTFORGE_PROVIDER=anthropic` to run the same pipeline on Claude. The mock exists for repeatability. |
| What stops it shipping something bad? | Tests written first and unmodifiable by the coder, reviewer, security gate, and a human approval before promotion. |
| What does it cost? | The dashboard shows model calls and tokens per run; budgets cap both. Mock mode is free. |
| How would this fit our platform? | Reuse approved registries, model gateways and CI. Lesson 08 lists the integration points and gaps. |
| What's the roadmap? | See below. |

## Proposed next steps (pick one to propose)
1. **Open a real pull request on approval** (GitHub), with branch protection and CODEOWNERS review.
2. **Add authentication and approver roles** to the API.
3. **Run the eval suite in CI** and block prompt/model changes that lower the score.
4. **Run generated code in a container sandbox** with no network.

## Success metrics to track in a pilot
- Tickets completed without human code edits (%)
- Guardrail block rate and false positive rate
- Attempts per ticket and tokens/cost per ticket
- Human approval rate and time-to-approve
- Eval pass count over time (`n/N`, not just %)
