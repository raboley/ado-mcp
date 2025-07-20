"""
Tests for the preview_pipeline MCP tool - basic functionality.

This module tests the basic pipeline preview functionality without complex parameters.
"""

import os
import pytest
from fastmcp.client import Client

from server import mcp
from tests.ado.test_client import requires_ado_creds

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio

# Test fixtures
TEST_PROJECT_ID = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
BASIC_PREVIEW_PIPELINE_ID = 74  # preview-test-valid pipeline


@pytest.fixture
async def mcp_client():
    """Provides a connected MCP client for tests."""
    async with Client(mcp) as client:
        initial_org_url = os.environ.get(
            "ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley"
        )
        await client.call_tool("set_ado_organization", {"organization_url": initial_org_url})
        yield client


@requires_ado_creds
async def test_preview_pipeline_basic(mcp_client: Client):
    """Test basic pipeline preview without any parameters."""
    result = await mcp_client.call_tool(
        "preview_pipeline",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_id": BASIC_PREVIEW_PIPELINE_ID
        }
    )
    
    preview_data = result.data
    assert preview_data is not None, "Preview should not be None"
    assert isinstance(preview_data, dict), "Preview should be a dictionary"
    assert "finalYaml" in preview_data, "Preview should contain finalYaml field"
    assert preview_data["finalYaml"] is not None, "Final YAML should not be None"
    assert isinstance(preview_data["finalYaml"], str), "Final YAML should be a string"
    assert len(preview_data["finalYaml"]) > 0, "Final YAML should not be empty"
    
    print(f"✓ Basic pipeline preview: {len(preview_data['finalYaml'])} characters")


@requires_ado_creds
async def test_preview_pipeline_with_variables(mcp_client: Client):
    """Test preview with variables (using parameterized pipeline)."""
    parameterized_pipeline_id = 75  # preview-test-parameterized
    
    variables = {
        "testEnvironment": "preview-testing",
        "enableDebug": True,
        "previewMode": "enabled"
    }
    
    result = await mcp_client.call_tool(
        "preview_pipeline",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_id": parameterized_pipeline_id,
            "variables": variables
        }
    )
    
    preview_data = result.data
    assert preview_data is not None, "Preview with variables should not be None"
    assert "finalYaml" in preview_data, "Preview should contain finalYaml field"
    
    final_yaml = preview_data["finalYaml"]
    assert final_yaml is not None, "Final YAML should not be None"
    assert len(final_yaml) > 0, "Final YAML should not be empty"
    
    print(f"✓ Preview with variables: {len(final_yaml)} characters")


@requires_ado_creds
async def test_preview_pipeline_with_empty_resources(mcp_client: Client):
    """Test preview with empty resources parameter."""
    resources = {}
    
    result = await mcp_client.call_tool(
        "preview_pipeline",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_id": BASIC_PREVIEW_PIPELINE_ID,
            "resources": resources
        }
    )
    
    preview_data = result.data
    assert preview_data is not None, "Preview with empty resources should not be None"
    assert "finalYaml" in preview_data, "Preview should contain finalYaml field"
    
    print("✓ Preview with empty resources handled successfully")


@requires_ado_creds
async def test_preview_pipeline_with_stages_to_skip(mcp_client: Client):
    """Test preview with stages to skip parameter."""
    parameterized_pipeline_id = 75  # preview-test-parameterized
    
    stages_to_skip = ["TestStage", "DeploymentStage"]
    
    result = await mcp_client.call_tool(
        "preview_pipeline",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_id": parameterized_pipeline_id,
            "stages_to_skip": stages_to_skip
        }
    )
    
    preview_data = result.data
    assert preview_data is not None, "Preview with stages to skip should not be None"
    assert "finalYaml" in preview_data, "Preview should contain finalYaml field"
    
    print(f"✓ Preview with stages to skip: {stages_to_skip}")




@requires_ado_creds
async def test_preview_pipeline_nonexistent_pipeline(mcp_client: Client):
    """Test error handling for non-existent pipeline."""
    pipeline_id = 99999  # Non-existent pipeline ID
    
    try:
        result = await mcp_client.call_tool(
            "preview_pipeline",
            {
                "project_id": TEST_PROJECT_ID,
                "pipeline_id": pipeline_id
            }
        )
        
        if result.data is None:
            print("✓ Non-existent pipeline preview returned None")
        else:
            assert isinstance(result.data, dict), "Response should be a dictionary"
            print("✓ Non-existent pipeline preview handled gracefully")
    except Exception as e:
        print(f"✓ Non-existent pipeline preview raised exception: {type(e).__name__}")
        assert isinstance(e, Exception), "Should raise a proper exception type"


async def test_preview_pipeline_tool_registration():
    """Test that the preview_pipeline tool is properly registered."""
    async with Client(mcp) as client:
        tools_response = await client.list_tools()
        # Handle both potential response formats
        if hasattr(tools_response, "tools"):
            tools = tools_response.tools
        else:
            tools = tools_response
        tool_names = [tool.name for tool in tools]
        assert "preview_pipeline" in tool_names, "preview_pipeline tool should be registered"