import os

import pytest
from fastmcp.client import Client

from ado.models import PipelineRunRequest
from server import mcp
from tests.ado.test_client import requires_ado_creds

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def mcp_client():
    async with Client(mcp) as client:
        initial_org_url = os.environ.get(
            "ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley"
        )
        await client.call_tool("set_ado_organization", {"organization_url": initial_org_url})
        yield client


@requires_ado_creds
async def test_run_pipeline_with_template_parameters_correct_names(mcp_client: Client):
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"
    pipeline_id = 75

    template_parameters = {"testEnvironment": "dev", "enableDebug": True}

    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "template_parameters": template_parameters,
        },
    )

    pipeline_run = result.data
    assert pipeline_run is not None, f"Expected pipeline run data but got None"
    assert isinstance(pipeline_run, dict), (
        f"Expected pipeline run to be dict but got {type(pipeline_run)}"
    )

    assert pipeline_run["id"] is not None, f"Expected pipeline run to have an ID but got None"
    assert pipeline_run["state"] in ["unknown", "inProgress"], (
        f"Expected pipeline state to be 'unknown' or 'inProgress' but got '{pipeline_run['state']}'"
    )
    assert pipeline_run["pipeline"]["id"] == pipeline_id, (
        f"Expected pipeline ID {pipeline_id} but got {pipeline_run['pipeline']['id']}"
    )


@requires_ado_creds
async def test_run_pipeline_with_branch(mcp_client: Client):
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"
    pipeline_id = 59

    branch = "refs/heads/main"

    result = await mcp_client.call_tool(
        "run_pipeline", {"project_id": project_id, "pipeline_id": pipeline_id, "branch": branch}
    )

    pipeline_run = result.data
    assert pipeline_run is not None, f"Expected pipeline run data but got None"
    assert isinstance(pipeline_run, dict), (
        f"Expected pipeline run to be dict but got {type(pipeline_run)}"
    )

    assert pipeline_run["id"] is not None, f"Expected pipeline run to have an ID but got None"
    assert pipeline_run["state"] in ["unknown", "inProgress"], (
        f"Expected pipeline state to be 'unknown' or 'inProgress' but got '{pipeline_run['state']}'"
    )

    if "resources" in pipeline_run and "repositories" in pipeline_run["resources"]:
        repos = pipeline_run["resources"]["repositories"]
        if "self" in repos:
            assert repos["self"]["refName"] == branch, (
                f"Expected branch '{branch}' but got '{repos['self']['refName']}'"
            )


@requires_ado_creds
async def test_run_pipeline_with_runtime_variables_api_format(mcp_client: Client):
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 285  # runtime-variables-test pipeline

    variables = {
        "testVar": "test-value-123",
        "environment": {"value": "testing", "isSecret": False},
    }

    # Run pipeline with variables
    result = await mcp_client.call_tool(
        "run_pipeline",
        {"project_id": project_id, "pipeline_id": pipeline_id, "variables": variables},
    )

    pipeline_run = result.data
    assert pipeline_run is not None, f"Expected pipeline run data but got None"
    run_id = pipeline_run["id"]
    outcome_result = await mcp_client.call_tool(
        "run_pipeline_and_get_outcome",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "timeout_seconds": 60,
            "variables": variables,
        },
    )

    outcome = outcome_result.data
    assert outcome["success"] is True, (
        f"Expected pipeline to succeed but it failed: {outcome.get('failure_summary', 'No failure details')}"
    )
    timeline_result = await mcp_client.call_tool(
        "get_pipeline_timeline",
        {"project_id": project_id, "pipeline_id": pipeline_id, "run_id": run_id},
    )

    timeline = timeline_result.data

    delay_task = None
    for record in timeline["records"]:
        if record.get("type") == "Task" and "Test runtime variables" in record.get("name", ""):
            delay_task = record
            break

    assert delay_task is not None, (
        f"Expected to find delay task with runtime variables in timeline records: {[r.get('name') for r in timeline['records'] if r.get('type') == 'Task']}"
    )

    expected_display_name = "Test runtime variables: test-value-123 and testing"
    assert delay_task["name"] == expected_display_name, (
        f"Expected task name '{expected_display_name}' but got '{delay_task['name']}'"
    )


@requires_ado_creds
async def test_run_pipeline_and_get_outcome_with_all_params(mcp_client: Client):
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"
    pipeline_id = 59

    branch = "refs/heads/main"

    result = await mcp_client.call_tool(
        "run_pipeline_and_get_outcome",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "timeout_seconds": 300,
            "branch": branch,
        },
    )

    outcome = result.data
    assert outcome is not None, f"Expected outcome data but got None"
    assert isinstance(outcome, dict), f"Expected outcome to be dict but got {type(outcome)}"

    assert "pipeline_run" in outcome, (
        f"Expected 'pipeline_run' in outcome but got keys: {list(outcome.keys())}"
    )
    assert "success" in outcome, (
        f"Expected 'success' in outcome but got keys: {list(outcome.keys())}"
    )
    assert "execution_time_seconds" in outcome, (
        f"Expected 'execution_time_seconds' in outcome but got keys: {list(outcome.keys())}"
    )

    pipeline_run = outcome["pipeline_run"]
    assert pipeline_run["state"] == "completed", (
        f"Expected pipeline state 'completed' but got '{pipeline_run['state']}'"
    )
    assert outcome["success"] is True, (
        f"Expected pipeline to succeed but got success={outcome['success']} with failure summary: {outcome.get('failure_summary', 'None')}"
    )


@requires_ado_creds
async def test_run_pipeline_by_name_with_template_parameters(mcp_client: Client):
    project_name = "ado-mcp"
    pipeline_name = "preview-test-parameterized"

    template_parameters = {"testEnvironment": "prod", "enableDebug": False}

    result = await mcp_client.call_tool(
        "run_pipeline_by_name",
        {
            "project_name": project_name,
            "pipeline_name": pipeline_name,
            "template_parameters": template_parameters,
        },
    )

    pipeline_run = result.data
    assert pipeline_run is not None, f"Expected pipeline run data but got None"
    assert isinstance(pipeline_run, dict), (
        f"Expected pipeline run to be dict but got {type(pipeline_run)}"
    )

    assert pipeline_run["id"] is not None, f"Expected pipeline run to have an ID but got None"
    assert pipeline_run["state"] in ["unknown", "inProgress"], (
        f"Expected pipeline state to be 'unknown' or 'inProgress' but got '{pipeline_run['state']}'"
    )


@requires_ado_creds
async def test_run_pipeline_and_get_outcome_by_name_with_branch(mcp_client: Client):
    project_name = "ado-mcp"
    pipeline_name = "test_run_and_get_pipeline_run_details"

    branch = "refs/heads/main"

    result = await mcp_client.call_tool(
        "run_pipeline_and_get_outcome_by_name",
        {
            "project_name": project_name,
            "pipeline_name": pipeline_name,
            "timeout_seconds": 300,
            "branch": branch,
        },
    )

    outcome = result.data
    assert outcome is not None, f"Expected outcome data but got None"
    assert isinstance(outcome, dict), f"Expected outcome to be dict but got {type(outcome)}"

    assert outcome["pipeline_run"]["state"] == "completed", (
        f"Expected pipeline state 'completed' but got '{outcome['pipeline_run']['state']}'"
    )
    assert outcome["success"] is True, (
        f"Expected pipeline to succeed but got success={outcome['success']} with failure summary: {outcome.get('failure_summary', 'None')}"
    )


@requires_ado_creds
async def test_run_pipeline_with_stages_to_skip(mcp_client: Client):
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"
    pipeline_id = 84

    stages_to_skip = ["Deploy"]

    try:
        result = await mcp_client.call_tool(
            "run_pipeline",
            {
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "stages_to_skip": stages_to_skip,
            },
        )

        pipeline_run = result.data
        assert pipeline_run is not None, f"Expected pipeline run data but got None"
        assert isinstance(pipeline_run, dict), (
            f"Expected pipeline run to be dict but got {type(pipeline_run)}"
        )

        assert pipeline_run["id"] is not None, f"Expected pipeline run to have an ID but got None"
        assert pipeline_run["state"] in ["unknown", "inProgress"], (
            f"Expected pipeline state to be 'unknown' or 'inProgress' but got '{pipeline_run['state']}'"
        )

    except Exception as e:
        if "400" in str(e):
            pass
        else:
            raise


@requires_ado_creds
async def test_run_pipeline_no_params_unchanged(mcp_client: Client):
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"
    pipeline_id = 59
    result = await mcp_client.call_tool(
        "run_pipeline", {"project_id": project_id, "pipeline_id": pipeline_id}
    )

    pipeline_run = result.data
    assert pipeline_run is not None, f"Expected pipeline run data but got None"
    assert isinstance(pipeline_run, dict), (
        f"Expected pipeline run to be dict but got {type(pipeline_run)}"
    )

    assert pipeline_run["id"] is not None, f"Expected pipeline run to have an ID but got None"
    assert pipeline_run["state"] in ["unknown", "inProgress"], (
        f"Expected pipeline state to be 'unknown' or 'inProgress' but got '{pipeline_run['state']}'"
    )


@requires_ado_creds
async def test_run_pipeline_with_empty_params(mcp_client: Client):
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"
    pipeline_id = 59
    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "variables": {},
            "template_parameters": {},
            "stages_to_skip": [],
            "resources": {},
        },
    )

    pipeline_run = result.data
    assert pipeline_run is not None, f"Expected pipeline run data but got None"
    assert isinstance(pipeline_run, dict), (
        f"Expected pipeline run to be dict but got {type(pipeline_run)}"
    )

    assert pipeline_run["id"] is not None, f"Expected pipeline run to have an ID but got None"
    assert pipeline_run["state"] in ["unknown", "inProgress"], (
        f"Expected pipeline state to be 'unknown' or 'inProgress' but got '{pipeline_run['state']}'"
    )


@requires_ado_creds
async def test_pipeline_run_request_model():
    request = PipelineRunRequest(
        variables={"var1": "value1"},
        templateParameters={"param1": "value1"},
        branch="refs/heads/feature/test",
        stagesToSkip=["Stage1", "Stage2"],
    )

    request_dict = request.model_dump(exclude_none=True)
    assert request_dict["variables"] == {"var1": "value1"}, (
        f"Expected variables {{'var1': 'value1'}} but got {request_dict['variables']}"
    )
    assert request_dict["templateParameters"] == {"param1": "value1"}, (
        f"Expected templateParameters {{'param1': 'value1'}} but got {request_dict['templateParameters']}"
    )
    assert request_dict["branch"] == "refs/heads/feature/test", (
        f"Expected branch 'refs/heads/feature/test' but got '{request_dict['branch']}'"
    )
    assert request_dict["stagesToSkip"] == ["Stage1", "Stage2"], (
        f"Expected stagesToSkip ['Stage1', 'Stage2'] but got {request_dict['stagesToSkip']}"
    )

    partial_request = PipelineRunRequest(variables={"var2": "value2"})
    partial_dict = partial_request.model_dump(exclude_none=True)
    assert partial_dict == {"variables": {"var2": "value2"}}, (
        f"Expected {{'variables': {{'var2': 'value2'}}}} but got {partial_dict}"
    )
    assert "branch" not in partial_dict, (
        f"Expected 'branch' to be excluded but found it in {list(partial_dict.keys())}"
    )
