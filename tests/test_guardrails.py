import unittest

from agentforge.guardrails import ApprovalGate, Budget, BudgetExceeded, check_write, scan_secrets
from agentforge.llm import extract_json


class TestPathAndRolePolicy(unittest.TestCase):
    def test_allows_coder_in_src(self):
        self.assertEqual(check_write("coder", "src/x.py", "def f() -> int:\n    return 1\n"), [])

    def test_blocks_traversal_and_absolute_paths(self):
        for bad in ("../evil.py", "src/../../evil.py", "/etc/passwd", "C:\\x.py", "~/x.py"):
            self.assertTrue(check_write("coder", bad, "x = 1"), bad)

    def test_coder_cannot_edit_tests(self):
        self.assertTrue(check_write("coder", "tests/test_x.py", "x = 1"))

    def test_tester_cannot_edit_src(self):
        self.assertTrue(check_write("tester", "src/x.py", "x = 1"))

    def test_unknown_role_gets_nothing(self):
        self.assertTrue(check_write("intern", "src/x.py", "x = 1"))

    def test_size_limit(self):
        self.assertTrue(check_write("coder", "src/x.py", "x" * 100, max_bytes=10))


class TestSecretScanner(unittest.TestCase):
    def test_flags_hardcoded_credentials(self):
        self.assertTrue(scan_secrets('API_KEY = "abcdefghijklmnop1234"'))
        self.assertTrue(scan_secrets('password: "correct-horse-battery"'))
        self.assertTrue(scan_secrets("key = AKIAABCDEFGHIJKLMNOP"))

    def test_allows_reading_from_environment(self):
        self.assertFalse(scan_secrets('key = os.environ.get("BILLING_API_KEY")'))
        self.assertFalse(scan_secrets('{"BILLING_API_KEY": "test-key-123"}'))


class TestBudgetAndGate(unittest.TestCase):
    def test_call_budget(self):
        budget = Budget(max_calls=2, max_tokens=10_000)
        budget.charge(10)
        budget.charge(10)
        with self.assertRaises(BudgetExceeded):
            budget.charge(10)

    def test_token_budget(self):
        with self.assertRaises(BudgetExceeded):
            Budget(max_calls=10, max_tokens=50).charge(100)

    def test_gate_times_out_as_rejection(self):
        self.assertFalse(ApprovalGate().wait(0.01)["approved"])

    def test_gate_decision(self):
        gate = ApprovalGate()
        gate.decide(True, by="tester")
        self.assertTrue(gate.wait(1)["approved"])


class TestExtractJson(unittest.TestCase):
    def test_plain_fenced_and_prose(self):
        self.assertEqual(extract_json('{"a": 1}'), {"a": 1})
        self.assertEqual(extract_json('```json\n{"a": 1}\n```'), {"a": 1})
        self.assertEqual(extract_json('Sure! Here you go: {"a": 1} Hope that helps.'), {"a": 1})

    def test_code_fence_inside_json_string(self):
        text = '{"content": "```python\\nprint(1)\\n```"}'
        self.assertIn("print(1)", extract_json(text)["content"])

    def test_rejects_garbage(self):
        with self.assertRaises(ValueError):
            extract_json("no json here")


if __name__ == "__main__":
    unittest.main()
