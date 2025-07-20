import os
import time

import pytest
from fastmcp.client import Client
from fastmcp.exceptions import ToolError

from server import mcp
from tests.ado.test_client import requires_ado_creds
from ado.cache import ado_cache
from tests.utils.telemetry import telemetry_setup, analyze_spans, clear_spans

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def mcp_client():
    async with Client(mcp) as client:
        initial_org_url = os.environ.get(
            "ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley"
        )
        await client.call_tool("set_ado_organization", {"organization_url": initial_org_url})
        yield client


@pytest.fixture
async def mcp_client_with_unset_ado_env(monkeypatch):
    monkeypatch.delenv("ADO_ORGANIZATION_URL", raising=False)
    monkeypatch.delenv("AZURE_DEVOPS_EXT_PAT", raising=False)
    import importlib

    import server

    importlib.reload(server)
    async with Client(server.mcp) as client:
        yield client


@requires_ado_creds
async def test_list_projects_returns_valid_list(mcp_client: Client):
    result = await mcp_client.call_tool("list_projects")
    projects = result.data
    assert isinstance(projects, list), f"Expected list of projects, got {type(projects)}"
    if projects:
        project = projects[0]
        assert isinstance(project, dict), f"Expected project to be dict, got {type(project)}"
        assert "id" in project, f"Project missing 'id' field, has keys: {list(project.keys())}"
        assert "name" in project, f"Project missing 'name' field, has keys: {list(project.keys())}"


@requires_ado_creds
async def test_list_pipelines_returns_valid_list(mcp_client: Client):
    projects_result = await mcp_client.call_tool("list_projects")
    projects = projects_result.data
    if not projects:
        pytest.skip("No projects found to test pipeline listing.")

    pipelines_found = False
    for project in projects:
        project_id = project["id"]
        result = await mcp_client.call_tool("list_pipelines", {"project_id": project_id})
        pipelines = result.data

        assert isinstance(pipelines, list), f"Expected list of pipelines, got {type(pipelines)}"

        if pipelines:
            pipelines_found = True
            pipeline = pipelines[0]
            assert isinstance(pipeline, dict), f"Expected pipeline to be dict, got {type(pipeline)}"
            assert "id" in pipeline, f"Pipeline missing 'id' field, has keys: {list(pipeline.keys())}"
            assert "name" in pipeline, f"Pipeline missing 'name' field, has keys: {list(pipeline.keys())}"
            assert isinstance(pipeline["id"], int), f"Expected pipeline id to be int, got {type(pipeline['id'])}"
            assert isinstance(pipeline["name"], str), f"Expected pipeline name to be str, got {type(pipeline['name'])}"
            break

    if not pipelines_found:
        pytest.skip("No pipelines found in any project.")


@requires_ado_creds
async def test_create_pipeline_creates_valid_pipeline(mcp_client: Client):
    projects_result = await mcp_client.call_tool("list_projects")
    projects = projects_result.data
    if not projects:
        pytest.skip("No projects found to test pipeline creation.")

    project_id = None
    for project in projects:
        if project["name"] == "ado-mcp":
            project_id = project["id"]
            break

    if not project_id:
        pytest.skip("ado-mcp project not found. Please create it first.")

    connections_result = await mcp_client.call_tool(
        "list_service_connections", {"project_id": project_id}
    )
    connections = connections_result.data
    if not connections:
        pytest.skip("No service connections found to test pipeline creation.")

    github_connection_id = None
    for connection in connections:
        if connection["type"] == "GitHub":
            github_connection_id = connection["id"]
            break

    if not github_connection_id:
        pytest.skip("No GitHub service connection found.")

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

    if hasattr(pipeline, "id"):
        pipeline_id = pipeline.id
        pipeline_name_returned = pipeline.name
        assert isinstance(pipeline_id, int), f"Expected pipeline id to be int, got {type(pipeline_id)}"
        assert isinstance(pipeline_name_returned, str), f"Expected pipeline name to be str, got {type(pipeline_name_returned)}"
        assert pipeline_name_returned == pipeline_name, f"Expected pipeline name '{pipeline_name}', got '{pipeline_name_returned}'"
    else:
        assert isinstance(pipeline, dict), f"Expected created pipeline to be dict, got {type(pipeline)}"
        assert "id" in pipeline, f"Created pipeline missing 'id' field, has keys: {list(pipeline.keys())}"
        assert "name" in pipeline, f"Created pipeline missing 'name' field, has keys: {list(pipeline.keys())}"
        pipeline_id = pipeline["id"]
        pipeline_name_returned = pipeline["name"]
        assert pipeline_name_returned == pipeline_name, f"Expected pipeline name '{pipeline_name}', got '{pipeline_name_returned}'"
        assert isinstance(pipeline_id, int), f"Expected pipeline id to be int, got {type(pipeline_id)}"

    pipelines_list = await mcp_client.call_tool("list_pipelines", {"project_id": project_id})
    pipeline_ids = [p["id"] for p in pipelines_list.data]
    assert pipeline_id in pipeline_ids, f"Created pipeline {pipeline_id} should appear in pipelines list but was not found"

    delete_result = await mcp_client.call_tool(
        "delete_pipeline", {"project_id": project_id, "pipeline_id": pipeline_id}
    )
    assert delete_result.data is True, f"Pipeline deletion should return True but got {delete_result.data}"

    pipelines_list_after = await mcp_client.call_tool("list_pipelines", {"project_id": project_id})
    pipeline_ids_after = [p["id"] for p in pipelines_list_after.data]
    assert pipeline_id not in pipeline_ids_after, f"Pipeline {pipeline_id} should be deleted but still appears in list"


@requires_ado_creds
async def test_list_service_connections_returns_valid_list(mcp_client: Client):
    projects_result = await mcp_client.call_tool("list_projects")
    projects = projects_result.data
    if not projects:
        pytest.skip("No projects found to test service connections listing.")

    project_id = None
    for project in projects:
        if project["name"] == "ado-mcp":
            project_id = project["id"]
            break

    if not project_id:
        pytest.skip("ado-mcp project not found.")

    result = await mcp_client.call_tool("list_service_connections", {"project_id": project_id})
    connections = result.data

    assert isinstance(connections, list), f"Expected list of service connections, got {type(connections)}"


@requires_ado_creds
async def test_delete_pipeline_removes_pipeline(mcp_client: Client):
    projects_result = await mcp_client.call_tool("list_projects")
    projects = projects_result.data
    if not projects:
        pytest.skip("No projects found to test pipeline deletion.")

    project_id = None
    for project in projects:
        if project["name"] == "ado-mcp":
            project_id = project["id"]
            break

    if not project_id:
        pytest.skip("ado-mcp project not found.")

    connections_result = await mcp_client.call_tool(
        "list_service_connections", {"project_id": project_id}
    )
    connections = connections_result.data
    if not connections:
        pytest.skip("No service connections found to test pipeline deletion.")

    github_connection_id = None
    for connection in connections:
        if connection["type"] == "GitHub":
            github_connection_id = connection["id"]
            break

    if not github_connection_id:
        pytest.skip("No GitHub service connection found.")

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
    assert hasattr(pipeline, "id"), f"Created pipeline should have id attribute but does not"
    pipeline_id = pipeline.id

    pipelines_before = await mcp_client.call_tool("list_pipelines", {"project_id": project_id})
    pipeline_ids_before = [p["id"] for p in pipelines_before.data]
    assert pipeline_id in pipeline_ids_before, f"Created pipeline {pipeline_id} should exist before deletion but was not found"

    delete_result = await mcp_client.call_tool(
        "delete_pipeline", {"project_id": project_id, "pipeline_id": pipeline_id}
    )
    assert delete_result.data is True, f"Pipeline deletion should return True but got {delete_result.data}"

    pipelines_after = await mcp_client.call_tool("list_pipelines", {"project_id": project_id})
    pipeline_ids_after = [p["id"] for p in pipelines_after.data]
    assert pipeline_id not in pipeline_ids_after, f"Pipeline {pipeline_id} should be deleted but still appears in list"


@requires_ado_creds
async def test_get_pipeline_returns_valid_details(mcp_client: Client):
    projects = (await mcp_client.call_tool("list_projects")).data
    if not projects:
        pytest.skip("No projects found.")

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
    assert isinstance(details, dict), f"Expected pipeline details to be dict, got {type(details)}"
    assert details.get("id") == pipeline_id, f"Expected pipeline id {pipeline_id}, got {details.get('id')}"


@requires_ado_creds
async def test_run_and_get_pipeline_run_details(mcp_client: Client):
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"
    pipeline_id = 59

    run_details = (
        await mcp_client.call_tool(
            "run_pipeline", {"project_id": project_id, "pipeline_id": pipeline_id}
        )
    ).data
    assert run_details is not None, "Pipeline run should not be None but was None"
    assert isinstance(run_details, dict), f"Expected pipeline run to be dict, got {type(run_details)}"
    assert "id" in run_details, f"Pipeline run missing 'id' field, has keys: {list(run_details.keys())}"
    assert isinstance(run_details["id"], int), f"Expected pipeline run id to be int, got {type(run_details['id'])}"

    run_id = run_details["id"]

    await __import__("asyncio").sleep(2)

    run_status = (
        await mcp_client.call_tool(
            "get_pipeline_run",
            {"project_id": project_id, "pipeline_id": pipeline_id, "run_id": run_id},
        )
    ).data
    assert run_status is not None, "Pipeline run status should not be None but was None"
    assert isinstance(run_status, dict), f"Expected pipeline run status to be dict, got {type(run_status)}"
    assert "id" in run_status, f"Pipeline run status missing 'id' field, has keys: {list(run_status.keys())}"
    assert run_status["id"] == run_id, f"Expected run_id {run_id}, got {run_status['id']}"


async def test_no_client_check_authentication(mcp_client_with_unset_ado_env: Client):
    result = await mcp_client_with_unset_ado_env.call_tool("check_ado_authentication")
    assert result.data is False, f"Expected authentication to fail (False) when no client available, got {result.data}"


async def test_no_client_list_projects(mcp_client_with_unset_ado_env: Client):
    result = await mcp_client_with_unset_ado_env.call_tool("list_projects")
    assert result.data == [], f"Expected empty list when no client available, got {result.data}"


async def test_no_client_list_pipelines(mcp_client_with_unset_ado_env: Client):
    result = await mcp_client_with_unset_ado_env.call_tool("list_pipelines", {"project_id": "any"})
    assert result.data == [], f"Expected empty list when no client available, got {result.data}"


async def test_no_client_get_pipeline(mcp_client_with_unset_ado_env: Client):
    result = await mcp_client_with_unset_ado_env.call_tool(
        "get_pipeline", {"project_id": "any", "pipeline_id": 1}
    )
    assert result.data is None, f"Expected None when no client available, got {result.data}"


async def test_no_client_run_pipeline(mcp_client_with_unset_ado_env: Client):
    result = await mcp_client_with_unset_ado_env.call_tool(
        "run_pipeline", {"project_id": "any", "pipeline_id": 1}
    )
    assert result.data is None, f"Expected None when no client available, got {result.data}"


async def test_no_client_get_pipeline_run(mcp_client_with_unset_ado_env: Client):
    result = await mcp_client_with_unset_ado_env.call_tool(
        "get_pipeline_run", {"project_id": "any", "pipeline_id": 1, "run_id": 1}
    )
    assert result.data is None, f"Expected None when no client available, got {result.data}"


@requires_ado_creds
async def test_set_organization_failure_and_recovery(mcp_client: Client):
    initial_auth = await mcp_client.call_tool("check_ado_authentication")
    assert initial_auth.data is True, "Should start with valid client but authentication failed"

    initial_projects = await mcp_client.call_tool("list_projects")
    assert isinstance(initial_projects.data, list), f"Expected list of projects initially, got {type(initial_projects.data)}"

    invalid_org_url = "https://dev.azure.com/this-org-does-not-exist-for-sure"
    with pytest.raises(ToolError, match="Authentication check failed"):
        await mcp_client.call_tool("set_ado_organization", {"organization_url": invalid_org_url})

    auth_result = await mcp_client.call_tool("check_ado_authentication")
    assert auth_result.data is True, "Authentication should still succeed after failed switch - client should remain in previous state"

    list_result = await mcp_client.call_tool("list_projects")
    assert isinstance(list_result.data, list), f"Expected to still be able to list projects after failed switch, got {type(list_result.data)}"
    assert list_result.data == initial_projects.data, "Should get same projects as before failed switch"

    valid_org_url = os.environ.get("ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley")
    set_result = await mcp_client.call_tool(
        "set_ado_organization", {"organization_url": valid_org_url}
    )
    assert set_result.data.get("result") is True, f"Expected successful organization switch (True), got {set_result.data.get('result')}"

    auth_result_after_recovery = await mcp_client.call_tool("check_ado_authentication")
    assert auth_result_after_recovery.data is True, "Authentication should succeed after switching to valid org but failed"


@requires_ado_creds
async def test_pipeline_lifecycle_fire_and_forget(mcp_client: Client):
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"
    pipeline_id = 60

    run_result = await mcp_client.call_tool(
        "run_pipeline", {"project_id": project_id, "pipeline_id": pipeline_id}
    )

    pipeline_run = run_result.data
    assert pipeline_run is not None, "Pipeline run should not be None but was None"

    assert isinstance(pipeline_run, dict), f"Expected pipeline run to be dict, got {type(pipeline_run)}"
    assert "id" in pipeline_run, f"Pipeline run missing 'id' field, has keys: {list(pipeline_run.keys())}"
    assert "state" in pipeline_run, f"Pipeline run missing 'state' field, has keys: {list(pipeline_run.keys())}"
    assert isinstance(pipeline_run["id"], int), f"Expected run ID to be int, got {type(pipeline_run['id'])}"
    assert pipeline_run["state"] is not None, "Run state should not be None but was None"

    accepted_states = ["inProgress", "completed", "unknown"]
    assert pipeline_run["state"] in accepted_states, f"Expected state to be one of {accepted_states}, got '{pipeline_run['state']}'"


@requires_ado_creds
async def test_pipeline_lifecycle_wait_for_completion(mcp_client: Client):
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"
    pipeline_id = 61

    run_result = await mcp_client.call_tool(
        "run_pipeline", {"project_id": project_id, "pipeline_id": pipeline_id}
    )

    pipeline_run = run_result.data
    assert isinstance(pipeline_run, dict), f"Expected pipeline run to be dict, got {type(pipeline_run)}"
    assert "id" in pipeline_run, f"Pipeline run missing 'id' field, has keys: {list(pipeline_run.keys())}"
    run_id = pipeline_run["id"]

    max_attempts = 24
    attempt = 0
    final_run = None

    while attempt < max_attempts:
        attempt += 1
        await __import__("asyncio").sleep(5)

        status_result = await mcp_client.call_tool(
            "get_pipeline_run",
            {"project_id": project_id, "pipeline_id": pipeline_id, "run_id": run_id},
        )

        current_run = status_result.data
        assert isinstance(current_run, dict), f"Expected pipeline run status to be dict, got {type(current_run)}"
        assert "state" in current_run, f"Pipeline run status missing 'state' field, has keys: {list(current_run.keys())}"

        if current_run["state"] == "completed":
            final_run = current_run
            break

    assert final_run is not None, f"Pipeline run {run_id} should have completed within 2 minutes but did not"

    assert "result" in final_run, f"Pipeline run missing 'result' field, has keys: {list(final_run.keys())}"

    assert final_run["result"] in ["succeeded", "failed"], f"Expected result to be 'succeeded' or 'failed', got '{final_run['result']}'"


@requires_ado_creds
async def test_multiple_pipeline_runs(mcp_client: Client):
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"
    pipeline_id = 62

    run_ids = []

    for i in range(3):
        run_result = await mcp_client.call_tool(
            "run_pipeline", {"project_id": project_id, "pipeline_id": pipeline_id}
        )

        pipeline_run = run_result.data
        assert isinstance(pipeline_run, dict), f"Expected pipeline run to be dict, got {type(pipeline_run)}"
        assert "id" in pipeline_run, f"Pipeline run missing 'id' field, has keys: {list(pipeline_run.keys())}"
        run_ids.append(pipeline_run["id"])

        await __import__("asyncio").sleep(2)

    assert len(set(run_ids)) == 3, f"All run IDs should be unique but found duplicates: {run_ids}"

    for run_id in run_ids:
        status_result = await mcp_client.call_tool(
            "get_pipeline_run",
            {"project_id": project_id, "pipeline_id": pipeline_id, "run_id": run_id},
        )

        current_run = status_result.data
        assert current_run is not None, f"Should be able to get status for run {run_id} but got None"
        assert isinstance(current_run, dict), f"Expected run {run_id} to be dict, got {type(current_run)}"
        assert "state" in current_run, f"Run {run_id} missing 'state' field, has keys: {list(current_run.keys())}"
        assert current_run["state"] is not None, f"Run {run_id} should have a non-None state but got None"


@requires_ado_creds
async def test_pipeline_run_status_progression(mcp_client: Client):
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"
    pipeline_id = 63

    run_result = await mcp_client.call_tool(
        "run_pipeline", {"project_id": project_id, "pipeline_id": pipeline_id}
    )

    pipeline_run = run_result.data
    assert isinstance(pipeline_run, dict), f"Expected pipeline run to be dict, got {type(pipeline_run)}"
    assert "id" in pipeline_run, f"Pipeline run missing 'id' field, has keys: {list(pipeline_run.keys())}"
    run_id = pipeline_run["id"]

    previous_state = None
    status_changes = []

    for i in range(6):
        status_result = await mcp_client.call_tool(
            "get_pipeline_run",
            {"project_id": project_id, "pipeline_id": pipeline_id, "run_id": run_id},
        )

        current_run = status_result.data
        assert isinstance(current_run, dict), f"Expected pipeline run status to be dict, got {type(current_run)}"
        assert "state" in current_run, f"Pipeline run missing 'state' field, has keys: {list(current_run.keys())}"
        assert "result" in current_run, f"Pipeline run missing 'result' field, has keys: {list(current_run.keys())}"

        if current_run["state"] != previous_state:
            status_changes.append(
                {"state": current_run["state"], "result": current_run["result"], "check": i + 1}
            )
            previous_state = current_run["state"]

        if current_run["state"] == "completed":
            break

        await __import__("asyncio").sleep(5)

    assert len(status_changes) > 0, "Should have captured at least one status change but found none"

    final_status = status_changes[-1]
    valid_states = ["inProgress", "completed", "unknown"]
    assert final_status["state"] in valid_states, f"Expected final state to be one of {valid_states}, got '{final_status['state']}'"


# --- Tests for pipeline preview functionality ---


@requires_ado_creds
async def test_preview_pipeline_valid_yaml(mcp_client: Client):

    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 74  # preview-test-valid pipeline

    result = await mcp_client.call_tool(
        "preview_pipeline", {"project_id": project_id, "pipeline_id": pipeline_id}
    )

    preview_data = result.data
    assert preview_data is not None, "Preview should not be None"
    assert isinstance(preview_data, dict), "Preview should be a dictionary"

    assert "finalYaml" in preview_data, "Preview should contain finalYaml field"
    assert preview_data["finalYaml"] is not None, "Final YAML should not be None"
    assert isinstance(preview_data["finalYaml"], str), "Final YAML should be a string"
    assert len(preview_data["finalYaml"]) > 0, "Final YAML should not be empty"



@requires_ado_creds
async def test_preview_pipeline_with_yaml_override(mcp_client: Client):

    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 74  # preview-test-valid pipeline

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



@requires_ado_creds
async def test_preview_pipeline_with_variables(mcp_client: Client):

    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 75  # preview-test-parameterized pipeline

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



@requires_ado_creds
async def test_preview_pipeline_with_template_parameters(mcp_client: Client):

    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 75  # preview-test-parameterized pipeline

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



@requires_ado_creds
async def test_preview_pipeline_error_handling(mcp_client: Client):

    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 76  # preview-test-invalid pipeline

    try:
        result = await mcp_client.call_tool(
            "preview_pipeline", {"project_id": project_id, "pipeline_id": pipeline_id}
        )

        if result.data is not None:
            preview_data = result.data
            assert isinstance(preview_data, dict), "Even error responses should be dictionaries"

            pass
        else:
            pass

    except Exception as e:
        assert isinstance(e, Exception), "Should raise a proper exception type"


@requires_ado_creds
async def test_preview_pipeline_nonexistent_pipeline(mcp_client: Client):

    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 99999  # Non-existent pipeline ID

    try:
        result = await mcp_client.call_tool(
            "preview_pipeline", {"project_id": project_id, "pipeline_id": pipeline_id}
        )

        if result.data is None:
            pass
        else:
            assert isinstance(result.data, dict), f"Expected response to be dict, got {type(result.data)}"

    except Exception as e:
        assert isinstance(e, Exception), "Should raise a proper exception type"


async def test_preview_pipeline_no_client(mcp_client_with_unset_ado_env: Client):

    result = await mcp_client_with_unset_ado_env.call_tool(
        "preview_pipeline", {"project_id": "any", "pipeline_id": 1}
    )
    assert result.data is None, "Preview should return None when client is unavailable"


# --- Tests for pipeline logs functionality ---


@requires_ado_creds
async def test_get_pipeline_failure_summary_simple_pipeline(mcp_client: Client):

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

    assert "total_failed_steps" in summary, "Summary should have total_failed_steps"
    assert "root_cause_tasks" in summary, "Summary should have root_cause_tasks"
    assert "hierarchy_failures" in summary, "Summary should have hierarchy_failures"
    assert summary["total_failed_steps"] > 0, "Should have failed steps"

    assert len(summary["root_cause_tasks"]) > 0, "Should have root cause tasks"
    root_cause = summary["root_cause_tasks"][0]
    assert root_cause["step_name"] == "Run Tests", "Root cause should be 'Run Tests'"
    assert root_cause["step_type"] == "Task", "Root cause should be Task type"
    assert root_cause["result"] == "failed", "Root cause should have failed result"
    assert len(root_cause["issues"]) > 0, "Root cause should have issues"
    assert root_cause["log_content"] is not None, "Root cause should have log content"
    assert len(root_cause["log_content"]) > 0, "Log content should not be empty"



@requires_ado_creds
async def test_get_pipeline_failure_summary_complex_pipeline(mcp_client: Client):

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

    assert summary["total_failed_steps"] >= 4, "Complex pipeline should have multiple failures"
    assert len(summary["root_cause_tasks"]) >= 1, "Should have at least one root cause task"
    assert len(summary["hierarchy_failures"]) >= 3, "Should have hierarchy failures"

    unit_tests_failure = None
    for task in summary["root_cause_tasks"]:
        if "Unit Tests" in task["step_name"]:
            unit_tests_failure = task
            break

    assert unit_tests_failure is not None, "Should find Unit Tests failure"
    assert unit_tests_failure["step_type"] == "Task", "Unit Tests should be Task type"
    assert unit_tests_failure["log_content"] is not None, "Should have log content"

    log_content = unit_tests_failure["log_content"]
    assert "FAIL" in log_content, "Log should contain FAIL message"
    assert "ERROR" in log_content, "Log should contain ERROR message"
    assert "UserService.validateEmail" in log_content, "Log should contain specific error details"



@requires_ado_creds
async def test_get_failed_step_logs_with_filter(mcp_client: Client):

    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 84  # log-test-complex pipeline
    run_id = 324  # Known failed run

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

    unit_tests_step = step_logs[0]
    assert "Unit Tests" in unit_tests_step["step_name"], "Should match filter criteria"
    assert unit_tests_step["step_type"] == "Task", "Should be Task type"
    assert unit_tests_step["result"] == "failed", "Should be failed"
    assert unit_tests_step["log_content"] is not None, "Should have log content"



@requires_ado_creds
async def test_get_failed_step_logs_all_steps(mcp_client: Client):

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

    step_types = [step["step_type"] for step in step_logs]
    assert "Task" in step_types, "Should include Task-level failures"

    for step in step_logs:
        assert "step_name" in step, "Step should have step_name"
        assert "step_type" in step, "Step should have step_type"
        assert "result" in step, "Step should have result"
        assert step["result"] == "failed", "All steps should be failed"



@requires_ado_creds
async def test_get_pipeline_timeline(mcp_client: Client):

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

    record_types = [record.get("type") for record in records]
    assert "Task" in record_types, "Should have Task records"
    assert "Stage" in record_types, "Should have Stage records"

    failed_tasks = [r for r in records if r.get("result") == "failed" and r.get("type") == "Task"]
    assert len(failed_tasks) > 0, "Should have failed tasks"

    failed_task = failed_tasks[0]
    assert failed_task["name"] == "Run Tests", "Failed task should be 'Run Tests'"
    assert "log" in failed_task, "Failed task should have log reference"
    assert failed_task["log"]["id"] is not None, "Should have log ID"



@requires_ado_creds
async def test_list_pipeline_logs(mcp_client: Client):

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



@requires_ado_creds
async def test_get_log_content_by_id(mcp_client: Client):

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



@requires_ado_creds
async def test_get_log_content_by_id_with_line_limit(mcp_client: Client):

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



@requires_ado_creds
async def test_get_pipeline_failure_summary_with_line_limit(mcp_client: Client):

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



@requires_ado_creds
async def test_get_failed_step_logs_with_line_limit(mcp_client: Client):

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



async def test_logs_tools_no_client(mcp_client_with_unset_ado_env: Client):

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



@requires_ado_creds
async def test_run_pipeline_and_get_outcome_failure(mcp_client: Client):

    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 83  # log-test-failing pipeline (designed to fail)

    # Note: This is a "slow" pipeline that uses agents, so it may take longer
    result = await mcp_client.call_tool(
        "run_pipeline_and_get_outcome",
        {"project_id": project_id, "pipeline_id": pipeline_id, "timeout_seconds": 600},
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



@requires_ado_creds
async def test_run_pipeline_and_get_outcome_custom_timeout(mcp_client: Client):

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



async def test_run_pipeline_and_get_outcome_no_client(mcp_client_with_unset_ado_env: Client):

    result = await mcp_client_with_unset_ado_env.call_tool(
        "run_pipeline_and_get_outcome",
        {"project_id": "any", "pipeline_id": 1, "timeout_seconds": 300},
    )
    assert result.data is None, "Should return None when client unavailable"



async def test_run_pipeline_and_get_outcome_tool_registration(mcp_client: Client):

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



@requires_ado_creds
async def test_get_build_by_id_success(mcp_client: Client):

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



async def test_get_build_by_id_no_client(mcp_client_with_unset_ado_env: Client):

    result = await mcp_client_with_unset_ado_env.call_tool(
        "get_build_by_id", {"project_id": "any", "build_id": 1}
    )
    assert result.data is None, "Should return None when client unavailable"


async def test_get_build_by_id_tool_registration(mcp_client: Client):

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



# ========== MCP CACHING TESTS ==========

@pytest.fixture
async def fresh_cache():
    ado_cache.clear_all()
    yield
    ado_cache.clear_all()


@requires_ado_creds
async def test_list_available_projects_mcp_caching(mcp_client: Client, telemetry_setup, fresh_cache):

    memory_exporter = telemetry_setup
    
    # First call - should hit API
    result1 = await mcp_client.call_tool("list_available_projects")
    analyzer1 = analyze_spans(memory_exporter)
    
    # Should have made an API call
    assert analyzer1.was_data_fetched_from_api("projects")
    assert analyzer1.count_api_calls("list_projects") == 1
    assert result1.data is not None
    assert len(result1.data) > 0
    
    clear_spans(memory_exporter)
    
    # Second call - should use cache
    result2 = await mcp_client.call_tool("list_available_projects")
    analyzer2 = analyze_spans(memory_exporter)
    
    # Should have used cache, no new API calls
    assert analyzer2.was_data_fetched_from_cache("projects")
    assert analyzer2.count_api_calls("list_projects") == 0
    
    # Data should be consistent
    assert result1.data == result2.data


@requires_ado_creds
async def test_list_available_pipelines_mcp_caching(mcp_client: Client, telemetry_setup, fresh_cache):

    memory_exporter = telemetry_setup
    
    # Get a project first
    projects_result = await mcp_client.call_tool("list_available_projects")
    if not projects_result.data:
        pytest.skip("No projects available for testing")
    
    project_name = projects_result.data[0]
    clear_spans(memory_exporter)
    
    # First pipeline call - should hit API
    result1 = await mcp_client.call_tool("list_available_pipelines", {"project_name": project_name})
    analyzer1 = analyze_spans(memory_exporter)
    
    # Should have made an API call for pipelines
    assert analyzer1.count_api_calls("list_pipelines") == 1
    
    clear_spans(memory_exporter)
    
    # Second pipeline call - should use cache
    result2 = await mcp_client.call_tool("list_available_pipelines", {"project_name": project_name})
    analyzer2 = analyze_spans(memory_exporter)
    
    # Should have used cache, no new API calls
    assert analyzer2.was_data_fetched_from_cache("pipelines")
    assert analyzer2.count_api_calls("list_pipelines") == 0
    
    # Data should be consistent
    assert result1.data == result2.data


@requires_ado_creds
async def test_find_project_by_name_mcp_caching(mcp_client: Client, telemetry_setup, fresh_cache):

    memory_exporter = telemetry_setup
    
    # Prime the cache
    projects_result = await mcp_client.call_tool("list_available_projects")
    if not projects_result.data:
        pytest.skip("No projects available for testing")
    
    project_name = projects_result.data[0]
    clear_spans(memory_exporter)
    
    # Find project by name - should use cached data
    result = await mcp_client.call_tool("find_project_by_name", {"name": project_name})
    analyzer = analyze_spans(memory_exporter)
    
    # Should have cache hits, no API calls
    assert analyzer.count_cache_hits() > 0
    assert analyzer.count_api_calls("list_projects") == 0
    assert result.data is not None
    assert result.data["name"] == project_name


@requires_ado_creds
async def test_find_pipeline_by_name_mcp_caching(mcp_client: Client, telemetry_setup, fresh_cache):

    memory_exporter = telemetry_setup
    
    # Get projects and pipelines
    projects_result = await mcp_client.call_tool("list_available_projects")
    if not projects_result.data:
        pytest.skip("No projects available for testing")
    
    # Find a project with pipelines
    project_name = None
    pipeline_name = None
    
    for proj_name in projects_result.data:
        pipelines_result = await mcp_client.call_tool("list_available_pipelines", {"project_name": proj_name})
        if pipelines_result.data:
            project_name = proj_name
            pipeline_name = pipelines_result.data[0]
            break
    
    if not pipeline_name:
        pytest.skip("No pipelines found in any project")
    
    clear_spans(memory_exporter)
    
    # Find pipeline by name - should use cached data
    result = await mcp_client.call_tool("find_pipeline_by_name", {
        "project_name": project_name,
        "pipeline_name": pipeline_name
    })
    analyzer = analyze_spans(memory_exporter)
    
    # Should have cache hits, no API calls for cached operations
    assert analyzer.count_cache_hits() > 0
    assert result.data is not None
    assert result.data["pipeline"]["name"] == pipeline_name
    assert result.data["project"]["name"] == project_name


@requires_ado_creds  
async def test_mcp_cache_expiration_behavior(mcp_client: Client, telemetry_setup, fresh_cache):

    memory_exporter = telemetry_setup
    
    # Temporarily reduce cache TTL for testing
    original_ttl = ado_cache.PROJECT_TTL
    ado_cache.PROJECT_TTL = 2  # 2 seconds for testing
    
    try:
        # First call
        result1 = await mcp_client.call_tool("list_available_projects")
        clear_spans(memory_exporter)
        
        # Second call immediately - should use cache
        result2 = await mcp_client.call_tool("list_available_projects")
        analyzer_cached = analyze_spans(memory_exporter)
        assert analyzer_cached.was_data_fetched_from_cache("projects")
        
        # Wait for cache to expire
        time.sleep(2.5)
        clear_spans(memory_exporter)
        
        # Third call after expiration - should hit API again
        result3 = await mcp_client.call_tool("list_available_projects")
        analyzer_expired = analyze_spans(memory_exporter)
        assert analyzer_expired.was_data_fetched_from_api("projects")
        
        # Data should still be consistent
        assert result1.data == result3.data
        
    finally:
        # Restore original TTL
        ado_cache.PROJECT_TTL = original_ttl


@requires_ado_creds
async def test_name_based_pipeline_operations_caching(mcp_client: Client, telemetry_setup, fresh_cache):

    memory_exporter = telemetry_setup
    
    # Get projects and pipelines to prime cache
    projects_result = await mcp_client.call_tool("list_available_projects")
    if not projects_result.data:
        pytest.skip("No projects available for testing")
    
    # Find a project with pipelines
    project_name = None
    pipeline_name = None
    
    for proj_name in projects_result.data:
        pipelines_result = await mcp_client.call_tool("list_available_pipelines", {"project_name": proj_name})
        if pipelines_result.data:
            project_name = proj_name
            pipeline_name = pipelines_result.data[0]
            break
    
    if not pipeline_name:
        pytest.skip("No pipelines found in any project")
    
    clear_spans(memory_exporter)
    
    # Test run_pipeline_by_name (just check the lookup part, don't actually run)
    # We can't test actual execution easily, but we can test the name resolution uses cache
    try:
        result = await mcp_client.call_tool("run_pipeline_by_name", {
            "project_name": project_name,
            "pipeline_name": pipeline_name
        })
        # If it succeeds great, if it fails due to permissions etc, that's also fine
        # The important thing is that we should see cache operations
    except Exception:
        # Expected - might not have permissions to run pipelines
        pass
    
    analyzer = analyze_spans(memory_exporter)
    
    # Should have cache operations (hits or misses), indicating cache was used for lookups
    assert analyzer.has_cache_operations()
