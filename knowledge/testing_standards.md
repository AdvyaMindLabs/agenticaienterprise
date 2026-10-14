# Testing standards (synthetic example)

**Tests first.** Write unit tests before the implementation (TDD). Use the standard library unittest framework and place tests under tests/ named test_<module>.py.

**Cover edge cases.** Test empty input, boundary values, invalid arguments and punctuation or whitespace handling, not only the happy path.

**Tests are immutable for implementers.** The person or agent writing the implementation must not modify the tests that define the requirement. Changing tests to make code pass is a policy violation.
