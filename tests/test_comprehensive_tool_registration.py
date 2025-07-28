"""Comprehensive tool registration test for all MCP tools."""

import pytest
from fastmcp.client import Client

from server import mcp


@pytest.fixture
async def mcp_client():
    """Fixture to provide MCP client for testing."""
    async with Client(mcp) as client:
        yield client


class TestComprehensiveToolRegistration:
    """
    Comprehensive test suite for verifying all MCP tools are properly registered.

    This consolidates all the scattered registration tests from individual tool test files
    into a single comprehensive test that validates the complete tool registry.
    """

    async def test_all_expected_tools_are_registered(self, mcp_client: Client):
        """Test that all expected MCP tools are properly registered with the server."""
        # Get registered tools
        tools_response = await mcp_client.list_tools()
        if hasattr(tools_response, "tools"):
            tools = tools_response.tools
        else:
            tools = tools_response

        registered_tool_names = {tool.name for tool in tools}

        # Define all expected tools organized by category
        expected_tools = {
            # Organization & Authentication
            "set_ado_organization",
            "check_ado_authentication",
            # Project Management
            "list_projects",
            "find_project_by_id_or_name",
            "list_all_projects_with_metadata",
            "get_project_suggestions",
            # Pipeline Management
            "list_pipelines",
            "create_pipeline",
            "delete_pipeline",
            "get_pipeline",
            "find_pipeline_by_name",
            "list_available_pipelines",
            # Pipeline Execution
            "run_pipeline",
            "run_pipeline_by_name",
            "run_pipeline_and_get_outcome",
            "run_pipeline_and_get_outcome_by_name",
            "watch_pipeline",
            "watch_pipeline_by_name",
            "preview_pipeline",
            # Pipeline Data Extraction
            "extract_pipeline_run_data",
            "extract_pipeline_run_data_by_name",
            # Build & Log Analysis
            "get_build_by_id",
            "get_pipeline_run",
            "get_pipeline_failure_summary",
            "get_pipeline_failure_summary_by_name",
            "get_failed_step_logs",
            "get_pipeline_timeline",
            "list_pipeline_logs",
            "get_log_content_by_id",
            # Service Connections
            "list_service_connections",
            # Work Item CRUD
            "create_work_item",
            "get_work_item",
            "update_work_item",
            "delete_work_item",
            # Work Item Batch Operations
            "get_work_items_batch",
            "update_work_items_batch",
            "delete_work_items_batch",
            # Work Item Queries
            "list_work_items",
            "query_work_items",
            "get_work_items_page",
            "get_my_work_items",
            "get_recent_work_items",
            # Work Item Metadata & Types
            "list_work_item_types",
            "get_work_item_type",
            "get_work_item_type_fields",
            "get_work_item_type_field",
            "list_area_paths",
            "list_iteration_paths",
            # Work Item Comments & History
            "add_work_item_comment",
            "get_work_item_comments",
            "get_work_item_history",
            "link_work_items",
            "get_work_item_relations",
            # Process & Templates
            "get_project_process_id",
            "get_project_process_info",
            "list_processes",
            "get_process_details",
            "get_work_item_templates",
            "get_work_item_template",
            # Helper & Utility Tools
            "analyze_pipeline_input",
            "find_pipeline_by_id_and_name",
            "resolve_pipeline_from_url",
        }

        # Check for missing tools
        missing_tools = expected_tools - registered_tool_names
        assert not missing_tools, (
            f"Missing {len(missing_tools)} expected tools: {sorted(missing_tools)}"
        )

        # Check for unexpected tools (tools that are registered but not in our expected list)
        unexpected_tools = registered_tool_names - expected_tools
        if unexpected_tools:
            # This is a warning, not an error, since new tools might be added
            print(
                f"Warning: Found {len(unexpected_tools)} unexpected tools: {sorted(unexpected_tools)}"
            )

        # Verify total count matches expectations
        assert len(registered_tool_names) >= len(expected_tools), (
            f"Expected at least {len(expected_tools)} tools, but only {len(registered_tool_names)} are registered"
        )

        print(f"✅ Successfully verified {len(expected_tools)} expected tools are registered")
        if unexpected_tools:
            print(f"ℹ️  Found {len(unexpected_tools)} additional tools beyond expected set")

    async def test_removed_tools_are_not_present(self, mcp_client: Client):
        """Test that tools identified for removal are no longer registered."""
        # Get registered tools
        tools_response = await mcp_client.list_tools()
        if hasattr(tools_response, "tools"):
            tools = tools_response.tools
        else:
            tools = tools_response

        registered_tool_names = {tool.name for tool in tools}

        # Define tools that should have been removed during redundancy cleanup
        removed_tools = {
            "find_project_by_name",  # Superseded by find_project_by_id_or_name
            "list_available_projects",  # Superseded by list_all_projects_with_metadata
        }

        # Check that none of the removed tools are still present
        still_present = removed_tools & registered_tool_names
        assert not still_present, (
            f"Found {len(still_present)} tools that should have been removed: {sorted(still_present)}"
        )

        print(f"✅ Successfully verified {len(removed_tools)} removed tools are no longer present")

    async def test_tool_registration_completeness_by_category(self, mcp_client: Client):
        """Test that each functional category has expected tools registered."""
        # Get registered tools
        tools_response = await mcp_client.list_tools()
        if hasattr(tools_response, "tools"):
            tools = tools_response.tools
        else:
            tools = tools_response

        registered_tool_names = {tool.name for tool in tools}

        # Define tool categories and their expected tools
        categories = {
            "Organization & Authentication": {
                "set_ado_organization",
                "check_ado_authentication",
            },
            "Project Management": {
                "list_projects",
                "find_project_by_id_or_name",
                "list_all_projects_with_metadata",
                "get_project_suggestions",
            },
            "Pipeline Management": {
                "list_pipelines",
                "create_pipeline",
                "delete_pipeline",
                "get_pipeline",
                "find_pipeline_by_name",
                "list_available_pipelines",
            },
            "Pipeline Execution": {
                "run_pipeline",
                "run_pipeline_by_name",
                "run_pipeline_and_get_outcome",
                "run_pipeline_and_get_outcome_by_name",
                "watch_pipeline",
                "watch_pipeline_by_name",
                "preview_pipeline",
            },
            "Work Item Operations": {
                "create_work_item",
                "get_work_item",
                "update_work_item",
                "delete_work_item",
                "list_work_items",
                "query_work_items",
            },
            "Work Item Batch Operations": {
                "get_work_items_batch",
                "update_work_items_batch",
                "delete_work_items_batch",
            },
        }

        # Verify each category has all expected tools
        all_missing = []
        for category, expected_tools in categories.items():
            missing_in_category = expected_tools - registered_tool_names
            if missing_in_category:
                all_missing.extend([(category, tool) for tool in missing_in_category])
            else:
                print(f"✅ {category}: All {len(expected_tools)} tools registered")

        assert not all_missing, f"Missing tools by category: {all_missing}"

    async def test_tool_descriptions_are_present(self, mcp_client: Client):
        """Test that all registered tools have proper descriptions."""
        # Get registered tools
        tools_response = await mcp_client.list_tools()
        if hasattr(tools_response, "tools"):
            tools = tools_response.tools
        else:
            tools = tools_response

        tools_without_descriptions = []
        tools_with_short_descriptions = []

        for tool in tools:
            description = getattr(tool, "description", None)
            if not description:
                tools_without_descriptions.append(tool.name)
            elif len(description.strip()) < 20:  # Arbitrary minimum length
                tools_with_short_descriptions.append((tool.name, len(description)))

        # All tools should have descriptions
        assert not tools_without_descriptions, (
            f"Tools missing descriptions: {sorted(tools_without_descriptions)}"
        )

        # Warn about suspiciously short descriptions
        if tools_with_short_descriptions:
            print(f"⚠️  Tools with short descriptions: {tools_with_short_descriptions}")

        print(f"✅ All {len(tools)} registered tools have descriptions")

    async def test_enhanced_project_tools_properly_registered(self, mcp_client: Client):
        """Test that enhanced project tools from task 3.0 are properly registered."""
        # Get registered tools
        tools_response = await mcp_client.list_tools()
        if hasattr(tools_response, "tools"):
            tools = tools_response.tools
        else:
            tools = tools_response

        registered_tool_names = {tool.name for tool in tools}

        # Enhanced tools added in task 3.0
        enhanced_project_tools = {
            "find_project_by_id_or_name",
            "list_all_projects_with_metadata",
            "get_project_suggestions",
        }

        # Verify all enhanced tools are registered
        missing_enhanced = enhanced_project_tools - registered_tool_names
        assert not missing_enhanced, f"Missing enhanced project tools: {sorted(missing_enhanced)}"

        print(
            f"✅ All {len(enhanced_project_tools)} enhanced project tools are properly registered"
        )
