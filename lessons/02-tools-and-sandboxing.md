# Lesson 02: Tools and sandboxing

**Read:** `tools.py`

## Ideas
- Tools are the agents' **only** way to affect anything. Centralising them gives one place for policy and logging.
- `write_files` is **atomic**: if any file violates policy, nothing is written.
- Work happens in a per-run **sandbox** (`runs/<id>/sandbox/`), a copy of `workspace/`. The real workspace changes only on approval.
- Tests run in a subprocess with a **stripped environment**, so your API keys are not inherited by generated code.
- **Honest limit:** a subprocess is *not* a security boundary. Generated code could still read files or open sockets. Production needs containers or microVMs, no network, resource limits, read-only mounts.

## Try
1. Run `billing`, then open `runs/<id>/sandbox/` and compare with `workspace/`.
2. In `run_tests`, print `env`. Confirm your key isn't there.
3. Read `diff()` and `promote()`: how do reviewers see exactly what will change?

## Exercise
Add a `read_file` tool that lets the Coder read other files in `src/`. Make it refuse paths outside the sandbox, trace every call, and write a test that tries `../`.

**Break it on purpose:** remove the `root not in dest.parents` check in `write_files`. Does any test fail? (The earlier `check_write` still blocks it, so that is why defence in depth matters, and why you need a test per layer.)
