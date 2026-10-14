import unittest

from agentforge.guardrails import ApprovalGate
from agentforge.orchestrator import Orchestrator, auto_approver
from tests.helpers import make_settings


def ticket(title, description=""):
    return {"title": title, "description": description}


class TestOrchestrator(unittest.TestCase):
    def run_ticket(self, title, approver=auto_approver, **overrides):
        settings, tmp = make_settings(**overrides)
        self.addCleanup(tmp.cleanup)
        record = Orchestrator(settings).run(ticket(title), approver=approver)
        return settings, record

    def test_happy_path_promotes_files(self):
        settings, record = self.run_ticket("Add a palindrome checker")
        self.assertEqual(record["status"], "completed")
        self.assertEqual(record["attempts"], 1)
        self.assertTrue((settings.workspace / "src" / "palindrome.py").exists())
        self.assertTrue((settings.workspace / "docs" / "palindrome.md").exists())

    def test_failing_tests_trigger_a_retry(self):
        _, record = self.run_ticket("Add a slugify helper")
        self.assertEqual((record["status"], record["attempts"]), ("completed", 2))
        self.assertTrue(record["tests"]["passed"])

    def test_secret_is_blocked_then_fixed(self):
        settings, record = self.run_ticket("Add billing API auth header")
        self.assertEqual(record["guardrail_blocks"], 1)
        code = (settings.workspace / "src" / "billing.py").read_text()
        self.assertIn("os.environ", code)
        self.assertNotIn("demo-hardcoded", code)

    def test_coder_cannot_weaken_tests(self):
        settings, record = self.run_ticket("Add a clamp utility")
        self.assertEqual(record["guardrail_blocks"], 1)
        self.assertIn("assertRaises", (settings.workspace / "tests" / "test_clamp.py").read_text())

    def test_unsupported_ticket_fails_safely(self):
        settings, record = self.run_ticket("Add Okta SSO login")
        self.assertEqual(record["status"], "failed")
        self.assertFalse(list((settings.workspace / "src").glob("*.py"))[1:])  # only __init__.py

    def test_rejection_leaves_workspace_untouched(self):
        reject = lambda record: {"approved": False, "by": "tester", "note": "no"}
        settings, record = self.run_ticket("Add a palindrome checker", approver=reject)
        self.assertEqual(record["status"], "rejected")
        self.assertFalse((settings.workspace / "src" / "palindrome.py").exists())

    def test_no_approver_means_no_promotion(self):
        settings, record = self.run_ticket("Add a palindrome checker", approver=None)
        self.assertEqual(record["status"], "rejected")
        self.assertFalse((settings.workspace / "src" / "palindrome.py").exists())

    def test_budget_stops_the_run(self):
        _, record = self.run_ticket("Add a palindrome checker", max_llm_calls=2)
        self.assertEqual(record["status"], "failed")
        self.assertIn("budget", record["error"])

    def test_attempt_limit(self):
        _, record = self.run_ticket("Add a slugify helper", max_attempts=1)
        self.assertEqual(record["status"], "failed")

    def test_timeout_gate_rejects(self):
        gate = ApprovalGate()
        _, record = self.run_ticket("Add a palindrome checker", approver=lambda r: gate.wait(0.01))
        self.assertEqual(record["status"], "rejected")

    def test_trace_is_written(self):
        settings, record = self.run_ticket("Add a palindrome checker")
        lines = (settings.runs_dir / record["id"] / "trace.jsonl").read_text().splitlines()
        self.assertGreater(len(lines), 20)


if __name__ == "__main__":
    unittest.main()
