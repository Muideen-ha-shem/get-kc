import unittest
from unittest.mock import patch

from src.api.routes.chat import chat
from src.api.schemas import ChatRequest
from src.chat import ask_knowledge_base


class ChatRouteRefactorTests(unittest.TestCase):
    def test_chat_uses_orchestrator_and_returns_response(self):
        with patch("src.api.routes.chat.chat_orchestrator.process_request", return_value={"answer": "ok", "sources": ["https://example.com"]}) as mock_process:
            result = chat(ChatRequest(message="hello"))

        self.assertEqual(result.answer, "ok")
        self.assertEqual(result.sources, ["https://example.com"])
        mock_process.assert_called_once_with("hello")

    def test_legacy_chat_entrypoint_delegates_to_orchestrator(self):
        with patch("src.chat.chat_orchestrator.process_request", return_value={"answer": "ok", "sources": []}) as mock_process:
            result = ask_knowledge_base("hello")

        self.assertEqual(result, {"answer": "ok", "sources": []})
        mock_process.assert_called_once_with("hello")


if __name__ == "__main__":
    unittest.main()
