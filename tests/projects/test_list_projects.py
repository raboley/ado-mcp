"""
Tests for the list_projects MCP tool.

This module tests the project listing functionality.
"""

import os
import pytest
from fastmcp.client import Client

from server import mcp
from tests.ado.test_client import requires_ado_creds

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio


@pytest.fixture
async def mcp_client():
    """Provides a connected MCP client for tests."""
    async with Client(mcp) as client:
        initial_org_url = os.environ.get(
            "ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley"
        )
        await client.call_tool("set_ado_organization", {"organization_url": initial_org_url})
        yield client


@pytest.fixture
async def mcp_client_no_auth(monkeypatch):
    """Provides a connected MCP client without authentication setup."""
    # Unset environment variables that provide authentication
    monkeypatch.delenv("AZURE_DEVOPS_EXT_PAT", raising=False)
    monkeypatch.delenv("ADO_ORGANIZATION_URL", raising=False)
    async with Client(mcp) as client:
        yield client


@requires_ado_creds
async def test_list_projects_returns_valid_list(mcp_client: Client):
    """Test that list_projects returns a valid list of projects."""
    result = await mcp_client.call_tool("list_projects")
    
    projects = result.data
    assert projects is not None, "Projects list should not be None"
    assert isinstance(projects, list), "Projects should be a list"
    
    if len(projects) > 0:
        # Verify structure of first project
        project = projects[0]
        assert isinstance(project, dict), "Project should be a dictionary"
        assert "id" in project, "Project should have an id"
        assert "name" in project, "Project should have a name"
        assert "url" in project, "Project should have a url"
        
        # Verify field types
        assert isinstance(project["id"], str), "Project id should be a string"
        assert isinstance(project["name"], str), "Project name should be a string"
        assert isinstance(project["url"], str), "Project url should be a string"
        
        print(f"Found {len(projects)} projects")
        print(f"First project: {project['name']} ({project['id']})")
    else:
        print("No projects found in organization")


async def test_list_projects_no_client(mcp_client_no_auth: Client):
    """Test list_projects behavior when no client is configured."""
    result = await mcp_client.call_tool("list_projects")
    
    projects = result.data
    assert projects == [], "Should return empty list when no client is configured"


@requires_ado_creds
async def test_list_projects_finds_expected_project(mcp_client: Client):
    """Test that list_projects finds the expected ado-mcp project."""
    result = await mcp_client.call_tool("list_projects")
    
    projects = result.data
    assert isinstance(projects, list), "Projects should be a list"
    
    # Look for the ado-mcp project
    ado_mcp_project = None
    for project in projects:
        if project.get("name") == "ado-mcp":
            ado_mcp_project = project
            break
    
    assert ado_mcp_project is not None, "Should find the ado-mcp project"
    assert ado_mcp_project["id"] == "49e895da-15c6-4211-97df-65c547a59c22", "Should have correct project ID"


async def test_list_projects_tool_registration():
    """Test that the list_projects tool is properly registered."""
    async with Client(mcp) as client:
        tools_response = await client.list_tools()
        # Handle both potential response formats
        if hasattr(tools_response, "tools"):
            tools = tools_response.tools
        else:
            tools = tools_response
        tool_names = [tool.name for tool in tools]
        assert "list_projects" in tool_names, "list_projects tool should be registered"