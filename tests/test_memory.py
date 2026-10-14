import unittest

from agentforge.config import PROJECT_ROOT
from agentforge.memory import KnowledgeBase


class TestKnowledgeBase(unittest.TestCase):
    def setUp(self):
        self.kb = KnowledgeBase(PROJECT_ROOT / "knowledge")

    def test_retrieves_relevant_standard(self):
        hits = self.kb.search("docstrings and type hints on public functions")
        self.assertEqual(hits[0]["source"], "coding_standards.md")

    def test_retrieves_past_ticket(self):
        hits = self.kb.search("slugify trailing hyphen")
        self.assertEqual(hits[0]["source"], "past_tickets.md")

    def test_no_match_returns_empty(self):
        self.assertEqual(self.kb.search("zzzqqq xylophone"), [])


if __name__ == "__main__":
    unittest.main()
