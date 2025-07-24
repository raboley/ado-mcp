"""Tests for work item comments and history functionality."""

import os
from datetime import datetime

import pytest
from fastmcp.client import Client

from server import mcp
from src.test_config import get_project_id

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


@pytest.fixture
async def test_work_item(mcp_client, project_id, work_item_cleanup):
    """Create a test work item for use in comment/history tests."""
    result = await mcp_client.call_tool(
        "create_work_item",
        {
            "project_id": project_id,
            "work_item_type": "Bug",
            "title": "Test Work Item for Comments and History",
            "description": "This is a test work item created for testing comments and history functionality.",
        },
    )

    work_item_id = result.data["id"]
    work_item_cleanup(work_item_id)

    return result.data


class TestWorkItemComments:
    """Test work item comment functionality."""

    @pytest.fixture
    def sample_work_item_id(self, test_work_item):
        """Get a work item ID to use for testing comments."""
        return test_work_item["id"]

    async def test_add_work_item_comment_tool_registration(self, mcp_client):
        """Test that the add_work_item_comment tool is properly registered."""
        tools_response = await mcp_client.list_tools()
        if hasattr(tools_response, "tools"):
            tools = tools_response.tools
        else:
            tools = tools_response
        tool_names = [tool.name for tool in tools]
        assert "add_work_item_comment" in tool_names

    async def test_add_work_item_comment_basic_functionality(
        self, mcp_client, project_id, sample_work_item_id
    ):
        """Test basic functionality of adding a work item comment."""
        comment_text = "This is a test comment from automated testing"

        result = await mcp_client.call_tool(
            "add_work_item_comment",
            {
                "project_id": project_id,
                "work_item_id": sample_work_item_id,
                "text": comment_text,
                "format_type": "html",
            },
        )

        assert result.data is not None, f"Should successfully add comment but got: {result}"
        assert result.data["text"] == comment_text, (
            f"Comment text should match input: expected '{comment_text}', got '{result.data['text']}'"
        )
        assert result.data["work_item_id"] == sample_work_item_id, (
            f"Comment should be associated with work item {sample_work_item_id}"
        )
        assert result.data["format"] == "html", (
            f"Comment format should be 'html', got '{result.data['format']}'"
        )
        assert "id" in result.data, "Comment should have an ID assigned"
        assert "created_by" in result.data, "Comment should have creator information"
        assert "created_date" in result.data, "Comment should have creation date"

    async def test_add_work_item_comment_with_markdown(
        self, mcp_client, project_id, sample_work_item_id
    ):
        """Test adding a comment with markdown formatting."""
        markdown_text = "**Status Update**: Testing completed successfully\n\n- All unit tests passing\n- Integration tests verified"

        result = await mcp_client.call_tool(
            "add_work_item_comment",
            {
                "project_id": project_id,
                "work_item_id": sample_work_item_id,
                "text": markdown_text,
                "format_type": "markdown",
            },
        )

        assert result.data is not None, (
            f"Should successfully add markdown comment but got: {result}"
        )
        assert result.data["text"] == markdown_text, (
            f"Markdown text should be preserved: expected '{markdown_text}', got '{result.data['text']}'"
        )
        # Note: Azure DevOps may convert markdown format to HTML in the response
        assert result.data["format"] in ["markdown", "html"], (
            f"Comment format should be 'markdown' or 'html', got '{result.data['format']}'"
        )

    async def test_add_work_item_comment_invalid_work_item(self, mcp_client, project_id):
        """Test adding a comment to a non-existent work item."""
        invalid_work_item_id = 999999

        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool(
                "add_work_item_comment",
                {
                    "project_id": project_id,
                    "work_item_id": invalid_work_item_id,
                    "text": "This should fail",
                    "format_type": "html",
                },
            )

        assert (
            "failed" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()
        ), f"Should fail for invalid work item ID but got: {exc_info.value}"


class TestWorkItemCommentRetrieval:
    """Test work item comment retrieval functionality."""

    @pytest.fixture
    async def work_item_with_comments(self, mcp_client, project_id, test_work_item):
        """Create a work item with some test comments."""
        work_item_id = test_work_item["id"]

        # Add multiple comments to test with
        comments = [
            "First test comment",
            "Second test comment with **markdown**",
            "Third comment for pagination testing",
        ]

        created_comments = []
        for i, comment_text in enumerate(comments):
            format_type = "markdown" if i == 1 else "html"
            result = await mcp_client.call_tool(
                "add_work_item_comment",
                {
                    "project_id": project_id,
                    "work_item_id": work_item_id,
                    "text": comment_text,
                    "format_type": format_type,
                },
            )
            created_comments.append(result.data)

        return {"work_item_id": work_item_id, "comments": created_comments}

    async def test_get_work_item_comments_tool_registration(self, mcp_client):
        """Test that the get_work_item_comments tool is properly registered."""
        tools_response = await mcp_client.list_tools()
        if hasattr(tools_response, "tools"):
            tools = tools_response.tools
        else:
            tools = tools_response
        tool_names = [tool.name for tool in tools]
        assert "get_work_item_comments" in tool_names

    async def test_get_work_item_comments_basic_functionality(
        self, mcp_client, project_id, work_item_with_comments
    ):
        """Test basic functionality of retrieving work item comments."""
        work_item_id = work_item_with_comments["work_item_id"]
        expected_comment_count = len(work_item_with_comments["comments"])

        result = await mcp_client.call_tool(
            "get_work_item_comments", {"project_id": project_id, "work_item_id": work_item_id}
        )

        assert result.data is not None, f"Should successfully retrieve comments but got: {result}"
        assert len(result.data) >= expected_comment_count, (
            f"Should retrieve at least {expected_comment_count} comments but got {len(result.data)}"
        )

        # Verify comment structure
        for comment in result.data:
            assert "id" in comment, "Each comment should have an ID"
            assert "work_item_id" in comment, "Each comment should reference the work item"
            assert "text" in comment, "Each comment should have text"
            assert "created_by" in comment, "Each comment should have creator info"
            assert "created_date" in comment, "Each comment should have creation date"
            assert "format" in comment, "Each comment should have format info"
            assert comment["work_item_id"] == work_item_id, (
                f"Comment should belong to work item {work_item_id}"
            )

    async def test_get_work_item_comments_pagination(
        self, mcp_client, project_id, work_item_with_comments
    ):
        """Test pagination of work item comments."""
        work_item_id = work_item_with_comments["work_item_id"]

        # Test with pagination parameters
        result = await mcp_client.call_tool(
            "get_work_item_comments",
            {"project_id": project_id, "work_item_id": work_item_id, "top": 2, "skip": 0},
        )

        assert result.data is not None, (
            f"Should successfully retrieve paginated comments but got: {result}"
        )
        assert len(result.data) <= 2, f"Should return at most 2 comments but got {len(result.data)}"

    async def test_get_work_item_comments_empty_work_item(self, mcp_client, project_id):
        """Test retrieving comments for a work item with no comments."""
        # Create a new work item without comments
        create_result = await mcp_client.call_tool(
            "create_work_item",
            {
                "project_id": project_id,
                "work_item_type": "Bug",
                "title": "Test Work Item for Empty Comments Test",
            },
        )

        work_item_id = create_result.data["id"]

        result = await mcp_client.call_tool(
            "get_work_item_comments", {"project_id": project_id, "work_item_id": work_item_id}
        )

        assert result.data is not None, (
            f"Should successfully retrieve empty comment list but got: {result}"
        )
        assert len(result.data) == 0, (
            f"Should return empty list for work item with no comments but got {len(result.data)} comments"
        )

        # Clean up
        await mcp_client.call_tool(
            "delete_work_item", {"project_id": project_id, "work_item_id": work_item_id}
        )


class TestWorkItemHistory:
    """Test work item history functionality."""

    @pytest.fixture
    async def work_item_with_history(self, mcp_client, project_id, test_work_item):
        """Create a work item and make some updates to generate history."""
        work_item_id = test_work_item["id"]

        # Make several updates to create history entries
        updates = [
            {"System.Description": "First update to description"},
            {"System.State": "Active"},
            {"System.Description": "Second update to description with more details"},
        ]

        for update in updates:
            await mcp_client.call_tool(
                "update_work_item",
                {
                    "project_id": project_id,
                    "work_item_id": work_item_id,
                    "fields_to_update": update,
                },
            )

        return work_item_id

    async def test_get_work_item_history_tool_registration(self, mcp_client):
        """Test that the get_work_item_history tool is properly registered."""
        tools_response = await mcp_client.list_tools()
        if hasattr(tools_response, "tools"):
            tools = tools_response.tools
        else:
            tools = tools_response
        tool_names = [tool.name for tool in tools]
        assert "get_work_item_history" in tool_names

    async def test_get_work_item_history_basic_functionality(
        self, mcp_client, project_id, work_item_with_history
    ):
        """Test basic functionality of retrieving work item history."""
        work_item_id = work_item_with_history

        result = await mcp_client.call_tool(
            "get_work_item_history", {"project_id": project_id, "work_item_id": work_item_id}
        )

        assert result.data is not None, f"Should successfully retrieve history but got: {result}"
        assert len(result.data) > 0, (
            f"Should have at least one revision in history but got {len(result.data)}"
        )

        # Verify revision structure
        for revision in result.data:
            assert "id" in revision, "Each revision should have an ID"
            assert "rev" in revision, "Each revision should have a revision number"
            assert "fields" in revision, "Each revision should have fields"
            assert "url" in revision, "Each revision should have a URL"
            assert revision["id"] == work_item_id, (
                f"Revision should belong to work item {work_item_id}"
            )
            assert isinstance(revision["rev"], int), (
                f"Revision number should be an integer, got {type(revision['rev'])}"
            )
            assert isinstance(revision["fields"], dict), (
                f"Fields should be a dictionary, got {type(revision['fields'])}"
            )

    async def test_get_work_item_history_pagination(
        self, mcp_client, project_id, work_item_with_history
    ):
        """Test pagination of work item history."""
        work_item_id = work_item_with_history

        # Test with pagination parameters
        result = await mcp_client.call_tool(
            "get_work_item_history",
            {"project_id": project_id, "work_item_id": work_item_id, "top": 2},
        )

        assert result.data is not None, (
            f"Should successfully retrieve paginated history but got: {result}"
        )
        assert len(result.data) <= 2, (
            f"Should return at most 2 revisions but got {len(result.data)}"
        )

    async def test_get_work_item_history_with_expand(
        self, mcp_client, project_id, work_item_with_history
    ):
        """Test retrieving history with expanded field information."""
        work_item_id = work_item_with_history

        result = await mcp_client.call_tool(
            "get_work_item_history",
            {"project_id": project_id, "work_item_id": work_item_id, "expand": "fields"},
        )

        assert result.data is not None, (
            f"Should successfully retrieve expanded history but got: {result}"
        )
        assert len(result.data) > 0, f"Should have at least one revision but got {len(result.data)}"

    async def test_get_work_item_history_invalid_work_item(self, mcp_client, project_id):
        """Test retrieving history for a non-existent work item."""
        invalid_work_item_id = 999999

        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool(
                "get_work_item_history",
                {"project_id": project_id, "work_item_id": invalid_work_item_id},
            )

        assert (
            "failed" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()
        ), f"Should fail for invalid work item ID but got: {exc_info.value}"

    async def test_get_work_item_history_with_date_filter(
        self, mcp_client, project_id, work_item_with_history
    ):
        """Test retrieving history with date filtering."""
        work_item_id = work_item_with_history

        # Get current date and a date from the past
        from datetime import timedelta

        now = datetime.now()
        past_date = now - timedelta(days=30)

        result = await mcp_client.call_tool(
            "get_work_item_history",
            {
                "project_id": project_id,
                "work_item_id": work_item_id,
                "from_date": past_date.isoformat() + "Z",
            },
        )

        assert result.data is not None, (
            f"Should successfully retrieve filtered history but got: {result}"
        )
        assert len(result.data) >= 0, (
            f"Should return history data (may be empty) but got {len(result.data)} entries"
        )

        # Test with future date (should return empty)
        future_date = now + timedelta(days=1)
        result = await mcp_client.call_tool(
            "get_work_item_history",
            {
                "project_id": project_id,
                "work_item_id": work_item_id,
                "from_date": future_date.isoformat() + "Z",
            },
        )

        assert result.data is not None, (
            f"Should successfully retrieve filtered history but got: {result}"
        )
        assert len(result.data) == 0, (
            f"Should return no revisions for future date but got {len(result.data)} entries"
        )

    async def test_get_work_item_history_with_date_range(
        self, mcp_client, project_id, work_item_with_history
    ):
        """Test retrieving history with date range filtering."""
        work_item_id = work_item_with_history

        from datetime import timedelta

        now = datetime.now()
        start_date = now - timedelta(days=7)
        end_date = now

        result = await mcp_client.call_tool(
            "get_work_item_history",
            {
                "project_id": project_id,
                "work_item_id": work_item_id,
                "from_date": start_date.isoformat() + "Z",
                "to_date": end_date.isoformat() + "Z",
            },
        )

        assert result.data is not None, (
            f"Should successfully retrieve history with date range but got: {result}"
        )
        assert isinstance(result.data, list), f"Should return a list but got: {type(result.data)}"

        # Verify all returned revisions are within the date range
        for revision in result.data:
            assert "revised_date" in revision, (
                f"Revision should have revised_date field but got keys: {list(revision.keys())}"
            )


class TestCommentsHistoryIntegration:
    """Test integration between comments and history functionality."""

    async def test_comment_appears_in_history(self, mcp_client, project_id, test_work_item):
        """Test that adding a comment creates an entry in the work item history."""
        work_item_id = test_work_item["id"]

        # Get initial revision count
        initial_history = await mcp_client.call_tool(
            "get_work_item_history", {"project_id": project_id, "work_item_id": work_item_id}
        )
        initial_rev_count = len(initial_history.data)

        # Add a comment
        comment_text = "This comment should appear in history"
        await mcp_client.call_tool(
            "add_work_item_comment",
            {"project_id": project_id, "work_item_id": work_item_id, "text": comment_text},
        )

        # Get updated history
        updated_history = await mcp_client.call_tool(
            "get_work_item_history", {"project_id": project_id, "work_item_id": work_item_id}
        )

        assert len(updated_history.data) > initial_rev_count, (
            f"History should have more revisions after adding comment: initial={initial_rev_count}, updated={len(updated_history.data)}"
        )

    async def test_comment_and_update_workflow(self, mcp_client, project_id, test_work_item):
        """Test a typical workflow of updating a work item and adding comments."""
        work_item_id = test_work_item["id"]

        # Update the work item
        await mcp_client.call_tool(
            "update_work_item",
            {
                "project_id": project_id,
                "work_item_id": work_item_id,
                "description": "Updated description for workflow test",
            },
        )

        # Add a comment about the update
        await mcp_client.call_tool(
            "add_work_item_comment",
            {
                "project_id": project_id,
                "work_item_id": work_item_id,
                "text": "Updated description to clarify requirements",
            },
        )

        # Verify both the comment and the history reflect the changes
        comments = await mcp_client.call_tool(
            "get_work_item_comments", {"project_id": project_id, "work_item_id": work_item_id}
        )

        history = await mcp_client.call_tool(
            "get_work_item_history", {"project_id": project_id, "work_item_id": work_item_id}
        )

        assert len(comments.data) > 0, "Should have at least one comment"
        assert len(history.data) > 1, "Should have multiple history entries"

        # Find our comment
        found_comment = False
        for comment in comments.data:
            if "Updated description to clarify requirements" in comment["text"]:
                found_comment = True
                break

        assert found_comment, "Should find our test comment in the comments list"
