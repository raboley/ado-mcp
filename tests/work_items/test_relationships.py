"""Tests for work item relationship functionality."""

import os
import pytest
from datetime import datetime
from typing import Dict, Any
from fastmcp.client import Client

from server import mcp
from tests.ado.test_client import requires_ado_creds
from ado.work_items.models import WorkItemRelation

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
async def work_item_cleanup(mcp_client, project_id):
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
            await mcp_client.call_tool("delete_work_item", {
                "project_id": project_id,
                "work_item_id": work_item_id,
                "destroy": True  # Permanently delete to avoid cluttering recycle bin
            })
        except Exception as e:
            # Don't fail the test if cleanup fails
            print(f"Warning: Failed to cleanup work item {work_item_id}: {e}")


@pytest.fixture
async def test_work_items(mcp_client, project_id, work_item_cleanup):
    """Create multiple test work items for relationship testing."""
    work_items = []
    
    # Create an Epic (parent)
    epic_result = await mcp_client.call_tool("create_work_item", {
        "project_id": project_id,
        "work_item_type": "Epic",
        "title": "Test Epic for Relationships",
        "description": "Epic for testing work item relationships"
    })
    epic_id = epic_result.data["id"]
    work_item_cleanup(epic_id)
    work_items.append({"id": epic_id, "type": "Epic"})
    
    # Create a User Story (child)
    user_story_result = await mcp_client.call_tool("create_work_item", {
        "project_id": project_id,
        "work_item_type": "User Story",
        "title": "Test User Story for Relationships",
        "description": "User Story for testing relationships"
    })
    user_story_id = user_story_result.data["id"]
    work_item_cleanup(user_story_id)
    work_items.append({"id": user_story_id, "type": "User Story"})
    
    # Create two Tasks (for dependency testing)
    task1_result = await mcp_client.call_tool("create_work_item", {
        "project_id": project_id,
        "work_item_type": "Task",
        "title": "First Task for Dependency Testing",
        "description": "First task for testing dependencies"
    })
    task1_id = task1_result.data["id"]
    work_item_cleanup(task1_id)
    work_items.append({"id": task1_id, "type": "Task"})
    
    task2_result = await mcp_client.call_tool("create_work_item", {
        "project_id": project_id,
        "work_item_type": "Task", 
        "title": "Second Task for Dependency Testing",
        "description": "Second task for testing dependencies"
    })
    task2_id = task2_result.data["id"]
    work_item_cleanup(task2_id)
    work_items.append({"id": task2_id, "type": "Task"})
    
    return work_items


class TestWorkItemLinking:
    """Test work item linking functionality."""

    async def test_link_work_items_tool_registration(self, mcp_client):
        """Test that the link_work_items tool is properly registered."""
        tools_response = await mcp_client.list_tools()
        if hasattr(tools_response, "tools"):
            tools = tools_response.tools
        else:
            tools = tools_response
        tool_names = [tool.name for tool in tools]
        assert "link_work_items" in tool_names

    async def test_link_work_items_hierarchy_forward(self, mcp_client, project_id, test_work_items):
        """Test creating a parent-child relationship (hierarchy forward)."""
        epic_id = test_work_items[0]["id"]
        user_story_id = test_work_items[1]["id"]
        
        result = await mcp_client.call_tool("link_work_items", {
            "project_id": project_id,
            "source_work_item_id": epic_id,  # Parent
            "target_work_item_id": user_story_id,  # Child
            "relationship_type": "System.LinkTypes.Hierarchy-Forward",
            "comment": "Epic broken down into user story"
        })
        
        assert result.data is not None, f"Should successfully create hierarchy link but got: {result}"
        assert result.data["id"] == epic_id, f"Should return updated parent work item but got ID: {result.data['id']}"
        
        # Verify the relationship exists
        relations_result = await mcp_client.call_tool("get_work_item_relations", {
            "project_id": project_id,
            "work_item_id": epic_id
        })
        
        assert relations_result.data is not None, f"Should retrieve relationships but got: {relations_result}"
        assert len(relations_result.data) >= 1, f"Should have at least 1 relationship but got {len(relations_result.data)}"
        
        # Check that we have a hierarchy-forward relationship
        hierarchy_links = [rel for rel in relations_result.data if rel["rel"] == "System.LinkTypes.Hierarchy-Forward"]
        assert len(hierarchy_links) >= 1, f"Should have hierarchy-forward relationship but got relationships: {[rel['rel'] for rel in relations_result.data]}"

    async def test_link_work_items_dependency_forward(self, mcp_client, project_id, test_work_items):
        """Test creating a dependency relationship (predecessor -> successor)."""
        task1_id = test_work_items[2]["id"]  # Predecessor
        task2_id = test_work_items[3]["id"]  # Successor
        
        result = await mcp_client.call_tool("link_work_items", {
            "project_id": project_id,
            "source_work_item_id": task1_id,  # Predecessor
            "target_work_item_id": task2_id,  # Successor
            "relationship_type": "System.LinkTypes.Dependency-Forward",
            "comment": "Task 1 must complete before Task 2"
        })
        
        assert result.data is not None, f"Should successfully create dependency link but got: {result}"
        assert result.data["id"] == task1_id, f"Should return updated predecessor work item but got ID: {result.data['id']}"
        
        # Verify the relationship exists
        relations_result = await mcp_client.call_tool("get_work_item_relations", {
            "project_id": project_id,
            "work_item_id": task1_id
        })
        
        assert relations_result.data is not None, f"Should retrieve relationships but got: {relations_result}"
        assert len(relations_result.data) >= 1, f"Should have at least 1 relationship but got {len(relations_result.data)}"
        
        # Check that we have a dependency-forward relationship
        dependency_links = [rel for rel in relations_result.data if rel["rel"] == "System.LinkTypes.Dependency-Forward"]
        assert len(dependency_links) >= 1, f"Should have dependency-forward relationship but got relationships: {[rel['rel'] for rel in relations_result.data]}"

    async def test_link_work_items_related(self, mcp_client, project_id, test_work_items):
        """Test creating a related relationship."""
        task1_id = test_work_items[2]["id"]
        user_story_id = test_work_items[1]["id"]
        
        result = await mcp_client.call_tool("link_work_items", {
            "project_id": project_id,
            "source_work_item_id": task1_id,
            "target_work_item_id": user_story_id,
            "relationship_type": "System.LinkTypes.Related",
            "comment": "These work items are related"
        })
        
        assert result.data is not None, f"Should successfully create related link but got: {result}"
        assert result.data["id"] == task1_id, f"Should return updated work item but got ID: {result.data['id']}"

    async def test_link_work_items_invalid_source(self, mcp_client, project_id, test_work_items):
        """Test linking with an invalid source work item."""
        invalid_source_id = 999999
        target_id = test_work_items[0]["id"]
        
        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool("link_work_items", {
                "project_id": project_id,
                "source_work_item_id": invalid_source_id,
                "target_work_item_id": target_id,
                "relationship_type": "System.LinkTypes.Related"
            })
        
        assert "failed" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower(), f"Should fail for invalid source work item but got: {exc_info.value}"

    async def test_link_work_items_invalid_target(self, mcp_client, project_id, test_work_items):
        """Test linking with an invalid target work item."""
        source_id = test_work_items[0]["id"]
        invalid_target_id = 999999
        
        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool("link_work_items", {
                "project_id": project_id,
                "source_work_item_id": source_id,
                "target_work_item_id": invalid_target_id,
                "relationship_type": "System.LinkTypes.Related"
            })
        
        assert "failed" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower(), f"Should fail for invalid target work item but got: {exc_info.value}"


class TestWorkItemRelationRetrieval:
    """Test work item relationship retrieval functionality."""

    async def test_get_work_item_relations_tool_registration(self, mcp_client):
        """Test that the get_work_item_relations tool is properly registered."""
        tools_response = await mcp_client.list_tools()
        if hasattr(tools_response, "tools"):
            tools = tools_response.tools
        else:
            tools = tools_response
        tool_names = [tool.name for tool in tools]
        assert "get_work_item_relations" in tool_names

    async def test_get_work_item_relations_basic_functionality(self, mcp_client, project_id, test_work_items):
        """Test basic functionality of retrieving work item relationships."""
        epic_id = test_work_items[0]["id"]
        
        # First create a relationship
        await mcp_client.call_tool("link_work_items", {
            "project_id": project_id,
            "source_work_item_id": epic_id,
            "target_work_item_id": test_work_items[1]["id"],
            "relationship_type": "System.LinkTypes.Hierarchy-Forward"
        })
        
        # Now retrieve relationships
        result = await mcp_client.call_tool("get_work_item_relations", {
            "project_id": project_id,
            "work_item_id": epic_id
        })
        
        assert result.data is not None, f"Should successfully retrieve relationships but got: {result}"
        assert len(result.data) >= 1, f"Should have at least 1 relationship but got {len(result.data)}"
        
        # Verify relationship structure
        for relation in result.data:
            assert "rel" in relation, f"Each relationship should have 'rel' field but got keys: {list(relation.keys())}"
            assert "url" in relation, f"Each relationship should have 'url' field but got keys: {list(relation.keys())}"
            assert isinstance(relation["rel"], str), f"Relationship type should be string but got: {type(relation['rel'])}"
            assert isinstance(relation["url"], str), f"Relationship URL should be string but got: {type(relation['url'])}"

    async def test_get_work_item_relations_empty(self, mcp_client, project_id):
        """Test retrieving relationships for a work item with no relationships."""
        # Create a work item without any relationships
        create_result = await mcp_client.call_tool("create_work_item", {
            "project_id": project_id,
            "work_item_type": "Task",
            "title": "Test Task with No Relationships"
        })
        
        work_item_id = create_result.data["id"]
        
        result = await mcp_client.call_tool("get_work_item_relations", {
            "project_id": project_id,
            "work_item_id": work_item_id
        })
        
        assert result.data is not None, f"Should successfully retrieve empty relationships list but got: {result}"
        assert len(result.data) == 0, f"Should return empty list for work item with no relationships but got {len(result.data)} relationships"
        
        # Clean up
        await mcp_client.call_tool("delete_work_item", {
            "project_id": project_id,
            "work_item_id": work_item_id,
            "destroy": True
        })

    async def test_get_work_item_relations_invalid_work_item(self, mcp_client, project_id):
        """Test retrieving relationships for a non-existent work item."""
        invalid_work_item_id = 999999
        
        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool("get_work_item_relations", {
                "project_id": project_id,
                "work_item_id": invalid_work_item_id
            })
        
        assert "failed" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower(), f"Should fail for invalid work item ID but got: {exc_info.value}"

    async def test_get_work_item_relations_multiple_types(self, mcp_client, project_id, test_work_items):
        """Test retrieving multiple different types of relationships."""
        source_id = test_work_items[0]["id"]
        
        # Create multiple different relationships
        relationships = [
            {
                "target_id": test_work_items[1]["id"],
                "type": "System.LinkTypes.Hierarchy-Forward",
                "comment": "Epic to User Story"
            },
            {
                "target_id": test_work_items[2]["id"],
                "type": "System.LinkTypes.Related",
                "comment": "Related work"
            }
        ]
        
        # Create all the relationships
        for rel in relationships:
            await mcp_client.call_tool("link_work_items", {
                "project_id": project_id,
                "source_work_item_id": source_id,
                "target_work_item_id": rel["target_id"],
                "relationship_type": rel["type"],
                "comment": rel["comment"]
            })
        
        # Retrieve all relationships
        result = await mcp_client.call_tool("get_work_item_relations", {
            "project_id": project_id,
            "work_item_id": source_id
        })
        
        assert result.data is not None, f"Should successfully retrieve relationships but got: {result}"
        assert len(result.data) >= len(relationships), f"Should have at least {len(relationships)} relationships but got {len(result.data)}"
        
        # Verify we have both relationship types
        relation_types = [rel["rel"] for rel in result.data]
        assert "System.LinkTypes.Hierarchy-Forward" in relation_types, f"Should have hierarchy relationship but got types: {relation_types}"
        assert "System.LinkTypes.Related" in relation_types, f"Should have related relationship but got types: {relation_types}"


class TestRelationshipIntegration:
    """Test integration scenarios with relationships."""

    async def test_relationship_workflow_epic_to_story_to_task(self, mcp_client, project_id, work_item_cleanup):
        """Test a complete workflow: Epic -> User Story -> Task hierarchy."""
        
        # Create Epic
        epic_result = await mcp_client.call_tool("create_work_item", {
            "project_id": project_id,
            "work_item_type": "Epic",
            "title": "Test Epic for Workflow"
        })
        epic_id = epic_result.data["id"]
        work_item_cleanup(epic_id)
        
        # Create User Story
        story_result = await mcp_client.call_tool("create_work_item", {
            "project_id": project_id,
            "work_item_type": "User Story",
            "title": "Test User Story for Workflow"
        })
        story_id = story_result.data["id"]
        work_item_cleanup(story_id)
        
        # Create Task
        task_result = await mcp_client.call_tool("create_work_item", {
            "project_id": project_id,
            "work_item_type": "Task",
            "title": "Test Task for Workflow"
        })
        task_id = task_result.data["id"]
        work_item_cleanup(task_id)
        
        # Link Epic -> User Story
        await mcp_client.call_tool("link_work_items", {
            "project_id": project_id,
            "source_work_item_id": epic_id,
            "target_work_item_id": story_id,
            "relationship_type": "System.LinkTypes.Hierarchy-Forward",
            "comment": "Epic breakdown"
        })
        
        # Link User Story -> Task
        await mcp_client.call_tool("link_work_items", {
            "project_id": project_id,
            "source_work_item_id": story_id,
            "target_work_item_id": task_id,
            "relationship_type": "System.LinkTypes.Hierarchy-Forward",
            "comment": "Story breakdown"
        })
        
        # Verify Epic has relationship to User Story
        epic_relations = await mcp_client.call_tool("get_work_item_relations", {
            "project_id": project_id,
            "work_item_id": epic_id
        })
        
        assert len(epic_relations.data) >= 1, f"Epic should have at least 1 relationship but got {len(epic_relations.data)}"
        
        # Verify User Story has relationship to Task
        story_relations = await mcp_client.call_tool("get_work_item_relations", {
            "project_id": project_id,
            "work_item_id": story_id
        })
        
        assert len(story_relations.data) >= 1, f"User Story should have at least 1 relationship but got {len(story_relations.data)}"
        
        # Verify relationships are appropriate for each work item
        # Epic should have hierarchy-forward relationships (Epic is parent)
        epic_hierarchy_relations = [rel for rel in epic_relations.data if "Hierarchy" in rel["rel"]]
        for relation in epic_hierarchy_relations:
            assert relation["rel"] == "System.LinkTypes.Hierarchy-Forward", f"Epic relationship should be hierarchy-forward but got: {relation['rel']}"
        
        # User Story should have both forward (to Task) and potentially reverse (from Epic) relationships
        story_hierarchy_relations = [rel for rel in story_relations.data if "Hierarchy" in rel["rel"]]
        assert len(story_hierarchy_relations) >= 1, f"Story should have at least 1 hierarchy relationship but got {len(story_hierarchy_relations)}"
        
        # Verify we have the expected relationship types (either forward to child or reverse from parent)
        relation_types = [rel["rel"] for rel in story_hierarchy_relations]
        expected_types = ["System.LinkTypes.Hierarchy-Forward", "System.LinkTypes.Hierarchy-Reverse"]
        found_expected = any(rel_type in expected_types for rel_type in relation_types)
        assert found_expected, f"Story should have hierarchy relationship but got types: {relation_types}"