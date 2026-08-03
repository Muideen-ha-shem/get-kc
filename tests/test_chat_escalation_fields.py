"""Tests for /chat's new Phase 24 escalation_recommended/escalation_reason
fields — additive, backward compatible. Does not edit test_phase20_routes.py's
existing assertions."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.schemas import ChatResponse


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


class TestChatEscalationFields:
    def test_defaults_to_not_recommended(self, client):
        with patch("src.api.routes.chat.chat_orchestrator.process_request_response") as mock_process:
            mock_process.return_value = ChatResponse(answer="ok", sources=[])
            response = client.post("/chat", json={"message": "hello"})

        body = response.json()
        assert body["escalation_recommended"] is False
        assert body["escalation_reason"] is None

    def test_surfaces_recommendation_when_orchestrator_sets_it(self, client):
        with patch("src.api.routes.chat.chat_orchestrator.process_request_response") as mock_process:
            mock_process.return_value = ChatResponse(
                answer="ok", sources=[], escalation_recommended=True, escalation_reason="explicit_request"
            )
            response = client.post("/chat", json={"message": "talk to a human"})

        body = response.json()
        assert body["escalation_recommended"] is True
        assert body["escalation_reason"] == "explicit_request"

    def test_client_ignoring_new_fields_sees_unchanged_pre_existing_keys(self, client):
        with patch("src.api.routes.chat.chat_orchestrator.process_request_response") as mock_process:
            mock_process.return_value = ChatResponse(answer="ok", sources=["https://a.com"], session_id="s1")
            response = client.post("/chat", json={"message": "hello"})

        body = response.json()
        assert body["answer"] == "ok"
        assert body["sources"] == ["https://a.com"]
        assert body["session_id"] == "s1"
