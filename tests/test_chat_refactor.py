import unittest
from unittest.mock import patch

from src.api.routes.chat import chat
from src.api.schemas import ChatRequest, ChatResponse
from src.chat import ask_knowledge_base
from src.services.workspace.workspace_models import DEFAULT_WORKSPACE_ID, DEFAULT_WORKSPACE_SLUG
from src.services.workspace.workspace_context import WorkspaceContext


class ChatRouteRefactorTests(unittest.TestCase):
    def test_chat_uses_orchestrator_and_returns_response(self):
        mocked_response = ChatResponse(answer="ok", sources=["https://example.com"])
        default_workspace = WorkspaceContext(
            workspace_id=DEFAULT_WORKSPACE_ID, slug=DEFAULT_WORKSPACE_SLUG, name="Ha-Shem", is_default=True
        )
        with patch("src.api.routes.chat.chat_orchestrator.process_request_response", return_value=mocked_response) as mock_process:
            result = chat(ChatRequest(message="hello"), user=None, workspace=default_workspace)

        self.assertEqual(result.answer, "ok")
        self.assertEqual(result.sources, ["https://example.com"])
        mock_process.assert_called_once_with(
            "hello", session_id=None, profile_context=None, workspace_id=DEFAULT_WORKSPACE_ID,
            workspace_name="Ha-Shem", workspace_welcome_message=None, handoff_context=None,
        )

    def test_legacy_chat_entrypoint_delegates_to_orchestrator(self):
        with patch("src.chat.chat_orchestrator.process_request", return_value={"answer": "ok", "sources": []}) as mock_process:
            result = ask_knowledge_base("hello")

        self.assertEqual(result, {"answer": "ok", "sources": []})
        mock_process.assert_called_once_with("hello")


if __name__ == "__main__":
    unittest.main()
