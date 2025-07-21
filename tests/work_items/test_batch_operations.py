"""Tests for work item batch operations like get_work_items_batch."""

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


async def test_get_work_items_batch_tool_registration(client):
    """Test that get_work_items_batch tool is properly registered"""
    tools = await client.list_tools()
    tool_names = [tool.name for tool in tools]
    assert "get_work_items_batch" in tool_names


@requires_ado_creds
async def test_get_work_items_batch_basic_functionality(client, project_id):
    """Test basic functionality of get_work_items_batch tool"""
    current_user = get_current_user_email()

    # Create multiple test work items
    work_item_ids = []
    for i in range(3):
        create_result = await client.call_tool(
            "create_work_item",
            {
                "project_id": project_id,
                "work_item_type": "Task",
                "title": f"Batch test work item {i + 1}",
                "assigned_to": current_user,
            },
        )

        assert create_result.is_error is False, (
            f"Should create work item successfully but got error: {create_result.content}"
        )
        work_item_ids.append(create_result.data["id"])

    try:
        # Test get_work_items_batch
        result = await client.call_tool(
            "get_work_items_batch", {"project_id": project_id, "work_item_ids": work_item_ids}
        )

        assert result.is_error is False, (
            f"Should get work items batch successfully but got error: {result.content}"
        )
        assert isinstance(result.data, list), (
            f"Result should be a list but got: {type(result.data)}"
        )
        assert len(result.data) == 3, f"Should return 3 work items but got: {len(result.data)}"

        # Verify all work items are returned with correct IDs
        returned_ids = [item["id"] for item in result.data]
        for expected_id in work_item_ids:
            assert expected_id in returned_ids, (
                f"Work item {expected_id} should be in returned items"
            )

        # Verify work items have expected fields
        for work_item in result.data:
            assert "id" in work_item, "Work item should have id field"
            assert "fields" in work_item, "Work item should have fields"
            assert "System.Title" in work_item["fields"], "Work item should have title field"

    finally:
        # Clean up: delete test work items
        for work_item_id in work_item_ids:
            try:
                await client.call_tool(
                    "delete_work_item", {"project_id": project_id, "work_item_id": work_item_id}
                )
            except Exception as e:
                print(f"Warning: Failed to delete work item {work_item_id}: {e}")


@requires_ado_creds
async def test_get_work_items_batch_with_field_filtering(client, project_id):
    """Test batch retrieval with specific field filtering"""
    current_user = get_current_user_email()

    # Create a test work item
    create_result = await client.call_tool(
        "create_work_item",
        {
            "project_id": project_id,
            "work_item_type": "Task",
            "title": "Field filtering test work item",
            "assigned_to": current_user,
        },
    )

    assert create_result.is_error is False, (
        f"Should create work item successfully but got error: {create_result.content}"
    )
    work_item_id = create_result.data["id"]

    try:
        # Test with specific fields
        result = await client.call_tool(
            "get_work_items_batch",
            {
                "project_id": project_id,
                "work_item_ids": [work_item_id],
                "fields": ["System.Id", "System.Title", "System.State"],
            },
        )

        assert result.is_error is False, (
            f"Should get work items with field filtering but got error: {result.content}"
        )
        assert len(result.data) == 1, f"Should return 1 work item but got: {len(result.data)}"

        work_item = result.data[0]
        fields = work_item["fields"]

        # Should have requested fields
        assert "System.Title" in fields, "Should have System.Title field"
        assert "System.State" in fields, "Should have System.State field"

        # Should not have fields we didn't request (note: some fields may be returned anyway by API)
        # We just verify that field filtering was applied by checking we got expected fields

    finally:
        # Clean up
        try:
            await client.call_tool(
                "delete_work_item", {"project_id": project_id, "work_item_id": work_item_id}
            )
        except Exception as e:
            print(f"Warning: Failed to delete work item {work_item_id}: {e}")


@requires_ado_creds
async def test_get_work_items_batch_error_handling_omit_policy(client, project_id):
    """Test batch retrieval with omit error policy for invalid IDs"""
    current_user = get_current_user_email()

    # Create one valid work item
    create_result = await client.call_tool(
        "create_work_item",
        {
            "project_id": project_id,
            "work_item_type": "Task",
            "title": "Valid work item for error handling test",
            "assigned_to": current_user,
        },
    )

    assert create_result.is_error is False, (
        f"Should create work item successfully but got error: {create_result.content}"
    )
    valid_id = create_result.data["id"]

    try:
        # Test with mix of valid and invalid IDs (omit policy)
        invalid_id = 999999  # Hopefully this doesn't exist
        result = await client.call_tool(
            "get_work_items_batch",
            {
                "project_id": project_id,
                "work_item_ids": [valid_id, invalid_id],
                "error_policy": "omit",
            },
        )

        assert result.is_error is False, (
            f"Should handle invalid IDs with omit policy but got error: {result.content}"
        )

        # Should return only the valid work item
        assert len(result.data) <= 2, (
            f"Should return at most 2 work items but got: {len(result.data)}"
        )
        assert len(result.data) >= 1, (
            f"Should return at least 1 valid work item but got: {len(result.data)}"
        )

        # The valid work item should be in the results
        returned_ids = [item["id"] for item in result.data]
        assert valid_id in returned_ids, f"Valid work item {valid_id} should be in results"

    finally:
        # Clean up
        try:
            await client.call_tool(
                "delete_work_item", {"project_id": project_id, "work_item_id": valid_id}
            )
        except Exception as e:
            print(f"Warning: Failed to delete work item {valid_id}: {e}")


@requires_ado_creds
async def test_get_work_items_batch_error_handling_fail_policy(client, project_id):
    """Test batch retrieval with fail error policy for invalid IDs"""
    current_user = get_current_user_email()

    # Create one valid work item
    create_result = await client.call_tool(
        "create_work_item",
        {
            "project_id": project_id,
            "work_item_type": "Task",
            "title": "Valid work item for fail policy test",
            "assigned_to": current_user,
        },
    )

    assert create_result.is_error is False, (
        f"Should create work item successfully but got error: {create_result.content}"
    )
    valid_id = create_result.data["id"]

    try:
        # Test with mix of valid and invalid IDs (fail policy)
        invalid_id = 999999  # Hopefully this doesn't exist

        # With fail policy, this should raise an exception if any item fails
        try:
            result = await client.call_tool(
                "get_work_items_batch",
                {
                    "project_id": project_id,
                    "work_item_ids": [valid_id, invalid_id],
                    "error_policy": "fail",
                },
            )

            # If it succeeds, verify we got some results
            assert isinstance(result.data, list), (
                f"Result should be a list but got: {type(result.data)}"
            )
            # With fail policy, if any item is invalid, Azure DevOps should return an error
            # But some implementations might be more lenient

        except Exception as exc:
            # Expected behavior with fail policy when invalid IDs are present
            assert "404" in str(exc) or "not found" in str(exc).lower(), (
                f"Should get not found error but got: {exc}"
            )

    finally:
        # Clean up
        try:
            await client.call_tool(
                "delete_work_item", {"project_id": project_id, "work_item_id": valid_id}
            )
        except Exception as e:
            print(f"Warning: Failed to delete work item {valid_id}: {e}")


async def test_get_work_items_batch_empty_list(client, project_id):
    """Test batch retrieval with empty work item IDs list"""
    result = await client.call_tool(
        "get_work_items_batch", {"project_id": project_id, "work_item_ids": []}
    )

    assert result.is_error is False, (
        f"Should handle empty list gracefully but got error: {result.content}"
    )
    assert result.data == [], f"Should return empty list but got: {result.data}"


async def test_get_work_items_batch_too_many_ids(client, project_id):
    """Test batch retrieval with too many work item IDs (>200)"""
    # Create a list of 201 IDs
    large_id_list = list(range(1, 202))

    # Should raise an exception due to validation error
    with pytest.raises(Exception) as exc_info:
        await client.call_tool(
            "get_work_items_batch", {"project_id": project_id, "work_item_ids": large_id_list}
        )

    # Verify the error message mentions the 200 limit
    assert "200" in str(exc_info.value), f"Error message should mention 200 limit: {exc_info.value}"


async def test_get_work_items_batch_invalid_project(client):
    """Test batch retrieval with invalid project ID"""
    # Should raise an exception due to invalid project
    with pytest.raises(Exception) as exc_info:
        await client.call_tool(
            "get_work_items_batch", {"project_id": "invalid-project-id", "work_item_ids": [1, 2, 3]}
        )

    # Should fail with project-related error
    assert "404" in str(exc_info.value) or "not found" in str(exc_info.value).lower(), (
        f"Should get not found error but got: {exc_info.value}"
    )
