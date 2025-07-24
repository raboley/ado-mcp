import os
from datetime import datetime

import pytest
from fastmcp.client import Client

from server import mcp
from src.test_config import get_project_id
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
    return get_project_id()


@pytest.fixture
async def work_item_cleanup(mcp_client, project_id):
    created_work_items = []

    def track_work_item(work_item_id):
        created_work_items.append(work_item_id)

    yield track_work_item

    for work_item_id in created_work_items:
        try:
            await mcp_client.call_tool(
                "delete_work_item",
                {
                    "project_id": project_id,
                    "work_item_id": work_item_id,
                    "destroy": True,
                },
            )
        except Exception:
            pass


@pytest.mark.asyncio
@requires_ado_creds
async def test_create_work_item_basic_bug(mcp_client, project_id, work_item_cleanup):
    result = await mcp_client.call_tool(
        "create_work_item",
        {"project_id": project_id, "work_item_type": "Bug", "title": "Test bug from MCP server"},
    )

    assert result.data is not None, "Work item creation should return data"
    work_item = result.data
    work_item_id = work_item["id"]

    work_item_cleanup(work_item_id)

    assert work_item_id is not None, f"Work item should have an ID but got: {work_item}"
    assert work_item["fields"]["System.Title"] == "Test bug from MCP server", (
        f"Title should match but got: {work_item['fields'].get('System.Title')}"
    )
    assert work_item["fields"]["System.WorkItemType"] == "Bug", (
        f"Work item type should be Bug but got: {work_item['fields'].get('System.WorkItemType')}"
    )
    assert work_item["fields"]["System.State"] in ["New", "Active"], (
        f"State should be New or Active but got: {work_item['fields'].get('System.State')}"
    )


@pytest.mark.asyncio
@requires_ado_creds
async def test_create_work_item_with_all_fields(mcp_client, project_id, work_item_cleanup):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    title = f"Test task with full fields {timestamp}"

    result = await mcp_client.call_tool(
        "create_work_item",
        {
            "project_id": project_id,
            "work_item_type": "Task",
            "title": title,
            "description": "This is a test task created with all fields populated",
            "tags": "test; automation; mcp",
            "additional_fields": {"Microsoft.VSTS.Common.Activity": "Development"},
        },
    )

    assert result.data is not None, "Work item creation should return data"
    work_item = result.data
    work_item_id = work_item["id"]

    work_item_cleanup(work_item_id)

    assert work_item_id is not None, f"Work item should have an ID but got: {work_item}"
    assert work_item["fields"]["System.Title"] == title, (
        f"Title should match but got: {work_item['fields'].get('System.Title')}"
    )
    assert work_item["fields"]["System.WorkItemType"] == "Task", (
        f"Work item type should be Task but got: {work_item['fields'].get('System.WorkItemType')}"
    )
    assert (
        work_item["fields"]["System.Description"]
        == "This is a test task created with all fields populated"
    ), f"Description should match but got: {work_item['fields'].get('System.Description')}"
    tags = work_item["fields"]["System.Tags"]
    assert "test" in tags and "automation" in tags and "mcp" in tags, (
        f"Tags should contain test, automation, and mcp but got: {tags}"
    )
    assert work_item["fields"]["Microsoft.VSTS.Common.Activity"] == "Development", (
        f"Activity should be Development but got: {work_item['fields'].get('Microsoft.VSTS.Common.Activity')}"
    )


@pytest.mark.asyncio
@requires_ado_creds
async def test_create_work_item_validation_only(mcp_client, project_id, work_item_cleanup):
    result = await mcp_client.call_tool(
        "create_work_item",
        {
            "project_id": project_id,
            "work_item_type": "User Story",
            "title": "Test validation only story",
            "validate_only": True,
        },
    )

    assert result.data is not None, "Validation should return data"


@pytest.mark.asyncio
@requires_ado_creds
async def test_get_work_item_basic(mcp_client, project_id, work_item_cleanup):
    create_result = await mcp_client.call_tool(
        "create_work_item",
        {"project_id": project_id, "work_item_type": "Bug", "title": "Test bug for retrieval"},
    )

    work_item_id = create_result.data["id"]

    work_item_cleanup(work_item_id)

    get_result = await mcp_client.call_tool(
        "get_work_item", {"project_id": project_id, "work_item_id": work_item_id}
    )

    assert get_result.data is not None, "Work item retrieval should return data"
    work_item = get_result.data

    assert work_item["id"] == work_item_id, (
        f"Retrieved work item ID should match created ID. Expected {work_item_id} but got {work_item['id']}"
    )
    assert work_item["fields"]["System.Title"] == "Test bug for retrieval", (
        f"Title should match but got: {work_item['fields'].get('System.Title')}"
    )


@pytest.mark.asyncio
@requires_ado_creds
async def test_get_work_item_with_specific_fields(mcp_client, project_id, work_item_cleanup):
    create_result = await mcp_client.call_tool(
        "create_work_item",
        {
            "project_id": project_id,
            "work_item_type": "Task",
            "title": "Test task for field filtering",
            "description": "This should not be returned in filtered result",
        },
    )

    work_item_id = create_result.data["id"]

    work_item_cleanup(work_item_id)

    get_result = await mcp_client.call_tool(
        "get_work_item",
        {
            "project_id": project_id,
            "work_item_id": work_item_id,
            "fields": ["System.Title", "System.State"],
        },
    )

    assert get_result.data is not None, "Work item retrieval should return data"
    work_item = get_result.data

    assert work_item["id"] == work_item_id, (
        f"Retrieved work item ID should match. Expected {work_item_id} but got {work_item['id']}"
    )
    assert "System.Title" in work_item["fields"], "Title field should be present in filtered result"
    assert "System.State" in work_item["fields"], "State field should be present in filtered result"
    assert "System.Description" not in work_item["fields"], (
        "Description field should not be present in filtered result"
    )


@pytest.mark.asyncio
@requires_ado_creds
async def test_update_work_item_basic(mcp_client, project_id, work_item_cleanup):
    create_result = await mcp_client.call_tool(
        "create_work_item",
        {
            "project_id": project_id,
            "work_item_type": "Bug",
            "title": "Original bug title",
            "description": "Original description",
        },
    )

    work_item_id = create_result.data["id"]

    work_item_cleanup(work_item_id)

    update_result = await mcp_client.call_tool(
        "update_work_item",
        {
            "project_id": project_id,
            "work_item_id": work_item_id,
            "title": "Updated bug title",
            "description": "Updated description",
        },
    )

    assert update_result.data is not None, "Work item update should return data"
    updated_work_item = update_result.data

    assert updated_work_item["id"] == work_item_id, (
        f"Updated work item ID should match. Expected {work_item_id} but got {updated_work_item['id']}"
    )
    assert updated_work_item["fields"]["System.Title"] == "Updated bug title", (
        f"Title should be updated but got: {updated_work_item['fields'].get('System.Title')}"
    )
    assert updated_work_item["fields"]["System.Description"] == "Updated description", (
        f"Description should be updated but got: {updated_work_item['fields'].get('System.Description')}"
    )


@pytest.mark.asyncio
@requires_ado_creds
async def test_update_work_item_with_custom_fields(mcp_client, project_id, work_item_cleanup):
    create_result = await mcp_client.call_tool(
        "create_work_item",
        {
            "project_id": project_id,
            "work_item_type": "Task",
            "title": "Task for custom field update",
        },
    )

    work_item_id = create_result.data["id"]

    work_item_cleanup(work_item_id)

    update_result = await mcp_client.call_tool(
        "update_work_item",
        {
            "project_id": project_id,
            "work_item_id": work_item_id,
            "fields_to_update": {
                "Microsoft.VSTS.Common.Activity": "Testing",
                "System.History": "Updated via MCP server test",
            },
        },
    )

    assert update_result.data is not None, "Work item update should return data"
    updated_work_item = update_result.data

    assert updated_work_item["fields"]["Microsoft.VSTS.Common.Activity"] == "Testing", (
        f"Activity should be Testing but got: {updated_work_item['fields'].get('Microsoft.VSTS.Common.Activity')}"
    )


@pytest.mark.asyncio
@requires_ado_creds
async def test_delete_work_item_soft_delete(mcp_client, project_id, work_item_cleanup):
    create_result = await mcp_client.call_tool(
        "create_work_item",
        {"project_id": project_id, "work_item_type": "Bug", "title": "Bug to be soft deleted"},
    )

    work_item_id = create_result.data["id"]

    delete_result = await mcp_client.call_tool(
        "delete_work_item",
        {"project_id": project_id, "work_item_id": work_item_id, "destroy": False},
    )

    assert delete_result.data is True, (
        f"Soft delete should return True but got: {delete_result.data}"
    )


@pytest.mark.asyncio
@requires_ado_creds
async def test_create_work_item_failure_invalid_type(mcp_client, project_id, caplog):
    import io
    import logging
    from contextlib import redirect_stderr

    with caplog.at_level(logging.CRITICAL):
        stderr_buffer = io.StringIO()
        with redirect_stderr(stderr_buffer):
            with pytest.raises(Exception) as exc_info:
                await mcp_client.call_tool(
                    "create_work_item",
                    {
                        "project_id": project_id,
                        "work_item_type": "InvalidWorkItemType",
                        "title": "This should fail",
                    },
                )

    assert (
        "work item type" in str(exc_info.value).lower()
        or "invalidworkitemtype" in str(exc_info.value).lower()
    ), f"Error should mention invalid work item type but got: {exc_info.value}"


@pytest.mark.asyncio
@requires_ado_creds
async def test_get_work_item_failure_nonexistent_id(mcp_client, project_id, caplog):
    import io
    import logging
    from contextlib import redirect_stderr

    with caplog.at_level(logging.CRITICAL):
        stderr_buffer = io.StringIO()
        with redirect_stderr(stderr_buffer):
            with pytest.raises(Exception) as exc_info:
                await mcp_client.call_tool(
                    "get_work_item",
                    {
                        "project_id": project_id,
                        "work_item_id": 999999999,
                    },
                )

    assert "not found" in str(exc_info.value).lower() or "999999999" in str(exc_info.value), (
        f"Error should indicate work item not found but got: {exc_info.value}"
    )


@pytest.mark.asyncio
@requires_ado_creds
async def test_work_item_tools_registered_in_mcp_server(mcp_client):
    tools_response = await mcp_client.list_tools()
    if hasattr(tools_response, "tools"):
        tools = tools_response.tools
    else:
        tools = tools_response
    tool_names = [tool.name for tool in tools]

    expected_tools = [
        "create_work_item",
        "get_work_item",
        "update_work_item",
        "delete_work_item",
        "list_work_items",
    ]

    for tool_name in expected_tools:
        assert tool_name in tool_names, (
            f"Tool '{tool_name}' should be registered but available tools are: {tool_names}"
        )


@pytest.mark.asyncio
@requires_ado_creds
async def test_list_work_items_create_verify_cleanup_pattern(
    mcp_client, project_id, work_item_cleanup
):
    import random
    import string

    test_pattern = f"TestPattern_{random.randint(1000, 9999)}_{''.join(random.choices(string.ascii_letters, k=5))}"

    work_item_types = ["Bug", "Task", "User Story"]
    created_work_item_ids = []

    for i, work_item_type in enumerate(work_item_types):
        create_result = await mcp_client.call_tool(
            "create_work_item",
            {
                "project_id": project_id,
                "work_item_type": work_item_type,
                "title": f"{test_pattern}_{work_item_type}_{i + 1}",
                "description": f"Test work item {i + 1} for list verification",
                "tags": f"test; automation; {test_pattern}",
            },
        )

        assert create_result.data is not None, (
            f"Work item creation should succeed but got: {create_result.data}"
        )
        work_item_id = create_result.data["id"]
        created_work_item_ids.append(work_item_id)
        work_item_cleanup(work_item_id)

    list_result = await mcp_client.call_tool("list_work_items", {"project_id": project_id})

    assert list_result.data is not None, "List work items should return data"
    work_items_list = list_result.data
    assert isinstance(work_items_list, list), (
        f"Work items should be a list but got: {type(work_items_list)}"
    )

    listed_work_item_ids = {item["id"] for item in work_items_list}

    for work_item_id in created_work_item_ids:
        assert work_item_id in listed_work_item_ids, (
            f"Created work item {work_item_id} should be in the list but was not found. Listed IDs: {listed_work_item_ids}"
        )

    query_result = await mcp_client.call_tool(
        "list_work_items",
        {
            "project_id": project_id,
            "wiql_query": f"SELECT [System.Id], [System.Title] FROM WorkItems WHERE [System.Title] CONTAINS '{test_pattern}'",
        },
    )

    assert query_result.data is not None, "Filtered query should return data"
    filtered_items = query_result.data
    filtered_ids = {item["id"] for item in filtered_items}

    for work_item_id in created_work_item_ids:
        assert work_item_id in filtered_ids, (
            f"Work item {work_item_id} with pattern {test_pattern} should be in filtered results but was not found. Filtered IDs: {filtered_ids}"
        )

    limited_result = await mcp_client.call_tool(
        "list_work_items", {"project_id": project_id, "top": 2}
    )

    assert limited_result.data is not None, "Limited query should return data"
    limited_items = limited_result.data
    assert len(limited_items) <= 2, (
        f"Limited query should return at most 2 items but got {len(limited_items)} items"
    )

    for work_item_id in created_work_item_ids:
        get_result = await mcp_client.call_tool(
            "get_work_item", {"project_id": project_id, "work_item_id": work_item_id}
        )
        assert get_result.data is not None, (
            f"Work item {work_item_id} should exist before cleanup but was not found"
        )
        assert get_result.data["fields"]["System.Title"].startswith(test_pattern), (
            f"Work item title should start with pattern {test_pattern} but got: {get_result.data['fields']['System.Title']}"
        )


@pytest.mark.asyncio
@requires_ado_creds
async def test_list_work_items_tool_registered_in_mcp_server(mcp_client):
    tools_response = await mcp_client.list_tools()
    if hasattr(tools_response, "tools"):
        tools = tools_response.tools
    else:
        tools = tools_response
    tool_names = [tool.name for tool in tools]

    assert "list_work_items" in tool_names, (
        f"Tool 'list_work_items' should be registered but available tools are: {tool_names}"
    )
