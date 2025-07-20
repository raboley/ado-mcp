"""
Tests for the check_ado_authentication MCP tool.

This module tests the authentication verification functionality.
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



@requires_ado_creds
async def test_check_authentication_success(mcp_client: Client):
    """Test successful authentication check."""
    result = await mcp_client.call_tool("check_ado_authentication")
    
    auth_result = result.data
    assert auth_result is True, "Authentication should succeed with valid credentials"



@requires_ado_creds 
async def test_check_authentication_after_org_change(mcp_client: Client):
    """Test authentication check after changing organization."""
    # Verify initial authentication works
    result = await mcp_client.call_tool("check_ado_authentication")
    assert result.data is True, "Initial authentication should work"
    
    # Change organization back to the same one
    org_url = os.environ.get("ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley")
    await mcp_client.call_tool("set_ado_organization", {"organization_url": org_url})
    
    # Verify authentication still works
    result = await mcp_client.call_tool("check_ado_authentication")
    assert result.data is True, "Authentication should still work after org change"


async def test_check_authentication_tool_registration():
    """Test that the check_ado_authentication tool is properly registered."""
    # This test verifies the tool exists in the MCP server
    async with Client(mcp) as client:
        tools_response = await client.list_tools()
        # Handle both potential response formats
        if hasattr(tools_response, "tools"):
            tools = tools_response.tools
        else:
            tools = tools_response
        tool_names = [tool.name for tool in tools]
        assert "check_ado_authentication" in tool_names, "check_ado_authentication tool should be registered"