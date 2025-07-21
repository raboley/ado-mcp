"""Tests for enhanced work item type and field introspection functionality."""

import pytest
from fastmcp.client import Client

from server import mcp
from tests.ado.test_client import requires_ado_creds

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def mcp_client():
    async with Client(mcp) as client:
        org_url = "https://dev.azure.com/RussellBoley"
        await client.call_tool("set_ado_organization", {"organization_url": org_url})
        yield client


@pytest.fixture
def project_id():
    return "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project


class TestEnhancedWorkItemTypeIntrospection:
    """Test enhanced work item type introspection tools."""

    async def test_enhanced_type_tools_registered_in_mcp_server(self, mcp_client):
        """Test that the new enhanced type tools are registered."""
        tools_response = await mcp_client.list_tools()
        if hasattr(tools_response, "tools"):
            tools = tools_response.tools
        else:
            tools = tools_response
        tool_names = [tool.name for tool in tools]
        
        expected_tools = [
            "get_work_item_type",
            "get_work_item_type_field"
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names, f"Tool '{expected_tool}' should be registered in MCP server"

    async def test_get_work_item_type_returns_detailed_info(self, mcp_client, project_id):
        """Test getting detailed information about a specific work item type."""
        result = await mcp_client.call_tool("get_work_item_type", {
            "project_id": project_id,
            "work_item_type": "Bug"
        })
        
        assert result.data is not None, f"Should return work item type details but got: {result}"
        
        # Verify required fields (result.data is a Pydantic model object)
        assert hasattr(result.data, 'name'), "Work item type should have name attribute"
        assert hasattr(result.data, 'referenceName'), "Work item type should have referenceName attribute"
        assert result.data.name == "Bug", f"Name should be 'Bug' but got: {result.data.name}"
        
        # Verify detailed fields that should be present with expand parameter
        optional_fields = ["color", "icon", "states", "transitions"]
        for field in optional_fields:
            if hasattr(result.data, field) and getattr(result.data, field) is not None:
                field_value = getattr(result.data, field)
                if field == "states":
                    assert isinstance(field_value, list), f"States should be list but got: {type(field_value)}"
                    if len(field_value) > 0:
                        # States can be complex objects, just verify it's not empty
                        pass
                elif field == "transitions":
                    assert isinstance(field_value, dict), f"Transitions should be dict but got: {type(field_value)}"

    async def test_get_work_item_type_for_task_type(self, mcp_client, project_id):
        """Test getting detailed information for Task work item type."""
        result = await mcp_client.call_tool("get_work_item_type", {
            "project_id": project_id,
            "work_item_type": "Task"
        })
        
        assert result.data is not None, f"Should return Task work item type details but got: {result}"
        assert result.data.name == "Task", f"Name should be 'Task' but got: {result.data.name}"
        
        # Task should have a reference name
        assert hasattr(result.data, 'referenceName'), "Task should have referenceName attribute"
        assert result.data.referenceName is not None, "Task reference name should not be None"

    async def test_get_work_item_type_invalid_type(self, mcp_client, project_id):
        """Test getting work item type with invalid type name."""
        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool("get_work_item_type", {
                "project_id": project_id,
                "work_item_type": "NonexistentWorkItemType"
            })
        
        assert "failed" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()

    async def test_get_work_item_type_invalid_project(self, mcp_client):
        """Test getting work item type with invalid project."""
        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool("get_work_item_type", {
                "project_id": "nonexistent-project",
                "work_item_type": "Bug"
            })
        
        assert "failed" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()


class TestEnhancedFieldIntrospection:
    """Test enhanced field introspection tools."""

    async def test_get_work_item_type_field_system_title(self, mcp_client, project_id):
        """Test getting detailed information about the System.Title field."""
        result = await mcp_client.call_tool("get_work_item_type_field", {
            "project_id": project_id,
            "work_item_type": "Bug",
            "field_reference_name": "System.Title"
        })
        
        assert result.data is not None, f"Should return field details but got: {result}"
        
        # Verify required fields (result.data is a Pydantic model object)
        assert hasattr(result.data, 'name'), "Field should have name attribute"
        assert hasattr(result.data, 'referenceName'), "Field should have referenceName attribute"
        assert result.data.referenceName == "System.Title", f"Reference name should be 'System.Title' but got: {result.data.referenceName}"
        
        # Title field should be required
        if hasattr(result.data, 'required'):
            # Title is typically required for most work item types
            pass  # We don't assert True here as it may vary by configuration
        
        # Verify field type information
        if hasattr(result.data, 'type') and result.data.type:
            assert isinstance(result.data.type, str), "Field type should be string"

    async def test_get_work_item_type_field_system_state(self, mcp_client, project_id):
        """Test getting detailed information about the System.State field."""
        result = await mcp_client.call_tool("get_work_item_type_field", {
            "project_id": project_id,
            "work_item_type": "Bug",
            "field_reference_name": "System.State"
        })
        
        assert result.data is not None, f"Should return State field details but got: {result}"
        assert result.data.referenceName == "System.State", f"Reference name should be 'System.State' but got: {result.data.referenceName}"
        
        # State field should have allowed values
        if hasattr(result.data, 'allowedValues') and result.data.allowedValues:
            allowed_values = result.data.allowedValues
            assert isinstance(allowed_values, list), f"Allowed values should be list but got: {type(allowed_values)}"
            assert len(allowed_values) > 0, "State field should have allowed values"
            
            # Common bug states
            state_names = [str(val) for val in allowed_values]
            # Don't assert specific states as they may vary by process template

    async def test_get_work_item_type_field_priority(self, mcp_client, project_id):
        """Test getting detailed information about the Priority field."""
        result = await mcp_client.call_tool("get_work_item_type_field", {
            "project_id": project_id,
            "work_item_type": "Bug",
            "field_reference_name": "Microsoft.VSTS.Common.Priority"
        })
        
        assert result.data is not None, f"Should return Priority field details but got: {result}"
        assert result.data.referenceName == "Microsoft.VSTS.Common.Priority", f"Reference name should match but got: {result.data.referenceName}"
        
        # Priority field typically has allowed values (1, 2, 3, 4)
        if hasattr(result.data, 'allowedValues') and result.data.allowedValues:
            allowed_values = result.data.allowedValues
            assert isinstance(allowed_values, list), "Priority allowed values should be list"

    async def test_get_work_item_type_field_invalid_field(self, mcp_client, project_id):
        """Test getting field details with invalid field reference name."""
        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool("get_work_item_type_field", {
                "project_id": project_id,
                "work_item_type": "Bug",
                "field_reference_name": "System.NonexistentField"
            })
        
        assert "failed" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()

    async def test_get_work_item_type_field_invalid_work_item_type(self, mcp_client, project_id):
        """Test getting field details with invalid work item type."""
        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool("get_work_item_type_field", {
                "project_id": project_id,
                "work_item_type": "NonexistentType",
                "field_reference_name": "System.Title"
            })
        
        assert "failed" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()

    async def test_get_work_item_type_field_invalid_project(self, mcp_client):
        """Test getting field details with invalid project."""
        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool("get_work_item_type_field", {
                "project_id": "nonexistent-project",
                "work_item_type": "Bug",
                "field_reference_name": "System.Title"
            })
        
        assert "failed" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()


class TestEnhancedTypeIntegration:
    """Test integration scenarios for enhanced work item type functionality."""

    async def test_compare_list_vs_detailed_work_item_type(self, mcp_client, project_id):
        """Test comparing list_work_item_types vs get_work_item_type for detail level."""
        # Get basic info from list
        list_result = await mcp_client.call_tool("list_work_item_types", {
            "project_id": project_id
        })
        
        # Find Bug in the list
        bug_from_list = None
        for work_item_type in list_result.data:
            if work_item_type["name"] == "Bug":
                bug_from_list = work_item_type
                break
        
        assert bug_from_list is not None, "Bug should be found in work item types list"
        
        # Get detailed info for Bug
        detailed_result = await mcp_client.call_tool("get_work_item_type", {
            "project_id": project_id,
            "work_item_type": "Bug"
        })
        
        bug_detailed = detailed_result.data
        
        # Both should have the same basic info
        assert bug_from_list["name"] == bug_detailed.name, "Names should match"
        assert bug_from_list["referenceName"] == bug_detailed.referenceName, "Reference names should match"
        
        # Detailed version should potentially have more information
        # (though this depends on the expand parameter and API response)

    async def test_get_type_then_get_field_workflow(self, mcp_client, project_id):
        """Test workflow: get work item type, then get details about one of its fields."""
        # Step 1: Get detailed work item type
        type_result = await mcp_client.call_tool("get_work_item_type", {
            "project_id": project_id,
            "work_item_type": "Bug"
        })
        
        assert type_result.data is not None, "Should get Bug work item type details"
        
        # Step 2: Get detailed field information
        field_result = await mcp_client.call_tool("get_work_item_type_field", {
            "project_id": project_id,
            "work_item_type": "Bug",
            "field_reference_name": "System.State"
        })
        
        assert field_result.data is not None, "Should get State field details"
        
        # Both results should be consistent
        assert field_result.data.referenceName == "System.State", "Field reference name should match"
        
        # If the work item type has state information and the field has allowed values,
        # they should be related (though the format may differ)