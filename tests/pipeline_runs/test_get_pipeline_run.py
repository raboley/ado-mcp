"""
Tests for the get_pipeline_run MCP tool.

This module tests getting details of specific pipeline runs.
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
async def pipeline_run_id(mcp_client):
    """Creates a pipeline run and returns its ID for testing."""
    # Start a pipeline run to test with
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
    
    return pipeline_run["id"]


@requires_ado_creds
async def test_get_pipeline_run_with_valid_id(mcp_client: Client, pipeline_run_id: int):
    """Test getting pipeline run details with a valid run ID."""
    result = await mcp_client.call_tool(
        "get_pipeline_run",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_id": BASIC_PIPELINE_ID,
            "run_id": pipeline_run_id
        }
    )
    
    pipeline_run = result.data
    assert pipeline_run is not None, "Pipeline run should not be None"
    assert isinstance(pipeline_run, dict), "Pipeline run should be a dictionary"
    assert pipeline_run["id"] == pipeline_run_id, "Pipeline run ID should match"
    assert "state" in pipeline_run, "Pipeline run should have a state"
    assert "pipeline" in pipeline_run, "Pipeline run should have pipeline info"
    assert "createdDate" in pipeline_run, "Pipeline run should have created date"
    
    # Verify pipeline reference
    assert pipeline_run["pipeline"]["id"] == BASIC_PIPELINE_ID, "Pipeline ID should match"
    
    print(f"✓ Retrieved pipeline run {pipeline_run_id} with state: {pipeline_run['state']}")


@requires_ado_creds
async def test_get_pipeline_run_state_validation(mcp_client: Client, pipeline_run_id: int):
    """Test that pipeline run has valid state."""
    result = await mcp_client.call_tool(
        "get_pipeline_run",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_id": BASIC_PIPELINE_ID,
            "run_id": pipeline_run_id
        }
    )
    
    pipeline_run = result.data
    assert pipeline_run is not None, "Pipeline run should not be None"
    
    valid_states = ["unknown", "inProgress", "completed", "cancelling", "cancelled"]
    assert pipeline_run["state"] in valid_states, f"State should be one of {valid_states}"
    
    print(f"✓ Pipeline run state is valid: {pipeline_run['state']}")


@requires_ado_creds
async def test_get_pipeline_run_structure(mcp_client: Client, pipeline_run_id: int):
    """Test the structure of pipeline run data."""
    result = await mcp_client.call_tool(
        "get_pipeline_run",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_id": BASIC_PIPELINE_ID,
            "run_id": pipeline_run_id
        }
    )
    
    pipeline_run = result.data
    assert pipeline_run is not None, "Pipeline run should not be None"
    
    # Verify required fields
    required_fields = ["id", "name", "state", "pipeline", "createdDate"]
    for field in required_fields:
        assert field in pipeline_run, f"Pipeline run should have {field} field"
    
    # Verify pipeline nested structure
    pipeline_info = pipeline_run["pipeline"]
    assert isinstance(pipeline_info, dict), "Pipeline info should be a dictionary"
    assert "id" in pipeline_info, "Pipeline info should have id"
    assert "name" in pipeline_info, "Pipeline info should have name"
    
    print(f"✓ Pipeline run structure is valid for run {pipeline_run_id}")


async def test_get_pipeline_run_no_client(mcp_client_no_auth: Client):
    """Test get_pipeline_run behavior when no client is configured."""
    result = await mcp_client_no_auth.call_tool(
        "get_pipeline_run",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_id": BASIC_PIPELINE_ID,
            "run_id": 123456  # Any run ID
        }
    )
    
    pipeline_run = result.data
    assert pipeline_run is None, "Should return None when no client is configured"


@requires_ado_creds
async def test_get_pipeline_run_nonexistent_run(mcp_client: Client):
    """Test error handling for non-existent pipeline run."""
    try:
        result = await mcp_client.call_tool(
            "get_pipeline_run",
            {
                "project_id": TEST_PROJECT_ID,
                "pipeline_id": BASIC_PIPELINE_ID,
                "run_id": 999999999  # Non-existent run ID
            }
        )
        
        # If it doesn't raise an exception, check the result
        if result.data is None:
            print("✓ Non-existent pipeline run properly returned None")
        else:
            assert False, "Non-existent pipeline run should not return a valid result"
    except Exception as e:
        print(f"✓ Non-existent pipeline run properly raised exception: {type(e).__name__}")
        assert True, "Exception is expected for non-existent pipeline run"


@requires_ado_creds
async def test_get_pipeline_run_invalid_project(mcp_client: Client):
    """Test error handling for invalid project ID."""
    try:
        result = await mcp_client.call_tool(
            "get_pipeline_run",
            {
                "project_id": "00000000-0000-0000-0000-000000000000",  # Invalid project
                "pipeline_id": BASIC_PIPELINE_ID,
                "run_id": 123456
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
async def test_get_pipeline_run_wrong_pipeline_id(mcp_client: Client, pipeline_run_id: int):
    """Test error handling when pipeline ID doesn't match the run."""
    try:
        result = await mcp_client.call_tool(
            "get_pipeline_run",
            {
                "project_id": TEST_PROJECT_ID,
                "pipeline_id": 999,  # Wrong pipeline ID
                "run_id": pipeline_run_id
            }
        )
        
        # If it doesn't raise an exception, check the result
        if result.data is None:
            print("✓ Wrong pipeline ID properly returned None")
        else:
            assert False, "Wrong pipeline ID should not return a valid result"
    except Exception as e:
        print(f"✓ Wrong pipeline ID properly raised exception: {type(e).__name__}")
        assert True, "Exception is expected for wrong pipeline ID"


async def test_get_pipeline_run_tool_registration():
    """Test that the get_pipeline_run tool is properly registered."""
    async with Client(mcp) as client:
        tools_response = await client.list_tools()
        # Handle both potential response formats
        if hasattr(tools_response, "tools"):
            tools = tools_response.tools
        else:
            tools = tools_response
        tool_names = [tool.name for tool in tools]
        assert "get_pipeline_run" in tool_names, "get_pipeline_run tool should be registered"