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
async def test_run_pipeline_with_github_resources_stable_branch(mcp_client: Client):
    get_project_name()
    pipeline_name = "github-resources-test-stable"
    resources = {"repositories": {"tooling": {"refName": "refs/heads/stable/0.0.1"}}}

    template_parameters = {"taskfileVersion": "latest", "installPath": "./bin/stable-test"}

    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_name": get_project_name(),
            "pipeline_name": pipeline_name,
            "resources": resources,
            "template_parameters": template_parameters,
        },
    )

    pipeline_run = result.data
    assert pipeline_run is not None, (
        f"Expected pipeline run data but got None, full result: {result}"
    )
    assert pipeline_run["id"] is not None, (
        f"Expected pipeline run ID but got None, pipeline run: {pipeline_run}"
    )
    assert pipeline_run["state"] in ["unknown", "inProgress"], (
        f"Expected pipeline state to be 'unknown' or 'inProgress' but got '{pipeline_run['state']}'"
    )


@requires_ado_creds
async def test_run_pipeline_with_github_resources_main_branch(mcp_client: Client):
    get_project_name()
    pipeline_name = "github-resources-test-stable"
    resources = {"repositories": {"tooling": {"refName": "refs/heads/main"}}}

    template_parameters = {"taskfileVersion": "latest", "installPath": "./bin/main-test"}

    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_name": get_project_name(),
            "pipeline_name": pipeline_name,
            "resources": resources,
            "template_parameters": template_parameters,
        },
    )

    pipeline_run = result.data
    assert pipeline_run is not None, (
        f"Expected pipeline run data but got None, full result: {result}"
    )
    assert pipeline_run["id"] is not None, (
        f"Expected pipeline run ID but got None, pipeline run: {pipeline_run}"
    )


@requires_ado_creds
async def test_run_pipeline_with_github_resources_feature_branch(mcp_client: Client):
    get_project_name()
    pipeline_name = "github-resources-test-stable"
    resources = {"repositories": {"tooling": {"refName": "refs/heads/stable/0.0.1"}}}

    template_parameters = {"taskfileVersion": "v1.0.0", "installPath": "./bin/feature-test"}

    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_name": get_project_name(),
            "pipeline_name": pipeline_name,
            "resources": resources,
            "template_parameters": template_parameters,
        },
    )

    pipeline_run = result.data
    assert pipeline_run is not None, (
        f"Expected pipeline run data but got None, full result: {result}"
    )
    assert pipeline_run["id"] is not None, (
        f"Expected pipeline run ID but got None, pipeline run: {pipeline_run}"
    )


@requires_ado_creds
async def test_run_pipeline_with_multiple_template_parameters(mcp_client: Client):
    get_project_name()
    pipeline_name = "github-resources-test-stable"
    template_parameters = {"taskfileVersion": "latest", "installPath": "./bin/multi-param-test"}

    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_name": get_project_name(),
            "pipeline_name": pipeline_name,
            "template_parameters": template_parameters,
        },
    )

    pipeline_run = result.data
    assert pipeline_run is not None, (
        f"Expected pipeline run data but got None, full result: {result}"
    )
    assert pipeline_run["id"] is not None, (
        f"Expected pipeline run ID but got None, pipeline run: {pipeline_run}"
    )


@requires_ado_creds
async def test_run_pipeline_with_template_parameters(mcp_client: Client):
    get_project_name()
    pipeline_name = "preview-test-parameterized"
    template_parameters = {"testEnvironment": "staging", "enableDebug": True}

    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_name": get_project_name(),
            "pipeline_name": pipeline_name,
            "template_parameters": template_parameters,
        },
    )

    pipeline_run = result.data
    assert pipeline_run is not None, (
        f"Expected pipeline run data but got None, full result: {result}"
    )
    assert pipeline_run["id"] is not None, (
        f"Expected pipeline run ID but got None, pipeline run: {pipeline_run}"
    )


@requires_ado_creds
async def test_run_pipeline_with_stages_to_skip(mcp_client: Client):
    get_project_name()
    pipeline_name = "slow.log-test-complex"
    stages_to_skip = ["Test"]

    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_name": get_project_name(),
            "pipeline_name": pipeline_name,
            "stages_to_skip": stages_to_skip,
        },
    )

    pipeline_run = result.data
    assert pipeline_run is not None, (
        f"Expected pipeline run data but got None, full result: {result}"
    )
    assert pipeline_run["id"] is not None, (
        f"Expected pipeline run ID but got None, pipeline run: {pipeline_run}"
    )


@requires_ado_creds
async def test_run_pipeline_with_branch_override_unsupported_pipeline(mcp_client: Client):
    """Test that branch override fails gracefully for pipelines that don't support resources."""
    get_project_name()
    pipeline_name = "test_run_and_get_pipeline_run_details"
    # This pipeline uses server pool and has no resources section, so branch override should fail
    with pytest.raises(Exception) as exc_info:
        await mcp_client.call_tool(
            "run_pipeline",
            {
                "project_name": get_project_name(),
                "pipeline_name": pipeline_name,
                "branch": "refs/heads/main",
            },
        )

    error_message = str(exc_info.value)
    assert "does not support branch overrides or 'self' repository resources" in error_message, (
        f"Expected error message about unsupported branch overrides, but got: {error_message}"
    )
    assert "'resources' section" in error_message, (
        f"Expected error message to mention 'resources' section, but got: {error_message}"
    )


@requires_ado_creds
async def test_run_pipeline_with_branch_resource_override_unsupported_pipeline(mcp_client: Client):
    """Test that resource override fails gracefully for pipelines that don't support resources."""
    get_project_name()
    pipeline_name = "test_run_and_get_pipeline_run_details"
    resources = {"repositories": {"self": {"refName": "refs/heads/main"}}}

    # This pipeline uses server pool and has no resources section, so resource override should fail
    with pytest.raises(Exception) as exc_info:
        await mcp_client.call_tool(
            "run_pipeline",
            {
                "project_name": get_project_name(),
                "pipeline_name": pipeline_name,
                "resources": resources,
            },
        )

    error_message = str(exc_info.value)
    assert "does not support branch overrides or 'self' repository resources" in error_message, (
        f"Expected error message about unsupported resources, but got: {error_message}"
    )
    assert "'resources' section" in error_message, (
        f"Expected error message to mention 'resources' section, but got: {error_message}"
    )


@requires_ado_creds
async def test_run_pipeline_with_external_resources_works(mcp_client: Client):
    """Test that external resource overrides work for pipelines that support them."""
    get_project_name()
    pipeline_name = "github-resources-test-stable"
    # This pipeline has resources section with external GitHub repo, which works
    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_name": get_project_name(),
            "pipeline_name": pipeline_name,
            "resources": {"repositories": {"tooling": {"refName": "refs/heads/main"}}},
            "template_parameters": {
                "taskfileVersion": "latest",
                "installPath": "./bin/external-resource-test",
            },
        },
    )

    pipeline_run = result.data
    assert pipeline_run is not None, (
        f"Expected pipeline run data but got None, full result: {result}"
    )
    assert pipeline_run["id"] is not None, (
        f"Expected pipeline run ID but got None, pipeline run: {pipeline_run}"
    )
    assert pipeline_run["state"] in ["unknown", "inProgress"], (
        f"Expected state to be 'unknown' or 'inProgress' but got '{pipeline_run['state']}'"
    )


@requires_ado_creds
async def test_run_pipeline_github_resources_complex_scenario(mcp_client: Client):
    get_project_name()
    pipeline_name = "github-resources-test-stable"
    resources = {"repositories": {"tooling": {"refName": "refs/heads/stable/0.0.1"}}}

    template_parameters = {"taskfileVersion": "latest", "installPath": "./bin/complex-test"}

    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_name": get_project_name(),
            "pipeline_name": pipeline_name,
            "resources": resources,
            "template_parameters": template_parameters,
        },
    )

    pipeline_run = result.data
    assert pipeline_run is not None, (
        f"Expected pipeline run data but got None, full result: {result}"
    )
    assert pipeline_run["id"] is not None, (
        f"Expected pipeline run ID but got None, pipeline run: {pipeline_run}"
    )


async def test_run_pipeline_parameter_combinations_tool_registration():
    async with Client(mcp) as client:
        tools = await client.list_tools()
        run_pipeline_tool = None

        for tool in tools:
            if tool.name == "run_pipeline":
                run_pipeline_tool = tool
                break

        assert run_pipeline_tool is not None, (
            f"Expected run_pipeline tool to be registered but not found in tools: {[t.name for t in tools]}"
        )
