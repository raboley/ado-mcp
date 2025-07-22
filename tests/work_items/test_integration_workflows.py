"""Integration tests for end-to-end work item workflows."""

import os
import pytest
from datetime import datetime
from typing import Dict, Any, List
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
async def workflow_cleanup(mcp_client, project_id):
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
            await mcp_client.call_tool(
                "delete_work_item",
                {
                    "project_id": project_id,
                    "work_item_id": work_item_id,
                    "destroy": True,  # Permanently delete to avoid cluttering recycle bin
                },
            )
        except Exception as e:
            # Don't fail the test if cleanup fails
            print(f"Warning: Failed to cleanup work item {work_item_id}: {e}")


class TestProjectManagementWorkflow:
    """Test complete project management workflows."""

    async def test_simple_workflow_with_tasks_and_bugs(
        self, mcp_client, project_id, workflow_cleanup
    ):
        """Test simple workflow with only Task and Bug work item types."""

        # Step 1: Create main Task (using minimal required fields)
        main_task_result = await mcp_client.call_tool(
            "create_work_item",
            {
                "project_id": project_id,
                "work_item_type": "Task",
                "title": "Integration Test: Implement Customer Management Feature",
            },
        )

        main_task_id = main_task_result.data["id"]
        workflow_cleanup(main_task_id)

        assert main_task_result.data["fields"]["System.WorkItemType"] == "Task"
        assert (
            main_task_result.data["fields"]["System.Title"]
            == "Integration Test: Implement Customer Management Feature"
        )

        # Step 2: Create sub-tasks related to the main task
        sub_tasks = []
        task_templates = ["Design UI components", "Implement backend API", "Write unit tests"]

        for task_title in task_templates:
            sub_task_result = await mcp_client.call_tool(
                "create_work_item",
                {
                    "project_id": project_id,
                    "work_item_type": "Task",
                    "title": f"{task_title} for main task",
                },
            )

            sub_task_id = sub_task_result.data["id"]
            workflow_cleanup(sub_task_id)
            sub_tasks.append({"id": sub_task_id, "main_task_id": main_task_id})

            # Link sub-task to main Task using Related relationship
            await mcp_client.call_tool(
                "link_work_items",
                {
                    "project_id": project_id,
                    "source_work_item_id": main_task_id,
                    "target_work_item_id": sub_task_id,
                    "relationship_type": "System.LinkTypes.Related",
                    "comment": f"Main task breakdown into sub-task",
                },
            )

        # Step 3: Verify main task relationships
        main_task_relations = await mcp_client.call_tool(
            "get_work_item_relations", {"project_id": project_id, "work_item_id": main_task_id}
        )

        # Main task should have relationships to sub-tasks
        assert len(main_task_relations.data) >= len(sub_tasks), (
            f"Main task should have at least {len(sub_tasks)} relationships but got {len(main_task_relations.data)}"
        )

        # Step 4: Verify a sub-task has relationship to main task
        sub_task_relations = await mcp_client.call_tool(
            "get_work_item_relations",
            {"project_id": project_id, "work_item_id": sub_tasks[0]["id"]},
        )

        # Sub-task should have relationship to main task
        assert len(sub_task_relations.data) >= 1, (
            f"Sub-task should have at least 1 relationship but got {len(sub_task_relations.data)}"
        )

        # Step 5: Update main task to add tags and verify workflow
        await mcp_client.call_tool(
            "update_work_item",
            {
                "project_id": project_id,
                "work_item_id": main_task_id,
                "tags": "integration-test; customer-management",
            },
        )

        # Query all work items to verify they exist
        all_items_query = await mcp_client.call_tool(
            "query_work_items",
            {"project_id": project_id, "simple_filter": {"tags": "integration-test"}},
        )

        # Should find at least the main task (which now has the tag)
        assert len(all_items_query.data["workItems"]) >= 1, (
            "Should find work items with integration-test tag"
        )

    async def test_bug_lifecycle_workflow(self, mcp_client, project_id, workflow_cleanup):
        """Test complete bug lifecycle: Creation -> Investigation -> Resolution -> Verification."""

        # Step 1: Create Bug (minimal fields first)
        bug_result = await mcp_client.call_tool(
            "create_work_item",
            {
                "project_id": project_id,
                "work_item_type": "Bug",
                "title": "Integration Test Bug: Login fails with special characters",
            },
        )

        bug_id = bug_result.data["id"]
        workflow_cleanup(bug_id)

        assert bug_result.data["fields"]["System.WorkItemType"] == "Bug"

        # Step 2: Update bug with description and priority
        bug_update = await mcp_client.call_tool(
            "update_work_item",
            {
                "project_id": project_id,
                "work_item_id": bug_id,
                "description": "Users cannot login when password contains special characters like @#$%",
                "tags": "integration-test; login; security",
            },
        )

        # Step 3: Add comments during investigation
        await mcp_client.call_tool(
            "add_work_item_comment",
            {
                "project_id": project_id,
                "work_item_id": bug_id,
                "text": "Starting investigation. Reproduced the issue with password containing @ symbol.",
            },
        )

        await mcp_client.call_tool(
            "add_work_item_comment",
            {
                "project_id": project_id,
                "work_item_id": bug_id,
                "text": "Root cause identified: input validation regex is too restrictive. Fix in progress.",
            },
        )

        # Step 4: Create related Task for the fix
        fix_task_result = await mcp_client.call_tool(
            "create_work_item",
            {
                "project_id": project_id,
                "work_item_type": "Task",
                "title": "Fix login validation for special characters",
            },
        )

        fix_task_id = fix_task_result.data["id"]
        workflow_cleanup(fix_task_id)

        # Link Bug to Fix Task
        await mcp_client.call_tool(
            "link_work_items",
            {
                "project_id": project_id,
                "source_work_item_id": bug_id,
                "target_work_item_id": fix_task_id,
                "relationship_type": "System.LinkTypes.Related",
                "comment": "Task created to fix this bug",
            },
        )

        # Step 5: Create Test Case to verify the fix
        test_case_result = await mcp_client.call_tool(
            "create_work_item",
            {
                "project_id": project_id,
                "work_item_type": "Test Case",
                "title": "Verify login with special character passwords",
            },
        )

        test_case_id = test_case_result.data["id"]
        workflow_cleanup(test_case_id)

        # Link Test Case to Bug
        await mcp_client.call_tool(
            "link_work_items",
            {
                "project_id": project_id,
                "source_work_item_id": test_case_id,
                "target_work_item_id": bug_id,
                "relationship_type": "Microsoft.VSTS.Common.TestedBy-Forward",
                "comment": "Test case to verify bug fix",
            },
        )

        # Step 6: Update Task and Bug descriptions
        await mcp_client.call_tool(
            "update_work_item",
            {
                "project_id": project_id,
                "work_item_id": fix_task_id,
                "description": "Update regex pattern to allow special characters in passwords",
            },
        )

        # Step 7: Add final resolution comment
        await mcp_client.call_tool(
            "add_work_item_comment",
            {
                "project_id": project_id,
                "work_item_id": bug_id,
                "text": "Bug resolved. Updated validation regex pattern. Ready for testing.",
            },
        )

        # Step 8: Verify relationships and history
        bug_relations = await mcp_client.call_tool(
            "get_work_item_relations", {"project_id": project_id, "work_item_id": bug_id}
        )

        # Bug should have relationships to both Task and Test Case
        assert len(bug_relations.data) >= 2, (
            f"Bug should have at least 2 relationships but got {len(bug_relations.data)}"
        )

        # Verify comments were added
        bug_comments = await mcp_client.call_tool(
            "get_work_item_comments", {"project_id": project_id, "work_item_id": bug_id}
        )

        assert len(bug_comments.data) >= 3, (
            f"Bug should have at least 3 comments but got {len(bug_comments.data)}"
        )

        # Verify work item history
        bug_history = await mcp_client.call_tool(
            "get_work_item_history", {"project_id": project_id, "work_item_id": bug_id}
        )

        assert len(bug_history.data) >= 2, (
            f"Bug should have multiple history entries but got {len(bug_history.data)}"
        )

    async def test_dependency_management_workflow(self, mcp_client, project_id, workflow_cleanup):
        """Test dependency management between work items."""

        # Step 1: Create Tasks with dependencies (minimal fields)
        database_task = await mcp_client.call_tool(
            "create_work_item",
            {"project_id": project_id, "work_item_type": "Task", "title": "Setup database schema"},
        )

        api_task = await mcp_client.call_tool(
            "create_work_item",
            {
                "project_id": project_id,
                "work_item_type": "Task",
                "title": "Implement REST API endpoints",
            },
        )

        ui_task = await mcp_client.call_tool(
            "create_work_item",
            {"project_id": project_id, "work_item_type": "Task", "title": "Build user interface"},
        )

        db_id = database_task.data["id"]
        api_id = api_task.data["id"]
        ui_id = ui_task.data["id"]

        for work_item_id in [db_id, api_id, ui_id]:
            workflow_cleanup(work_item_id)

        # Step 2: Create dependency relationships
        # API depends on Database
        await mcp_client.call_tool(
            "link_work_items",
            {
                "project_id": project_id,
                "source_work_item_id": db_id,
                "target_work_item_id": api_id,
                "relationship_type": "System.LinkTypes.Dependency-Forward",
                "comment": "API implementation requires database to be ready",
            },
        )

        # UI depends on API
        await mcp_client.call_tool(
            "link_work_items",
            {
                "project_id": project_id,
                "source_work_item_id": api_id,
                "target_work_item_id": ui_id,
                "relationship_type": "System.LinkTypes.Dependency-Forward",
                "comment": "UI requires API endpoints to be implemented",
            },
        )

        # Step 3: Add descriptions and simulate work progress
        await mcp_client.call_tool(
            "update_work_item",
            {
                "project_id": project_id,
                "work_item_id": db_id,
                "description": "Create database tables and relationships",
                "tags": "integration-test; database",
            },
        )

        await mcp_client.call_tool(
            "add_work_item_comment",
            {
                "project_id": project_id,
                "work_item_id": db_id,
                "text": "Database schema completed. Tables created and tested.",
            },
        )

        # Update API task
        await mcp_client.call_tool(
            "update_work_item",
            {
                "project_id": project_id,
                "work_item_id": api_id,
                "description": "Create CRUD API endpoints for customer management",
                "tags": "integration-test; api",
            },
        )

        # Update UI task
        await mcp_client.call_tool(
            "update_work_item",
            {
                "project_id": project_id,
                "work_item_id": ui_id,
                "description": "Create user interface components",
                "tags": "integration-test; ui",
            },
        )

        # Step 4: Verify dependency relationships
        db_relations = await mcp_client.call_tool(
            "get_work_item_relations", {"project_id": project_id, "work_item_id": db_id}
        )

        # Database should have forward dependency to API
        dependency_relations = [rel for rel in db_relations.data if "Dependency" in rel["rel"]]
        assert len(dependency_relations) >= 1, "Database should have dependency relationship to API"

        api_relations = await mcp_client.call_tool(
            "get_work_item_relations", {"project_id": project_id, "work_item_id": api_id}
        )

        # API should have both dependency relationships (from DB and to UI)
        api_dependency_relations = [rel for rel in api_relations.data if "Dependency" in rel["rel"]]
        assert len(api_dependency_relations) >= 2, (
            "API should have dependency relationships both ways"
        )

        # Step 5: Query work items by tag to verify all are created
        tagged_items = await mcp_client.call_tool(
            "query_work_items",
            {"project_id": project_id, "simple_filter": {"tags": "integration-test"}},
        )

        assert len(tagged_items.data["workItems"]) >= 3, "Should find all tagged work items"

    async def test_batch_operations_workflow(self, mcp_client, project_id, workflow_cleanup):
        """Test batch operations for efficient bulk updates."""

        # Step 1: Create multiple work items for batch testing
        work_items = []
        for i in range(3):  # Reduce to 3 items for faster testing
            result = await mcp_client.call_tool(
                "create_work_item",
                {
                    "project_id": project_id,
                    "work_item_type": "Task",
                    "title": f"Batch Test Task {i + 1}",
                },
            )

            work_item_id = result.data["id"]
            work_items.append(work_item_id)
            workflow_cleanup(work_item_id)

        # Step 2: Get all work items in a batch
        batch_result = await mcp_client.call_tool(
            "get_work_items_batch",
            {
                "project_id": project_id,
                "work_item_ids": work_items,
                "fields": ["System.Id", "System.Title", "System.State", "System.WorkItemType"],
            },
        )

        assert len(batch_result.data) == len(work_items), (
            f"Should retrieve all {len(work_items)} work items in batch"
        )

        # Step 3: Batch update all items to Active state
        update_operations = []
        for work_item_id in work_items:
            update_operations.append(
                {
                    "work_item_id": work_item_id,
                    "operations": [
                        {
                            "op": "replace",
                            "path": "/fields/System.Description",
                            "value": "Updated via batch operation",
                        },
                        {
                            "op": "replace",
                            "path": "/fields/System.Tags",
                            "value": "integration-test; batch",
                        },
                    ],
                }
            )

        batch_update_result = await mcp_client.call_tool(
            "update_work_items_batch",
            {"project_id": project_id, "work_item_updates": update_operations},
        )

        assert len(batch_update_result.data) == len(work_items), (
            f"Should update all {len(work_items)} work items in batch"
        )

        # Step 4: Verify all items were updated
        updated_batch = await mcp_client.call_tool(
            "get_work_items_batch",
            {
                "project_id": project_id,
                "work_item_ids": work_items,
                "fields": ["System.Id", "System.Description", "System.Tags"],
            },
        )

        for item in updated_batch.data:
            assert item["fields"].get("System.Description") == "Updated via batch operation", (
                f"Work item {item['id']} should have updated description"
            )
            assert "batch" in item["fields"].get("System.Tags", ""), (
                f"Work item {item['id']} should have batch tag"
            )

        # Step 5: Query to find all batch test items
        batch_query = await mcp_client.call_tool(
            "query_work_items", {"project_id": project_id, "simple_filter": {"tags": "batch"}}
        )

        assert len(batch_query.data["workItems"]) >= len(work_items), (
            "Should find all batch test items with batch tag"
        )


class TestDataIntegrityWorkflow:
    """Test data integrity and error handling across workflows."""

    async def test_relationship_data_integrity(self, mcp_client, project_id, workflow_cleanup):
        """Test that relationships maintain data integrity."""

        # Create parent and child work items
        parent_result = await mcp_client.call_tool(
            "create_work_item",
            {
                "project_id": project_id,
                "work_item_type": "Epic",
                "title": "Data Integrity Test Epic",
            },
        )

        child_result = await mcp_client.call_tool(
            "create_work_item",
            {
                "project_id": project_id,
                "work_item_type": "User Story",
                "title": "Data Integrity Test Story",
            },
        )

        parent_id = parent_result.data["id"]
        child_id = child_result.data["id"]
        workflow_cleanup(parent_id)
        workflow_cleanup(child_id)

        # Create relationship
        await mcp_client.call_tool(
            "link_work_items",
            {
                "project_id": project_id,
                "source_work_item_id": parent_id,
                "target_work_item_id": child_id,
                "relationship_type": "System.LinkTypes.Hierarchy-Forward",
                "comment": "Parent-child relationship for data integrity test",
            },
        )

        # Verify bidirectional relationship integrity
        parent_relations = await mcp_client.call_tool(
            "get_work_item_relations", {"project_id": project_id, "work_item_id": parent_id}
        )

        child_relations = await mcp_client.call_tool(
            "get_work_item_relations", {"project_id": project_id, "work_item_id": child_id}
        )

        # Parent should have forward relationship
        forward_relations = [
            rel
            for rel in parent_relations.data
            if rel["rel"] == "System.LinkTypes.Hierarchy-Forward"
        ]
        assert len(forward_relations) >= 1, "Parent should have hierarchy-forward relationship"

        # Child should have reverse relationship
        reverse_relations = [
            rel
            for rel in child_relations.data
            if rel["rel"] == "System.LinkTypes.Hierarchy-Reverse"
        ]
        assert len(reverse_relations) >= 1, "Child should have hierarchy-reverse relationship"

    async def test_concurrent_operations_workflow(self, mcp_client, project_id, workflow_cleanup):
        """Test handling of concurrent operations on same work items."""

        # Create a work item for concurrent testing
        result = await mcp_client.call_tool(
            "create_work_item",
            {
                "project_id": project_id,
                "work_item_type": "Task",
                "title": "Concurrent Operations Test Task",
            },
        )

        work_item_id = result.data["id"]
        workflow_cleanup(work_item_id)

        # Simulate multiple rapid updates (in real concurrent scenario these would be parallel)
        updates = [
            {"description": "First update for concurrent test"},
            {"tags": "urgent"},
            {"description": "Updated description for concurrent test"},
        ]

        for i, update_data in enumerate(updates):
            await mcp_client.call_tool(
                "update_work_item",
                {"project_id": project_id, "work_item_id": work_item_id, **update_data},
            )

            # Add comment to track the update
            await mcp_client.call_tool(
                "add_work_item_comment",
                {
                    "project_id": project_id,
                    "work_item_id": work_item_id,
                    "text": f"Update {i + 1} completed",
                },
            )

        # Verify final state
        final_result = await mcp_client.call_tool(
            "get_work_item", {"project_id": project_id, "work_item_id": work_item_id}
        )

        # Should have the latest values
        assert (
            final_result.data["fields"]["System.Description"]
            == "Updated description for concurrent test"
        )
        assert "urgent" in final_result.data["fields"].get("System.Tags", "")

        # Verify all comments were added
        comments = await mcp_client.call_tool(
            "get_work_item_comments", {"project_id": project_id, "work_item_id": work_item_id}
        )

        assert len(comments.data) >= len(updates), f"Should have at least {len(updates)} comments"
