"""Tests for Azure DevOps processes functionality."""

import logging
import os
import pytest
from fastmcp.client import Client

from server import mcp
from src.test_config import get_project_id
from tests.ado.test_client import requires_ado_creds

logger = logging.getLogger(__name__)

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
    return get_project_id()  # ado-mcp project

class TestProcessDiscovery:
    """Test process discovery functionality."""

    async def test_process_tools_registered_in_mcp_server(self, mcp_client):
        """Test that all process tools are properly registered."""
        tools_response = await mcp_client.list_tools()
        if hasattr(tools_response, "tools"):
            tools = tools_response.tools
        else:
            tools = tools_response
        tool_names = [tool.name for tool in tools]

        expected_tools = [
            "get_project_process_id",
            "get_project_process_info",
            "list_processes",
            "get_process_details",
            "get_work_item_templates",
            "get_work_item_template",
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names, f"Tool '{expected_tool}' should be registered"

    async def test_get_project_process_id_returns_valid_id(self, mcp_client, project_id):
        """Test getting project process ID returns a valid UUID."""
        result = await mcp_client.call_tool("get_project_process_id", {"project_id": project_id})

        assert result.data is not None, f"Should return process ID but got: {result}"
        assert isinstance(result.data, str), (
            f"Process ID should be string but got: {type(result.data)}"
        )
        assert len(result.data) > 0, "Process ID should not be empty"

        # Should be a UUID format (8-4-4-4-12 characters)
        import re

        uuid_pattern = (
            r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
        )
        assert re.match(uuid_pattern, result.data), (
            f"Process ID should be UUID format but got: {result.data}"
        )

    async def test_get_project_process_info_returns_complete_info(self, mcp_client, project_id):
        """Test getting comprehensive project process information."""
        result = await mcp_client.call_tool("get_project_process_info", {"project_id": project_id})

        assert result.data is not None, f"Should return process info but got: {result}"

        # Verify required fields
        assert "projectId" in result.data, "Should include project ID"
        assert "currentProcessTemplateId" in result.data, (
            "Should include current process template ID"
        )
        assert result.data["projectId"] == project_id, "Project ID should match input"

        # Current process template ID should be valid UUID
        current_process_id = result.data["currentProcessTemplateId"]
        assert current_process_id is not None, "Current process template ID should not be None"
        assert isinstance(current_process_id, str), "Current process template ID should be string"

        # Optional fields that might be present
        optional_fields = [
            "originalProcessTemplateId",
            "processTemplateName",
            "processTemplateType",
        ]
        for field in optional_fields:
            if field in result.data:
                assert result.data[field] is None or isinstance(result.data[field], str), (
                    f"Field '{field}' should be string or None"
                )

    async def test_list_processes_returns_valid_data(self, mcp_client):
        """Test listing available processes returns valid data."""
        result = await mcp_client.call_tool("list_processes", {})

        assert result.data is not None, f"Should return processes list but got: {result}"
        assert isinstance(result.data, list), (
            f"Processes should be list but got: {type(result.data)}"
        )
        assert len(result.data) > 0, "Should return at least one process"

        # Verify structure of first process
        first_process = result.data[0]
        required_fields = ["id", "name"]
        for field in required_fields:
            assert field in first_process, f"Process should have '{field}' field"
            assert first_process[field] is not None, f"Process '{field}' should not be None"
            assert isinstance(first_process[field], str), f"Process '{field}' should be string"

        # Verify optional fields if present
        optional_fields = ["description", "type", "isDefault", "isEnabled"]
        for field in optional_fields:
            if field in first_process and first_process[field] is not None:
                if field in ["isDefault", "isEnabled"]:
                    assert isinstance(first_process[field], bool), (
                        f"Process '{field}' should be boolean"
                    )
                else:
                    assert isinstance(first_process[field], str), (
                        f"Process '{field}' should be string"
                    )

    async def test_get_process_details_with_valid_process_id(self, mcp_client, project_id):
        """Test getting process details with a valid process ID."""
        # First get the project's process ID
        process_id_result = await mcp_client.call_tool(
            "get_project_process_id", {"project_id": project_id}
        )
        process_id = process_id_result.data

        # Now get detailed process information
        result = await mcp_client.call_tool("get_process_details", {"process_id": process_id})

        assert result.data is not None, f"Should return process details but got: {result}"

        # Verify required fields
        assert "id" in result.data, "Process should have ID"
        assert "name" in result.data, "Process should have name"
        assert result.data["id"] == process_id, "Process ID should match input"
        assert isinstance(result.data["name"], str), "Process name should be string"
        assert len(result.data["name"]) > 0, "Process name should not be empty"

    async def test_get_process_details_with_invalid_process_id(self, mcp_client):
        """Test getting process details with invalid process ID."""
        invalid_process_id = "00000000-0000-0000-0000-000000000000"

        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool("get_process_details", {"process_id": invalid_process_id})

        assert "failed" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()

    async def test_get_project_process_id_with_invalid_project(self, mcp_client):
        """Test getting process ID with invalid project."""
        invalid_project_id = "nonexistent-project"

        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool("get_project_process_id", {"project_id": invalid_project_id})

        assert "failed" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()

class TestWorkItemTemplates:
    """Test work item template functionality."""

    async def test_get_work_item_templates_returns_list(self, mcp_client, project_id):
        """Test getting work item templates returns a valid list."""
        result = await mcp_client.call_tool("get_work_item_templates", {"project_id": project_id})

        assert result.data is not None, f"Should return templates list but got: {result}"
        assert isinstance(result.data, list), (
            f"Templates should be list but got: {type(result.data)}"
        )
        # Note: It's OK if there are no templates, some projects might not have any

        # If templates exist, verify structure
        if len(result.data) > 0:
            first_template = result.data[0]
            required_fields = ["id", "name", "workItemTypeName"]
            for field in required_fields:
                assert field in first_template, f"Template should have '{field}' field"
                assert first_template[field] is not None, f"Template '{field}' should not be None"
                assert isinstance(first_template[field], str), (
                    f"Template '{field}' should be string"
                )

            # Fields should have defaults
            assert "fields" in first_template, "Template should have 'fields' field"
            assert isinstance(first_template["fields"], dict), "Template fields should be dict"

    async def test_get_work_item_templates_with_type_filter(self, mcp_client, project_id):
        """Test getting work item templates filtered by type."""
        result = await mcp_client.call_tool(
            "get_work_item_templates", {"project_id": project_id, "work_item_type": "Task"}
        )

        assert result.data is not None, f"Should return templates list but got: {result}"
        assert isinstance(result.data, list), (
            f"Templates should be list but got: {type(result.data)}"
        )

        # All templates should be for Task type if any exist
        for template in result.data:
            assert template["workItemTypeName"] == "Task", (
                f"All templates should be for Task type but got: {template['workItemTypeName']}"
            )

    async def test_get_work_item_template_with_invalid_template_id(self, mcp_client, project_id):
        """Test getting specific template with invalid ID."""
        invalid_template_id = "00000000-0000-0000-0000-000000000000"

        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool(
                "get_work_item_template",
                {"project_id": project_id, "template_id": invalid_template_id},
            )

        assert "failed" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()

    async def test_get_work_item_templates_with_invalid_project(self, mcp_client):
        """Test getting templates with invalid project."""
        invalid_project_id = "nonexistent-project"

        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool(
                "get_work_item_templates", {"project_id": invalid_project_id}
            )

        assert "failed" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()

class TestProcessIntegration:
    """Test integration scenarios for processes."""

    async def test_project_process_workflow(self, mcp_client, project_id):
        """Test complete workflow: get project process, then get process details."""
        # Step 1: Get project process ID
        process_id_result = await mcp_client.call_tool(
            "get_project_process_id", {"project_id": project_id}
        )
        process_id = process_id_result.data

        # Step 2: Get comprehensive project process info
        process_info_result = await mcp_client.call_tool(
            "get_project_process_info", {"project_id": project_id}
        )

        # Process IDs should match
        assert process_info_result.data["currentProcessTemplateId"] == process_id, (
            "Process IDs should match"
        )

        # Step 3: Get detailed process information
        process_details_result = await mcp_client.call_tool(
            "get_process_details", {"process_id": process_id}
        )

        # Process details should have the same ID
        assert process_details_result.data["id"] == process_id, "Process detail ID should match"

        # If process info has a name, it should match process details
        if (
            "processTemplateName" in process_info_result.data
            and process_info_result.data["processTemplateName"]
        ):
            process_name_from_info = process_info_result.data["processTemplateName"]
            process_name_from_details = process_details_result.data["name"]
            assert process_name_from_info == process_name_from_details, (
                f"Process names should match: '{process_name_from_info}' vs '{process_name_from_details}'"
            )

    async def test_list_all_processes_then_get_project_process(self, mcp_client, project_id):
        """Test listing all processes and checking project's process compatibility."""
        # Step 1: List all available processes
        all_processes_result = await mcp_client.call_tool("list_processes", {})
        all_processes = all_processes_result.data

        # Step 2: Get project's process ID
        project_process_id_result = await mcp_client.call_tool(
            "get_project_process_id", {"project_id": project_id}
        )
        project_process_id = project_process_id_result.data

        # Step 3: Get comprehensive project process info
        project_process_info_result = await mcp_client.call_tool(
            "get_project_process_info", {"project_id": project_id}
        )
        project_process_info = project_process_info_result.data

        # Step 4: Try to find the project's process in the list
        project_process_found = False
        for process in all_processes:
            if process["id"] == project_process_id:
                project_process_found = True
                # Verify the process exists in the list and has required fields
                assert "name" in process, "Process in list should have name"
                assert isinstance(process["name"], str), "Process name should be string"
                break

        # If not found in base processes list, check if it might be a custom process
        if not project_process_found:
            # This is acceptable - projects can use custom process templates
            # that are derived from base processes but have their own IDs
            logger.info(
                f"Project uses custom process template '{project_process_id}' not found in base process list"
            )

            # The process should still be accessible via get_process_details (with fallback)
            process_details_result = await mcp_client.call_tool(
                "get_process_details", {"process_id": project_process_id}
            )
            assert process_details_result.data is not None, (
                "Should be able to get process details even for custom processes"
            )
            assert process_details_result.data["id"] == project_process_id, (
                "Process details ID should match requested ID"
            )
        else:
            # If found in base processes, verify it matches
            assert project_process_found, (
                f"Project's process ID '{project_process_id}' should be found in organization's process list"
            )
