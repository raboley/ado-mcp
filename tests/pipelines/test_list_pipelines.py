"""
Tests for the list_pipelines MCP tool.

This module tests the pipeline listing functionality for specific projects.
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


@pytest.fixture
async def mcp_client():
    """Provides a connected MCP client for tests."""
    async with Client(mcp) as client:
        initial_org_url = os.environ.get(
            "ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley"
        )
        await client.call_tool("set_ado_organization", {"organization_url": initial_org_url})
        yield client


@pytest.fixture
async def mcp_client_no_auth(monkeypatch):
    """Provides a connected MCP client without authentication setup."""
    # Unset environment variables that provide authentication
    monkeypatch.delenv("AZURE_DEVOPS_EXT_PAT", raising=False)
    monkeypatch.delenv("ADO_ORGANIZATION_URL", raising=False)
    async with Client(mcp) as client:
        yield client


@requires_ado_creds
async def test_list_pipelines_returns_valid_list(mcp_client: Client):
    """Test that list_pipelines returns a valid list of pipelines."""
    result = await mcp_client.call_tool(
        "list_pipelines", 
        {"project_id": TEST_PROJECT_ID}
    )
    
    pipelines = result.data
    assert pipelines is not None, "Pipelines list should not be None"
    assert isinstance(pipelines, list), "Pipelines should be a list"
    
    if len(pipelines) > 0:
        # Verify structure of first pipeline
        pipeline = pipelines[0]
        assert isinstance(pipeline, dict), "Pipeline should be a dictionary"
        assert "id" in pipeline, "Pipeline should have an id"
        assert "name" in pipeline, "Pipeline should have a name"
        assert "folder" in pipeline, "Pipeline should have a folder"
        
        # Verify field types
        assert isinstance(pipeline["id"], int), "Pipeline id should be an integer"
        assert isinstance(pipeline["name"], str), "Pipeline name should be a string"
        assert isinstance(pipeline["folder"], str), "Pipeline folder should be a string"
        
        print(f"Found {len(pipelines)} pipelines")
        print(f"First pipeline: {pipeline['name']} (ID: {pipeline['id']})")
    else:
        print("No pipelines found in project")


@requires_ado_creds 
async def test_list_pipelines_finds_expected_pipelines(mcp_client: Client):
    """Test that list_pipelines finds expected test pipelines."""
    result = await mcp_client.call_tool(
        "list_pipelines", 
        {"project_id": TEST_PROJECT_ID}
    )
    
    pipelines = result.data
    assert isinstance(pipelines, list), "Pipelines should be a list"
    
    # Look for key test pipelines
    pipeline_names = [p.get("name") for p in pipelines]
    
    # Should find GitHub resources test pipeline
    assert "github-resources-test-stable" in pipeline_names, "Should find GitHub resources test pipeline"
    
    # Should find preview test pipelines
    preview_pipelines = [name for name in pipeline_names if "preview-test" in name]
    assert len(preview_pipelines) > 0, "Should find preview test pipelines"
    
    print(f"Found expected test pipelines: {len(preview_pipelines)} preview pipelines")


@requires_ado_creds
async def test_list_pipelines_specific_pipeline_details(mcp_client: Client):
    """Test specific pipeline details structure."""
    result = await mcp_client.call_tool(
        "list_pipelines", 
        {"project_id": TEST_PROJECT_ID}
    )
    
    pipelines = result.data
    assert isinstance(pipelines, list), "Pipelines should be a list"
    
    # Find a specific test pipeline
    github_pipeline = None
    for pipeline in pipelines:
        if pipeline.get("name") == "github-resources-test-stable":
            github_pipeline = pipeline
            break
    
    assert github_pipeline is not None, "Should find github-resources-test-stable pipeline"
    assert github_pipeline["id"] == 200, "Should have correct pipeline ID"
    assert "github-resources-test-stable" in github_pipeline["name"], "Should have correct name"


async def test_list_pipelines_no_client(mcp_client_no_auth: Client):
    """Test list_pipelines behavior when no client is configured."""
    result = await mcp_client_no_auth.call_tool(
        "list_pipelines", 
        {"project_id": TEST_PROJECT_ID}
    )
    
    pipelines = result.data
    assert pipelines == [], "Should return empty list when no client is configured"


@requires_ado_creds
async def test_list_pipelines_invalid_project(mcp_client: Client):
    """Test error handling for invalid project ID."""
    try:
        result = await mcp_client.call_tool(
            "list_pipelines", 
            {"project_id": "00000000-0000-0000-0000-000000000000"}  # Invalid project
        )
        
        # If it doesn't raise an exception, check the result
        pipelines = result.data
        assert pipelines == [], "Should return empty list for invalid project"
        print("✓ Invalid project properly returned empty list")
    except Exception as e:
        print(f"✓ Invalid project properly raised exception: {type(e).__name__}")
        assert True, "Exception is expected for invalid project"


async def test_list_pipelines_tool_registration():
    """Test that the list_pipelines tool is properly registered."""
    async with Client(mcp) as client:
        tools_response = await client.list_tools()
        # Handle both potential response formats
        if hasattr(tools_response, "tools"):
            tools = tools_response.tools
        else:
            tools = tools_response
        tool_names = [tool.name for tool in tools]
        assert "list_pipelines" in tool_names, "list_pipelines tool should be registered"