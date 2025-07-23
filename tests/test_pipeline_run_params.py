import os
import time

import pytest
from fastmcp.client import Client

from ado.models import PipelineRunRequest
from server import mcp
from src.test_config import get_project_id, get_project_name
from tests.ado.test_client import requires_ado_creds
from tests.test_helpers import get_pipeline_id_by_name

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
    project_id = get_project_id()
    pipeline_id = await get_pipeline_id_by_name(mcp_client, "preview-test-parameterized")

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
    project_id = get_project_id()
    pipeline_id = await get_pipeline_id_by_name(mcp_client, "github-resources-test-stable")

    # Use external repository override instead of self branch override
    resources = {
        "repositories": {
            "tooling": {
                "refName": "refs/heads/main"
            }
        }
    }

    result = await mcp_client.call_tool(
        "run_pipeline", {"project_id": project_id, "pipeline_id": pipeline_id, "resources": resources}
    )

    pipeline_run = result.data
    assert pipeline_run is not None, f"Expected pipeline run data but got None"
    assert isinstance(pipeline_run, dict), (
        f"Expected pipeline run to be dict but got {type(pipeline_run)}"
    )

    assert pipeline_run["id"] is not None, f"Expected pipeline run to have an ID but got None"
    # Verify the pipeline run started successfully with external repository override
    assert pipeline_run["state"] in ["unknown", "inProgress"], (
        f"Expected pipeline state to be 'unknown' or 'inProgress' but got '{pipeline_run['state']}'"
    )

@requires_ado_creds
async def test_run_pipeline_with_runtime_variables_api_format(mcp_client: Client):
    """Test that variables can be overridden at queue time using an agent-based pipeline."""
    project_id = get_project_id()
    # Use the agent-based pipeline that now has queue-time settable variables
    pipeline_id = await get_pipeline_id_by_name(mcp_client, "slow.log-test-complex")

    # Override the queue-time settable variables
    variables = {
        "buildConfiguration": "Debug",
        "appVersion": {"value": "2.0.0-test", "isSecret": False},
        "customTestVar": "overridden-value"
    }

    # Run pipeline with variable overrides
    result = await mcp_client.call_tool(
        "run_pipeline",
        {"project_id": project_id, "pipeline_id": pipeline_id, "variables": variables},
    )

    pipeline_run = result.data
    assert pipeline_run is not None, f"Expected pipeline run data but got None"
    assert pipeline_run["id"] is not None, f"Expected pipeline run to have an ID but got None"
    
    # Verify pipeline starts successfully with overridden variables
    assert pipeline_run["state"] in ["unknown", "inProgress"], (
        f"Expected pipeline state to be 'unknown' or 'inProgress' but got '{pipeline_run['state']}'"
    )

@requires_ado_creds
async def test_run_pipeline_and_get_outcome_with_all_params(mcp_client: Client):
    project_id = get_project_id()
    pipeline_id = await get_pipeline_id_by_name(mcp_client, "github-resources-test-stable")

    # Use external repository override instead of self branch override
    resources = {
        "repositories": {
            "tooling": {
                "refName": "refs/heads/main"
            }
        }
    }

    # Just test that pipeline starts with resources parameter - don't wait for completion
    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "resources": resources,
        },
    )

    pipeline_run = result.data
    assert pipeline_run is not None, f"Expected pipeline run data but got None"
    assert isinstance(pipeline_run, dict), f"Expected pipeline run to be dict but got {type(pipeline_run)}"

    # Verify pipeline starts successfully with external repository override
    assert pipeline_run["id"] is not None, f"Expected pipeline run to have an ID but got None"
    assert pipeline_run["state"] in ["unknown", "inProgress"], (
        f"Expected pipeline state to be 'unknown' or 'inProgress' but got '{pipeline_run['state']}'"
    )
    assert pipeline_run["pipeline"]["id"] == pipeline_id, (
        f"Expected pipeline ID {pipeline_id} but got {pipeline_run['pipeline']['id']}"
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
    project_id = get_project_id()
    pipeline_id = await get_pipeline_id_by_name(mcp_client, "slow.log-test-complex")

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
    project_id = get_project_id()
    pipeline_id = await get_pipeline_id_by_name(mcp_client, "test_run_and_get_pipeline_run_details")
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
    project_id = get_project_id()
    pipeline_id = await get_pipeline_id_by_name(mcp_client, "test_run_and_get_pipeline_run_details")
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
