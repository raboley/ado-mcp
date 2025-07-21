"""Tests for work item batch update operations."""

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


async def test_update_work_items_batch_tool_registration(client):
    """Test that update_work_items_batch tool is properly registered"""
    tools = await client.list_tools()
    tool_names = [tool.name for tool in tools]
    assert "update_work_items_batch" in tool_names


@requires_ado_creds
async def test_update_work_items_batch_basic_functionality(client, project_id):
    """Test basic functionality of update_work_items_batch tool"""
    current_user = get_current_user_email()

    # Create multiple test work items to update
    work_item_ids = []
    for i in range(3):
        create_result = await client.call_tool(
            "create_work_item",
            {
                "project_id": project_id,
                "work_item_type": "Task",
                "title": f"Batch update test work item {i + 1}",
                "assigned_to": current_user,
            },
        )

        assert create_result.is_error is False, (
            f"Should create work item successfully but got error: {create_result.content}"
        )
        work_item_ids.append(create_result.data["id"])

    try:
        # Prepare batch update operations
        work_item_updates = []
        for i, work_item_id in enumerate(work_item_ids):
            work_item_updates.append(
                {
                    "work_item_id": work_item_id,
                    "operations": [
                        {
                            "op": "replace",
                            "path": "/fields/System.Title",
                            "value": f"Updated batch test work item {i + 1}",
                        },
                        {
                            "op": "replace",
                            "path": "/fields/System.Description",
                            "value": f"This work item was updated via batch operation {i + 1}",
                        },
                    ],
                }
            )

        # Test update_work_items_batch
        result = await client.call_tool(
            "update_work_items_batch",
            {"project_id": project_id, "work_item_updates": work_item_updates},
        )

        assert result.is_error is False, (
            f"Should update work items batch successfully but got error: {result.content}"
        )
        assert result.data is not None, f"Result data should not be None: {result.data}"

        # The result.data is the actual return value from the tool
        updated_items = result.data
        assert isinstance(updated_items, list), (
            f"Result should be a list but got: {type(updated_items)}"
        )
        assert len(updated_items) == 3, (
            f"Should return 3 updated work items but got: {len(updated_items)}"
        )

        # Verify all work items were updated correctly
        returned_ids = [item["id"] for item in updated_items]
        for work_item_id in work_item_ids:
            assert work_item_id in returned_ids, (
                f"Updated work item {work_item_id} should be in returned items: {returned_ids}"
            )

        # Verify content was updated (check titles match the expected pattern)
        updated_titles = [item["fields"]["System.Title"] for item in updated_items]
        for i in range(3):
            expected_title = f"Updated batch test work item {i + 1}"
            assert expected_title in updated_titles, (
                f"Expected title '{expected_title}' should be in updated titles: {updated_titles}"
            )

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
async def test_update_work_items_batch_error_handling_fail_policy(client, project_id):
    """Test batch update with fail error policy for invalid operations"""
    current_user = get_current_user_email()

    # Create one valid work item
    create_result = await client.call_tool(
        "create_work_item",
        {
            "project_id": project_id,
            "work_item_type": "Task",
            "title": "Valid work item for batch update error test",
            "assigned_to": current_user,
        },
    )

    assert create_result.is_error is False, (
        f"Should create work item successfully but got error: {create_result.content}"
    )
    valid_id = create_result.data["id"]

    try:
        # Create batch update with mix of valid and invalid operations
        invalid_id = 999999  # Hopefully this doesn't exist
        work_item_updates = [
            {
                "work_item_id": valid_id,
                "operations": [
                    {"op": "replace", "path": "/fields/System.Title", "value": "Updated valid item"}
                ],
            },
            {
                "work_item_id": invalid_id,
                "operations": [
                    {"op": "replace", "path": "/fields/System.Title", "value": "This should fail"}
                ],
            },
        ]

        # With fail policy, this should raise an exception if any item fails
        with pytest.raises(Exception) as exc_info:
            await client.call_tool(
                "update_work_items_batch",
                {
                    "project_id": project_id,
                    "work_item_updates": work_item_updates,
                    "error_policy": "fail",
                },
            )

        # Should get an error about the invalid work item
        assert (
            "404" in str(exc_info.value)
            or "not found" in str(exc_info.value).lower()
            or "batch" in str(exc_info.value).lower()
        ), f"Should get batch failure error but got: {exc_info.value}"

    finally:
        # Clean up
        try:
            await client.call_tool(
                "delete_work_item", {"project_id": project_id, "work_item_id": valid_id}
            )
        except Exception as e:
            print(f"Warning: Failed to delete work item {valid_id}: {e}")


@requires_ado_creds
async def test_update_work_items_batch_error_handling_omit_policy(client, project_id):
    """Test batch update with omit error policy for invalid operations"""
    current_user = get_current_user_email()

    # Create one valid work item
    create_result = await client.call_tool(
        "create_work_item",
        {
            "project_id": project_id,
            "work_item_type": "Task",
            "title": "Valid work item for omit policy test",
            "assigned_to": current_user,
        },
    )

    assert create_result.is_error is False, (
        f"Should create work item successfully but got error: {create_result.content}"
    )
    valid_id = create_result.data["id"]

    try:
        # Create batch update with mix of valid and invalid operations
        invalid_id = 999999  # Hopefully this doesn't exist
        work_item_updates = [
            {
                "work_item_id": valid_id,
                "operations": [
                    {
                        "op": "replace",
                        "path": "/fields/System.Title",
                        "value": "Updated valid item via omit policy",
                    }
                ],
            },
            {
                "work_item_id": invalid_id,
                "operations": [
                    {
                        "op": "replace",
                        "path": "/fields/System.Title",
                        "value": "This should be omitted",
                    }
                ],
            },
        ]

        # With omit policy, should succeed with partial results
        result = await client.call_tool(
            "update_work_items_batch",
            {
                "project_id": project_id,
                "work_item_updates": work_item_updates,
                "error_policy": "omit",
            },
        )

        assert result.is_error is False, (
            f"Should handle invalid IDs with omit policy but got error: {result.content}"
        )

        # Should return only the valid work item that was updated
        assert len(result.data) <= 2, (
            f"Should return at most 2 work items but got: {len(result.data)}"
        )
        assert len(result.data) >= 1, (
            f"Should return at least 1 valid work item but got: {len(result.data)}"
        )

        # The valid work item should be in the results with updated title
        updated_items = result.data
        found_valid = False
        for item in updated_items:
            if item["id"] == valid_id:
                found_valid = True
                assert item["fields"]["System.Title"] == "Updated valid item via omit policy", (
                    f"Valid item should be updated"
                )
                break

        assert found_valid, f"Valid work item {valid_id} should be in results"

    finally:
        # Clean up
        try:
            await client.call_tool(
                "delete_work_item", {"project_id": project_id, "work_item_id": valid_id}
            )
        except Exception as e:
            print(f"Warning: Failed to delete work item {valid_id}: {e}")


async def test_update_work_items_batch_empty_list(client, project_id):
    """Test batch update with empty work item updates list"""
    result = await client.call_tool(
        "update_work_items_batch", {"project_id": project_id, "work_item_updates": []}
    )

    assert result.is_error is False, (
        f"Should handle empty list gracefully but got error: {result.content}"
    )
    assert result.data == [], f"Should return empty list but got: {result.data}"


async def test_update_work_items_batch_too_many_items(client, project_id):
    """Test batch update with too many work item updates (>200)"""
    # Create a list of 201 updates
    large_update_list = []
    for i in range(201):
        large_update_list.append(
            {
                "work_item_id": i + 1,
                "operations": [
                    {"op": "replace", "path": "/fields/System.Title", "value": f"Item {i + 1}"}
                ],
            }
        )

    # Should raise an exception due to validation error
    with pytest.raises(Exception) as exc_info:
        await client.call_tool(
            "update_work_items_batch",
            {"project_id": project_id, "work_item_updates": large_update_list},
        )

    # Verify the error message mentions the 200 limit
    assert "200" in str(exc_info.value), f"Error message should mention 200 limit: {exc_info.value}"


async def test_update_work_items_batch_invalid_project(client):
    """Test batch update with invalid project ID"""
    work_item_updates = [
        {
            "work_item_id": 123,
            "operations": [{"op": "replace", "path": "/fields/System.Title", "value": "Test"}],
        }
    ]

    # Should raise an exception due to invalid project
    with pytest.raises(Exception) as exc_info:
        await client.call_tool(
            "update_work_items_batch",
            {"project_id": "invalid-project-id", "work_item_updates": work_item_updates},
        )

    # Should fail with project-related error
    assert "404" in str(exc_info.value) or "not found" in str(exc_info.value).lower(), (
        f"Should get not found error but got: {exc_info.value}"
    )


@requires_ado_creds
async def test_update_work_items_batch_validation_only(client, project_id):
    """Test batch update with validation_only flag"""
    current_user = get_current_user_email()

    # Create a test work item
    create_result = await client.call_tool(
        "create_work_item",
        {
            "project_id": project_id,
            "work_item_type": "Task",
            "title": "Work item for validation test",
            "assigned_to": current_user,
        },
    )

    assert create_result.is_error is False, (
        f"Should create work item successfully but got error: {create_result.content}"
    )
    work_item_id = create_result.data["id"]
    original_title = create_result.data["fields"]["System.Title"]

    try:
        # Test validation-only update
        work_item_updates = [
            {
                "work_item_id": work_item_id,
                "operations": [
                    {
                        "op": "replace",
                        "path": "/fields/System.Title",
                        "value": "Validation test title",
                    }
                ],
            }
        ]

        result = await client.call_tool(
            "update_work_items_batch",
            {
                "project_id": project_id,
                "work_item_updates": work_item_updates,
                "validate_only": True,
            },
        )

        # Should succeed validation
        assert result.is_error is False, (
            f"Should validate successfully but got error: {result.content}"
        )

        # Verify work item was not actually updated
        get_result = await client.call_tool(
            "get_work_item", {"project_id": project_id, "work_item_id": work_item_id}
        )

        assert get_result.data["fields"]["System.Title"] == original_title, (
            f"Work item should not be updated during validation-only operation"
        )

    finally:
        # Clean up
        try:
            await client.call_tool(
                "delete_work_item", {"project_id": project_id, "work_item_id": work_item_id}
            )
        except Exception as e:
            print(f"Warning: Failed to delete work item {work_item_id}: {e}")


@requires_ado_creds
async def test_update_work_items_batch_malformed_operations(client, project_id):
    """Test batch update with malformed update operations"""
    current_user = get_current_user_email()

    # Create a test work item
    create_result = await client.call_tool(
        "create_work_item",
        {
            "project_id": project_id,
            "work_item_type": "Task",
            "title": "Work item for malformed operations test",
            "assigned_to": current_user,
        },
    )

    assert create_result.is_error is False, (
        f"Should create work item successfully but got error: {create_result.content}"
    )
    work_item_id = create_result.data["id"]

    try:
        # Test with missing work_item_id
        with pytest.raises(Exception) as exc_info:
            await client.call_tool(
                "update_work_items_batch",
                {
                    "project_id": project_id,
                    "work_item_updates": [
                        {
                            "operations": [
                                {"op": "replace", "path": "/fields/System.Title", "value": "Test"}
                            ]
                        }
                    ],
                    "error_policy": "fail",
                },
            )

        assert "work_item_id" in str(exc_info.value), (
            f"Should complain about missing work_item_id: {exc_info.value}"
        )

        # Test with missing operations
        with pytest.raises(Exception) as exc_info:
            await client.call_tool(
                "update_work_items_batch",
                {
                    "project_id": project_id,
                    "work_item_updates": [{"work_item_id": work_item_id}],
                    "error_policy": "fail",
                },
            )

        assert "operations" in str(exc_info.value), (
            f"Should complain about missing operations: {exc_info.value}"
        )

    finally:
        # Clean up
        try:
            await client.call_tool(
                "delete_work_item", {"project_id": project_id, "work_item_id": work_item_id}
            )
        except Exception as e:
            print(f"Warning: Failed to delete work item {work_item_id}: {e}")
