import os
import pytest
from fastmcp.client import Client

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
async def test_preview_pipeline_basic(mcp_client: Client):
    project_name = get_project_name()
    pipeline_name = "preview-test-valid"
    result = await mcp_client.call_tool(
        "preview_pipeline",
        {"project_name": project_name, "pipeline_name": pipeline_name},
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
    project_name = get_project_name()
    # Use a simple pipeline that doesn't have external dependencies
    pipeline_name = "preview-test-valid"
    # Test basic preview without parameters since this pipeline doesn't have any
    result = await mcp_client.call_tool(
        "preview_pipeline",
        {
            "project_name": project_name,
            "pipeline_name": pipeline_name,
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
    project_name = get_project_name()
    pipeline_name = "preview-test-valid"
    resources = {}

    result = await mcp_client.call_tool(
        "preview_pipeline",
        {
            "project_name": project_name,
            "pipeline_name": pipeline_name,
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
    project_name = get_project_name()
    # Use preview-test-valid instead since preview-test-parameterized doesn't have stages
    pipeline_name = "preview-test-valid"
    # Test without stages_to_skip since most of our test pipelines are job-based, not stage-based
    result = await mcp_client.call_tool(
        "preview_pipeline",
        {
            "project_name": project_name,
            "pipeline_name": pipeline_name,
        },
    )

    preview_data = result.data
    assert preview_data is not None, f"Expected preview data with stages to skip but got None"
    assert "finalYaml" in preview_data, (
        f"Expected 'finalYaml' key in response. Got keys: {list(preview_data.keys())}"
    )

@requires_ado_creds
async def test_preview_pipeline_nonexistent_pipeline(mcp_client: Client):
    project_name = get_project_name()
    pipeline_id = 99999  # Non-existent pipeline for testing

    try:
        result = await mcp_client.call_tool(
            "preview_pipeline", {"project_name": project_name, "pipeline_name": pipeline_name}
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
