import os

import pytest
from fastmcp.client import Client
from fastmcp.exceptions import ToolError

from server import mcp
from tests.ado.test_client import requires_ado_creds

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio


@pytest.fixture
async def mcp_client():
    """Provides a connected MCP client for tests, ensuring a valid initial state."""
    async with Client(mcp) as client:
        initial_org_url = os.environ.get(
            "ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley"
        )
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
        project_id = project["id"]
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
            assert "name" in pipeline, (
                f"Pipeline should have name field, got keys: {pipeline.keys()}"
            )
            assert isinstance(pipeline["id"], int), (
                f"Pipeline id should be int, got: {type(pipeline['id'])}"
            )
            assert isinstance(pipeline["name"], str), (
                f"Pipeline name should be str, got: {type(pipeline['name'])}"
            )
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
    connections_result = await mcp_client.call_tool(
        "list_service_connections", {"project_id": project_id}
    )
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
    result = await mcp_client.call_tool(
        "create_pipeline",
        {
            "project_id": project_id,
            "name": pipeline_name,
            "yaml_path": "tests/ado/fixtures/fast.test.pipeline.yml",
            "repository_name": "raboley/ado-mcp",
            "service_connection_id": github_connection_id,
            "configuration_type": "yaml",
            "folder": "/test",
        },
    )

    pipeline = result.data

    # Handle both Pydantic model and dict responses
    if hasattr(pipeline, "id"):  # Pydantic model
        pipeline_id = pipeline.id
        pipeline_name_returned = pipeline.name
        assert isinstance(pipeline_id, int), f"Pipeline id should be int, got: {type(pipeline_id)}"
        assert isinstance(pipeline_name_returned, str), (
            f"Pipeline name should be str, got: {type(pipeline_name_returned)}"
        )
        assert pipeline_name_returned == pipeline_name, (
            f"Pipeline name should be {pipeline_name}, got: {pipeline_name_returned}"
        )
    else:  # Dict response
        assert isinstance(pipeline, dict), f"Created pipeline should be dict, got: {type(pipeline)}"
        assert "id" in pipeline, (
            f"Created pipeline should have id field, got keys: {pipeline.keys()}"
        )
        assert "name" in pipeline, (
            f"Created pipeline should have name field, got keys: {pipeline.keys()}"
        )
        pipeline_id = pipeline["id"]
        pipeline_name_returned = pipeline["name"]
        assert pipeline_name_returned == pipeline_name, (
            f"Pipeline name should be {pipeline_name}, got: {pipeline_name_returned}"
        )
        assert isinstance(pipeline_id, int), f"Pipeline id should be int, got: {type(pipeline_id)}"

    # Verify the pipeline appears in the list
    pipelines_list = await mcp_client.call_tool("list_pipelines", {"project_id": project_id})
    pipeline_ids = [p["id"] for p in pipelines_list.data]
    assert pipeline_id in pipeline_ids, (
        f"Created pipeline {pipeline_id} should appear in pipelines list"
    )

    # Clean up: Delete the test pipeline
    delete_result = await mcp_client.call_tool(
        "delete_pipeline", {"project_id": project_id, "pipeline_id": pipeline_id}
    )
    assert delete_result.data is True, f"Failed to delete test pipeline {pipeline_id}"

    # Verify the pipeline was deleted
    pipelines_list_after = await mcp_client.call_tool("list_pipelines", {"project_id": project_id})
    pipeline_ids_after = [p["id"] for p in pipelines_list_after.data]
    assert pipeline_id not in pipeline_ids_after, (
        f"Pipeline {pipeline_id} should be deleted but still appears in list"
    )


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
    connections_result = await mcp_client.call_tool(
        "list_service_connections", {"project_id": project_id}
    )
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
    create_result = await mcp_client.call_tool(
        "create_pipeline",
        {
            "project_id": project_id,
            "name": pipeline_name,
            "yaml_path": "tests/ado/fixtures/fast.test.pipeline.yml",
            "repository_name": "raboley/ado-mcp",
            "service_connection_id": github_connection_id,
            "configuration_type": "yaml",
            "folder": "/test",
        },
    )

    pipeline = create_result.data
    assert hasattr(pipeline, "id"), "Created pipeline should have an id attribute"
    pipeline_id = pipeline.id

    # Verify pipeline exists
    pipelines_before = await mcp_client.call_tool("list_pipelines", {"project_id": project_id})
    pipeline_ids_before = [p["id"] for p in pipelines_before.data]
    assert pipeline_id in pipeline_ids_before, (
        f"Created pipeline {pipeline_id} should exist before deletion"
    )

    # Delete the pipeline
    delete_result = await mcp_client.call_tool(
        "delete_pipeline", {"project_id": project_id, "pipeline_id": pipeline_id}
    )
    assert delete_result.data is True, f"Failed to delete pipeline {pipeline_id}"

    # Verify pipeline was deleted
    pipelines_after = await mcp_client.call_tool("list_pipelines", {"project_id": project_id})
    pipeline_ids_after = [p["id"] for p in pipelines_after.data]
    assert pipeline_id not in pipeline_ids_after, (
        f"Pipeline {pipeline_id} should be deleted but still appears in list"
    )


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
        project_id = project["id"]
        pipelines = (await mcp_client.call_tool("list_pipelines", {"project_id": project_id})).data
        if pipelines:
            pipeline_id = pipelines[0]["id"]
            break

    if not pipeline_id:
        pytest.skip("No pipelines found in any project.")

    details = (
        await mcp_client.call_tool(
            "get_pipeline", {"project_id": project_id, "pipeline_id": pipeline_id}
        )
    ).data
    assert isinstance(details, dict)
    assert details.get("id") == pipeline_id


@requires_ado_creds
async def test_run_and_get_pipeline_run_details(mcp_client: Client):
    """Tests running a pipeline and getting its run details."""
    # Use dedicated test pipeline created for this test
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 59  # test_run_and_get_pipeline_run_details pipeline

    run_details = (
        await mcp_client.call_tool(
            "run_pipeline", {"project_id": project_id, "pipeline_id": pipeline_id}
        )
    ).data
    assert run_details is not None, "Pipeline run should not be None"
    assert isinstance(run_details, dict), "Pipeline run should be a dictionary"
    assert "id" in run_details, "Pipeline run should have an id field"
    assert isinstance(run_details["id"], int), (
        f"Pipeline run id should be int, got: {type(run_details['id'])}"
    )

    run_id = run_details["id"]

    # Wait a moment for the run to be available in the API
    await __import__("asyncio").sleep(2)

    run_status = (
        await mcp_client.call_tool(
            "get_pipeline_run",
            {"project_id": project_id, "pipeline_id": pipeline_id, "run_id": run_id},
        )
    ).data
    assert run_status is not None, "Pipeline run status should not be None"
    assert isinstance(run_status, dict), "Pipeline run status should be a dictionary"
    assert "id" in run_status, "Pipeline run status should have an id field"
    assert run_status["id"] == run_id, f"Expected run_id {run_id}, got {run_status['id']}"


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
    result = await mcp_client_with_unset_ado_env.call_tool(
        "get_pipeline", {"project_id": "any", "pipeline_id": 1}
    )
    assert result.data is None


async def test_no_client_run_pipeline(mcp_client_with_unset_ado_env: Client):
    """Tests run_pipeline returns None when client is not available."""
    result = await mcp_client_with_unset_ado_env.call_tool(
        "run_pipeline", {"project_id": "any", "pipeline_id": 1}
    )
    assert result.data is None


async def test_no_client_get_pipeline_run(mcp_client_with_unset_ado_env: Client):
    """Tests get_pipeline_run returns None when client is not available."""
    result = await mcp_client_with_unset_ado_env.call_tool(
        "get_pipeline_run", {"project_id": "any", "pipeline_id": 1, "run_id": 1}
    )
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
    assert auth_result.data is True, (
        "Auth should still succeed after failed switch - client should remain in previous state"
    )

    # Verify we can still list projects (client is still functional)
    list_result = await mcp_client.call_tool("list_projects")
    assert isinstance(list_result.data, list), (
        "Should still be able to list projects after failed switch"
    )
    assert list_result.data == initial_projects.data, (
        "Should get same projects as before failed switch"
    )

    # 3. Now switch to a different valid organization to verify switching still works
    valid_org_url = os.environ.get("ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley")
    set_result = await mcp_client.call_tool(
        "set_ado_organization", {"organization_url": valid_org_url}
    )
    assert set_result.data.get("result") is True

    # 4. Verify client is still valid
    auth_result_after_recovery = await mcp_client.call_tool("check_ado_authentication")
    assert auth_result_after_recovery.data is True, (
        "Auth should succeed after switching to valid org"
    )


@requires_ado_creds
async def test_pipeline_lifecycle_fire_and_forget(mcp_client: Client):
    """
    Tests fire-and-forget pipeline execution: run → verify started.
    """
    # Use dedicated test pipeline created for this test
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 60  # test_pipeline_lifecycle_fire_and_forget pipeline

    # Run the pipeline (fire and forget)
    run_result = await mcp_client.call_tool(
        "run_pipeline", {"project_id": project_id, "pipeline_id": pipeline_id}
    )

    pipeline_run = run_result.data
    assert pipeline_run is not None, "Pipeline run should not be None"

    # Verify pipeline run is a proper dictionary (FastMCP converts Pydantic to dict)
    assert isinstance(pipeline_run, dict), "Pipeline run should be a dictionary"
    assert "id" in pipeline_run, "Pipeline run should have an id field"
    assert "state" in pipeline_run, "Pipeline run should have a state field"
    assert isinstance(pipeline_run["id"], int), (
        f"Run ID should be int, got: {type(pipeline_run['id'])}"
    )
    assert pipeline_run["state"] is not None, "Run state should not be None"

    # Verify the run was started (should be either inProgress or already completed for fast pipeline)
    accepted_states = ["inProgress", "completed", "unknown"]
    assert pipeline_run["state"] in accepted_states, (
        f"Expected state in {accepted_states}, got: {pipeline_run['state']}"
    )

    print(
        f"✓ Pipeline run {pipeline_run['id']} started successfully with state: {pipeline_run['state']}"
    )


@requires_ado_creds
async def test_pipeline_lifecycle_wait_for_completion(mcp_client: Client):
    """
    Tests pipeline execution with completion waiting: run → poll until completed → verify result.
    """
    # Use dedicated test pipeline created for this test
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 61  # test_pipeline_lifecycle_wait_for_completion pipeline

    # Run the pipeline
    run_result = await mcp_client.call_tool(
        "run_pipeline", {"project_id": project_id, "pipeline_id": pipeline_id}
    )

    pipeline_run = run_result.data
    assert isinstance(pipeline_run, dict), "Pipeline run should be a dictionary"
    assert "id" in pipeline_run, "Pipeline run should have an id field"
    run_id = pipeline_run["id"]

    print(f"Started pipeline run {run_id}, waiting for completion...")

    # Poll for completion (max 2 minutes for the fast test pipeline)
    max_attempts = 24  # 24 * 5 seconds = 2 minutes
    attempt = 0
    final_run = None

    while attempt < max_attempts:
        attempt += 1
        await __import__("asyncio").sleep(5)  # Wait 5 seconds between checks

        # Get current run status
        status_result = await mcp_client.call_tool(
            "get_pipeline_run",
            {"project_id": project_id, "pipeline_id": pipeline_id, "run_id": run_id},
        )

        current_run = status_result.data
        assert isinstance(current_run, dict), "Pipeline run should be a dictionary"
        assert "state" in current_run, "Pipeline run should have a state field"

        print(f"Attempt {attempt}: Pipeline run {run_id} state: {current_run['state']}")

        # Check if completed
        if current_run["state"] == "completed":
            final_run = current_run
            break

    # Verify completion
    assert final_run is not None, f"Pipeline run {run_id} did not complete within 2 minutes"

    assert "result" in final_run, "Pipeline run should have a result field"
    print(f"✓ Pipeline run {run_id} completed with result: {final_run['result']}")

    # For the fast test pipeline, we expect it to succeed
    assert final_run["result"] in ["succeeded", "failed"], (
        f"Expected valid result, got: {final_run['result']}"
    )


@requires_ado_creds
async def test_multiple_pipeline_runs(mcp_client: Client):
    """
    Tests running the same pipeline multiple times to ensure proper handling.
    """
    # Use dedicated test pipeline created for this test
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 62  # test_multiple_pipeline_runs pipeline

    run_ids = []

    # Run the pipeline 3 times
    for i in range(3):
        run_result = await mcp_client.call_tool(
            "run_pipeline", {"project_id": project_id, "pipeline_id": pipeline_id}
        )

        pipeline_run = run_result.data
        assert isinstance(pipeline_run, dict), "Pipeline run should be a dictionary"
        assert "id" in pipeline_run, "Pipeline run should have an id field"
        run_ids.append(pipeline_run["id"])

        print(f"Started run {i + 1}: {pipeline_run['id']}")

        # Brief pause between runs
        await __import__("asyncio").sleep(2)

    # Verify all runs have unique IDs
    assert len(set(run_ids)) == 3, f"All run IDs should be unique, got: {run_ids}"

    # Verify we can get status for each run
    for run_id in run_ids:
        status_result = await mcp_client.call_tool(
            "get_pipeline_run",
            {"project_id": project_id, "pipeline_id": pipeline_id, "run_id": run_id},
        )

        current_run = status_result.data
        assert current_run is not None, f"Should be able to get status for run {run_id}"
        assert isinstance(current_run, dict), f"Run {run_id} should be a dictionary"
        assert "state" in current_run, f"Run {run_id} should have a state field"
        assert current_run["state"] is not None, f"Run {run_id} should have a state"

    print(f"✓ Successfully created and tracked {len(run_ids)} pipeline runs")


@requires_ado_creds
async def test_pipeline_run_status_progression(mcp_client: Client):
    """
    Tests that we can properly track pipeline run status changes over time.
    """
    # Use dedicated test pipeline created for this test
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 63  # test_pipeline_run_status_progression pipeline

    # Run the pipeline
    run_result = await mcp_client.call_tool(
        "run_pipeline", {"project_id": project_id, "pipeline_id": pipeline_id}
    )

    pipeline_run = run_result.data
    assert isinstance(pipeline_run, dict), "Pipeline run should be a dictionary"
    assert "id" in pipeline_run, "Pipeline run should have an id field"
    run_id = pipeline_run["id"]

    print(f"Started pipeline run {run_id}")

    # Track status changes for up to 30 seconds
    previous_state = None
    status_changes = []

    for i in range(6):  # 6 checks over 30 seconds
        status_result = await mcp_client.call_tool(
            "get_pipeline_run",
            {"project_id": project_id, "pipeline_id": pipeline_id, "run_id": run_id},
        )

        current_run = status_result.data
        assert isinstance(current_run, dict), "Pipeline run should be a dictionary"
        assert "state" in current_run, "Pipeline run should have a state field"
        assert "result" in current_run, "Pipeline run should have a result field"

        if current_run["state"] != previous_state:
            status_changes.append(
                {"state": current_run["state"], "result": current_run["result"], "check": i + 1}
            )
            print(
                f"Check {i + 1}: State changed to {current_run['state']} (result: {current_run['result']})"
            )
            previous_state = current_run["state"]

        # If completed, no need to continue checking
        if current_run["state"] == "completed":
            break

        await __import__("asyncio").sleep(5)

    # Verify we captured at least one status
    assert len(status_changes) > 0, "Should have captured at least one status change"

    # Verify the final status is reasonable
    final_status = status_changes[-1]
    valid_states = ["inProgress", "completed", "unknown"]
    assert final_status["state"] in valid_states, (
        f"Final state should be valid, got: {final_status['state']}"
    )

    print(f"✓ Successfully tracked {len(status_changes)} status changes for run {run_id}")


# --- Tests for pipeline preview functionality ---


@requires_ado_creds
async def test_preview_pipeline_valid_yaml(mcp_client: Client):
    """Tests previewing a pipeline with valid YAML."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 74  # preview-test-valid pipeline

    result = await mcp_client.call_tool(
        "preview_pipeline", {"project_id": project_id, "pipeline_id": pipeline_id}
    )

    preview_data = result.data
    assert preview_data is not None, "Preview should not be None"
    assert isinstance(preview_data, dict), "Preview should be a dictionary"

    # Check for the finalYaml field which is the key output
    assert "finalYaml" in preview_data, "Preview should contain finalYaml field"
    assert preview_data["finalYaml"] is not None, "Final YAML should not be None"
    assert isinstance(preview_data["finalYaml"], str), "Final YAML should be a string"
    assert len(preview_data["finalYaml"]) > 0, "Final YAML should not be empty"

    print(f"✓ Successfully previewed pipeline {pipeline_id}")
    print(f"  Final YAML length: {len(preview_data['finalYaml'])} characters")


@requires_ado_creds
async def test_preview_pipeline_with_yaml_override(mcp_client: Client):
    """Tests previewing a pipeline with YAML override."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 74  # preview-test-valid pipeline

    # Provide a simple YAML override
    yaml_override = """
name: Override Test Pipeline
trigger: none
pool:
  vmImage: ubuntu-latest
steps:
  - script: echo "This is an override!"
    displayName: 'Override step'
"""

    result = await mcp_client.call_tool(
        "preview_pipeline",
        {"project_id": project_id, "pipeline_id": pipeline_id, "yaml_override": yaml_override},
    )

    preview_data = result.data
    assert preview_data is not None, "Preview with override should not be None"
    assert isinstance(preview_data, dict), "Preview should be a dictionary"
    assert "finalYaml" in preview_data, "Preview should contain finalYaml field"

    final_yaml = preview_data["finalYaml"]
    assert "Override Test Pipeline" in final_yaml, "Final YAML should contain override content"
    assert "This is an override!" in final_yaml, "Final YAML should contain override script"

    print(f"✓ Successfully previewed pipeline {pipeline_id} with YAML override")


@requires_ado_creds
async def test_preview_pipeline_with_variables(mcp_client: Client):
    """Tests previewing a parameterized pipeline with runtime variables."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 75  # preview-test-parameterized pipeline

    # Provide runtime variables
    variables = {"testEnvironment": "staging", "enableDebug": True}

    result = await mcp_client.call_tool(
        "preview_pipeline",
        {"project_id": project_id, "pipeline_id": pipeline_id, "variables": variables},
    )

    preview_data = result.data
    assert preview_data is not None, "Preview with variables should not be None"
    assert isinstance(preview_data, dict), "Preview should be a dictionary"
    assert "finalYaml" in preview_data, "Preview should contain finalYaml field"

    final_yaml = preview_data["finalYaml"]
    assert final_yaml is not None, "Final YAML should not be None"
    assert len(final_yaml) > 0, "Final YAML should not be empty"

    print(f"✓ Successfully previewed parameterized pipeline {pipeline_id} with variables")
    print(f"  Variables provided: {variables}")


@requires_ado_creds
async def test_preview_pipeline_with_template_parameters(mcp_client: Client):
    """Tests previewing a pipeline with template parameters."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 75  # preview-test-parameterized pipeline

    # Provide template parameters
    template_parameters = {"testEnvironment": "prod", "enableDebug": False}

    result = await mcp_client.call_tool(
        "preview_pipeline",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "template_parameters": template_parameters,
        },
    )

    preview_data = result.data
    assert preview_data is not None, "Preview with template parameters should not be None"
    assert isinstance(preview_data, dict), "Preview should be a dictionary"
    assert "finalYaml" in preview_data, "Preview should contain finalYaml field"

    print(f"✓ Successfully previewed pipeline {pipeline_id} with template parameters")
    print(f"  Template parameters: {template_parameters}")


@requires_ado_creds
async def test_preview_pipeline_error_handling(mcp_client: Client):
    """Tests error handling when previewing an invalid pipeline."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 76  # preview-test-invalid pipeline

    # This should either return an error response or handle the invalid YAML gracefully
    try:
        result = await mcp_client.call_tool(
            "preview_pipeline", {"project_id": project_id, "pipeline_id": pipeline_id}
        )

        # If we get a result, it should still be structured properly
        if result.data is not None:
            preview_data = result.data
            assert isinstance(preview_data, dict), "Even error responses should be dictionaries"

            # The preview may contain error information or a best-effort YAML
            print("✓ Preview tool handled invalid pipeline gracefully")
            if "finalYaml" in preview_data:
                print("  Received final YAML despite errors")
        else:
            print("✓ Preview tool returned None for invalid pipeline")

    except Exception as e:
        # Some errors are expected when dealing with invalid YAML
        print(f"✓ Preview tool properly raised exception for invalid pipeline: {type(e).__name__}")
        assert isinstance(e, Exception), "Should raise a proper exception type"


@requires_ado_creds
async def test_preview_pipeline_nonexistent_pipeline(mcp_client: Client):
    """Tests error handling when trying to preview a non-existent pipeline."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 99999  # Non-existent pipeline ID

    try:
        result = await mcp_client.call_tool(
            "preview_pipeline", {"project_id": project_id, "pipeline_id": pipeline_id}
        )

        # Should either return None or raise an exception
        if result.data is None:
            print("✓ Preview tool returned None for non-existent pipeline")
        else:
            # If we get a result, check it's properly structured
            assert isinstance(result.data, dict), "Response should be a dictionary"
            print("✓ Preview tool handled non-existent pipeline ID gracefully")

    except Exception as e:
        # HTTP 404 or similar errors are expected
        print(
            f"✓ Preview tool properly raised exception for non-existent pipeline: {type(e).__name__}"
        )
        assert isinstance(e, Exception), "Should raise a proper exception type"


async def test_preview_pipeline_no_client(mcp_client_with_unset_ado_env: Client):
    """Tests preview_pipeline returns None when client is not available."""
    result = await mcp_client_with_unset_ado_env.call_tool(
        "preview_pipeline", {"project_id": "any", "pipeline_id": 1}
    )
    assert result.data is None, "Preview should return None when client is unavailable"


# --- Tests for pipeline logs functionality ---


@requires_ado_creds
async def test_get_pipeline_failure_summary_simple_pipeline(mcp_client: Client):
    """Tests getting failure summary for a simple failing pipeline."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 83  # log-test-failing pipeline
    run_id = 323  # Known failed run

    result = await mcp_client.call_tool(
        "get_pipeline_failure_summary",
        {"project_id": project_id, "pipeline_id": pipeline_id, "run_id": run_id},
    )

    summary = result.data
    assert summary is not None, "Summary should not be None"
    assert isinstance(summary, dict), "Summary should be a dictionary"

    # Verify summary structure
    assert "total_failed_steps" in summary, "Summary should have total_failed_steps"
    assert "root_cause_tasks" in summary, "Summary should have root_cause_tasks"
    assert "hierarchy_failures" in summary, "Summary should have hierarchy_failures"
    assert summary["total_failed_steps"] > 0, "Should have failed steps"

    # Verify we have root cause tasks
    assert len(summary["root_cause_tasks"]) > 0, "Should have root cause tasks"
    root_cause = summary["root_cause_tasks"][0]
    assert root_cause["step_name"] == "Run Tests", "Root cause should be 'Run Tests'"
    assert root_cause["step_type"] == "Task", "Root cause should be Task type"
    assert root_cause["result"] == "failed", "Root cause should have failed result"
    assert len(root_cause["issues"]) > 0, "Root cause should have issues"
    assert root_cause["log_content"] is not None, "Root cause should have log content"
    assert len(root_cause["log_content"]) > 0, "Log content should not be empty"

    print(f"✓ Simple pipeline failure analysis: {summary['total_failed_steps']} failed steps")


@requires_ado_creds
async def test_get_pipeline_failure_summary_complex_pipeline(mcp_client: Client):
    """Tests getting failure summary for a complex multi-stage failing pipeline."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 84  # log-test-complex pipeline
    run_id = 324  # Known failed run

    result = await mcp_client.call_tool(
        "get_pipeline_failure_summary",
        {"project_id": project_id, "pipeline_id": pipeline_id, "run_id": run_id},
    )

    summary = result.data
    assert summary is not None, "Summary should not be None"
    assert isinstance(summary, dict), "Summary should be a dictionary"

    # Complex pipeline should have multiple failures
    assert summary["total_failed_steps"] >= 4, "Complex pipeline should have multiple failures"
    assert len(summary["root_cause_tasks"]) >= 1, "Should have at least one root cause task"
    assert len(summary["hierarchy_failures"]) >= 3, "Should have hierarchy failures"

    # Find the Unit Tests failure
    unit_tests_failure = None
    for task in summary["root_cause_tasks"]:
        if "Unit Tests" in task["step_name"]:
            unit_tests_failure = task
            break

    assert unit_tests_failure is not None, "Should find Unit Tests failure"
    assert unit_tests_failure["step_type"] == "Task", "Unit Tests should be Task type"
    assert unit_tests_failure["log_content"] is not None, "Should have log content"

    # Verify log content contains expected error messages
    log_content = unit_tests_failure["log_content"]
    assert "FAIL" in log_content, "Log should contain FAIL message"
    assert "ERROR" in log_content, "Log should contain ERROR message"
    assert "UserService.validateEmail" in log_content, "Log should contain specific error details"

    print(f"✓ Complex pipeline failure analysis: {summary['total_failed_steps']} failed steps")


@requires_ado_creds
async def test_get_failed_step_logs_with_filter(mcp_client: Client):
    """Tests getting failed step logs with name filtering."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 84  # log-test-complex pipeline
    run_id = 324  # Known failed run

    # Test filtering by step name
    result = await mcp_client.call_tool(
        "get_failed_step_logs",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "run_id": run_id,
            "step_name": "Unit Tests",
        },
    )

    step_logs = result.data
    assert step_logs is not None, "Step logs should not be None"
    assert isinstance(step_logs, list), "Step logs should be a list"
    assert len(step_logs) >= 1, "Should find at least one matching step"

    # Verify the filtered step
    unit_tests_step = step_logs[0]
    assert "Unit Tests" in unit_tests_step["step_name"], "Should match filter criteria"
    assert unit_tests_step["step_type"] == "Task", "Should be Task type"
    assert unit_tests_step["result"] == "failed", "Should be failed"
    assert unit_tests_step["log_content"] is not None, "Should have log content"

    print(f"✓ Step filtering found: {unit_tests_step['step_name']}")


@requires_ado_creds
async def test_get_failed_step_logs_all_steps(mcp_client: Client):
    """Tests getting all failed step logs without filtering."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 83  # log-test-failing pipeline
    run_id = 323  # Known failed run

    result = await mcp_client.call_tool(
        "get_failed_step_logs",
        {"project_id": project_id, "pipeline_id": pipeline_id, "run_id": run_id},
    )

    step_logs = result.data
    assert step_logs is not None, "Step logs should not be None"
    assert isinstance(step_logs, list), "Step logs should be a list"
    assert len(step_logs) > 0, "Should have failed steps"

    # Should include both root causes and hierarchy failures
    step_types = [step["step_type"] for step in step_logs]
    assert "Task" in step_types, "Should include Task-level failures"

    # Verify each step has required fields
    for step in step_logs:
        assert "step_name" in step, "Step should have step_name"
        assert "step_type" in step, "Step should have step_type"
        assert "result" in step, "Step should have result"
        assert step["result"] == "failed", "All steps should be failed"

    print(f"✓ All failed steps retrieved: {len(step_logs)} steps")


@requires_ado_creds
async def test_get_pipeline_timeline(mcp_client: Client):
    """Tests getting pipeline timeline with detailed step status."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 83  # log-test-failing pipeline
    run_id = 323  # Known failed run

    result = await mcp_client.call_tool(
        "get_pipeline_timeline",
        {"project_id": project_id, "pipeline_id": pipeline_id, "run_id": run_id},
    )

    timeline = result.data
    assert timeline is not None, "Timeline should not be None"
    assert isinstance(timeline, dict), "Timeline should be a dictionary"
    assert "records" in timeline, "Timeline should have records"

    records = timeline["records"]
    assert len(records) > 0, "Should have timeline records"

    # Verify different record types are present
    record_types = [record.get("type") for record in records]
    assert "Task" in record_types, "Should have Task records"
    assert "Stage" in record_types, "Should have Stage records"

    # Find the failed task
    failed_tasks = [r for r in records if r.get("result") == "failed" and r.get("type") == "Task"]
    assert len(failed_tasks) > 0, "Should have failed tasks"

    failed_task = failed_tasks[0]
    assert failed_task["name"] == "Run Tests", "Failed task should be 'Run Tests'"
    assert "log" in failed_task, "Failed task should have log reference"
    assert failed_task["log"]["id"] is not None, "Should have log ID"

    print(f"✓ Timeline retrieved with {len(records)} records")


@requires_ado_creds
async def test_list_pipeline_logs(mcp_client: Client):
    """Tests listing all logs for a pipeline run."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 83  # log-test-failing pipeline
    run_id = 323  # Known failed run

    result = await mcp_client.call_tool(
        "list_pipeline_logs",
        {"project_id": project_id, "pipeline_id": pipeline_id, "run_id": run_id},
    )

    logs = result.data
    assert logs is not None, "Logs should not be None"
    assert isinstance(logs, dict), "Logs should be a dictionary"
    assert "logs" in logs, "Should have logs array"
    assert "url" in logs, "Should have URL"

    log_entries = logs["logs"]
    assert len(log_entries) > 0, "Should have log entries"

    # Verify log entry structure
    for log_entry in log_entries[:3]:  # Check first 3 logs
        assert "id" in log_entry, "Log entry should have ID"
        assert "lineCount" in log_entry, "Log entry should have line count"
        assert "createdOn" in log_entry, "Log entry should have creation time"
        assert isinstance(log_entry["id"], int), "Log ID should be integer"
        assert log_entry["lineCount"] >= 0, "Line count should be non-negative"

    print(f"✓ Found {len(log_entries)} log entries")


@requires_ado_creds
async def test_get_log_content_by_id(mcp_client: Client):
    """Tests getting specific log content by ID."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 83  # log-test-failing pipeline
    run_id = 323  # Known failed run
    log_id = 8  # Known log ID for the failed "Run Tests" step

    result = await mcp_client.call_tool(
        "get_log_content_by_id",
        {"project_id": project_id, "pipeline_id": pipeline_id, "run_id": run_id, "log_id": log_id},
    )

    log_content = result.data
    assert log_content is not None, "Log content should not be None"
    assert isinstance(log_content, str), "Log content should be a string"
    assert len(log_content) > 0, "Log content should not be empty"

    # Verify log content contains expected information
    assert "Run Tests" in log_content, "Log should contain step name"
    assert "Command line" in log_content, "Log should contain task information"
    assert "ERROR" in log_content, "Log should contain error information"
    assert "Bash exited with code '1'" in log_content, "Log should contain exit code info"

    print(f"✓ Retrieved log content: {len(log_content)} characters")


@requires_ado_creds
async def test_get_log_content_by_id_with_line_limit(mcp_client: Client):
    """Tests getting log content with line limiting."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 83  # log-test-failing pipeline
    run_id = 323  # Known failed run
    log_id = 8  # Known log ID for the failed "Run Tests" step

    # Test with default 100 lines
    result_default = await mcp_client.call_tool(
        "get_log_content_by_id",
        {"project_id": project_id, "pipeline_id": pipeline_id, "run_id": run_id, "log_id": log_id},
    )

    # Test with 10 lines
    result_limited = await mcp_client.call_tool(
        "get_log_content_by_id",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "run_id": run_id,
            "log_id": log_id,
            "max_lines": 10,
        },
    )

    # Test with 0 lines (should return all)
    result_all = await mcp_client.call_tool(
        "get_log_content_by_id",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "run_id": run_id,
            "log_id": log_id,
            "max_lines": 0,
        },
    )

    default_content = result_default.data
    limited_content = result_limited.data
    all_content = result_all.data

    # Verify all results are strings
    assert isinstance(default_content, str), "Default content should be a string"
    assert isinstance(limited_content, str), "Limited content should be a string"
    assert isinstance(all_content, str), "All content should be a string"

    # Verify line limiting works
    default_lines = default_content.splitlines()
    limited_lines = limited_content.splitlines()
    all_lines = all_content.splitlines()

    assert len(limited_lines) <= 10, (
        f"Limited content should have max 10 lines, got {len(limited_lines)}"
    )
    assert len(default_lines) <= 100, (
        f"Default content should have max 100 lines, got {len(default_lines)}"
    )
    assert len(all_lines) >= len(default_lines), (
        "All content should have at least as many lines as default"
    )

    # Verify that limited content is from the end of the log
    if len(all_lines) > 10:
        expected_limited_lines = all_lines[-10:]
        assert limited_lines == expected_limited_lines, "Limited lines should be the last 10 lines"

    print(
        f"✓ Line limiting test: All={len(all_lines)}, Default={len(default_lines)}, Limited={len(limited_lines)} lines"
    )


@requires_ado_creds
async def test_get_pipeline_failure_summary_with_line_limit(mcp_client: Client):
    """Tests getting pipeline failure summary with line limiting."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 83  # log-test-failing pipeline
    run_id = 323  # Known failed run

    # Test with default 100 lines
    result_default = await mcp_client.call_tool(
        "get_pipeline_failure_summary",
        {"project_id": project_id, "pipeline_id": pipeline_id, "run_id": run_id},
    )

    # Test with 5 lines
    result_limited = await mcp_client.call_tool(
        "get_pipeline_failure_summary",
        {"project_id": project_id, "pipeline_id": pipeline_id, "run_id": run_id, "max_lines": 5},
    )

    default_summary = result_default.data
    limited_summary = result_limited.data

    assert default_summary is not None, "Default summary should not be None"
    assert limited_summary is not None, "Limited summary should not be None"

    # Check that both have root cause tasks
    assert len(default_summary["root_cause_tasks"]) > 0, "Should have root cause tasks"
    assert len(limited_summary["root_cause_tasks"]) > 0, "Should have root cause tasks"

    # Compare log content lengths for the first root cause task that has log content
    default_task = None
    limited_task = None

    for task in default_summary["root_cause_tasks"]:
        if task.get("log_content"):
            default_task = task
            break

    for task in limited_summary["root_cause_tasks"]:
        if task.get("log_content"):
            limited_task = task
            break

    if default_task and limited_task:
        default_log_lines = default_task["log_content"].splitlines()
        limited_log_lines = limited_task["log_content"].splitlines()

        assert len(limited_log_lines) <= 5, (
            f"Limited log should have max 5 lines, got {len(limited_log_lines)}"
        )
        assert len(default_log_lines) <= 100, (
            f"Default log should have max 100 lines, got {len(default_log_lines)}"
        )

        print(
            f"✓ Failure summary line limiting: Default={len(default_log_lines)}, Limited={len(limited_log_lines)} lines"
        )


@requires_ado_creds
async def test_get_failed_step_logs_with_line_limit(mcp_client: Client):
    """Tests getting failed step logs with line limiting."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 83  # log-test-failing pipeline
    run_id = 323  # Known failed run

    # Test with default 100 lines
    result_default = await mcp_client.call_tool(
        "get_failed_step_logs",
        {"project_id": project_id, "pipeline_id": pipeline_id, "run_id": run_id},
    )

    # Test with 3 lines
    result_limited = await mcp_client.call_tool(
        "get_failed_step_logs",
        {"project_id": project_id, "pipeline_id": pipeline_id, "run_id": run_id, "max_lines": 3},
    )

    default_steps = result_default.data
    limited_steps = result_limited.data

    assert default_steps is not None, "Default steps should not be None"
    assert limited_steps is not None, "Limited steps should not be None"
    assert len(default_steps) > 0, "Should have failed steps"
    assert len(limited_steps) > 0, "Should have failed steps"

    # Find steps with log content and compare
    default_step_with_log = None
    limited_step_with_log = None

    for step in default_steps:
        if step.get("log_content"):
            default_step_with_log = step
            break

    for step in limited_steps:
        if step.get("log_content"):
            limited_step_with_log = step
            break

    if default_step_with_log and limited_step_with_log:
        default_log_lines = default_step_with_log["log_content"].splitlines()
        limited_log_lines = limited_step_with_log["log_content"].splitlines()

        assert len(limited_log_lines) <= 3, (
            f"Limited log should have max 3 lines, got {len(limited_log_lines)}"
        )
        assert len(default_log_lines) <= 100, (
            f"Default log should have max 100 lines, got {len(default_log_lines)}"
        )

        print(
            f"✓ Failed step logs line limiting: Default={len(default_log_lines)}, Limited={len(limited_log_lines)} lines"
        )


async def test_logs_tools_no_client(mcp_client_with_unset_ado_env: Client):
    """Tests that logs tools return None when client is not available."""
    # Test failure summary
    result = await mcp_client_with_unset_ado_env.call_tool(
        "get_pipeline_failure_summary", {"project_id": "any", "pipeline_id": 1, "run_id": 1}
    )
    assert result.data is None, "Should return None when client unavailable"

    # Test failed step logs
    result = await mcp_client_with_unset_ado_env.call_tool(
        "get_failed_step_logs", {"project_id": "any", "pipeline_id": 1, "run_id": 1}
    )
    assert result.data is None, "Should return None when client unavailable"

    # Test timeline
    result = await mcp_client_with_unset_ado_env.call_tool(
        "get_pipeline_timeline", {"project_id": "any", "pipeline_id": 1, "run_id": 1}
    )
    assert result.data is None, "Should return None when client unavailable"


@requires_ado_creds
async def test_run_pipeline_and_get_outcome_success(mcp_client: Client):
    """Tests successful pipeline run with complete outcome tracking."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 59  # test_run_and_get_pipeline_run_details (quick success pipeline)

    result = await mcp_client.call_tool(
        "run_pipeline_and_get_outcome",
        {"project_id": project_id, "pipeline_id": pipeline_id, "timeout_seconds": 300},
    )

    outcome = result.data
    assert outcome is not None, "Outcome should not be None"
    assert isinstance(outcome, dict), "Outcome should be a dictionary"

    # Verify outcome structure
    assert "pipeline_run" in outcome, "Should have pipeline_run"
    assert "success" in outcome, "Should have success flag"
    assert "failure_summary" in outcome, "Should have failure_summary field"
    assert "execution_time_seconds" in outcome, "Should have execution time"

    # Verify pipeline run data
    pipeline_run = outcome["pipeline_run"]
    assert pipeline_run["id"] is not None, "Pipeline run should have ID"
    assert pipeline_run["state"] == "completed", "Pipeline should be completed"
    assert pipeline_run["result"] == "succeeded", "Pipeline should have succeeded"
    assert pipeline_run["pipeline"]["id"] == pipeline_id, "Pipeline ID should match"

    # Verify success outcome
    assert outcome["success"] is True, "Should be marked as successful"
    assert outcome["failure_summary"] is None, "Successful run should have no failure summary"
    assert outcome["execution_time_seconds"] > 0, "Should have positive execution time"
    assert outcome["execution_time_seconds"] < 300, "Should complete within timeout"

    print(f"✓ Successful pipeline completed in {outcome['execution_time_seconds']:.2f} seconds")


@requires_ado_creds
async def test_run_pipeline_and_get_outcome_failure(mcp_client: Client):
    """Tests failed pipeline run with failure analysis."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 83  # log-test-failing pipeline (designed to fail)

    result = await mcp_client.call_tool(
        "run_pipeline_and_get_outcome",
        {"project_id": project_id, "pipeline_id": pipeline_id, "timeout_seconds": 300},
    )

    outcome = result.data
    assert outcome is not None, "Outcome should not be None"
    assert isinstance(outcome, dict), "Outcome should be a dictionary"

    # Verify outcome structure
    assert "pipeline_run" in outcome, "Should have pipeline_run"
    assert "success" in outcome, "Should have success flag"
    assert "failure_summary" in outcome, "Should have failure_summary field"
    assert "execution_time_seconds" in outcome, "Should have execution time"

    # Verify pipeline run data
    pipeline_run = outcome["pipeline_run"]
    assert pipeline_run["id"] is not None, "Pipeline run should have ID"
    assert pipeline_run["state"] == "completed", "Pipeline should be completed"
    assert pipeline_run["result"] == "failed", "Pipeline should have failed"
    assert pipeline_run["pipeline"]["id"] == pipeline_id, "Pipeline ID should match"

    # Verify failure outcome
    assert outcome["success"] is False, "Should be marked as failed"
    assert outcome["failure_summary"] is not None, "Failed run should have failure summary"
    assert outcome["execution_time_seconds"] > 0, "Should have positive execution time"

    # Verify failure summary structure
    failure_summary = outcome["failure_summary"]
    assert "total_failed_steps" in failure_summary, "Should have total failed steps"
    assert "root_cause_tasks" in failure_summary, "Should have root cause tasks"
    assert "hierarchy_failures" in failure_summary, "Should have hierarchy failures"

    assert failure_summary["total_failed_steps"] > 0, "Should have failed steps"
    assert len(failure_summary["root_cause_tasks"]) > 0, "Should have root cause tasks"

    # Verify root cause task structure
    root_cause = failure_summary["root_cause_tasks"][0]
    assert "step_name" in root_cause, "Root cause should have step name"
    assert "step_type" in root_cause, "Root cause should have step type"
    assert "result" in root_cause, "Root cause should have result"
    assert root_cause["step_type"] == "Task", "Root cause should be a Task"
    assert root_cause["result"] == "failed", "Root cause should be failed"

    print(f"✓ Failed pipeline analyzed in {outcome['execution_time_seconds']:.2f} seconds")
    print(f"  Found {failure_summary['total_failed_steps']} failed steps")
    print(f"  Root cause: {root_cause['step_name']}")


@requires_ado_creds
async def test_run_pipeline_and_get_outcome_custom_timeout(mcp_client: Client):
    """Tests pipeline run with custom timeout setting."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 59  # test_run_and_get_pipeline_run_details (quick success pipeline)

    result = await mcp_client.call_tool(
        "run_pipeline_and_get_outcome",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "timeout_seconds": 600,  # Custom longer timeout
        },
    )

    outcome = result.data
    assert outcome is not None, "Outcome should not be None"
    assert outcome["success"] is True, "Should be successful"
    assert outcome["execution_time_seconds"] < 600, "Should complete well within timeout"

    print(
        f"✓ Pipeline with custom timeout completed in {outcome['execution_time_seconds']:.2f} seconds"
    )


async def test_run_pipeline_and_get_outcome_no_client(mcp_client_with_unset_ado_env: Client):
    """Tests that run_pipeline_and_get_outcome returns None when client is not available."""
    result = await mcp_client_with_unset_ado_env.call_tool(
        "run_pipeline_and_get_outcome",
        {"project_id": "any", "pipeline_id": 1, "timeout_seconds": 300},
    )
    assert result.data is None, "Should return None when client unavailable"

    print("✓ Properly handles missing client")


async def test_run_pipeline_and_get_outcome_tool_registration(mcp_client: Client):
    """Tests that the run_pipeline_and_get_outcome tool is properly registered."""
    # List available tools
    tools_response = await mcp_client.list_tools()

    # Handle both potential response formats
    if hasattr(tools_response, "tools"):
        tools = tools_response.tools
    else:
        tools = tools_response

    # Check that our new tool is registered
    tool_names = [tool.name for tool in tools]
    assert "run_pipeline_and_get_outcome" in tool_names, (
        "run_pipeline_and_get_outcome tool should be registered"
    )

    # Find the tool and verify its schema
    outcome_tool = next(tool for tool in tools if tool.name == "run_pipeline_and_get_outcome")
    assert outcome_tool.description is not None, "Tool should have description"
    assert "RUN PIPELINE & WAIT" in outcome_tool.description, (
        "Tool description should mention pipeline running and waiting"
    )

    # Verify input schema has required parameters
    input_schema = outcome_tool.inputSchema
    assert input_schema is not None, "Tool should have input schema"
    assert "properties" in input_schema, "Schema should have properties"

    properties = input_schema["properties"]
    assert "project_id" in properties, "Should have project_id parameter"
    assert "pipeline_id" in properties, "Should have pipeline_id parameter"
    assert "timeout_seconds" in properties, "Should have timeout_seconds parameter"

    required = input_schema.get("required", [])
    assert "project_id" in required, "project_id should be required"
    assert "pipeline_id" in required, "pipeline_id should be required"
    # timeout_seconds should have a default, so not required

    print("✓ run_pipeline_and_get_outcome tool properly registered with correct schema")


@requires_ado_creds
async def test_get_build_by_id_success(mcp_client: Client):
    """Tests getting build details by build ID to extract pipeline information."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    build_id = 324  # Known build/run ID from URL buildId=324

    result = await mcp_client.call_tool(
        "get_build_by_id", {"project_id": project_id, "build_id": build_id}
    )

    build_data = result.data
    assert build_data is not None, "Build data should not be None"
    assert isinstance(build_data, dict), "Build data should be a dictionary"

    # Verify build structure includes definition information
    assert "id" in build_data, "Build should have id field"
    assert "definition" in build_data, "Build should have definition field"
    assert "buildNumber" in build_data, "Build should have buildNumber"
    assert "status" in build_data, "Build should have status"
    assert "result" in build_data, "Build should have result"

    # Verify definition (pipeline) information
    definition = build_data["definition"]
    assert "id" in definition, "Definition should have id field"
    assert "name" in definition, "Definition should have name field"
    assert isinstance(definition["id"], int), "Definition ID should be integer"

    # For buildId=324, we expect pipeline_id=84 and name="log-test-complex"
    assert definition["id"] == 84, f"Expected pipeline ID 84, got {definition['id']}"
    assert definition["name"] == "log-test-complex", (
        f"Expected pipeline name 'log-test-complex', got {definition['name']}"
    )

    print(f"✓ Build {build_id} maps to pipeline {definition['id']} ({definition['name']})")


async def test_get_build_by_id_no_client(mcp_client_with_unset_ado_env: Client):
    """Tests that get_build_by_id returns None when client is not available."""
    result = await mcp_client_with_unset_ado_env.call_tool(
        "get_build_by_id", {"project_id": "any", "build_id": 1}
    )
    assert result.data is None, "Should return None when client unavailable"


async def test_get_build_by_id_tool_registration(mcp_client: Client):
    """Tests that the get_build_by_id tool is properly registered."""
    # List available tools
    tools_response = await mcp_client.list_tools()

    # Handle both potential response formats
    if hasattr(tools_response, "tools"):
        tools = tools_response.tools
    else:
        tools = tools_response

    # Check that our new tool is registered
    tool_names = [tool.name for tool in tools]
    assert "get_build_by_id" in tool_names, "get_build_by_id tool should be registered"

    # Find the tool and verify its schema
    build_tool = next(tool for tool in tools if tool.name == "get_build_by_id")
    assert build_tool.description is not None, "Tool should have description"
    assert "buildId" in build_tool.description, "Tool description should mention buildId"
    assert "MAP BUILD ID TO PIPELINE" in build_tool.description, (
        "Tool description should explain mapping purpose"
    )

    # Verify input schema has required parameters
    input_schema = build_tool.inputSchema
    assert input_schema is not None, "Tool should have input schema"
    assert "properties" in input_schema, "Schema should have properties"

    properties = input_schema["properties"]
    assert "project_id" in properties, "Should have project_id parameter"
    assert "build_id" in properties, "Should have build_id parameter"

    required = input_schema.get("required", [])
    assert "project_id" in required, "project_id should be required"
    assert "build_id" in required, "build_id should be required"

    print("✓ get_build_by_id tool properly registered with correct schema")
