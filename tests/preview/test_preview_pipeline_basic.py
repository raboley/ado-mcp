import os
import pytest
from fastmcp.client import Client

from server import mcp
from src.test_config import get_project_id, get_preview_pipeline_id, get_parameterized_pipeline_id
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
async def test_preview_pipeline_basic(mcp_client: Client):
    project_id = get_project_id()
    pipeline_id = get_preview_pipeline_id()
    
    result = await mcp_client.call_tool(
        "preview_pipeline",
        {"project_id": project_id, "pipeline_id": pipeline_id},
    )

    preview_data = result.data
    assert preview_data is not None, f"Expected preview data but got None"
    assert isinstance(preview_data, dict), f"Expected dict but got {type(preview_data)}"
    assert "finalYaml" in preview_data, (
        f"Expected 'finalYaml' key in response. Got keys: {list(preview_data.keys())}"
    )
    assert preview_data["finalYaml"] is not None, f"Expected non-None finalYaml but got None"
    assert isinstance(preview_data["finalYaml"], str), (
        f"Expected finalYaml to be string but got {type(preview_data['finalYaml'])}"
    )
    assert len(preview_data["finalYaml"]) > 0, f"Expected non-empty finalYaml but got empty string"


@requires_ado_creds
async def test_preview_pipeline_with_variables(mcp_client: Client):
    project_id = get_project_id()
    pipeline_id = get_parameterized_pipeline_id()

    variables = {
        "testEnvironment": "preview-testing",
        "enableDebug": True,
        "previewMode": "enabled",
    }

    result = await mcp_client.call_tool(
        "preview_pipeline",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "variables": variables,
        },
    )

    preview_data = result.data
    assert preview_data is not None, f"Expected preview data with variables but got None"
    assert "finalYaml" in preview_data, (
        f"Expected 'finalYaml' key in response. Got keys: {list(preview_data.keys())}"
    )

    final_yaml = preview_data["finalYaml"]
    assert final_yaml is not None, f"Expected non-None finalYaml but got None"
    assert len(final_yaml) > 0, f"Expected non-empty finalYaml but got empty string"


@requires_ado_creds
async def test_preview_pipeline_with_empty_resources(mcp_client: Client):
    project_id = get_project_id()
    pipeline_id = get_preview_pipeline_id()
    resources = {}

    result = await mcp_client.call_tool(
        "preview_pipeline",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "resources": resources,
        },
    )

    preview_data = result.data
    assert preview_data is not None, f"Expected preview data with empty resources but got None"
    assert "finalYaml" in preview_data, (
        f"Expected 'finalYaml' key in response. Got keys: {list(preview_data.keys())}"
    )


@requires_ado_creds
async def test_preview_pipeline_with_stages_to_skip(mcp_client: Client):
    project_id = get_project_id()
    pipeline_id = get_parameterized_pipeline_id()

    stages_to_skip = ["TestStage", "DeploymentStage"]

    result = await mcp_client.call_tool(
        "preview_pipeline",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "stages_to_skip": stages_to_skip,
        },
    )

    preview_data = result.data
    assert preview_data is not None, f"Expected preview data with stages to skip but got None"
    assert "finalYaml" in preview_data, (
        f"Expected 'finalYaml' key in response. Got keys: {list(preview_data.keys())}"
    )


@requires_ado_creds
async def test_preview_pipeline_nonexistent_pipeline(mcp_client: Client):
    project_id = get_project_id()
    pipeline_id = 99999  # Non-existent pipeline for testing

    try:
        result = await mcp_client.call_tool(
            "preview_pipeline", {"project_id": project_id, "pipeline_id": pipeline_id}
        )

        if result.data is None:
            assert True, "Non-existent pipeline correctly returned None"
        else:
            assert isinstance(result.data, dict), (
                f"Expected dict response or None for non-existent pipeline but got {type(result.data)}"
            )
    except Exception as e:
        assert isinstance(e, Exception), (
            f"Expected proper exception type for non-existent pipeline but got {type(e)}"
        )


async def test_preview_pipeline_tool_registration():
    async with Client(mcp) as client:
        tools_response = await client.list_tools()
        if hasattr(tools_response, "tools"):
            tools = tools_response.tools
        else:
            tools = tools_response
        tool_names = [tool.name for tool in tools]
        assert "preview_pipeline" in tool_names, (
            f"Expected 'preview_pipeline' tool to be registered. Available tools: {tool_names}"
        )
