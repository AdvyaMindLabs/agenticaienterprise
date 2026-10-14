# Coding standards (Acme Engineering, synthetic example)

**Docstrings and type hints.** Every public function must have a docstring and full type hints on all parameters and the return value. Reviewers reject code that lacks them.

**Standard library first.** Prefer the Python standard library. Do not add third-party dependencies without an approved exception.

**Small pure functions.** Keep functions small and side-effect free where possible. Raise specific exceptions (ValueError, RuntimeError) with a clear message instead of returning error codes.

**Naming.** Use snake_case for functions and variables, PascalCase for classes, and one module per feature under src/.
