"""
Unit tests for the Ha-Shem AI Support Platform MCP Server.
Validates tool registration, metadata, and responses under mocked conditions.
"""

from __future__ import annotations
import unittest
from unittest.mock import patch, MagicMock

# Import the MCP server and its tools
from src.mcp.server import mcp, search_knowledge_base, list_products, check_service_status


class MCPServerTests(unittest.TestCase):
    """Verifies registration and functionality of MCP tools."""

    def test_mcp_server_initialization(self) -> None:
        """Ensure the FastMCP server is correctly named and configured."""
        self.assertEqual(mcp.name, "Ha-Shem AI Support Platform")

    def test_list_products_tool(self) -> None:
        """Verify list_products returns a detailed description of services."""
        result = list_products()
        self.assertIn("Ha-Shem Limited - Products & Services Portfolio", result)
        self.assertIn("Microsoft 365 Integration", result)
        self.assertIn("Cybersecurity", result)

    @patch("src.services.knowledge.knowledge_service.KnowledgeService.retrieve_context")
    def test_search_knowledge_base_success(self, mock_retrieve: MagicMock) -> None:
        """Verify search_knowledge_base formats search results correctly."""
        # Mock vector search results
        mock_retrieve.return_value = (
            [
                {
                    "chunk_content": "Ha-Shem provides cloud solutions.",
                    "parent_url": "https://ha-shem.com/cloud",
                    "similarity": 0.85,
                }
            ],
            [0.85],
            ["https://ha-shem.com/cloud"],
        )

        result = search_knowledge_base("cloud solutions")
        self.assertIn("Search Results", result)
        self.assertIn("Ha-Shem provides cloud solutions.", result)
        self.assertIn("https://ha-shem.com/cloud", result)
        mock_retrieve.assert_called_once_with("cloud solutions")

    @patch("src.services.knowledge.knowledge_service.KnowledgeService.retrieve_context")
    def test_search_knowledge_base_empty(self, mock_retrieve: MagicMock) -> None:
        """Verify search_knowledge_base handles empty search results gracefully."""
        mock_retrieve.return_value = ([], [], [])

        result = search_knowledge_base("invalid query")
        self.assertEqual(result, "No matching documentation found in the knowledge base.")
        mock_retrieve.assert_called_once_with("invalid query")

    @patch("os.getenv")
    @patch("src.infrastructure.database.supabase.get_client")
    @patch("src.api.services.embeddings.embed_query")
    @patch("groq.Groq")
    def test_check_service_status_operational(
        self, mock_groq: MagicMock, mock_embed: MagicMock, mock_supabase: MagicMock, mock_getenv: MagicMock
    ) -> None:
        """Verify check_service_status reports system component availability."""
        # Setup mocks for environment keys
        mock_getenv.side_effect = lambda key: {
            "GOOGLE_API_KEY": "fake_google_key",
            "GROQ_API_KEY": "fake_groq_key",
            "SUPABASE_URL": "fake_sb_url",
            "SUPABASE_KEY": "fake_sb_key",
        }.get(key)

        # Mock Supabase query execution
        mock_db_client = MagicMock()
        mock_supabase.return_value = mock_db_client
        mock_db_client.table.return_value.select.return_value.limit.return_value.execute.return_value.data = [{"id": 1}]

        # Mock Google Embeddings response size
        mock_embed.return_value = [0.1] * 768

        # Mock Groq client chat completion response
        mock_groq_client = MagicMock()
        mock_groq.return_value = mock_groq_client
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content="pong"))]
        mock_groq_client.chat.completions.create.return_value = mock_completion

        # Run health check
        result = check_service_status()

        self.assertIn("System Health & Connectivity Audit", result)
        self.assertIn("GOOGLE_API_KEY:** Present", result)
        self.assertIn("Database Connectivity (Supabase)", result)
        self.assertIn("Connection:** Success", result)
        self.assertIn("Embeddings Engine (Google Gemini)", result)
        self.assertIn("Status:** Operational", result)
        self.assertIn("Language Generation Engine (Groq API)", result)


if __name__ == "__main__":
    unittest.main()
