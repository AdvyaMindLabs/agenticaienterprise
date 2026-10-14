"""Exercises the REAL-model code path against a local fake of the Messages API:
request shape, auth headers, response parsing, usage accounting, and a full orchestrated run."""
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from agentforge.llm import AnthropicProvider, get_provider
from agentforge.mock_library import respond
from agentforge.orchestrator import Orchestrator, auto_approver
from tests.helpers import make_settings

SEEN = []


def role_from_system(system: str) -> str:
    for role in ("Planner", "Tester", "Coder", "Reviewer", "Security", "Docs"):
        if f"You are the {role}" in system:
            return role.lower()
    return "unknown"


class FakeMessagesAPI(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        SEEN.append({"path": self.path, "key": self.headers.get("x-api-key"),
                     "version": self.headers.get("anthropic-version"), "model": body["model"]})
        text = respond(role_from_system(body["system"]), body["messages"][0]["content"])
        # Real models often wrap JSON in prose or fences. Do the same to test robustness.
        text = f"Here is my answer:\n```json\n{text}\n```"
        payload = json.dumps({"content": [{"type": "text", "text": text}],
                              "usage": {"input_tokens": 100, "output_tokens": 50}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


class TestAnthropicPath(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = HTTPServer(("127.0.0.1", 0), FakeMessagesAPI)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.httpd.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def test_provider_request_and_parsing(self):
        SEEN.clear()
        reply = AnthropicProvider("k-123", "some-model", self.url).complete("planner", "You are the Planner.", "hi")
        self.assertIn("Here is my answer", reply.text)
        self.assertEqual((reply.input_tokens, reply.output_tokens), (100, 50))
        self.assertEqual(SEEN[0]["path"], "/v1/messages")
        self.assertEqual((SEEN[0]["key"], SEEN[0]["version"], SEEN[0]["model"]), ("k-123", "2023-06-01", "some-model"))

    def test_missing_key_is_a_clear_error(self):
        settings, tmp = make_settings()
        self.addCleanup(tmp.cleanup)
        settings.provider, settings.api_key = "anthropic", ""
        with self.assertRaises(ValueError):
            get_provider(settings)

    def test_full_run_through_anthropic_provider(self):
        settings, tmp = make_settings()
        self.addCleanup(tmp.cleanup)
        settings.provider, settings.api_key, settings.base_url = "anthropic", "k-123", self.url
        record = Orchestrator(settings).run({"title": "Add a slugify helper", "description": ""}, approver=auto_approver)
        self.assertEqual((record["status"], record["attempts"]), ("completed", 2))
        self.assertEqual(record["provider"], "anthropic")
        self.assertGreater(record["usage"]["tokens"], 0)


if __name__ == "__main__":
    unittest.main()
