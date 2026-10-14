# Security standards (synthetic example)

**No hardcoded secrets.** API keys, tokens, passwords and private keys must never appear in source code. Read credentials from environment variables and fail loudly if they are missing.

**No dynamic code execution.** Do not use eval(), exec(), os.system(), or subprocess with shell=True. Do not deserialize untrusted data with pickle.

**Least privilege.** Each agent and service gets only the permissions it needs. Implementers may not edit tests; testers may not edit source.

**Human approval.** Changes leave the sandbox only after a human approves them, unless the scan reports low risk and policy allows auto-approval.
