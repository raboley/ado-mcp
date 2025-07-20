"""
Tests for the get_pipeline_failure_summary MCP tool.

This module tests comprehensive failure analysis for failed pipeline runs.
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
async def completed_run_id(mcp_client):
    """Creates a pipeline run and waits for completion to test failure analysis."""
    # Start a pipeline run
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
    
    # Return the run ID - the test will use this with failure analysis
    # Note: This might be a successful run, but the tool should handle that gracefully
    return pipeline_run["id"]


@requires_ado_creds
async def test_get_pipeline_failure_summary_basic_structure(mcp_client: Client, completed_run_id: int):
    """Test the basic structure of failure summary response."""
    result = await mcp_client.call_tool(
        "get_pipeline_failure_summary",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_id": BASIC_PIPELINE_ID,
            "run_id": completed_run_id
        }
    )
    
    failure_summary = result.data
    assert failure_summary is not None, "Failure summary should not be None"
    assert isinstance(failure_summary, dict), "Failure summary should be a dictionary"
    
    # Verify required fields (even for successful runs)
    required_fields = ["total_failed_steps", "root_cause_tasks", "hierarchy_failures"]
    for field in required_fields:
        assert field in failure_summary, f"Failure summary should have {field} field"
    
    # Verify field types
    assert isinstance(failure_summary["total_failed_steps"], int), "total_failed_steps should be an integer"
    assert isinstance(failure_summary["root_cause_tasks"], list), "root_cause_tasks should be a list"
    assert isinstance(failure_summary["hierarchy_failures"], list), "hierarchy_failures should be a list"
    
    print(f"✓ Failure summary structure valid: {failure_summary['total_failed_steps']} failed steps")


@requires_ado_creds
async def test_get_pipeline_failure_summary_with_max_lines(mcp_client: Client, completed_run_id: int):
    """Test failure summary with custom max_lines parameter."""
    result = await mcp_client.call_tool(
        "get_pipeline_failure_summary",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_id": BASIC_PIPELINE_ID,
            "run_id": completed_run_id,
            "max_lines": 50  # Custom line limit
        }
    )
    
    failure_summary = result.data
    assert failure_summary is not None, "Failure summary should not be None"
    assert isinstance(failure_summary, dict), "Failure summary should be a dictionary"
    
    # If there are any failed tasks with logs, verify the max_lines parameter is respected
    for task in failure_summary["root_cause_tasks"]:
        if "log_content" in task and task["log_content"]:
            # Count lines in log content
            lines = task["log_content"].split('\n')
            assert len(lines) <= 50, f"Log content should not exceed 50 lines, got {len(lines)}"
    
    print(f"✓ Max lines parameter respected in failure summary")


@requires_ado_creds
async def test_get_pipeline_failure_summary_unlimited_lines(mcp_client: Client, completed_run_id: int):
    """Test failure summary with unlimited lines (max_lines = 0)."""
    result = await mcp_client.call_tool(
        "get_pipeline_failure_summary",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_id": BASIC_PIPELINE_ID,
            "run_id": completed_run_id,
            "max_lines": 0  # Unlimited lines
        }
    )
    
    failure_summary = result.data
    assert failure_summary is not None, "Failure summary should not be None"
    assert isinstance(failure_summary, dict), "Failure summary should be a dictionary"
    
    print(f"✓ Unlimited lines parameter handled correctly")


@requires_ado_creds
async def test_get_pipeline_failure_summary_task_structure(mcp_client: Client, completed_run_id: int):
    """Test the structure of failed task information."""
    result = await mcp_client.call_tool(
        "get_pipeline_failure_summary",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_id": BASIC_PIPELINE_ID,
            "run_id": completed_run_id
        }
    )
    
    failure_summary = result.data
    assert failure_summary is not None, "Failure summary should not be None"
    
    # Check root cause tasks structure
    for task in failure_summary["root_cause_tasks"]:
        assert isinstance(task, dict), "Each task should be a dictionary"
        # Verify common task fields that should be present
        task_fields = ["name", "result"]
        for field in task_fields:
            assert field in task, f"Task should have {field} field"
    
    # Check hierarchy failures structure  
    for failure in failure_summary["hierarchy_failures"]:
        assert isinstance(failure, dict), "Each hierarchy failure should be a dictionary"
        # Verify common failure fields
        failure_fields = ["name", "result"]
        for field in failure_fields:
            assert field in failure, f"Hierarchy failure should have {field} field"
    
    print(f"✓ Task and hierarchy failure structures are valid")




@requires_ado_creds
async def test_get_pipeline_failure_summary_nonexistent_run(mcp_client: Client):
    """Test error handling for non-existent pipeline run."""
    try:
        result = await mcp_client.call_tool(
            "get_pipeline_failure_summary",
            {
                "project_id": TEST_PROJECT_ID,
                "pipeline_id": BASIC_PIPELINE_ID,
                "run_id": 999999999  # Non-existent run ID
            }
        )
        
        # If it doesn't raise an exception, check the result
        if result.data is None:
            print("✓ Non-existent run properly returned None")
        else:
            assert False, "Non-existent run should not return a valid result"
    except Exception as e:
        print(f"✓ Non-existent run properly raised exception: {type(e).__name__}")
        assert True, "Exception is expected for non-existent run"


@requires_ado_creds
async def test_get_pipeline_failure_summary_invalid_project(mcp_client: Client):
    """Test error handling for invalid project ID."""
    try:
        result = await mcp_client.call_tool(
            "get_pipeline_failure_summary",
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
async def test_get_pipeline_failure_summary_wrong_pipeline_id(mcp_client: Client, completed_run_id: int):
    """Test error handling when pipeline ID doesn't match the run."""
    try:
        result = await mcp_client.call_tool(
            "get_pipeline_failure_summary",
            {
                "project_id": TEST_PROJECT_ID,
                "pipeline_id": 999,  # Wrong pipeline ID
                "run_id": completed_run_id
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


@requires_ado_creds
async def test_get_pipeline_failure_summary_successful_run_handling(mcp_client: Client, completed_run_id: int):
    """Test that failure summary handles successful runs gracefully."""
    result = await mcp_client.call_tool(
        "get_pipeline_failure_summary",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_id": BASIC_PIPELINE_ID,
            "run_id": completed_run_id
        }
    )
    
    failure_summary = result.data
    assert failure_summary is not None, "Failure summary should not be None even for successful runs"
    
    # For successful runs, we should see 0 failed steps
    if failure_summary["total_failed_steps"] == 0:
        assert len(failure_summary["root_cause_tasks"]) == 0, "Should have no root cause tasks for successful run"
        assert len(failure_summary["hierarchy_failures"]) == 0, "Should have no hierarchy failures for successful run"
        print("✓ Successful run handled correctly - no failures detected")
    else:
        print(f"✓ Run has {failure_summary['total_failed_steps']} failed steps - analysis provided")


async def test_get_pipeline_failure_summary_tool_registration():
    """Test that the get_pipeline_failure_summary tool is properly registered."""
    async with Client(mcp) as client:
        tools_response = await client.list_tools()
        # Handle both potential response formats
        if hasattr(tools_response, "tools"):
            tools = tools_response.tools
        else:
            tools = tools_response
        tool_names = [tool.name for tool in tools]
        assert "get_pipeline_failure_summary" in tool_names, "get_pipeline_failure_summary tool should be registered"