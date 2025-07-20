"""Tests for work item metadata operations."""

import os
import pytest
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


@pytest.mark.asyncio
@requires_ado_creds
async def test_list_work_item_types_returns_valid_data(mcp_client, project_id):
    result = await mcp_client.call_tool("list_work_item_types", {
        "project_id": project_id
    })
    
    assert result.data is not None, "Work item types list should return data"
    work_item_types = result.data
    assert isinstance(work_item_types, list), f"Work item types should be a list but got: {type(work_item_types)}"
    assert len(work_item_types) > 0, f"Should have at least one work item type but got: {work_item_types}"
    
    # Check structure of first work item type
    first_type = work_item_types[0]
    assert isinstance(first_type, dict), f"Work item type should be a dictionary but got: {type(first_type)}"
    assert "name" in first_type, f"Work item type should have 'name' field but got keys: {list(first_type.keys())}"
    assert "referenceName" in first_type, f"Work item type should have 'referenceName' field but got keys: {list(first_type.keys())}"
    
    # Verify we have common work item types
    type_names = [wit["name"] for wit in work_item_types]
    common_types = ["Bug", "Task", "User Story", "Feature", "Epic"]
    found_types = [t for t in common_types if t in type_names]
    assert len(found_types) >= 2, f"Should find at least 2 common work item types but found: {found_types} in {type_names}"


@pytest.mark.asyncio
@requires_ado_creds
async def test_get_work_item_type_fields_for_bug(mcp_client, project_id):
    result = await mcp_client.call_tool("get_work_item_type_fields", {
        "project_id": project_id,
        "work_item_type": "Bug"
    })
    
    assert result.data is not None, "Bug fields should return data"
    fields = result.data
    assert isinstance(fields, list), f"Fields should be a list but got: {type(fields)}"
    assert len(fields) > 0, f"Bug should have at least one field but got: {fields}"
    
    # Check structure of first field
    first_field = fields[0]
    assert isinstance(first_field, dict), f"Field should be a dictionary but got: {type(first_field)}"
    assert "referenceName" in first_field, f"Field should have 'referenceName' but got keys: {list(first_field.keys())}"
    assert "name" in first_field, f"Field should have 'name' but got keys: {list(first_field.keys())}"
    assert "type" in first_field, f"Field should have 'type' but got keys: {list(first_field.keys())}"
    
    # Verify we have required system fields
    field_refs = [field["referenceName"] for field in fields]
    required_fields = ["System.Title", "System.State", "System.WorkItemType"]
    found_fields = [f for f in required_fields if f in field_refs]
    assert len(found_fields) == len(required_fields), f"Should find all required fields {required_fields} but found: {found_fields} in {field_refs}"


@pytest.mark.asyncio
@requires_ado_creds
async def test_get_work_item_type_fields_for_task(mcp_client, project_id):
    result = await mcp_client.call_tool("get_work_item_type_fields", {
        "project_id": project_id,
        "work_item_type": "Task"
    })
    
    assert result.data is not None, "Task fields should return data"
    fields = result.data
    assert isinstance(fields, list), f"Fields should be a list but got: {type(fields)}"
    assert len(fields) > 0, f"Task should have at least one field but got: {fields}"
    
    # Check for Activity field which is common in Task work items
    field_refs = [field["referenceName"] for field in fields]
    activity_field = next((field for field in fields if field["referenceName"] == "Microsoft.VSTS.Common.Activity"), None)
    if activity_field:
        # Some fields don't have a type in the API response, which is ok
        field_type = activity_field.get("type")
        if field_type:
            assert field_type in ["String", "TreePath"], f"Activity field should be String or TreePath but got: {field_type}"


@pytest.mark.asyncio
@requires_ado_creds
async def test_get_work_item_type_fields_invalid_type(mcp_client, project_id):
    with pytest.raises(Exception) as exc_info:
        await mcp_client.call_tool("get_work_item_type_fields", {
            "project_id": project_id,
            "work_item_type": "InvalidWorkItemType"
        })
    
    assert "not found" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower(), f"Should indicate invalid work item type but got: {exc_info.value}"


@pytest.mark.asyncio
@requires_ado_creds
async def test_list_area_paths_returns_valid_data(mcp_client, project_id):
    result = await mcp_client.call_tool("list_area_paths", {
        "project_id": project_id
    })
    
    assert result.data is not None, "Area paths should return data"
    area_paths = result.data
    assert isinstance(area_paths, list), f"Area paths should be a list but got: {type(area_paths)}"
    assert len(area_paths) > 0, f"Should have at least one area path but got: {area_paths}"
    
    # Check structure of area path node
    root_node = area_paths[0]
    assert isinstance(root_node, dict), f"Area path node should be a dictionary but got: {type(root_node)}"
    assert "name" in root_node, f"Area path should have 'name' field but got keys: {list(root_node.keys())}"
    assert "path" in root_node, f"Area path should have 'path' field but got keys: {list(root_node.keys())}"


@pytest.mark.asyncio
@requires_ado_creds
async def test_list_area_paths_with_depth_limit(mcp_client, project_id):
    result = await mcp_client.call_tool("list_area_paths", {
        "project_id": project_id,
        "depth": 1
    })
    
    assert result.data is not None, "Area paths with depth should return data"
    area_paths = result.data
    assert isinstance(area_paths, list), f"Area paths should be a list but got: {type(area_paths)}"
    
    # With depth=1, we should get the root area without deep children
    if len(area_paths) > 0:
        root_node = area_paths[0]
        # The depth parameter affects how deeply nested children are included
        # At depth=1, we should get the root node but not necessarily deep nesting


@pytest.mark.asyncio
@requires_ado_creds
async def test_list_iteration_paths_returns_valid_data(mcp_client, project_id):
    result = await mcp_client.call_tool("list_iteration_paths", {
        "project_id": project_id
    })
    
    assert result.data is not None, "Iteration paths should return data"
    iteration_paths = result.data
    assert isinstance(iteration_paths, list), f"Iteration paths should be a list but got: {type(iteration_paths)}"
    assert len(iteration_paths) > 0, f"Should have at least one iteration path but got: {iteration_paths}"
    
    # Check structure of iteration path node
    root_node = iteration_paths[0]
    assert isinstance(root_node, dict), f"Iteration path node should be a dictionary but got: {type(root_node)}"
    assert "name" in root_node, f"Iteration path should have 'name' field but got keys: {list(root_node.keys())}"
    assert "path" in root_node, f"Iteration path should have 'path' field but got keys: {list(root_node.keys())}"


@pytest.mark.asyncio
@requires_ado_creds
async def test_list_iteration_paths_with_depth_limit(mcp_client, project_id):
    result = await mcp_client.call_tool("list_iteration_paths", {
        "project_id": project_id,
        "depth": 2
    })
    
    assert result.data is not None, "Iteration paths with depth should return data"
    iteration_paths = result.data
    assert isinstance(iteration_paths, list), f"Iteration paths should be a list but got: {type(iteration_paths)}"
    
    # With depth=2, we should get reasonable nesting but not infinite depth
    if len(iteration_paths) > 0:
        root_node = iteration_paths[0]
        # The depth parameter affects how deeply nested children are included


@pytest.mark.asyncio
@requires_ado_creds
async def test_metadata_tools_registered_in_mcp_server(mcp_client):
    # List all available tools
    tools_response = await mcp_client.list_tools()
    if hasattr(tools_response, "tools"):
        tools = tools_response.tools
    else:
        tools = tools_response
    tool_names = [tool.name for tool in tools]
    
    # Check that our metadata tools are registered
    expected_tools = [
        "list_work_item_types",
        "get_work_item_type_fields",
        "list_area_paths",
        "list_iteration_paths"
    ]
    
    for tool_name in expected_tools:
        assert tool_name in tool_names, f"Tool '{tool_name}' should be registered but available tools are: {tool_names}"


@pytest.mark.asyncio
@requires_ado_creds
async def test_work_item_type_field_validation_properties(mcp_client, project_id):
    result = await mcp_client.call_tool("get_work_item_type_fields", {
        "project_id": project_id,
        "work_item_type": "Bug"
    })
    
    fields = result.data
    
    # Find the System.Title field
    title_field = next((field for field in fields if field["referenceName"] == "System.Title"), None)
    assert title_field is not None, f"Should find System.Title field but available fields are: {[f['referenceName'] for f in fields]}"
    
    # Title should be required
    is_required = title_field.get("alwaysRequired", False) or title_field.get("required", False)
    assert is_required is True, f"System.Title should be required but got alwaysRequired: {title_field.get('alwaysRequired')}, required: {title_field.get('required')}"
    
    # Find the System.State field
    state_field = next((field for field in fields if field["referenceName"] == "System.State"), None)
    assert state_field is not None, f"Should find System.State field but available fields are: {[f['referenceName'] for f in fields]}"
    
    # State field should have allowed values
    allowed_values = state_field.get("allowedValues")
    if allowed_values:
        assert isinstance(allowed_values, list), f"State allowedValues should be a list but got: {type(allowed_values)}"
        assert len(allowed_values) > 0, f"State should have allowed values but got: {allowed_values}"
        # Common Bug states
        common_states = ["New", "Active", "Resolved", "Closed"]
        found_states = [state for state in common_states if state in allowed_values]
        assert len(found_states) >= 2, f"Should find at least 2 common states but found: {found_states} in {allowed_values}"