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
    
    # Try multiple projects to find one with pipelines
    pipelines_found = False
    for project in projects:
        project_id = project['id']
        result = await mcp_client.call_tool("list_pipelines", {"project_id": project_id})
        pipelines = result.data
        
        # Check that we always get a list back
        assert isinstance(pipelines, list), f"Expected list, got {type(pipelines)}"
        
        # If we find pipelines, test their structure
        if pipelines:
            pipelines_found = True
            pipeline = pipelines[0]
            # FastMCP converts Pydantic models to dicts for transport, so we expect a dict
            assert isinstance(pipeline, dict), f"Pipeline should be dict, got: {type(pipeline)}"
            assert "id" in pipeline, f"Pipeline should have id field, got keys: {pipeline.keys()}"
            assert "name" in pipeline, f"Pipeline should have name field, got keys: {pipeline.keys()}"
            assert isinstance(pipeline["id"], int), f"Pipeline id should be int, got: {type(pipeline['id'])}"
            assert isinstance(pipeline["name"], str), f"Pipeline name should be str, got: {type(pipeline['name'])}"
            break
    
    # If no project has pipelines, that's still a valid test result
    if not pipelines_found:
        pytest.skip("No pipelines found in any project.")

@requires_ado_creds
async def test_create_pipeline_creates_valid_pipeline(mcp_client: Client):
    """Tests that the create_pipeline tool creates a valid pipeline."""
    projects_result = await mcp_client.call_tool("list_projects")
    projects = projects_result.data
    if not projects:
        pytest.skip("No projects found to test pipeline creation.")
    
    # Use the ado-mcp project
    project_id = None
    for project in projects:
        if project["name"] == "ado-mcp":
            project_id = project["id"]
            break
    
    if not project_id:
        pytest.skip("ado-mcp project not found. Please create it first.")
    
    # Get service connections first
    connections_result = await mcp_client.call_tool("list_service_connections", {"project_id": project_id})
    connections = connections_result.data
    if not connections:
        pytest.skip("No service connections found to test pipeline creation.")
    
    # Find GitHub service connection
    github_connection_id = None
    for connection in connections:
        if connection["type"] == "GitHub":
            github_connection_id = connection["id"]
            break
    
    if not github_connection_id:
        pytest.skip("No GitHub service connection found.")
    
    # Create a test pipeline
    pipeline_name = f"test-pipeline-{int(__import__('time').time())}"
    result = await mcp_client.call_tool("create_pipeline", {
        "project_id": project_id,
        "name": pipeline_name,
        "yaml_path": "tests/ado/fixtures/fast.test.pipeline.yml",
        "repository_name": "raboley/ado-mcp",
        "service_connection_id": github_connection_id,
        "configuration_type": "yaml",
        "folder": "/test"
    })
    
    pipeline = result.data
    
    # Handle both Pydantic model and dict responses
    if hasattr(pipeline, 'id'):  # Pydantic model
        pipeline_id = pipeline.id
        pipeline_name_returned = pipeline.name
        assert isinstance(pipeline_id, int), f"Pipeline id should be int, got: {type(pipeline_id)}"
        assert isinstance(pipeline_name_returned, str), f"Pipeline name should be str, got: {type(pipeline_name_returned)}"
        assert pipeline_name_returned == pipeline_name, f"Pipeline name should be {pipeline_name}, got: {pipeline_name_returned}"
    else:  # Dict response
        assert isinstance(pipeline, dict), f"Created pipeline should be dict, got: {type(pipeline)}"
        assert "id" in pipeline, f"Created pipeline should have id field, got keys: {pipeline.keys()}"
        assert "name" in pipeline, f"Created pipeline should have name field, got keys: {pipeline.keys()}"
        pipeline_id = pipeline["id"]
        pipeline_name_returned = pipeline["name"]
        assert pipeline_name_returned == pipeline_name, f"Pipeline name should be {pipeline_name}, got: {pipeline_name_returned}"
        assert isinstance(pipeline_id, int), f"Pipeline id should be int, got: {type(pipeline_id)}"
    
    # Verify the pipeline appears in the list
    pipelines_list = await mcp_client.call_tool("list_pipelines", {"project_id": project_id})
    pipeline_ids = [p["id"] for p in pipelines_list.data]
    assert pipeline_id in pipeline_ids, f"Created pipeline {pipeline_id} should appear in pipelines list"
    
    # Clean up: Delete the test pipeline
    delete_result = await mcp_client.call_tool("delete_pipeline", {"project_id": project_id, "pipeline_id": pipeline_id})
    assert delete_result.data is True, f"Failed to delete test pipeline {pipeline_id}"
    
    # Verify the pipeline was deleted
    pipelines_list_after = await mcp_client.call_tool("list_pipelines", {"project_id": project_id})
    pipeline_ids_after = [p["id"] for p in pipelines_list_after.data]
    assert pipeline_id not in pipeline_ids_after, f"Pipeline {pipeline_id} should be deleted but still appears in list"

@requires_ado_creds
async def test_list_service_connections_returns_valid_list(mcp_client: Client):
    """Tests that the list_service_connections tool returns a valid list."""
    projects_result = await mcp_client.call_tool("list_projects")
    projects = projects_result.data
    if not projects:
        pytest.skip("No projects found to test service connections listing.")
    
    # Use the ado-mcp project
    project_id = None
    for project in projects:
        if project["name"] == "ado-mcp":
            project_id = project["id"]
            break
    
    if not project_id:
        pytest.skip("ado-mcp project not found.")
    
    result = await mcp_client.call_tool("list_service_connections", {"project_id": project_id})
    connections = result.data
    
    print(f"Connections type: {type(connections)}")
    print(f"Connections content: {connections}")
    if connections:
        print(f"First connection type: {type(connections[0])}")
        print(f"First connection content: {connections[0]}")
    
    assert isinstance(connections, list), f"Expected list, got {type(connections)}"

@requires_ado_creds
async def test_delete_pipeline_removes_pipeline(mcp_client: Client):
    """Tests that the delete_pipeline tool successfully removes a pipeline."""
    projects_result = await mcp_client.call_tool("list_projects")
    projects = projects_result.data
    if not projects:
        pytest.skip("No projects found to test pipeline deletion.")
    
    # Use the ado-mcp project
    project_id = None
    for project in projects:
        if project["name"] == "ado-mcp":
            project_id = project["id"]
            break
    
    if not project_id:
        pytest.skip("ado-mcp project not found.")
    
    # Get service connections first
    connections_result = await mcp_client.call_tool("list_service_connections", {"project_id": project_id})
    connections = connections_result.data
    if not connections:
        pytest.skip("No service connections found to test pipeline deletion.")
    
    # Find GitHub service connection
    github_connection_id = None
    for connection in connections:
        if connection["type"] == "GitHub":
            github_connection_id = connection["id"]
            break
    
    if not github_connection_id:
        pytest.skip("No GitHub service connection found.")
    
    # Create a test pipeline to delete
    pipeline_name = f"delete-test-pipeline-{int(__import__('time').time())}"
    create_result = await mcp_client.call_tool("create_pipeline", {
        "project_id": project_id,
        "name": pipeline_name,
        "yaml_path": "tests/ado/fixtures/fast.test.pipeline.yml",
        "repository_name": "raboley/ado-mcp",
        "service_connection_id": github_connection_id,
        "configuration_type": "yaml",
        "folder": "/test"
    })
    
    pipeline = create_result.data
    pipeline_id = pipeline.id if hasattr(pipeline, 'id') else pipeline["id"]
    
    # Verify pipeline exists
    pipelines_before = await mcp_client.call_tool("list_pipelines", {"project_id": project_id})
    pipeline_ids_before = [p["id"] for p in pipelines_before.data]
    assert pipeline_id in pipeline_ids_before, f"Created pipeline {pipeline_id} should exist before deletion"
    
    # Delete the pipeline
    delete_result = await mcp_client.call_tool("delete_pipeline", {"project_id": project_id, "pipeline_id": pipeline_id})
    assert delete_result.data is True, f"Failed to delete pipeline {pipeline_id}"
    
    # Verify pipeline was deleted
    pipelines_after = await mcp_client.call_tool("list_pipelines", {"project_id": project_id})
    pipeline_ids_after = [p["id"] for p in pipelines_after.data]
    assert pipeline_id not in pipeline_ids_after, f"Pipeline {pipeline_id} should be deleted but still appears in list"

@requires_ado_creds
async def test_cleanup_existing_test_pipelines(mcp_client: Client):
    """Clean up any existing test pipelines from previous test runs."""
    projects_result = await mcp_client.call_tool("list_projects")
    projects = projects_result.data
    if not projects:
        pytest.skip("No projects found to clean up test pipelines.")
    
    # Use the ado-mcp project
    project_id = None
    for project in projects:
        if project["name"] == "ado-mcp":
            project_id = project["id"]
            break
    
    if not project_id:
        pytest.skip("ado-mcp project not found.")
    
    # Get all pipelines
    pipelines_result = await mcp_client.call_tool("list_pipelines", {"project_id": project_id})
    pipelines = pipelines_result.data
    
    # Find test pipelines (those starting with "test")
    test_pipelines = [p for p in pipelines if p["name"].startswith("test")]
    
    if not test_pipelines:
        pytest.skip("No test pipelines found to clean up.")
    
    # Delete each test pipeline
    deleted_count = 0
    for pipeline in test_pipelines:
        pipeline_id = pipeline["id"]
        pipeline_name = pipeline["name"]
        
        delete_result = await mcp_client.call_tool("delete_pipeline", {"project_id": project_id, "pipeline_id": pipeline_id})
        if delete_result.data:
            deleted_count += 1
            print(f"Deleted test pipeline: {pipeline_name} (ID: {pipeline_id})")
        else:
            print(f"Failed to delete test pipeline: {pipeline_name} (ID: {pipeline_id})")
    
    print(f"Successfully cleaned up {deleted_count} test pipelines")
    assert deleted_count > 0, "Should have deleted at least one test pipeline"

@requires_ado_creds
async def test_get_pipeline_returns_valid_details(mcp_client: Client):
    """Tests that get_pipeline returns valid details for a specific pipeline."""
    projects = (await mcp_client.call_tool("list_projects")).data
    if not projects:
        pytest.skip("No projects found.")
    
    # Try multiple projects to find one with pipelines
    pipeline_id = None
    project_id = None
    for project in projects:
        project_id = project['id']
        pipelines = (await mcp_client.call_tool("list_pipelines", {"project_id": project_id})).data
        if pipelines:
            pipeline_id = pipelines[0]["id"]
            break
    
    if not pipeline_id:
        pytest.skip("No pipelines found in any project.")

    details = (await mcp_client.call_tool("get_pipeline", {"project_id": project_id, "pipeline_id": pipeline_id})).data
    assert isinstance(details, dict)
    assert details.get("id") == pipeline_id

@requires_ado_creds
async def test_run_and_get_pipeline_run_details(mcp_client: Client):
    """Tests running a pipeline and getting its run details."""
    projects = (await mcp_client.call_tool("list_projects")).data
    if not projects:
        pytest.skip("No projects found.")
    
    # Try multiple projects to find one with pipelines
    pipeline_id = None
    project_id = None
    for project in projects:
        project_id = project['id']
        pipelines = (await mcp_client.call_tool("list_pipelines", {"project_id": project_id})).data
        if pipelines:
            pipeline_id = pipelines[0]["id"]
            break
    
    if not pipeline_id:
        pytest.skip("No pipelines found in any project.")

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
    """Tests that switching to a nonexistent org fails but preserves the previous valid client state."""
    # First verify we start with a valid client
    initial_auth = await mcp_client.call_tool("check_ado_authentication")
    assert initial_auth.data is True, "Should start with a valid client"
    
    # Get some data to verify the client is working
    initial_projects = await mcp_client.call_tool("list_projects")
    assert isinstance(initial_projects.data, list), "Should be able to list projects initially"
    
    # 1. Try to switch to an invalid organization - this should fail
    invalid_org_url = "https://dev.azure.com/this-org-does-not-exist-for-sure"
    with pytest.raises(ToolError, match="Authentication check failed"):
        await mcp_client.call_tool("set_ado_organization", {"organization_url": invalid_org_url})

    # 2. Verify client remains valid with the previous organization
    auth_result = await mcp_client.call_tool("check_ado_authentication")
    assert auth_result.data is True, "Auth should still succeed after failed switch - client should remain in previous state"

    # Verify we can still list projects (client is still functional)
    list_result = await mcp_client.call_tool("list_projects")
    assert isinstance(list_result.data, list), "Should still be able to list projects after failed switch"
    assert list_result.data == initial_projects.data, "Should get same projects as before failed switch"

    # 3. Now switch to a different valid organization to verify switching still works
    valid_org_url = os.environ.get("ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley")
    set_result = await mcp_client.call_tool("set_ado_organization", {"organization_url": valid_org_url})
    assert set_result.data.get("result") is True

    # 4. Verify client is still valid
    auth_result_after_recovery = await mcp_client.call_tool("check_ado_authentication")
    assert auth_result_after_recovery.data is True, "Auth should succeed after switching to valid org"
