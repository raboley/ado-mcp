"""
Test that pipeline tools are properly registered and have correct signatures.
"""

import pytest
from fastmcp.client import Client

from server import mcp

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def mcp_client():
    async with Client(mcp) as client:
        yield client


@pytest.mark.parametrize(
    "tool_name",
    [
        "run_pipeline",
        "run_pipeline_and_get_outcome",
        "get_pipeline",
        "get_pipeline_run",
    ],
)
async def test_name_based_pipeline_tools_registered(mcp_client: Client, tool_name: str):
    """Test that name-based pipeline tools are registered with correct parameters."""
    tools_response = await mcp_client.list_tools()
    if hasattr(tools_response, "tools"):
        tools = tools_response.tools
    else:
        tools = tools_response

    tool_names = [tool.name for tool in tools]
    assert tool_name in tool_names, f"{tool_name} tool should be registered"

    # Find the tool
    tool = next(t for t in tools if t.name == tool_name)

    # Check that it has name-based parameters
    input_schema = tool.inputSchema
    required_fields = input_schema.get("required", [])
    properties = input_schema.get("properties", {})

    assert "project_name" in required_fields, (
        f"{tool_name} should have project_name as required parameter"
    )
    assert "pipeline_name" in required_fields, (
        f"{tool_name} should have pipeline_name as required parameter"
    )
    assert "project_name" in properties, f"{tool_name} should have project_name in properties"
    assert "pipeline_name" in properties, f"{tool_name} should have pipeline_name in properties"

    # Check parameter types
    assert properties["project_name"]["type"] == "string", (
        f"{tool_name} project_name should be string type"
    )
    assert properties["pipeline_name"]["type"] == "string", (
        f"{tool_name} pipeline_name should be string type"
    )


async def test_pipeline_tool_descriptions_updated(mcp_client: Client):
    """Test that pipeline tool descriptions emphasize run_pipeline_and_get_outcome as preferred."""
    tools_response = await mcp_client.list_tools()
    if hasattr(tools_response, "tools"):
        tools = tools_response.tools
    else:
        tools = tools_response

    # Find run_pipeline_and_get_outcome tool
    outcome_tool = next(tool for tool in tools if tool.name == "run_pipeline_and_get_outcome")
    description = outcome_tool.description.lower()

    assert "preferred" in description, (
        "run_pipeline_and_get_outcome should be marked as preferred tool"
    )
    assert "outcome" in description, "Description should mention outcome/results"

    # Find run_pipeline tool
    run_tool = next(tool for tool in tools if tool.name == "run_pipeline")
    run_description = run_tool.description.lower()

    assert "most users want" in run_description or "usually want" in run_description, (
        "run_pipeline should direct users to outcome tool"
    )


async def test_no_old_id_based_parameters(mcp_client: Client):
    """Test that old ID-based parameters are removed from pipeline tools."""
    tools_response = await mcp_client.list_tools()
    if hasattr(tools_response, "tools"):
        tools = tools_response.tools
    else:
        tools = tools_response

    pipeline_tools = [tool for tool in tools if "run_pipeline" in tool.name]

    for tool in pipeline_tools:
        input_schema = tool.inputSchema
        properties = input_schema.get("properties", {})

        # Should not have old ID-based parameters
        assert "project_id" not in properties, f"{tool.name} should not have project_id parameter"
        assert "pipeline_id" not in properties, f"{tool.name} should not have pipeline_id parameter"
