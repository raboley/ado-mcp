import os

import pytest
from fastmcp.client import Client

from server import mcp
from src.test_config import get_project_id
from tests.ado.test_client import requires_ado_creds

pytestmark = pytest.mark.asyncio

@pytest.fixture
async def client():
    async with Client(mcp) as client:
        yield client

@pytest.fixture
def project_id():
    return get_project_id()

def get_current_user_email():
    return os.getenv("AZURE_DEVOPS_USER_EMAIL", "raboley@gmail.com")

@requires_ado_creds
async def test_get_work_items_batch_basic_functionality(client, project_id):
    current_user = get_current_user_email()

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

        returned_ids = [item["id"] for item in result.data]
        for expected_id in work_item_ids:
            assert expected_id in returned_ids, (
                f"Work item {expected_id} should be in returned items but found: {returned_ids}"
            )

        for work_item in result.data:
            assert "id" in work_item, "Work item should have id field"
            assert "fields" in work_item, "Work item should have fields"
            assert "System.Title" in work_item["fields"], "Work item should have title field"

    finally:
        for work_item_id in work_item_ids:
            try:
                await client.call_tool(
                    "delete_work_item", {"project_id": project_id, "work_item_id": work_item_id}
                )
            except Exception:
                pass

@requires_ado_creds
async def test_get_work_items_batch_with_field_filtering(client, project_id):
    current_user = get_current_user_email()

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

        assert "System.Title" in fields, (
            f"Should have System.Title field but found: {list(fields.keys())}"
        )
        assert "System.State" in fields, (
            f"Should have System.State field but found: {list(fields.keys())}"
        )

    finally:
        try:
            await client.call_tool(
                "delete_work_item", {"project_id": project_id, "work_item_id": work_item_id}
            )
        except Exception:
            pass

@requires_ado_creds
async def test_get_work_items_batch_error_handling_omit_policy(client, project_id):
    current_user = get_current_user_email()

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
        invalid_id = 999999
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

        assert len(result.data) <= 2, (
            f"Should return at most 2 work items but got: {len(result.data)}"
        )
        assert len(result.data) >= 1, (
            f"Should return at least 1 valid work item but got: {len(result.data)}"
        )

        returned_ids = [item["id"] for item in result.data]
        assert valid_id in returned_ids, (
            f"Valid work item {valid_id} should be in results but found: {returned_ids}"
        )

    finally:
        try:
            await client.call_tool(
                "delete_work_item", {"project_id": project_id, "work_item_id": valid_id}
            )
        except Exception:
            pass

@requires_ado_creds
async def test_get_work_items_batch_error_handling_fail_policy(client, project_id):
    current_user = get_current_user_email()

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
        invalid_id = 999999

        try:
            result = await client.call_tool(
                "get_work_items_batch",
                {
                    "project_id": project_id,
                    "work_item_ids": [valid_id, invalid_id],
                    "error_policy": "fail",
                },
            )

            assert isinstance(result.data, list), (
                f"Result should be a list but got: {type(result.data)}"
            )

        except Exception as exc:
            assert "404" in str(exc) or "not found" in str(exc).lower(), (
                f"Should get not found error but got: {exc}"
            )

    finally:
        try:
            await client.call_tool(
                "delete_work_item", {"project_id": project_id, "work_item_id": valid_id}
            )
        except Exception:
            pass

async def test_get_work_items_batch_empty_list(client, project_id):
    result = await client.call_tool(
        "get_work_items_batch", {"project_id": project_id, "work_item_ids": []}
    )

    assert result.is_error is False, (
        f"Should handle empty list gracefully but got error: {result.content}"
    )
    assert result.data == [], f"Should return empty list but got: {result.data}"

async def test_get_work_items_batch_too_many_ids(client, project_id):
    large_id_list = list(range(1, 202))

    with pytest.raises(Exception) as exc_info:
        await client.call_tool(
            "get_work_items_batch", {"project_id": project_id, "work_item_ids": large_id_list}
        )

    assert "200" in str(exc_info.value), (
        f"Error message should mention 200 limit but got: {exc_info.value}"
    )

async def test_get_work_items_batch_invalid_project(client):
    with pytest.raises(Exception) as exc_info:
        await client.call_tool(
            "get_work_items_batch", {"project_id": "invalid-project-id", "work_item_ids": [1, 2, 3]}
        )

    assert "404" in str(exc_info.value) or "not found" in str(exc_info.value).lower(), (
        f"Should get not found error but got: {exc_info.value}"
    )
