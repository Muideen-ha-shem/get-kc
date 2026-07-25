"""Tests for the demo-request feature: schema validation, the persistence
service, and the route handler. All Supabase calls are mocked.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


class TestDemoRequestSchema:
    def test_valid_payload(self):
        from src.api.schemas import DemoRequest

        req = DemoRequest(name="Ada", email="ada@example.com", company="Acme", use_case="KYC", product="SPIDIFY")
        assert req.email == "ada@example.com"

    def test_minimal_payload_optional_fields_default_none(self):
        from src.api.schemas import DemoRequest

        req = DemoRequest(name="Ada", email="ada@example.com")
        assert req.company is None
        assert req.use_case is None
        assert req.product is None

    def test_invalid_email_rejected(self):
        from pydantic import ValidationError
        from src.api.schemas import DemoRequest

        with pytest.raises(ValidationError):
            DemoRequest(name="Ada", email="not-an-email")

    def test_empty_name_rejected(self):
        from pydantic import ValidationError
        from src.api.schemas import DemoRequest

        with pytest.raises(ValidationError):
            DemoRequest(name="", email="ada@example.com")


# ---------------------------------------------------------------------------
# submit_demo_request service
# ---------------------------------------------------------------------------


class TestSubmitDemoRequest:
    def test_successful_insert_returns_row(self):
        from src.api.services import demo_requests

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{"id": 1, "name": "Ada", "email": "ada@example.com", "company": None, "use_case": None, "product": None}]
        mock_client.table.return_value.insert.return_value.execute.return_value = mock_response

        with patch.object(demo_requests, "get_client", return_value=mock_client):
            result = demo_requests.submit_demo_request(name="Ada", email="ada@example.com")

        assert result["id"] == 1
        mock_client.table.assert_called_once_with("demo_requests")

    def test_missing_table_raises_specific_error(self):
        from src.api.services import demo_requests

        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.side_effect = Exception(
            "Could not find the table 'public.demo_requests' in the schema cache"
        )

        with patch.object(demo_requests, "get_client", return_value=mock_client):
            with pytest.raises(demo_requests.DemoRequestTableMissingError):
                demo_requests.submit_demo_request(name="Ada", email="ada@example.com")

    def test_other_errors_propagate_unchanged(self):
        from src.api.services import demo_requests

        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.side_effect = RuntimeError("network down")

        with patch.object(demo_requests, "get_client", return_value=mock_client):
            with pytest.raises(RuntimeError, match="network down"):
                demo_requests.submit_demo_request(name="Ada", email="ada@example.com")

    def test_falls_back_to_payload_when_no_rows_returned(self):
        from src.api.services import demo_requests

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        mock_client.table.return_value.insert.return_value.execute.return_value = mock_response

        with patch.object(demo_requests, "get_client", return_value=mock_client):
            result = demo_requests.submit_demo_request(name="Ada", email="ada@example.com", product="SPIDIFY")

        assert result["name"] == "Ada"
        assert result["product"] == "SPIDIFY"


# ---------------------------------------------------------------------------
# Route handler
# ---------------------------------------------------------------------------


class TestDemoRequestRoute:
    def test_successful_submission(self):
        from src.api.routes.demo_request import create_demo_request
        from src.api.schemas import DemoRequest

        with patch(
            "src.api.routes.demo_request.submit_demo_request",
            return_value={"id": 7, "name": "Ada", "email": "ada@example.com", "company": "Acme", "use_case": "KYC", "product": "SPIDIFY"},
        ) as mock_submit:
            result = create_demo_request(DemoRequest(name="Ada", email="ada@example.com", company="Acme", use_case="KYC", product="SPIDIFY"))

        assert result.id == 7
        assert result.status == "received"
        mock_submit.assert_called_once_with(name="Ada", email="ada@example.com", company="Acme", use_case="KYC", product="SPIDIFY")

    def test_missing_table_returns_503(self):
        from fastapi import HTTPException
        from src.api.routes.demo_request import create_demo_request
        from src.api.schemas import DemoRequest
        from src.api.services.demo_requests import DemoRequestTableMissingError

        with patch(
            "src.api.routes.demo_request.submit_demo_request",
            side_effect=DemoRequestTableMissingError("table missing"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                create_demo_request(DemoRequest(name="Ada", email="ada@example.com"))

        assert exc_info.value.status_code == 503

    def test_generic_failure_returns_500(self):
        from fastapi import HTTPException
        from src.api.routes.demo_request import create_demo_request
        from src.api.schemas import DemoRequest

        with patch(
            "src.api.routes.demo_request.submit_demo_request",
            side_effect=RuntimeError("boom"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                create_demo_request(DemoRequest(name="Ada", email="ada@example.com"))

        assert exc_info.value.status_code == 500
