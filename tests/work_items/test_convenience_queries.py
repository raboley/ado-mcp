"""Tests for work item convenience query tools like get_my_work_items and get_recent_work_items."""

import os
import pytest
from datetime import datetime, timedelta
from fastmcp.client import Client

from server import mcp
from tests.ado.test_client import requires_ado_creds

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def client():
    """Create MCP client for testing."""
    async with Client(mcp) as client:
        yield client


@pytest.fixture
def project_id():
    """Test project ID."""
    return "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project


def get_current_user_email():
    """Get current user email from environment or use test default."""
    # Try to get from environment, fall back to a test user
    return os.environ.get("AZURE_DEVOPS_USER_EMAIL", "raboley@gmail.com")


@requires_ado_creds
async def test_get_my_work_items_tool_registration(client):
    """Verify get_my_work_items tool is registered in MCP server"""
    tools_response = await client.list_tools()
    if hasattr(tools_response, "tools"):
        tools = tools_response.tools
    else:
        tools = tools_response
    tool_names = [tool.name for tool in tools]
    
    assert "get_my_work_items" in tool_names, f"get_my_work_items should be registered but found: {tool_names}"


@requires_ado_creds
async def test_get_recent_work_items_tool_registration(client):
    """Verify get_recent_work_items tool is registered in MCP server"""
    tools_response = await client.list_tools()
    if hasattr(tools_response, "tools"):
        tools = tools_response.tools
    else:
        tools = tools_response
    tool_names = [tool.name for tool in tools]
    
    assert "get_recent_work_items" in tool_names, f"get_recent_work_items should be registered but found: {tool_names}"


@requires_ado_creds
async def test_get_my_work_items_basic_functionality(client, project_id):
    """Test basic functionality of get_my_work_items tool"""
    current_user = get_current_user_email()
    
    # Create a test work item assigned to current user
    create_result = await client.call_tool("create_work_item", {
        "project_id": project_id,
        "work_item_type": "Task",
        "title": "Test work item for get_my_work_items",
        "assigned_to": current_user
    })
    
    assert create_result.is_error is False, f"Should create work item successfully but got error: {create_result.content}"
    work_item_id = create_result.data["id"]
    
    try:
        # Test get_my_work_items
        result = await client.call_tool("get_my_work_items", {
            "project_id": project_id,
            "assigned_to": current_user
        })
        
        assert result.is_error is False, f"Should get my work items successfully but got error: {result.content}"
        assert "work_items" in result.data, f"Result should contain work_items but got: {result.data.keys()}"
        assert "pagination" in result.data, f"Result should contain pagination but got: {result.data.keys()}"
        assert "assignment_info" in result.data, f"Result should contain assignment_info but got: {result.data.keys()}"
        
        # Verify assignment info
        assignment_info = result.data["assignment_info"]
        assert assignment_info["assigned_to"] == current_user, f"Should filter by current user but got: {assignment_info['assigned_to']}"
        
        # Find our created work item
        work_item_ids = [item["id"] for item in result.data["work_items"]]
        assert work_item_id in work_item_ids, f"Should find our created work item {work_item_id} in results: {work_item_ids}"
        
    finally:
        # Clean up
        await client.call_tool("delete_work_item", {
            "project_id": project_id,
            "work_item_id": work_item_id
        })


@requires_ado_creds
async def test_get_my_work_items_with_filters(client, project_id):
    """Test get_my_work_items with state and type filters"""
    current_user = get_current_user_email()
    
    # Create two test work items
    bug_result = await client.call_tool("create_work_item", {
        "project_id": project_id,
        "work_item_type": "Bug",
        "title": "Test bug for filtering",
        "assigned_to": current_user,
        "state": "New"
    })
    
    task_result = await client.call_tool("create_work_item", {
        "project_id": project_id,
        "work_item_type": "Task", 
        "title": "Test task for filtering",
        "assigned_to": current_user,
        "state": "Active"
    })
    
    assert bug_result.is_error is False, f"Should create bug successfully but got error: {bug_result.content}"
    assert task_result.is_error is False, f"Should create task successfully but got error: {task_result.content}"
    
    bug_id = bug_result.data["id"]
    task_id = task_result.data["id"]
    
    try:
        # Test filtering by work item type
        bugs_result = await client.call_tool("get_my_work_items", {
            "project_id": project_id,
            "assigned_to": current_user,
            "work_item_type": "Bug"
        })
        
        assert bugs_result.is_error is False, f"Should get bugs successfully but got error: {bugs_result.content}"
        bug_ids = [item["id"] for item in bugs_result.data["work_items"]]
        assert bug_id in bug_ids, f"Should find bug {bug_id} in filtered results: {bug_ids}"
        
        # Verify assignment info includes filters
        assignment_info = bugs_result.data["assignment_info"]
        assert assignment_info["type_filter"] == "Bug", f"Should show Bug filter but got: {assignment_info['type_filter']}"
        
        # Test filtering by state
        new_items_result = await client.call_tool("get_my_work_items", {
            "project_id": project_id,
            "assigned_to": current_user,
            "state": "New"
        })
        
        assert new_items_result.is_error is False, f"Should get new items successfully but got error: {new_items_result.content}"
        new_item_ids = [item["id"] for item in new_items_result.data["work_items"]]
        assert bug_id in new_item_ids, f"Should find bug {bug_id} in new items: {new_item_ids}"
        
        # Verify state filter info
        assignment_info = new_items_result.data["assignment_info"]
        assert assignment_info["state_filter"] == "New", f"Should show New state filter but got: {assignment_info['state_filter']}"
        
    finally:
        # Clean up
        await client.call_tool("delete_work_item", {"project_id": project_id, "work_item_id": bug_id})
        await client.call_tool("delete_work_item", {"project_id": project_id, "work_item_id": task_id})


@requires_ado_creds
async def test_get_recent_work_items_basic_functionality(client, project_id):
    """Test basic functionality of get_recent_work_items tool"""
    # Create a test work item that should appear in recent items
    create_result = await client.call_tool("create_work_item", {
        "project_id": project_id,
        "work_item_type": "Task",
        "title": "Test work item for get_recent_work_items"
    })
    
    assert create_result.is_error is False, f"Should create work item successfully but got error: {create_result.content}"
    work_item_id = create_result.data["id"]
    
    try:
        # Test get_recent_work_items with default 7 days
        result = await client.call_tool("get_recent_work_items", {
            "project_id": project_id
        })
        
        assert result.is_error is False, f"Should get recent work items successfully but got error: {result.content}"
        assert "work_items" in result.data, f"Result should contain work_items but got: {result.data.keys()}"
        assert "pagination" in result.data, f"Result should contain pagination but got: {result.data.keys()}"
        assert "time_filter" in result.data, f"Result should contain time_filter but got: {result.data.keys()}"
        
        # Verify time filter info
        time_filter = result.data["time_filter"]
        assert time_filter["days"] == 7, f"Should default to 7 days but got: {time_filter['days']}"
        assert "start_date" in time_filter, f"Should have start_date but got: {time_filter.keys()}"
        assert "end_date" in time_filter, f"Should have end_date but got: {time_filter.keys()}"
        
        # Find our created work item (should be very recent)
        work_item_ids = [item["id"] for item in result.data["work_items"]]
        assert work_item_id in work_item_ids, f"Should find our recently created work item {work_item_id} in results: {work_item_ids}"
        
    finally:
        # Clean up
        await client.call_tool("delete_work_item", {
            "project_id": project_id,
            "work_item_id": work_item_id
        })


@requires_ado_creds
async def test_get_recent_work_items_with_custom_days(client, project_id):
    """Test get_recent_work_items with custom days parameter"""
    # Create a test work item
    create_result = await client.call_tool("create_work_item", {
        "project_id": project_id,
        "work_item_type": "Bug",
        "title": "Test recent bug with custom days"
    })
    
    assert create_result.is_error is False, f"Should create work item successfully but got error: {create_result.content}"
    work_item_id = create_result.data["id"]
    
    try:
        # Test with 1 day (should include our just-created item)
        result = await client.call_tool("get_recent_work_items", {
            "project_id": project_id,
            "days": 1,
            "work_item_type": "Bug"
        })
        
        assert result.is_error is False, f"Should get recent work items successfully but got error: {result.content}"
        
        # Verify time filter shows custom days
        time_filter = result.data["time_filter"]
        assert time_filter["days"] == 1, f"Should use 1 day but got: {time_filter['days']}"
        assert time_filter["type_filter"] == "Bug", f"Should filter by Bug type but got: {time_filter['type_filter']}"
        
        # Should find our recently created bug
        work_item_ids = [item["id"] for item in result.data["work_items"]]
        assert work_item_id in work_item_ids, f"Should find our recently created bug {work_item_id} in results: {work_item_ids}"
        
    finally:
        # Clean up
        await client.call_tool("delete_work_item", {
            "project_id": project_id,
            "work_item_id": work_item_id
        })


@requires_ado_creds
async def test_get_recent_work_items_with_state_filter(client, project_id):
    """Test get_recent_work_items with state filter"""
    # Create test work items with different states
    new_item_result = await client.call_tool("create_work_item", {
        "project_id": project_id,
        "work_item_type": "Task",
        "title": "New task for state filtering",
        "state": "New"
    })
    
    assert new_item_result.is_error is False, f"Should create new task successfully but got error: {new_item_result.content}"
    new_item_id = new_item_result.data["id"]
    
    try:
        # Test filtering by state = "New"
        result = await client.call_tool("get_recent_work_items", {
            "project_id": project_id,
            "state": "New",
            "days": 1
        })
        
        assert result.is_error is False, f"Should get recent new items successfully but got error: {result.content}"
        
        # Verify state filter
        time_filter = result.data["time_filter"]
        assert time_filter["state_filter"] == "New", f"Should filter by New state but got: {time_filter['state_filter']}"
        
        # Should find our new item
        work_item_ids = [item["id"] for item in result.data["work_items"]]
        assert new_item_id in work_item_ids, f"Should find our new item {new_item_id} in results: {work_item_ids}"
        
    finally:
        # Clean up
        await client.call_tool("delete_work_item", {
            "project_id": project_id,
            "work_item_id": new_item_id
        })


@requires_ado_creds
async def test_get_recent_work_items_pagination(client, project_id):
    """Test pagination in get_recent_work_items"""
    # Test with small page size
    result = await client.call_tool("get_recent_work_items", {
        "project_id": project_id,
        "page_size": 2,
        "page_number": 1
    })
    
    assert result.is_error is False, f"Should get recent work items with pagination successfully but got error: {result.content}"
    
    # Verify pagination metadata
    pagination = result.data["pagination"]
    assert pagination["page_number"] == 1, f"Should be on page 1 but got: {pagination['page_number']}"
    assert pagination["page_size"] == 2, f"Should have page size 2 but got: {pagination['page_size']}"
    assert pagination["items_count"] <= 2, f"Should have at most 2 items but got: {pagination['items_count']}"
    assert "has_more" in pagination, f"Should have has_more field but got: {pagination.keys()}"
    assert "has_previous" in pagination, f"Should have has_previous field but got: {pagination.keys()}"


@requires_ado_creds
async def test_convenience_tools_error_handling(client):
    """Test error handling in convenience tools"""
    # Test with invalid project
    with pytest.raises(Exception) as exc_info:
        await client.call_tool("get_my_work_items", {
            "project_id": "00000000-0000-0000-0000-000000000000",
            "assigned_to": "test@example.com"
        })
    
    assert "400" in str(exc_info.value) or "not found" in str(exc_info.value).lower(), f"Should get bad request error but got: {exc_info.value}"
    
    # Test get_recent_work_items with invalid project
    with pytest.raises(Exception) as exc_info:
        await client.call_tool("get_recent_work_items", {
            "project_id": "00000000-0000-0000-0000-000000000000"
        })
    
    assert "400" in str(exc_info.value) or "not found" in str(exc_info.value).lower(), f"Should get bad request error but got: {exc_info.value}"