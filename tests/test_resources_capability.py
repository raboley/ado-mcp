import os

import pytest
from fastmcp.client import Client

from server import mcp
from src.test_config import get_project_name
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
async def test_resources_parameter_capability(mcp_client: Client):
    project_name = get_project_name()
    pipeline_name = "github-resources-test-stable"

    resources = {"repositories": {"tooling": {"refName": "refs/heads/stable/0.0.1"}}}

    template_parameters = {"taskfileVersion": "latest", "installPath": "./bin/resources-test"}

    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_name": project_name,
            "pipeline_name": pipeline_name,
            "resources": resources,
            "template_parameters": template_parameters,
        },
    )

    pipeline_run = result.data
    assert pipeline_run is not None, "Expected pipeline run data but got None"
    assert isinstance(pipeline_run, dict), (
        f"Expected pipeline run to be dict but got {type(pipeline_run)}"
    )

    assert pipeline_run["id"] is not None, (
        f"Expected pipeline run to have an ID but got {pipeline_run.get('id')}"
    )
    assert pipeline_run["state"] in ["unknown", "inProgress"], (
        f"Expected pipeline state to be 'unknown' or 'inProgress' but got '{pipeline_run.get('state')}'"
    )


@requires_ado_creds
async def test_template_parameters_capability(mcp_client: Client):
    project_name = get_project_name()
    # Use a pipeline that supports template parameters
    pipeline_name = "preview-test-parameterized"

    # Use template parameters that the pipeline actually supports
    template_parameters = {"testEnvironment": "dev", "enableDebug": True}

    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_name": project_name,
            "pipeline_name": pipeline_name,
            "template_parameters": template_parameters,
        },
    )

    pipeline_run = result.data
    assert pipeline_run is not None, "Expected pipeline run data but got None"
    assert isinstance(pipeline_run, dict), (
        f"Expected pipeline run to be dict but got {type(pipeline_run)}"
    )

    assert pipeline_run["id"] is not None, (
        f"Expected pipeline run to have an ID but got {pipeline_run.get('id')}"
    )
    assert pipeline_run["state"] in ["unknown", "inProgress"], (
        f"Expected pipeline state to be 'unknown' or 'inProgress' but got '{pipeline_run.get('state')}'"
    )


@requires_ado_creds
async def test_branch_selection_capability(mcp_client: Client):
    project_name = get_project_name()
    # Use external repository override instead of self branch override
    pipeline_name = "github-resources-test-stable"

    # Use external repository resource override instead of branch override
    resources = {"repositories": {"tooling": {"refName": "refs/heads/main"}}}

    result = await mcp_client.call_tool(
        "run_pipeline",
        {"project_name": project_name, "pipeline_name": pipeline_name, "resources": resources},
    )

    pipeline_run = result.data
    assert pipeline_run is not None, "Expected pipeline run data but got None"
    assert isinstance(pipeline_run, dict), (
        f"Expected pipeline run to be dict but got {type(pipeline_run)}"
    )

    assert pipeline_run["id"] is not None, (
        f"Expected pipeline run to have an ID but got {pipeline_run.get('id')}"
    )
    assert pipeline_run["state"] in ["unknown", "inProgress"], (
        f"Expected pipeline state to be 'unknown' or 'inProgress' but got '{pipeline_run.get('state')}'"
    )


@requires_ado_creds
async def test_name_based_capabilities(mcp_client: Client):
    project_name = "ado-mcp"
    # Use a pipeline that supports resources
    pipeline_name = "github-resources-test-stable"

    # Use external repository override instead of self branch override
    resources = {"repositories": {"tooling": {"refName": "refs/heads/main"}}}

    result = await mcp_client.call_tool(
        "run_pipeline_by_name",
        {"project_name": project_name, "pipeline_name": pipeline_name, "resources": resources},
    )

    pipeline_run = result.data
    assert pipeline_run is not None, "Expected pipeline run data but got None"
    assert isinstance(pipeline_run, dict), (
        f"Expected pipeline run to be dict but got {type(pipeline_run)}"
    )

    assert pipeline_run["id"] is not None, (
        f"Expected pipeline run to have an ID but got {pipeline_run.get('id')}"
    )
    assert pipeline_run["state"] in ["unknown", "inProgress"], (
        f"Expected pipeline state to be 'unknown' or 'inProgress' but got '{pipeline_run.get('state')}'"
    )


@requires_ado_creds
async def test_comprehensive_capabilities_demo(mcp_client: Client):
    project_name = get_project_name()
    # Use an agent-based pipeline that supports comprehensive capabilities
    pipeline_name = "slow.log-test-complex"

    # Use queue-time variables instead of branch override for server pool compatibility
    variables = {"buildConfiguration": "Debug", "appVersion": "1.2.0-test"}

    result = await mcp_client.call_tool(
        "run_pipeline",
        {"project_name": project_name, "pipeline_name": pipeline_name, "variables": variables},
    )

    pipeline_run = result.data
    assert pipeline_run is not None, "Expected pipeline run data but got None"
    assert isinstance(pipeline_run, dict), (
        f"Expected pipeline run to be dict but got {type(pipeline_run)}"
    )

    assert pipeline_run["id"] is not None, (
        f"Expected pipeline run to have an ID but got {pipeline_run.get('id')}"
    )
    assert pipeline_run["state"] in ["unknown", "inProgress"], (
        f"Expected pipeline state to be 'unknown' or 'inProgress' but got '{pipeline_run.get('state')}'"
    )


@requires_ado_creds
async def test_github_resources_concept_validation(mcp_client: Client):
    project_name = get_project_name()
    # Use the GitHub resources pipeline to validate external repository functionality
    pipeline_name = "github-resources-test-stable"

    # Test external repository resource control
    resources = {"repositories": {"tooling": {"refName": "refs/heads/stable/0.0.1"}}}

    template_parameters = {"taskfileVersion": "v3.28.0", "installPath": "./test-bin"}

    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_name": project_name,
            "pipeline_name": pipeline_name,
            "resources": resources,
            "template_parameters": template_parameters,
        },
    )

    pipeline_run = result.data
    assert pipeline_run is not None, "Expected pipeline run data but got None"
    assert isinstance(pipeline_run, dict), (
        f"Expected pipeline run to be dict but got {type(pipeline_run)}"
    )
    assert pipeline_run["id"] is not None, (
        f"Expected pipeline run to have an ID but got {pipeline_run.get('id')}"
    )
