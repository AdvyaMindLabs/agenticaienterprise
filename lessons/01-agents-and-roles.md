# Lesson 01: Agents and roles

**Read:** `agents.py`, `llm.py`, `mock_library.py`

## Ideas
- An **agent** here is three things: a role, a system prompt, and a narrow job. Narrow jobs are easier to test,
  constrain and replace than one giant "do everything" prompt.
- Agents return **structured JSON**. `Agent.ask()` retries once on invalid JSON, and `extract_json()` tolerates
  prose and code fences. It tries a strict parse first (a bug we hit while building this: a markdown fence
  *inside* a JSON string was mistaken for the outer fence).
- Agents depend on the `Provider` interface only. The mock and Claude are interchangeable.
- The **Reviewer** in mock mode is real code (it parses the source with `ast`), while the others are scripted.

## Try
1. Read the Planner system prompt, then the JSON it must return. Why does the prompt include an `unsupported` escape hatch?
2. Run `python -m agentforge run --sample sso` and explain why failing is the right outcome.
3. Compare `Tester` and `Coder` prompts. What is each *not allowed* to do, and where is that enforced? (Hint: not in the prompt.)

## Exercise: add an agent
Add a `Refactorer` that runs after review and proposes a simplification. Follow the pattern: subclass `Agent`,
write a system prompt, add a role to `ROLE_WRITE_PREFIXES`, call it from the orchestrator, add a branch to
`mock_library.respond`, and add a test.

**Break it on purpose:** make `Coder.system` say "ignore the standards". Does anything stop bad code? (Yes: the reviewer and scanners. That is defence in depth.)
