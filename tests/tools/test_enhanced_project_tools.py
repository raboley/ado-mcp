"""Tests for enhanced project tools integration in MCP server."""

import os

import pytest
from fastmcp.client import Client

from server import mcp
from src.test_config import get_organization_url

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def mcp_client():
    """Get an MCP client for testing."""
    async with Client(mcp) as client:
        try:
            initial_org_url = get_organization_url()
        except Exception:
            # Fallback to environment variable if dynamic config not available
            initial_org_url = os.environ.get(
                "ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley"
            )
        await client.call_tool("set_ado_organization", {"organization_url": initial_org_url})
        yield client


async def test_find_project_by_id_or_name_tool_available(mcp_client: Client):
    """Test that find_project_by_id_or_name tool is available and has correct description."""
    tools = await mcp_client.list_tools()
    tool_names = [tool.name for tool in tools]

    assert "find_project_by_id_or_name" in tool_names

    # Find the specific tool
    find_tool = next(tool for tool in tools if tool.name == "find_project_by_id_or_name")

    # Check it has the expected description
    assert (
        "Find a project by either ID or name with fuzzy matching support" in find_tool.description
    )
    assert "unified project discovery" in find_tool.description


async def test_list_all_projects_with_metadata_tool_available(mcp_client: Client):
    """Test that list_all_projects_with_metadata tool is available and has correct description."""
    tools = await mcp_client.list_tools()
    tool_names = [tool.name for tool in tools]

    assert "list_all_projects_with_metadata" in tool_names

    # Find the specific tool
    list_tool = next(tool for tool in tools if tool.name == "list_all_projects_with_metadata")

    # Check it has the expected description
    assert "List all projects with enhanced metadata" in list_tool.description
    assert "LLM understanding" in list_tool.description


async def test_get_project_suggestions_tool_available(mcp_client: Client):
    """Test that get_project_suggestions tool is available and has correct description."""
    tools = await mcp_client.list_tools()
    tool_names = [tool.name for tool in tools]

    assert "get_project_suggestions" in tool_names

    # Find the specific tool
    suggestions_tool = next(tool for tool in tools if tool.name == "get_project_suggestions")

    # Check it has the expected description
    assert "Get fuzzy match suggestions for a project query" in suggestions_tool.description
    assert "similar project names" in suggestions_tool.description
