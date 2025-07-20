"""Tests for work item CRUD operations."""

import os
import pytest
from datetime import datetime
from fastmcp.client import Client

from server import mcp
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


@pytest.fixture
def project_id():
    return "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project


@pytest.fixture
async def work_item_cleanup(mcp_client, project_id):
    """Fixture to track and cleanup created work items."""
    created_work_items = []
    
    def track_work_item(work_item_id):
        """Track a work item ID for cleanup."""
        created_work_items.append(work_item_id)
    
    # Yield the tracking function
    yield track_work_item
    
    # Cleanup all created work items
    for work_item_id in created_work_items:
        try:
            await mcp_client.call_tool("delete_work_item", {
                "project_id": project_id,
                "work_item_id": work_item_id,
                "destroy": True  # Permanently delete to avoid cluttering recycle bin
            })
        except Exception as e:
            # Don't fail the test if cleanup fails
            print(f"Warning: Failed to cleanup work item {work_item_id}: {e}")
            pass


@pytest.mark.asyncio
@requires_ado_creds
async def test_create_work_item_basic_bug(mcp_client, project_id, work_item_cleanup):
    """Test creating a basic bug work item with required fields only."""
    result = await mcp_client.call_tool("create_work_item", {
        "project_id": project_id,
        "work_item_type": "Bug", 
        "title": "Test bug from MCP server"
    })
    
    assert result.data is not None, "Work item creation should return data"
    work_item = result.data
    work_item_id = work_item["id"]
    
    # Track for cleanup
    work_item_cleanup(work_item_id)
    
    assert work_item_id is not None, f"Work item should have an ID but got: {work_item}"
    assert work_item["fields"]["System.Title"] == "Test bug from MCP server", f"Title should match but got: {work_item['fields'].get('System.Title')}"
    assert work_item["fields"]["System.WorkItemType"] == "Bug", f"Work item type should be Bug but got: {work_item['fields'].get('System.WorkItemType')}"
    assert work_item["fields"]["System.State"] in ["New", "Active"], f"State should be New or Active but got: {work_item['fields'].get('System.State')}"


@pytest.mark.asyncio
@requires_ado_creds
async def test_create_work_item_with_all_fields(mcp_client, project_id, work_item_cleanup):
    """Test creating a work item with all common fields populated."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    title = f"Test task with full fields {timestamp}"
    
    result = await mcp_client.call_tool("create_work_item", {
        "project_id": project_id,
        "work_item_type": "Task",
        "title": title,
        "description": "This is a test task created with all fields populated",
        "tags": "test; automation; mcp",
        "additional_fields": {
            "Microsoft.VSTS.Common.Activity": "Development"
        }
    })
    
    assert result.data is not None, "Work item creation should return data"
    work_item = result.data
    work_item_id = work_item["id"]
    
    # Track for cleanup
    work_item_cleanup(work_item_id)
    
    assert work_item_id is not None, f"Work item should have an ID but got: {work_item}"
    assert work_item["fields"]["System.Title"] == title, f"Title should match but got: {work_item['fields'].get('System.Title')}"
    assert work_item["fields"]["System.WorkItemType"] == "Task", f"Work item type should be Task but got: {work_item['fields'].get('System.WorkItemType')}"
    assert work_item["fields"]["System.Description"] == "This is a test task created with all fields populated", f"Description should match but got: {work_item['fields'].get('System.Description')}"
    # Priority field removed as it doesn't exist for Task work items in this project
    # Tags get reordered by Azure DevOps, so check they contain the expected tags
    tags = work_item["fields"]["System.Tags"]
    assert "test" in tags and "automation" in tags and "mcp" in tags, f"Tags should contain test, automation, and mcp but got: {tags}"
    assert work_item["fields"]["Microsoft.VSTS.Common.Activity"] == "Development", f"Activity should be Development but got: {work_item['fields'].get('Microsoft.VSTS.Common.Activity')}"


@pytest.mark.asyncio
@requires_ado_creds
async def test_create_work_item_validation_only(mcp_client, project_id, work_item_cleanup):
    """Test creating a work item with validation only mode."""
    result = await mcp_client.call_tool("create_work_item", {
        "project_id": project_id,
        "work_item_type": "User Story",
        "title": "Test validation only story",
        "validate_only": True
    })
    
    assert result.data is not None, "Validation should return data"
    # Validation mode returns the would-be work item structure but without actual creation


@pytest.mark.asyncio
@requires_ado_creds
async def test_get_work_item_basic(mcp_client, project_id, work_item_cleanup):
    """Test retrieving a work item by ID."""
    # First create a work item
    create_result = await mcp_client.call_tool("create_work_item", {
        "project_id": project_id,
        "work_item_type": "Bug",
        "title": "Test bug for retrieval"
    })
    
    work_item_id = create_result.data["id"]
    
    # Track for cleanup
    work_item_cleanup(work_item_id)
    
    # Now retrieve it
    get_result = await mcp_client.call_tool("get_work_item", {
        "project_id": project_id,
        "work_item_id": work_item_id
    })
    
    assert get_result.data is not None, "Work item retrieval should return data"
    work_item = get_result.data
    
    assert work_item["id"] == work_item_id, f"Retrieved work item ID should match created ID. Expected {work_item_id} but got {work_item['id']}"
    assert work_item["fields"]["System.Title"] == "Test bug for retrieval", f"Title should match but got: {work_item['fields'].get('System.Title')}"


@pytest.mark.asyncio
@requires_ado_creds
async def test_get_work_item_with_specific_fields(mcp_client, project_id, work_item_cleanup):
    """Test retrieving a work item with specific fields only."""
    # First create a work item
    create_result = await mcp_client.call_tool("create_work_item", {
        "project_id": project_id,
        "work_item_type": "Task",
        "title": "Test task for field filtering",
        "description": "This should not be returned in filtered result"
    })
    
    work_item_id = create_result.data["id"]
    
    # Track for cleanup
    work_item_cleanup(work_item_id)
    
    # Retrieve with specific fields only
    get_result = await mcp_client.call_tool("get_work_item", {
        "project_id": project_id,
        "work_item_id": work_item_id,
        "fields": ["System.Title", "System.State"]
    })
    
    assert get_result.data is not None, "Work item retrieval should return data"
    work_item = get_result.data
    
    assert work_item["id"] == work_item_id, f"Retrieved work item ID should match. Expected {work_item_id} but got {work_item['id']}"
    assert "System.Title" in work_item["fields"], "Title field should be present in filtered result"
    assert "System.State" in work_item["fields"], "State field should be present in filtered result"
    # Description should not be present since we didn't request it
    assert "System.Description" not in work_item["fields"], "Description field should not be present in filtered result"


@pytest.mark.asyncio
@requires_ado_creds
async def test_update_work_item_basic(mcp_client, project_id, work_item_cleanup):
    """Test updating a work item with basic field changes."""
    # First create a work item
    create_result = await mcp_client.call_tool("create_work_item", {
        "project_id": project_id,
        "work_item_type": "Bug",
        "title": "Original bug title",
        "description": "Original description"
    })
    
    work_item_id = create_result.data["id"]
    
    # Track for cleanup
    work_item_cleanup(work_item_id)
    
    # Update the work item (only fields that exist for Bug type)
    update_result = await mcp_client.call_tool("update_work_item", {
        "project_id": project_id,
        "work_item_id": work_item_id,
        "title": "Updated bug title",
        "description": "Updated description"
    })
    
    assert update_result.data is not None, "Work item update should return data"
    updated_work_item = update_result.data
    
    assert updated_work_item["id"] == work_item_id, f"Updated work item ID should match. Expected {work_item_id} but got {updated_work_item['id']}"
    assert updated_work_item["fields"]["System.Title"] == "Updated bug title", f"Title should be updated but got: {updated_work_item['fields'].get('System.Title')}"
    assert updated_work_item["fields"]["System.Description"] == "Updated description", f"Description should be updated but got: {updated_work_item['fields'].get('System.Description')}"
    # Priority field doesn't exist for Bug work items, so we don't test it


@pytest.mark.asyncio
@requires_ado_creds
async def test_update_work_item_with_custom_fields(mcp_client, project_id, work_item_cleanup):
    """Test updating a work item with custom fields."""
    # First create a work item
    create_result = await mcp_client.call_tool("create_work_item", {
        "project_id": project_id,
        "work_item_type": "Task",
        "title": "Task for custom field update"
    })
    
    work_item_id = create_result.data["id"]
    
    # Track for cleanup
    work_item_cleanup(work_item_id)
    
    # Update with custom fields
    update_result = await mcp_client.call_tool("update_work_item", {
        "project_id": project_id,
        "work_item_id": work_item_id,
        "fields_to_update": {
            "Microsoft.VSTS.Common.Activity": "Testing",
            "System.History": "Updated via MCP server test"
        }
    })
    
    assert update_result.data is not None, "Work item update should return data"
    updated_work_item = update_result.data
    
    assert updated_work_item["fields"]["Microsoft.VSTS.Common.Activity"] == "Testing", f"Activity should be Testing but got: {updated_work_item['fields'].get('Microsoft.VSTS.Common.Activity')}"


@pytest.mark.asyncio
@requires_ado_creds
async def test_delete_work_item_soft_delete(mcp_client, project_id, work_item_cleanup):
    """Test soft deleting a work item (move to recycle bin)."""
    # First create a work item
    create_result = await mcp_client.call_tool("create_work_item", {
        "project_id": project_id,
        "work_item_type": "Bug",
        "title": "Bug to be soft deleted"
    })
    
    work_item_id = create_result.data["id"]
    
    # Track for cleanup (will be soft deleted by test but tracking anyway)
    work_item_cleanup(work_item_id)
    
    # Soft delete the work item
    delete_result = await mcp_client.call_tool("delete_work_item", {
        "project_id": project_id,
        "work_item_id": work_item_id,
        "destroy": False
    })
    
    assert delete_result.data is True, f"Soft delete should return True but got: {delete_result.data}"


@pytest.mark.asyncio 
@requires_ado_creds
async def test_create_work_item_failure_invalid_type(mcp_client, project_id):
    """Test creating a work item with invalid work item type."""
    with pytest.raises(Exception) as exc_info:
        await mcp_client.call_tool("create_work_item", {
            "project_id": project_id,
            "work_item_type": "InvalidWorkItemType",
            "title": "This should fail"
        })
    
    assert "work item type" in str(exc_info.value).lower() or "invalidworkitemtype" in str(exc_info.value).lower(), f"Error should mention invalid work item type but got: {exc_info.value}"


@pytest.mark.asyncio
@requires_ado_creds
async def test_get_work_item_failure_nonexistent_id(mcp_client, project_id):
    """Test retrieving a work item with non-existent ID."""
    with pytest.raises(Exception) as exc_info:
        await mcp_client.call_tool("get_work_item", {
            "project_id": project_id,
            "work_item_id": 999999999  # Very unlikely to exist
        })
    
    assert "not found" in str(exc_info.value).lower() or "999999999" in str(exc_info.value), f"Error should indicate work item not found but got: {exc_info.value}"


@pytest.mark.asyncio
@requires_ado_creds
async def test_work_item_tools_registered_in_mcp_server(mcp_client):
    """Test that work item tools are properly registered in the MCP server."""
    # List all available tools
    tools_response = await mcp_client.list_tools()
    if hasattr(tools_response, "tools"):
        tools = tools_response.tools
    else:
        tools = tools_response
    tool_names = [tool.name for tool in tools]
    
    # Check that our work item tools are registered
    expected_tools = [
        "create_work_item",
        "get_work_item", 
        "update_work_item",
        "delete_work_item"
    ]
    
    for tool_name in expected_tools:
        assert tool_name in tool_names, f"Tool '{tool_name}' should be registered but available tools are: {tool_names}"