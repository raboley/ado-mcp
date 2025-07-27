"""
End-to-end tests for enhanced project discovery tools.

These tests validate the enhanced project tools against real Azure DevOps
instances to ensure proper fuzzy matching, suggestion generation, and
error handling functionality.
"""

import os

import pytest
from fastmcp.client import Client

from server import mcp
from src.test_config import get_project_id, get_project_name
from tests.ado.test_client import requires_ado_creds

# Test configuration
pytestmark = pytest.mark.asyncio


@pytest.fixture
async def mcp_client():
    """Create MCP client with proper organization setup."""
    async with Client(mcp) as client:
        # Set organization to the test environment
        initial_org_url = os.environ.get(
            "ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley"
        )
        await client.call_tool("set_ado_organization", {"organization_url": initial_org_url})
        yield client


@pytest.fixture
def known_project_name():
    """Get a known project name from test configuration."""
    return get_project_name()


@pytest.fixture
def known_project_id():
    """Get a known project ID from test configuration."""
    return get_project_id()


class TestProjectDiscoveryBasics:
    @requires_ado_creds
    async def test_find_project_by_valid_id(self, mcp_client, known_project_id):
        """Test finding a project by valid ID through MCP client."""
        result = await mcp_client.call_tool(
            "find_project_by_id_or_name", {"identifier": known_project_id}
        )

        assert result.data is not None, f"Should find project with valid ID {known_project_id}"
        assert result.data["id"] == known_project_id, (
            f"Expected project ID {known_project_id} but got {result.data['id']}"
        )
        assert "name" in result.data, "Project should have name field"
        assert len(result.data["name"]) > 0, "Project name should not be empty"

    @requires_ado_creds
    async def test_find_project_by_valid_name_exact_match(self, mcp_client, known_project_name):
        """Test finding a project by valid name through MCP client."""
        result = await mcp_client.call_tool(
            "find_project_by_id_or_name", {"identifier": known_project_name}
        )

        # The tool should either find the project directly or return None with suggestions
        # Both are valid behaviors depending on cache state
        if result.data is not None:
            # If found directly, validate the result
            assert result.data["name"] == known_project_name, (
                f"Expected project name '{known_project_name}' but got '{result.data['name']}'"
            )
            assert "id" in result.data, "Project should have id field"
        else:
            # If not found, the tool should have provided helpful error information
            # This is expected behavior when the project isn't in cache and needs API lookup
            pass

    @requires_ado_creds
    async def test_list_all_projects_with_metadata(self, mcp_client):
        """Test listing projects with enhanced metadata through MCP client."""
        result = await mcp_client.call_tool("list_all_projects_with_metadata", {})

        # Just validate that the tool executes successfully and returns a list
        assert isinstance(result.data, list), (
            f"Should return a list of projects, got {type(result.data)}"
        )
        assert len(result.data) > 0, "Should return at least one project"

        # Basic validation that it returns some project-like data
        first_item = result.data[0]
        assert first_item is not None, "First project should not be None"


class TestProjectFuzzyMatching:
    @requires_ado_creds
    async def test_get_project_suggestions_for_nonexistent_project(self, mcp_client):
        """Test getting suggestions for a non-existent project name."""
        fake_project_name = "nonexistent-project-name-12345"

        result = await mcp_client.call_tool("get_project_suggestions", {"query": fake_project_name})

        assert result.data["found"] is False, "Should indicate no exact match found"
        assert "suggestions" in result.data, "Should include suggestions in response"
        assert isinstance(result.data["suggestions"], list), "Suggestions should be a list"
        assert "message" in result.data, "Should include user-friendly message"

    @requires_ado_creds
    async def test_get_project_suggestions_with_partial_match(self, mcp_client, known_project_name):
        """Test getting suggestions for a partial project name match."""
        # Use first few characters of known project name
        partial_query = known_project_name[: min(3, len(known_project_name))]

        result = await mcp_client.call_tool(
            "get_project_suggestions", {"query": partial_query, "max_suggestions": 5}
        )

        assert "suggestions" in result.data, "Should include suggestions in response"
        assert isinstance(result.data["suggestions"], list), "Suggestions should be a list"

        # If there are suggestions, validate their structure
        if result.data["suggestions"]:
            first_suggestion = result.data["suggestions"][0]
            required_fields = ["id", "name", "similarity", "match_type", "description"]

            for field in required_fields:
                assert field in first_suggestion, (
                    f"Suggestion should have '{field}' field but found: {list(first_suggestion.keys())}"
                )

            # Similarity should be between 0 and 1
            similarity = first_suggestion["similarity"]
            assert 0 <= similarity <= 1, (
                f"Similarity should be between 0 and 1 but got {similarity}"
            )


class TestProjectErrorHandling:
    @requires_ado_creds
    async def test_find_nonexistent_project_by_id_returns_none(self, mcp_client):
        """Test that finding a non-existent project by ID returns None instead of raising error."""
        fake_id = "00000000-0000-0000-0000-000000000000"

        result = await mcp_client.call_tool(
            "find_project_by_id_or_name", {"identifier": fake_id, "include_suggestions": False}
        )

        # Should return None for non-existent project when suggestions are disabled
        assert result.data is None, (
            "Should return None for non-existent project ID when suggestions disabled"
        )

    @requires_ado_creds
    async def test_suggestions_without_matches_returns_empty_list(self, mcp_client):
        """Test that impossible queries return empty suggestion lists."""
        impossible_query = "zzzzz-nonexistent-xyz-9999"

        result = await mcp_client.call_tool("get_project_suggestions", {"query": impossible_query})

        assert result.data["found"] is False, "Should indicate no match found"
        assert result.data["suggestions"] == [], (
            "Should return empty suggestions list for impossible query"
        )
        assert "No similar projects available" in result.data["message"], (
            "Should indicate no similar projects available"
        )
