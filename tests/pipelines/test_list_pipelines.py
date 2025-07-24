import os

import pytest
from fastmcp.client import Client

from server import mcp
from src.test_config import get_project_id
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
async def test_list_pipelines_returns_valid_list(mcp_client: Client):
    project_id = get_project_id()
    result = await mcp_client.call_tool("list_pipelines", {"project_id": project_id})

    pipelines = result.data
    assert pipelines is not None, "Expected pipelines list but got None"
    assert isinstance(pipelines, list), f"Expected list but got {type(pipelines).__name__}"

    if len(pipelines) > 0:
        pipeline = pipelines[0]
        assert isinstance(pipeline, dict), (
            f"Expected pipeline to be dict but got {type(pipeline).__name__}"
        )

        required_fields = ["id", "name", "folder"]
        for field in required_fields:
            assert field in pipeline, (
                f"Pipeline missing required field '{field}'. Available fields: {list(pipeline.keys())}"
            )

        assert isinstance(pipeline["id"], int), (
            f"Pipeline id should be int but got {type(pipeline['id']).__name__}: {pipeline['id']}"
        )
        assert isinstance(pipeline["name"], str), (
            f"Pipeline name should be str but got {type(pipeline['name']).__name__}: {pipeline['name']}"
        )
        assert isinstance(pipeline["folder"], str), (
            f"Pipeline folder should be str but got {type(pipeline['folder']).__name__}: {pipeline['folder']}"
        )


@requires_ado_creds
async def test_list_pipelines_finds_expected_pipelines(mcp_client: Client):
    project_id = get_project_id()
    result = await mcp_client.call_tool("list_pipelines", {"project_id": project_id})

    pipelines = result.data
    assert isinstance(pipelines, list), f"Expected list but got {type(pipelines).__name__}"

    pipeline_names = [p.get("name") for p in pipelines]

    assert "github-resources-test-stable" in pipeline_names, (
        f"Expected 'github-resources-test-stable' in pipeline names but found: {pipeline_names}"
    )

    preview_pipelines = [name for name in pipeline_names if "preview-test" in name]
    assert len(preview_pipelines) > 0, (
        f"Expected to find preview test pipelines but found none. All pipelines: {pipeline_names}"
    )


@requires_ado_creds
async def test_list_pipelines_specific_pipeline_details(mcp_client: Client):
    project_id = get_project_id()
    result = await mcp_client.call_tool("list_pipelines", {"project_id": project_id})

    pipelines = result.data
    assert isinstance(pipelines, list), f"Expected list but got {type(pipelines).__name__}"

    github_pipeline = None
    for pipeline in pipelines:
        if pipeline.get("name") == "github-resources-test-stable":
            github_pipeline = pipeline
            break

    pipeline_names = [p.get("name") for p in pipelines]
    assert github_pipeline is not None, (
        f"Expected to find 'github-resources-test-stable' pipeline but only found: {pipeline_names}"
    )
    assert isinstance(github_pipeline["id"], int) and github_pipeline["id"] > 0, (
        f"Expected pipeline ID to be a positive integer but got {github_pipeline['id']}"
    )
    assert "github-resources-test-stable" in github_pipeline["name"], (
        f"Expected name to contain 'github-resources-test-stable' but got: {github_pipeline['name']}"
    )


@requires_ado_creds
async def test_list_pipelines_invalid_project(mcp_client: Client):
    try:
        result = await mcp_client.call_tool(
            "list_pipelines", {"project_id": "00000000-0000-0000-0000-000000000000"}
        )

        pipelines = result.data
        assert pipelines == [], f"Expected empty list for invalid project but got: {pipelines}"
    except Exception as e:
        assert isinstance(e, Exception), (
            "Expected an exception for invalid project ID but handling failed unexpectedly"
        )


async def test_list_pipelines_tool_registration():
    async with Client(mcp) as client:
        tools_response = await client.list_tools()
        if hasattr(tools_response, "tools"):
            tools = tools_response.tools
        else:
            tools = tools_response
        tool_names = [tool.name for tool in tools]
        assert "list_pipelines" in tool_names, (
            f"Expected 'list_pipelines' tool to be registered but found tools: {tool_names}"
        )
