"""Tests proving workspace_name/workspace_welcome_message actually reach
SourceRouter.route(), SearchManager.retrieve(), and
ResponseGenerator.generate() end-to-end through ChatOrchestrator — the
plumbing half of the "Tell me about Ha-Shem" self-identity fix (the
detection/guard logic itself is tested in test_self_identity.py,
test_routing.py, test_search_manager.py, and test_response_generator.py).
All additive: omitting the new params must behave exactly like before."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.orchestrator.chat_orchestrator import ChatOrchestrator
from src.services.routing.source_router import RoutingDecision


def _make_orchestrator():
    source_router = MagicMock()
    source_router.route.return_value = RoutingDecision(knowledge=True, web=False)

    search_manager = MagicMock()
    search_manager.retrieve.return_value = []
    search_manager.product_match = None

    response_generator = MagicMock()
    response_generator.generate.return_value = {"answer": "Answer.", "citations": []}

    orchestrator = ChatOrchestrator(
        source_router=source_router,
        search_manager=search_manager,
        response_generator=response_generator,
    )
    return orchestrator, source_router, search_manager, response_generator


class TestWorkspaceIdentityPlumbing:
    def test_workspace_name_reaches_all_three_collaborators(self):
        orchestrator, source_router, search_manager, response_generator = _make_orchestrator()

        orchestrator.chat(
            "Tell me about Ha-Shem",
            workspace_id="w1",
            workspace_name="Ha-Shem",
            workspace_welcome_message="Welcome to Ha-Shem — how can HavisIQ help today?",
        )

        assert source_router.route.call_args.kwargs["workspace_name"] == "Ha-Shem"
        assert search_manager.retrieve.call_args.kwargs["workspace_name"] == "Ha-Shem"
        assert search_manager.retrieve.call_args.kwargs["workspace_id"] == "w1"
        assert response_generator.generate.call_args.kwargs["workspace_name"] == "Ha-Shem"
        assert (
            response_generator.generate.call_args.kwargs["workspace_welcome_message"]
            == "Welcome to Ha-Shem — how can HavisIQ help today?"
        )

    def test_omitted_workspace_name_flows_as_none_to_all_three(self):
        orchestrator, source_router, search_manager, response_generator = _make_orchestrator()

        orchestrator.chat("What are your office hours?")

        assert source_router.route.call_args.kwargs["workspace_name"] is None
        assert search_manager.retrieve.call_args.kwargs["workspace_name"] is None
        assert response_generator.generate.call_args.kwargs["workspace_name"] is None
        assert response_generator.generate.call_args.kwargs["workspace_welcome_message"] is None

    def test_process_request_response_forwards_workspace_identity_too(self):
        orchestrator, source_router, _search_manager, response_generator = _make_orchestrator()

        orchestrator.process_request_response(
            "Tell me about Ha-Shem", workspace_name="Ha-Shem", workspace_welcome_message="Hi there"
        )

        assert source_router.route.call_args.kwargs["workspace_name"] == "Ha-Shem"
        assert response_generator.generate.call_args.kwargs["workspace_welcome_message"] == "Hi there"
