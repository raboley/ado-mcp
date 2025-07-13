import pytest
from fastmcp.client import Client
from server import mcp
from fastmcp.exceptions import ToolError
from tests.ado.test_client import requires_ado_creds
import os

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio

@pytest.fixture
async def mcp_client():
    """Provides a connected MCP client for tests, ensuring a valid initial state."""
    async with Client(mcp) as client:
        initial_org_url = os.environ.get("ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley")
        await client.call_tool("set_ado_organization", {"organization_url": initial_org_url})
        yield client

@pytest.fixture
async def mcp_client_with_unset_ado_env(monkeypatch):
    """
    Provides a client for tests where ADO env vars are unset,
    simulating a server startup without initial credentials.
    """
    monkeypatch.delenv("ADO_ORGANIZATION_URL", raising=False)
    monkeypatch.delenv("AZURE_DEVOPS_EXT_PAT", raising=False)
    import importlib
    import server
    importlib.reload(server)
    async with Client(server.mcp) as client:
        yield client

@requires_ado_creds
async def test_list_projects_returns_valid_list(mcp_client: Client):
    """Tests that the list_projects tool returns a valid list of projects."""
    result = await mcp_client.call_tool("list_projects")
    projects = result.data
    assert isinstance(projects, list)
    if projects:
        project = projects[0]
        assert isinstance(project, dict)
        assert "id" in project
        assert "name" in project

@requires_ado_creds
async def test_list_pipelines_returns_valid_list(mcp_client: Client):
    """Tests that the list_pipelines tool returns a valid list of pipelines."""
    projects_result = await mcp_client.call_tool("list_projects")
    projects = projects_result.data
    if not projects:
        pytest.skip("No projects found to test pipeline listing.")
    
    project_id = projects[0]['id']
    result = await mcp_client.call_tool("list_pipelines", {"project_id": project_id})
    pipelines = result.data # Assuming result.data is already the list
    assert isinstance(pipelines, list)
    if pipelines:
        pipeline = pipelines[0]
        assert isinstance(pipeline, dict)
        assert "id" in pipeline
        assert "name" in pipeline

@requires_ado_creds
async def test_get_pipeline_returns_valid_details(mcp_client: Client):
    """Tests that get_pipeline returns valid details for a specific pipeline."""
    projects = (await mcp_client.call_tool("list_projects")).data
    if not projects:
        pytest.skip("No projects found.")
    project_id = projects[0]['id']

    pipelines = (await mcp_client.call_tool("list_pipelines", {"project_id": project_id})).data
    if not pipelines:
        pytest.skip("No pipelines found.")
    pipeline_id = pipelines[0]['id']

    details = (await mcp_client.call_tool("get_pipeline", {"project_id": project_id, "pipeline_id": pipeline_id})).data
    assert isinstance(details, dict)
    assert details.get("id") == pipeline_id

@requires_ado_creds
async def test_run_and_get_pipeline_run_details(mcp_client: Client):
    """Tests running a pipeline and getting its run details."""
    projects = (await mcp_client.call_tool("list_projects")).data
    if not projects:
        pytest.skip("No projects found.")
    project_id = projects[0]['id']

    pipelines = (await mcp_client.call_tool("list_pipelines", {"project_id": project_id})).data
    if not pipelines:
        pytest.skip("No pipelines found.")
    pipeline_id = pipelines[0]['id']

    run_details = (await mcp_client.call_tool("run_pipeline", {"project_id": project_id, "pipeline_id": pipeline_id})).data
    assert isinstance(run_details, dict)
    assert "id" in run_details
    run_id = run_details["id"]

    run_status = (await mcp_client.call_tool("get_pipeline_run", {"project_id": project_id, "run_id": run_id})).data
    assert isinstance(run_status, dict)
    assert run_status.get("id") == run_id

# --- Tests for behavior without a valid ADO client ---

async def test_no_client_check_authentication(mcp_client_with_unset_ado_env: Client):
    """Tests check_ado_authentication returns False when client is not available."""
    result = await mcp_client_with_unset_ado_env.call_tool("check_ado_authentication")
    assert result.data is False

async def test_no_client_list_projects(mcp_client_with_unset_ado_env: Client):
    """Tests list_projects returns empty list when client is not available."""
    result = await mcp_client_with_unset_ado_env.call_tool("list_projects")
    assert result.data == []

async def test_no_client_list_pipelines(mcp_client_with_unset_ado_env: Client):
    """Tests list_pipelines returns empty list when client is not available."""
    result = await mcp_client_with_unset_ado_env.call_tool("list_pipelines", {"project_id": "any"})
    assert result.data == []

async def test_no_client_get_pipeline(mcp_client_with_unset_ado_env: Client):
    """Tests get_pipeline returns None when client is not available."""
    result = await mcp_client_with_unset_ado_env.call_tool("get_pipeline", {"project_id": "any", "pipeline_id": 1})
    assert result.data is None

async def test_no_client_run_pipeline(mcp_client_with_unset_ado_env: Client):
    """Tests run_pipeline returns None when client is not available."""
    result = await mcp_client_with_unset_ado_env.call_tool("run_pipeline", {"project_id": "any", "pipeline_id": 1})
    assert result.data is None

async def test_no_client_get_pipeline_run(mcp_client_with_unset_ado_env: Client):
    """Tests get_pipeline_run returns None when client is not available."""
    result = await mcp_client_with_unset_ado_env.call_tool("get_pipeline_run", {"project_id": "any", "run_id": 1})
    assert result.data is None

# --- Tests for stateful behavior (switching orgs) ---

@requires_ado_creds
async def test_set_organization_failure_and_recovery(mcp_client: Client):
    """Tests that switching to a nonexistent org fails and the client becomes invalid."""
    # 1. Switch to an invalid organization
    invalid_org_url = "https://dev.azure.com/this-org-does-not-exist-for-sure"
    with pytest.raises(ToolError, match="Authentication check failed"):
        await mcp_client.call_tool("set_ado_organization", {"organization_url": invalid_org_url})

    # 2. Verify client is now invalid
    auth_result = await mcp_client.call_tool("check_ado_authentication")
    assert auth_result.data is False, "Auth should fail after switching to an invalid org."

    list_result = await mcp_client.call_tool("list_projects")
    assert list_result.data == [], "list_projects should return empty when client is invalid."

    # 3. (Recovery) Switch back to a valid organization
    valid_org_url = os.environ.get("ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley")
    set_result = await mcp_client.call_tool("set_ado_organization", {"organization_url": valid_org_url})
    assert set_result.data.get("result") is True

    # 4. Verify client is valid again
    auth_result_after_recovery = await mcp_client.call_tool("check_ado_authentication")
    assert auth_result_after_recovery.data is True, "Auth should succeed after switching back to a valid org."
