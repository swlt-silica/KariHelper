import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import MagicMock, patch

from ai_clients import (
    PROVIDER_CODEX,
    call_openai_chat,
    fetch_codex_models,
    fetch_openai_models,
    find_codex_cli,
    run_codex_prompt,
)
from ai_extract import _call_chat


class _OpenAIHandler(BaseHTTPRequestHandler):
    requested_model = None
    authorization = None

    def do_GET(self):
        if self.path != "/v1/models":
            self.send_error(404)
            return
        self.__class__.authorization = self.headers.get("Authorization")
        self._write_json({"object": "list", "data": [{"id": "vendor-b"}, {"id": "vendor-a"}]})

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8"))
        self.__class__.requested_model = body["model"]
        self._write_json({"choices": [{"message": {"content": "OK"}}]})

    def _write_json(self, body):
        raw = json.dumps(body).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, _format, *_args):
        pass


class AIClientsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _OpenAIHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}/v1"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_fetch_openai_models(self):
        models = fetch_openai_models(self.base_url, "test-key")
        self.assertEqual(models, ["vendor-a", "vendor-b"])
        self.assertEqual(_OpenAIHandler.authorization, "Bearer test-key")

    def test_call_openai_chat_uses_manual_model(self):
        reply = call_openai_chat(
            {
                "api_base": self.base_url,
                "api_key": "test-key",
                "model": "vendor-a",
                "prompt": "system",
            },
            "hello",
        )
        self.assertEqual(reply, "OK")
        self.assertEqual(_OpenAIHandler.requested_model, "vendor-a")

    def test_find_codex_cli_prefers_configured_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "codex.exe")
            with open(path, "wb") as file:
                file.write(b"test")
            self.assertEqual(find_codex_cli(path), os.path.abspath(path))

    @patch("ai_clients.CodexAppServer")
    def test_fetch_codex_models_uses_model_list(self, server_class):
        server = MagicMock()
        server_class.return_value.__enter__.return_value = server
        server.request.return_value = {
            "data": [{"id": "gpt-a", "model": "gpt-a"}, {"id": "gpt-b", "model": "gpt-b"}],
            "nextCursor": None,
        }
        self.assertEqual(fetch_codex_models("codex.exe"), ["gpt-a", "gpt-b"])
        server.request.assert_called_once_with(
            "model/list", {"limit": 200, "includeHidden": False}, timeout=30
        )

    @patch("ai_clients.CodexAppServer")
    def test_run_codex_prompt_returns_final_agent_message(self, server_class):
        server = MagicMock()
        server_class.return_value.__enter__.return_value = server

        def request(method, _params=None, timeout=None):
            if method == "thread/start":
                return {"thread": {"id": "thread-1"}}
            if method == "turn/start":
                return {"turn": {"id": "turn-1", "status": "inProgress"}}
            self.fail(f"unexpected method: {method}")

        server.request.side_effect = request
        server.next_event.side_effect = [
            {
                "method": "item/completed",
                "params": {"item": {"type": "agentMessage", "text": '{"author":"Alice"}'}},
            },
            {"method": "turn/completed", "params": {"turn": {"status": "completed"}}},
        ]
        result = run_codex_prompt("codex.exe", "gpt-a", "identify", timeout=5)
        self.assertEqual(result, '{"author":"Alice"}')

    @patch("ai_extract.run_codex_prompt", return_value='{"author":"Alice"}')
    def test_author_extractor_dispatches_to_codex(self, run_prompt):
        result = _call_chat(
            {
                "ai_provider": PROVIDER_CODEX,
                "codex_cli_path": "codex.exe",
                "model": "gpt-a",
                "prompt": "system",
            },
            "readme",
        )
        self.assertEqual(result, '{"author":"Alice"}')
        run_prompt.assert_called_once()


if __name__ == "__main__":
    unittest.main()
