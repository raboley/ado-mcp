"""Tests for work item batch deletion operations."""

import os
import pytest
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
    """Get project ID from environment."""
    return os.getenv("ADO_PROJECT_ID", "49e895da-15c6-4211-97df-65c547a59c22")


def get_current_user_email():
    """Get current user email from environment."""
    return os.getenv("AZURE_DEVOPS_USER_EMAIL", "raboley@gmail.com")


async def test_delete_work_items_batch_tool_registration(client):
    """Test that delete_work_items_batch tool is properly registered"""
    tools = await client.list_tools()
    tool_names = [tool.name for tool in tools]
    assert "delete_work_items_batch" in tool_names


@requires_ado_creds
async def test_delete_work_items_batch_basic_functionality(client, project_id):
    """Test basic functionality of delete_work_items_batch tool"""
    current_user = get_current_user_email()

    # Create multiple test work items to delete
    work_item_ids = []
    for i in range(3):
        create_result = await client.call_tool("create_work_item", {
            "project_id": project_id,
            "work_item_type": "Task",
            "title": f"Batch deletion test work item {i+1}",
            "assigned_to": current_user
        })
        
        assert create_result.is_error is False, f"Should create work item successfully but got error: {create_result.content}"
        work_item_ids.append(create_result.data["id"])

    # Test delete_work_items_batch (soft delete)
    result = await client.call_tool("delete_work_items_batch", {
        "project_id": project_id,
        "work_item_ids": work_item_ids,
        "destroy": False
    })
    
    assert result.is_error is False, f"Should delete work items batch successfully but got error: {result.content}"
    assert result.data is not None, f"Result data should not be None: {result.data}"
    
    # The result.data is the actual return value from the tool
    deletion_results = result.data
    assert isinstance(deletion_results, list), f"Result should be a list but got: {type(deletion_results)}"
    assert len(deletion_results) == 3, f"Should return 3 deletion results but got: {len(deletion_results)}"
    
    # Verify all work items were deleted successfully
    for i, success in enumerate(deletion_results):
        assert success is True, f"Deletion should be successful for work item {work_item_ids[i]} at position {i}"
    
    # Verify work items are no longer accessible (moved to recycle bin)
    for work_item_id in work_item_ids:
        try:
            get_result = await client.call_tool("get_work_item", {
                "project_id": project_id,
                "work_item_id": work_item_id
            })
            # If we get here, the work item was not deleted, which is unexpected
            assert False, f"Should not be able to get deleted work item {work_item_id}, but got: {get_result.data}"
        except Exception as e:
            # This is expected - deleted work items should not be accessible
            assert "404" in str(e) or "not found" in str(e).lower(), f"Should get 404 error for deleted work item {work_item_id}, but got: {e}"


@requires_ado_creds
async def test_delete_work_items_batch_destroy_mode(client, project_id):
    """Test batch deletion with destroy=True (permanent deletion)"""
    current_user = get_current_user_email()

    # Create test work items
    work_item_ids = []
    for i in range(2):
        create_result = await client.call_tool("create_work_item", {
            "project_id": project_id,
            "work_item_type": "Task",
            "title": f"Batch destroy test work item {i+1}",
            "assigned_to": current_user
        })
        
        assert create_result.is_error is False, f"Should create work item successfully but got error: {create_result.content}"
        work_item_ids.append(create_result.data["id"])

    # Test delete_work_items_batch with destroy=True
    result = await client.call_tool("delete_work_items_batch", {
        "project_id": project_id,
        "work_item_ids": work_item_ids,
        "destroy": True
    })
    
    assert result.is_error is False, f"Should destroy work items batch successfully but got error: {result.content}"
    
    deletion_results = result.data
    assert len(deletion_results) == 2, f"Should return 2 deletion results"
    
    # Verify all work items were destroyed successfully
    for i, success in enumerate(deletion_results):
        assert success is True, f"Destruction should be successful for work item {work_item_ids[i]}"


@requires_ado_creds
async def test_delete_work_items_batch_error_handling_fail_policy(client, project_id):
    """Test batch deletion with fail error policy for invalid IDs"""
    current_user = get_current_user_email()

    # Create one valid work item
    create_result = await client.call_tool("create_work_item", {
        "project_id": project_id,
        "work_item_type": "Task",
        "title": "Valid work item for batch delete error test",
        "assigned_to": current_user
    })
    
    assert create_result.is_error is False, f"Should create work item successfully but got error: {create_result.content}"
    valid_id = create_result.data["id"]

    try:
        # Test with mix of valid and invalid IDs (fail policy)
        invalid_id = 999999  # Hopefully this doesn't exist
        
        # With fail policy, this should raise an exception if any item fails
        with pytest.raises(Exception) as exc_info:
            await client.call_tool("delete_work_items_batch", {
                "project_id": project_id,
                "work_item_ids": [valid_id, invalid_id],
                "error_policy": "fail"
            })
        
        # Should get an error about the invalid work item
        assert "404" in str(exc_info.value) or "not found" in str(exc_info.value).lower() or "batch" in str(exc_info.value).lower(), f"Should get batch failure error but got: {exc_info.value}"
        
    finally:
        # Clean up valid work item (it might not have been deleted due to failure)
        try:
            await client.call_tool("delete_work_item", {
                "project_id": project_id,
                "work_item_id": valid_id
            })
        except Exception as e:
            print(f"Note: Work item {valid_id} may have been deleted already: {e}")


@requires_ado_creds
async def test_delete_work_items_batch_error_handling_omit_policy(client, project_id):
    """Test batch deletion with omit error policy for invalid IDs"""
    current_user = get_current_user_email()

    # Create one valid work item
    create_result = await client.call_tool("create_work_item", {
        "project_id": project_id,
        "work_item_type": "Task",
        "title": "Valid work item for omit policy test",
        "assigned_to": current_user
    })
    
    assert create_result.is_error is False, f"Should create work item successfully but got error: {create_result.content}"
    valid_id = create_result.data["id"]

    # Test with mix of valid and invalid IDs (omit policy)
    invalid_id = 999999  # Hopefully this doesn't exist
    result = await client.call_tool("delete_work_items_batch", {
        "project_id": project_id,
        "work_item_ids": [valid_id, invalid_id],
        "error_policy": "omit"
    })
    
    assert result.is_error is False, f"Should handle invalid IDs with omit policy but got error: {result.content}"
    
    # Should return results for both items
    deletion_results = result.data
    assert len(deletion_results) == 2, f"Should return 2 deletion results but got: {len(deletion_results)}"
    
    # The valid work item (first in list) should be deleted successfully
    # The invalid work item (second in list) should fail to delete
    assert deletion_results[0] is True, f"Valid work item should be deleted successfully"
    assert deletion_results[1] is False, f"Invalid work item should fail to delete"


async def test_delete_work_items_batch_empty_list(client, project_id):
    """Test batch deletion with empty work item IDs list"""
    result = await client.call_tool("delete_work_items_batch", {
        "project_id": project_id,
        "work_item_ids": []
    })
    
    assert result.is_error is False, f"Should handle empty list gracefully but got error: {result.content}"
    assert result.data == [], f"Should return empty list but got: {result.data}"


async def test_delete_work_items_batch_too_many_ids(client, project_id):
    """Test batch deletion with too many work item IDs (>200)"""
    # Create a list of 201 IDs
    large_id_list = list(range(1, 202))
    
    # Should raise an exception due to validation error
    with pytest.raises(Exception) as exc_info:
        await client.call_tool("delete_work_items_batch", {
            "project_id": project_id,
            "work_item_ids": large_id_list
        })
    
    # Verify the error message mentions the 200 limit
    assert "200" in str(exc_info.value), f"Error message should mention 200 limit: {exc_info.value}"


async def test_delete_work_items_batch_invalid_project(client):
    """Test batch deletion with invalid project ID"""
    # Should raise an exception due to invalid project
    with pytest.raises(Exception) as exc_info:
        await client.call_tool("delete_work_items_batch", {
            "project_id": "invalid-project-id",
            "work_item_ids": [1, 2, 3]
        })
    
    # Should fail with project-related error
    assert "404" in str(exc_info.value) or "not found" in str(exc_info.value).lower(), f"Should get not found error but got: {exc_info.value}"


@requires_ado_creds
async def test_delete_work_items_batch_single_item(client, project_id):
    """Test batch deletion with a single work item"""
    current_user = get_current_user_email()

    # Create a single test work item
    create_result = await client.call_tool("create_work_item", {
        "project_id": project_id,
        "work_item_type": "Task",
        "title": "Single item batch deletion test",
        "assigned_to": current_user
    })
    
    assert create_result.is_error is False, f"Should create work item successfully but got error: {create_result.content}"
    work_item_id = create_result.data["id"]

    # Test batch deletion with single item
    result = await client.call_tool("delete_work_items_batch", {
        "project_id": project_id,
        "work_item_ids": [work_item_id]
    })
    
    assert result.is_error is False, f"Should delete single work item successfully but got error: {result.content}"
    
    deletion_results = result.data
    assert len(deletion_results) == 1, f"Should return 1 deletion result"
    assert deletion_results[0] is True, f"Deletion should be successful"


@requires_ado_creds
async def test_delete_work_items_batch_performance_with_many_items(client, project_id):
    """Test batch deletion performance with multiple items (stress test)"""
    current_user = get_current_user_email()

    # Create multiple work items for performance testing
    work_item_ids = []
    item_count = 5  # Small number for CI, but tests the pattern
    for i in range(item_count):
        create_result = await client.call_tool("create_work_item", {
            "project_id": project_id,
            "work_item_type": "Task",
            "title": f"Performance test work item {i+1}",
            "assigned_to": current_user
        })
        
        assert create_result.is_error is False, f"Should create work item successfully but got error: {create_result.content}"
        work_item_ids.append(create_result.data["id"])

    import time
    start_time = time.time()
    
    # Test batch deletion performance
    result = await client.call_tool("delete_work_items_batch", {
        "project_id": project_id,
        "work_item_ids": work_item_ids
    })
    
    end_time = time.time()
    duration = end_time - start_time
    
    assert result.is_error is False, f"Should delete work items batch successfully"
    
    deletion_results = result.data
    assert len(deletion_results) == item_count, f"Should return {item_count} deletion results"
    
    # Verify all deletions were successful
    successful_deletions = sum(deletion_results)
    assert successful_deletions == item_count, f"All {item_count} deletions should be successful"
    
    # Performance expectation: should complete reasonably quickly
    assert duration < 30.0, f"Batch deletion should complete in reasonable time, took {duration:.2f}s"
    
    print(f"Performance: Deleted {item_count} work items in {duration:.2f}s ({item_count/duration:.2f} items/sec)")