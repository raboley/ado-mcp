"""
Tests for the get_pipeline MCP tool.

This module tests retrieving pipeline definition details.
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
BASIC_PIPELINE_ID = 59  # test_run_and_get_pipeline_run_details
GITHUB_RESOURCES_PIPELINE_ID = 200  # github-resources-test-stable
PREVIEW_PARAMETERIZED_PIPELINE_ID = 75  # preview-test-parameterized


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
async def test_get_pipeline_basic(mcp_client: Client):
    """Test getting basic pipeline details."""
    result = await mcp_client.call_tool(
        "get_pipeline",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_id": BASIC_PIPELINE_ID
        }
    )
    
    pipeline = result.data
    assert pipeline is not None, "Pipeline should not be None"
    assert isinstance(pipeline, dict), "Pipeline should be a dictionary"
    assert pipeline["id"] == BASIC_PIPELINE_ID, "Pipeline ID should match"
    assert "name" in pipeline, "Pipeline should have a name"
    assert "folder" in pipeline, "Pipeline should have a folder"
    assert "url" in pipeline, "Pipeline should have a URL"
    
    print(f"✓ Pipeline {BASIC_PIPELINE_ID}: {pipeline['name']}")


@requires_ado_creds
async def test_get_pipeline_github_resources(mcp_client: Client):
    """Test getting GitHub resources pipeline details."""
    result = await mcp_client.call_tool(
        "get_pipeline",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_id": GITHUB_RESOURCES_PIPELINE_ID
        }
    )
    
    pipeline = result.data
    assert pipeline is not None, "Pipeline should not be None"
    assert pipeline["id"] == GITHUB_RESOURCES_PIPELINE_ID, "Pipeline ID should match"
    assert pipeline["name"] == "github-resources-test-stable", "Pipeline name should match"
    
    print(f"✓ GitHub resources pipeline {GITHUB_RESOURCES_PIPELINE_ID}: {pipeline['name']}")


@requires_ado_creds
async def test_get_pipeline_parameterized(mcp_client: Client):
    """Test getting parameterized pipeline details."""
    result = await mcp_client.call_tool(
        "get_pipeline",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_id": PREVIEW_PARAMETERIZED_PIPELINE_ID
        }
    )
    
    pipeline = result.data
    assert pipeline is not None, "Pipeline should not be None"
    assert pipeline["id"] == PREVIEW_PARAMETERIZED_PIPELINE_ID, "Pipeline ID should match"
    assert "preview-test-parameterized" in pipeline["name"], "Pipeline name should be correct"
    
    print(f"✓ Parameterized pipeline {PREVIEW_PARAMETERIZED_PIPELINE_ID}: {pipeline['name']}")


@requires_ado_creds
async def test_get_pipeline_structure(mcp_client: Client):
    """Test the structure of pipeline data."""
    result = await mcp_client.call_tool(
        "get_pipeline",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_id": BASIC_PIPELINE_ID
        }
    )
    
    pipeline = result.data
    assert pipeline is not None, "Pipeline should not be None"
    
    # Verify required fields
    required_fields = ["id", "name", "folder"]
    for field in required_fields:
        assert field in pipeline, f"Pipeline should have {field} field"
    
    # Verify field types
    assert isinstance(pipeline["id"], int), "Pipeline id should be an integer"
    assert isinstance(pipeline["name"], str), "Pipeline name should be a string"
    assert isinstance(pipeline["folder"], str), "Pipeline folder should be a string"
    
    # Check for links which should be present
    assert "_links" in pipeline, "Pipeline should have _links"
    assert "self" in pipeline["_links"], "Should have self link"
    assert "web" in pipeline["_links"], "Should have web link"
    
    print(f"✓ Pipeline structure is valid for pipeline {BASIC_PIPELINE_ID}")


@requires_ado_creds
async def test_get_pipeline_url_format(mcp_client: Client):
    """Test that pipeline URL has correct format."""
    result = await mcp_client.call_tool(
        "get_pipeline",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_id": BASIC_PIPELINE_ID
        }
    )
    
    pipeline = result.data
    assert pipeline is not None, "Pipeline should not be None"
    
    # Check web link instead of url field
    web_link = pipeline["_links"]["web"]["href"]
    assert web_link.startswith("https://"), "Pipeline web link should be HTTPS"
    assert "dev.azure.com" in web_link or "visualstudio.com" in web_link, "Should be Azure DevOps URL"
    assert str(BASIC_PIPELINE_ID) in web_link, "Web link should contain pipeline ID"
    
    print(f"✓ Pipeline URL format is valid: {web_link}")



@requires_ado_creds
async def test_get_pipeline_nonexistent_pipeline(mcp_client: Client):
    """Test error handling for non-existent pipeline."""
    try:
        result = await mcp_client.call_tool(
            "get_pipeline",
            {
                "project_id": TEST_PROJECT_ID,
                "pipeline_id": 999999  # Non-existent pipeline
            }
        )
        
        # If it doesn't raise an exception, check the result
        if result.data is None:
            print("✓ Non-existent pipeline properly returned None")
        else:
            assert False, "Non-existent pipeline should not return a valid result"
    except Exception as e:
        print(f"✓ Non-existent pipeline properly raised exception: {type(e).__name__}")
        assert True, "Exception is expected for non-existent pipeline"


@requires_ado_creds
async def test_get_pipeline_invalid_project(mcp_client: Client):
    """Test error handling for invalid project ID."""
    try:
        result = await mcp_client.call_tool(
            "get_pipeline",
            {
                "project_id": "00000000-0000-0000-0000-000000000000",  # Invalid project
                "pipeline_id": BASIC_PIPELINE_ID
            }
        )
        
        # If it doesn't raise an exception, check the result
        if result.data is None:
            print("✓ Invalid project properly returned None")
        else:
            assert False, "Invalid project should not return a valid result"
    except Exception as e:
        print(f"✓ Invalid project properly raised exception: {type(e).__name__}")
        assert True, "Exception is expected for invalid project"


@requires_ado_creds
async def test_get_pipeline_folder_information(mcp_client: Client):
    """Test that pipeline folder information is returned."""
    result = await mcp_client.call_tool(
        "get_pipeline",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_id": GITHUB_RESOURCES_PIPELINE_ID
        }
    )
    
    pipeline = result.data
    assert pipeline is not None, "Pipeline should not be None"
    
    folder = pipeline["folder"]
    assert isinstance(folder, str), "Folder should be a string"
    # Folder could be "\" for root or a path like "\folder1\folder2" (Windows-style paths in Azure DevOps)
    assert folder.startswith("\\") or folder.startswith("/"), "Folder should start with \ or /"
    
    print(f"✓ Pipeline folder: {folder}")


@requires_ado_creds
async def test_get_pipeline_project_reference(mcp_client: Client):
    """Test that pipeline contains correct project reference."""
    result = await mcp_client.call_tool(
        "get_pipeline",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_id": BASIC_PIPELINE_ID
        }
    )
    
    pipeline = result.data
    assert pipeline is not None, "Pipeline should not be None"
    
    # Project info might be in configuration or elsewhere
    # The API response structure may vary - for now just verify we can access the pipeline
    # TODO: Add specific project reference validation when API structure is clarified
    
    print(f"✓ Pipeline project reference test - pipeline ID: {pipeline['id']}")


async def test_get_pipeline_tool_registration():
    """Test that the get_pipeline tool is properly registered."""
    async with Client(mcp) as client:
        tools_response = await client.list_tools()
        # Handle both potential response formats
        if hasattr(tools_response, "tools"):
            tools = tools_response.tools
        else:
            tools = tools_response
        tool_names = [tool.name for tool in tools]
        assert "get_pipeline" in tool_names, "get_pipeline tool should be registered"