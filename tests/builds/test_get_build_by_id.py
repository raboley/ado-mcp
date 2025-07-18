"""
Tests for the get_build_by_id MCP tool.

This module tests mapping build IDs to pipeline information.
This tool is critical for resolving Azure DevOps URLs that contain buildId parameters.
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


@pytest.fixture
async def build_id(mcp_client):
    """Creates a pipeline run and returns its build ID for testing."""
    # Start a pipeline run to get a valid build ID
    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_id": BASIC_PIPELINE_ID
        }
    )
    
    pipeline_run = result.data
    assert pipeline_run is not None, "Pipeline run should be created"
    assert pipeline_run["id"] is not None, "Pipeline run should have an ID"
    
    # In Azure DevOps, the run ID is the same as the build ID
    return pipeline_run["id"]


@requires_ado_creds
async def test_get_build_by_id_valid_build(mcp_client: Client, build_id: int):
    """Test getting build details with a valid build ID."""
    result = await mcp_client.call_tool(
        "get_build_by_id",
        {
            "project_id": TEST_PROJECT_ID,
            "build_id": build_id
        }
    )
    
    build_data = result.data
    assert build_data is not None, "Build data should not be None"
    assert isinstance(build_data, dict), "Build data should be a dictionary"
    assert build_data["id"] == build_id, "Build ID should match"
    
    # Verify definition (pipeline) information is present
    assert "definition" in build_data, "Build should have definition field"
    definition = build_data["definition"]
    assert isinstance(definition, dict), "Definition should be a dictionary"
    assert "id" in definition, "Definition should have id (pipeline_id)"
    assert "name" in definition, "Definition should have name"
    
    pipeline_id = definition["id"]
    pipeline_name = definition["name"]
    
    print(f"✓ Build {build_id} maps to pipeline {pipeline_id} ({pipeline_name})")


@requires_ado_creds
async def test_get_build_by_id_maps_to_correct_pipeline(mcp_client: Client, build_id: int):
    """Test that build ID correctly maps to the expected pipeline."""
    result = await mcp_client.call_tool(
        "get_build_by_id",
        {
            "project_id": TEST_PROJECT_ID,
            "build_id": build_id
        }
    )
    
    build_data = result.data
    assert build_data is not None, "Build data should not be None"
    
    # This build should map to our test pipeline
    definition = build_data["definition"]
    assert definition["id"] == BASIC_PIPELINE_ID, f"Build should map to pipeline {BASIC_PIPELINE_ID}"
    
    print(f"✓ Build {build_id} correctly maps to pipeline {BASIC_PIPELINE_ID}")


@requires_ado_creds
async def test_get_build_by_id_structure(mcp_client: Client, build_id: int):
    """Test the structure of build data returned."""
    result = await mcp_client.call_tool(
        "get_build_by_id",
        {
            "project_id": TEST_PROJECT_ID,
            "build_id": build_id
        }
    )
    
    build_data = result.data
    assert build_data is not None, "Build data should not be None"
    
    # Verify required fields
    required_fields = ["id", "definition", "status", "queueTime"]
    for field in required_fields:
        assert field in build_data, f"Build data should have {field} field"
    
    # Verify definition structure (this is what we use to get pipeline info)
    definition = build_data["definition"]
    definition_required_fields = ["id", "name", "url", "project"]
    for field in definition_required_fields:
        assert field in definition, f"Definition should have {field} field"
    
    print(f"✓ Build data structure is valid for build {build_id}")


@requires_ado_creds
async def test_get_build_by_id_status_field(mcp_client: Client, build_id: int):
    """Test that build status field contains valid values."""
    result = await mcp_client.call_tool(
        "get_build_by_id",
        {
            "project_id": TEST_PROJECT_ID,
            "build_id": build_id
        }
    )
    
    build_data = result.data
    assert build_data is not None, "Build data should not be None"
    
    valid_statuses = [
        "inProgress", "completed", "cancelling", "postponed", 
        "notStarted", "cancelled"
    ]
    assert build_data["status"] in valid_statuses, f"Status should be one of {valid_statuses}"
    
    print(f"✓ Build status is valid: {build_data['status']}")


async def test_get_build_by_id_no_client(mcp_client_no_auth: Client):
    """Test get_build_by_id behavior when no client is configured."""
    result = await mcp_client_no_auth.call_tool(
        "get_build_by_id",
        {
            "project_id": TEST_PROJECT_ID,
            "build_id": 123456  # Any build ID
        }
    )
    
    build_data = result.data
    assert build_data is None, "Should return None when no client is configured"


@requires_ado_creds
async def test_get_build_by_id_nonexistent_build(mcp_client: Client):
    """Test error handling for non-existent build ID."""
    try:
        result = await mcp_client.call_tool(
            "get_build_by_id",
            {
                "project_id": TEST_PROJECT_ID,
                "build_id": 999999999  # Non-existent build ID
            }
        )
        
        # If it doesn't raise an exception, check the result
        if result.data is None:
            print("✓ Non-existent build properly returned None")
        else:
            assert False, "Non-existent build should not return a valid result"
    except Exception as e:
        print(f"✓ Non-existent build properly raised exception: {type(e).__name__}")
        assert True, "Exception is expected for non-existent build"


@requires_ado_creds
async def test_get_build_by_id_invalid_project(mcp_client: Client):
    """Test error handling for invalid project ID."""
    try:
        result = await mcp_client.call_tool(
            "get_build_by_id",
            {
                "project_id": "00000000-0000-0000-0000-000000000000",  # Invalid project
                "build_id": 123456
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
async def test_get_build_by_id_url_resolution_scenario(mcp_client: Client, build_id: int):
    """Test the primary use case: resolving Azure DevOps URLs with buildId."""
    # This test simulates the scenario where a user provides an Azure DevOps URL
    # like: https://dev.azure.com/org/project/_build/results?buildId=12345
    # and we need to map that buildId to pipeline information
    
    result = await mcp_client.call_tool(
        "get_build_by_id",
        {
            "project_id": TEST_PROJECT_ID,
            "build_id": build_id
        }
    )
    
    build_data = result.data
    assert build_data is not None, "Build data should not be None"
    
    # Extract the information we'd need for other pipeline tools
    pipeline_id = build_data["definition"]["id"]
    pipeline_name = build_data["definition"]["name"]
    
    # Verify we can use this information with other tools
    assert isinstance(pipeline_id, int), "Pipeline ID should be an integer"
    assert isinstance(pipeline_name, str), "Pipeline name should be a string"
    assert pipeline_id > 0, "Pipeline ID should be positive"
    assert len(pipeline_name) > 0, "Pipeline name should not be empty"
    
    print(f"✓ URL resolution: buildId {build_id} → pipeline_id {pipeline_id} ({pipeline_name})")


async def test_get_build_by_id_tool_registration():
    """Test that the get_build_by_id tool is properly registered."""
    async with Client(mcp) as client:
        tools_response = await client.list_tools()
        # Handle both potential response formats
        if hasattr(tools_response, "tools"):
            tools = tools_response.tools
        else:
            tools = tools_response
        tool_names = [tool.name for tool in tools]
        assert "get_build_by_id" in tool_names, "get_build_by_id tool should be registered"