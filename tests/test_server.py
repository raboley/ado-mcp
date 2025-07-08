import pytest
from fastmcp.client import Client
from server import mcp, ado_client

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio


@pytest.fixture
async def mcp_client():
    """Provides a connected MCP client for tests."""
    async with Client(mcp) as client:
        yield client


async def assert_tool_is_discoverable(mcp_client: Client, tool_name: str):
    """Asserts that a tool is present in the server's tool list."""
    # Correctly access the list of tools from the server capabilities
    tool_names = [tool.name for tool in await mcp_client.list_tools()]
    assert tool_name in tool_names, f"Tool '{tool_name}' should be discoverable."


async def test_tool_discovery(mcp_client: Client):
    """Tests that all expected tools are registered and discoverable."""
    expected_tools = ["check_ado_authentication", "list_projects"]
    for tool in expected_tools:
        await assert_tool_is_discoverable(mcp_client, tool)


async def test_check_ado_authentication_tool(mcp_client: Client):
    """Tests the check_ado_authentication tool returns a boolean."""
    if not ado_client:
        pytest.skip("ADO client not initialized, skipping authentication tool test.")

    result = await mcp_client.call_tool("check_ado_authentication")
    assert result.data is True, "Expected authentication check to return True."


async def test_list_projects_tool_returns_valid_list(mcp_client: Client):
    """Tests that the list_projects tool returns a valid list of projects."""
    if not ado_client:
        pytest.skip("ADO client not initialized, skipping list_projects tool test.")

    result = await mcp_client.call_tool("list_projects")
    projects = result.data

    assert isinstance(projects, list), "The result should be a list."
    # If there are projects, validate the structure of the first one.
    if projects:
        project = projects[0]
        # Use 'in' to check for keys in a dictionary
        assert "id" in project, "Project should have an 'id' key."
        assert "name" in project, "Project should have a 'name' key."