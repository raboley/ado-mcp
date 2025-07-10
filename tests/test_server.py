import pytest
from fastmcp.client import Client
from server import mcp
from ado.errors import AdoAuthenticationError
from fastmcp.exceptions import ToolError

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
    expected_tools = ["check_ado_authentication", "list_projects", "set_ado_organization"]
    for tool in expected_tools:
        await assert_tool_is_discoverable(mcp_client, tool)


async def test_check_ado_authentication_tool(mcp_client: Client):
    """Tests the check_ado_authentication tool returns a boolean."""
    # This test assumes that ADO_ORGANIZATION_URL and AZURE_DEVOPS_EXT_PAT are set
    # in the environment for the test run, as per Taskfile.yaml.
    # If they are not set or invalid, the initial client initialization in server.py
    # will fail, and ado_client will be None, causing check_ado_authentication to return False.
    result = await mcp_client.call_tool("check_ado_authentication")
    assert isinstance(result.data, bool), "Expected authentication check to return a boolean."
    # Further assertion depends on whether valid credentials are provided in the test environment
    # For now, we just check it returns a boolean.


async def test_list_projects_tool_returns_valid_list(mcp_client: Client):
    """Tests that the list_projects tool returns a valid list of projects."""
    # This test also depends on valid ADO credentials being set in the environment.
    result = await mcp_client.call_tool("list_projects")
    projects = result.data

    assert isinstance(projects, list), "The result should be a list."
    # If there are projects, validate the structure of the first one.
    if projects:
        project = projects[0]
        # Use 'in' to check for keys in a dictionary
        assert "id" in project, "Project should have an 'id' key."
        assert "name" in project, "Project should have a 'name' key."


async def test_set_ado_organization_success(mcp_client: Client):
    """Tests that the ado_organization can be switched successfully."""
    # This test requires a valid ADO_ORGANIZATION_URL and AZURE_DEVOPS_EXT_PAT to be set
    # in the environment for the test to pass.
    new_org_url = "https://dev.azure.com/RussellBoley" # Use a known good organization
    result = await mcp_client.call_tool("set_ado_organization", {"organization_url": new_org_url})
    assert result.data["result"] is True, f"Expected organization switch to {new_org_url} to succeed."

    # Verify that the authentication check now passes with the new org
    auth_result = await mcp_client.call_tool("check_ado_authentication")
    assert auth_result.data is True, "Expected authentication to succeed after switching to a valid organization."


async def test_set_ado_organization_failure(mcp_client: Client):
    """Tests that switching to a nonexistent organization fails gracefully and raises an AdoAuthenticationError."""
    invalid_org_url = "https://dev.azure.com/doesntexist" # Use a known bad organization
    with pytest.raises(ToolError, match="Authentication check failed"):
        await mcp_client.call_tool("set_ado_organization", {"organization_url": invalid_org_url})

    # Verify that the authentication check now fails
    auth_result = await mcp_client.call_tool("check_ado_authentication")
    assert auth_result.data is False, "Expected authentication to fail after switching to an invalid organization."


async def test_customer_change_organization(mcp_client: Client):
    """Tests the change_organization tool as a customer would use it."""
    target_url = "https://dev.azure.com/RussellBoley"
    result = await mcp_client.call_tool("set_ado_organization", {"organization_url": target_url})
    assert result.data["result"] is True, f"Expected organization to change to {target_url}"


async def test_list_projects_after_invalid_org_switch(mcp_client: Client):
    """Tests that list_projects fails or returns empty after an invalid organization switch."""
    invalid_org_url = "https://dev.azure.com/definitely-not-a-real-org"
    # Attempt to switch to an invalid organization, expecting an error
    with pytest.raises(ToolError, match="Authentication check failed"):
        await mcp_client.call_tool("set_ado_organization", {"organization_url": invalid_org_url})

    # Now try to list projects
    list_projects_result = await mcp_client.call_tool("list_projects")
    assert list_projects_result.data == [], "Expected list_projects to return an empty list or indicate failure."
    # Optionally, you might assert that check_ado_authentication is False here as well
    auth_result = await mcp_client.call_tool("check_ado_authentication")
    assert auth_result.data is False, "Expected authentication to be false after invalid switch."


@pytest.fixture
async def mcp_client_with_unset_ado_env(monkeypatch):
    """
    Provides a connected MCP client for tests where ADO_ORGANIZATION_URL
    and AZURE_DEVOPS_EXT_PAT environment variables are unset,
    simulating a server startup without these variables.
    """
    monkeypatch.delenv("ADO_ORGANIZATION_URL", raising=False)
    monkeypatch.delenv("AZURE_DEVOPS_EXT_PAT", raising=False)

    # Re-import server to ensure initialize_ado_client runs with unset env
    import importlib
    import server
    importlib.reload(server)

    async with Client(server.mcp) as client:
        yield client


async def test_initial_client_no_ado_org_url(mcp_client_with_unset_ado_env: Client):
    """
    Tests the initial state of the MCP client when ADO_ORGANIZATION_URL
    and AZURE_DEVOPS_EXT_PAT are not set during server startup.
    """
    # Verify that check_ado_authentication returns False
    auth_result = await mcp_client_with_unset_ado_env.call_tool("check_ado_authentication")
    assert auth_result.data is False, "Expected authentication to be false when ADO_ORGANIZATION_URL is unset."

    # Verify that list_projects returns an empty list
    list_projects_result = await mcp_client_with_unset_ado_env.call_tool("list_projects")
    assert list_projects_result.data == [], "Expected list_projects to return an empty list when ADO_ORGANIZATION_URL is unset."

    # Verify that set_ado_organization raises an AdoAuthenticationError
    with pytest.raises(ToolError, match="Authentication check failed"):
        await mcp_client_with_unset_ado_env.call_tool("set_ado_organization", {"organization_url": "https://dev.azure.com/someorg"})