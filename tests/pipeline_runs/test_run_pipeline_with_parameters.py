import os
import pytest
from fastmcp.client import Client

from server import mcp
from src.test_config import get_project_id, get_basic_pipeline_id, get_parameterized_pipeline_id, get_github_resources_pipeline_id, get_complex_pipeline_id
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
    project_id = get_project_id()
    pipeline_id = get_github_resources_pipeline_id()
    resources = {"repositories": {"tooling": {"refName": "refs/heads/stable/0.0.1"}}}

    template_parameters = {"taskfileVersion": "latest", "installPath": "./bin/stable-test"}

    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
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
    project_id = get_project_id()
    pipeline_id = get_github_resources_pipeline_id()
    resources = {"repositories": {"tooling": {"refName": "refs/heads/main"}}}

    template_parameters = {"taskfileVersion": "latest", "installPath": "./bin/main-test"}

    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
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
    project_id = get_project_id()
    pipeline_id = get_github_resources_pipeline_id()
    resources = {"repositories": {"tooling": {"refName": "refs/heads/stable/0.0.1"}}}

    template_parameters = {"taskfileVersion": "v1.0.0", "installPath": "./bin/feature-test"}

    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
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
    project_id = get_project_id()
    pipeline_id = get_github_resources_pipeline_id()
    template_parameters = {"taskfileVersion": "latest", "installPath": "./bin/multi-param-test"}

    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
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
    project_id = get_project_id()
    pipeline_id = get_parameterized_pipeline_id()
    template_parameters = {"testEnvironment": "staging", "enableDebug": True}

    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
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
    project_id = get_project_id()
    pipeline_id = get_complex_pipeline_id()
    stages_to_skip = ["Test"]

    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
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
async def test_run_pipeline_with_branch_override(mcp_client: Client):
    project_id = get_project_id()
    pipeline_id = get_basic_pipeline_id()
    
    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "branch": "refs/heads/main",
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
async def test_run_pipeline_with_branch_resource_override(mcp_client: Client):
    project_id = get_project_id()
    pipeline_id = get_basic_pipeline_id()
    resources = {"repositories": {"self": {"refName": "refs/heads/main"}}}

    result = await mcp_client.call_tool(
        "run_pipeline",
        {"project_id": project_id, "pipeline_id": pipeline_id, "resources": resources},
    )

    pipeline_run = result.data
    assert pipeline_run is not None, (
        f"Expected pipeline run data but got None, full result: {result}"
    )
    assert pipeline_run["id"] is not None, (
        f"Expected pipeline run ID but got None, pipeline run: {pipeline_run}"
    )


@requires_ado_creds
async def test_run_pipeline_github_resources_complex_scenario(mcp_client: Client):
    project_id = get_project_id()
    pipeline_id = get_github_resources_pipeline_id()
    resources = {"repositories": {"tooling": {"refName": "refs/heads/stable/0.0.1"}}}

    template_parameters = {"taskfileVersion": "latest", "installPath": "./bin/complex-test"}

    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
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
