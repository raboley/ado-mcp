"""MCP tool definitions for Azure DevOps Work Items comments and history operations."""

import logging
from typing import Any, Dict, List, Optional

from ado.work_items.client import WorkItemsClient
from ado.work_items.models import (
    WorkItemComment,
    WorkItemRevision,
    WorkItem,
    WorkItemRelation,
)
from ado.work_items.validation import WorkItemValidator

logger = logging.getLogger(__name__)


def register_comment_tools(mcp_instance, client_container):
    """
    Register comment and history related tools with the FastMCP instance.

    Args:
        mcp_instance: The FastMCP instance to register tools with.
        client_container: Dictionary holding the AdoClient instance.
    """

    @mcp_instance.tool
    def add_work_item_comment(
        project_id: str, work_item_id: int, text: str, format_type: str = "html"
    ) -> Optional[WorkItemComment]:
        """
        Add a comment to a work item.

        This tool allows you to add comments to work items with support for HTML
        or Markdown formatting. Comments are useful for documenting automated actions,
        providing status updates, or communicating with team members.

        Args:
            project_id: The ID or name of the project.
            work_item_id: The ID of the work item to add a comment to.
            text: The comment text (supports HTML/Markdown formatting).
            format_type: The format of the comment text ("html" or "markdown").
                       Default is "html".

        Returns:
            WorkItemComment: The created comment object, or None if client unavailable.

        Examples:
            # Add a simple HTML comment
            add_work_item_comment(
                project_id="MyProject",
                work_item_id=123,
                text="<p>Updated the implementation to fix the login issue.</p>",
                format_type="html"
            )

            # Add a markdown comment
            add_work_item_comment(
                project_id="MyProject",
                work_item_id=456,
                text="**Status Update**: Testing completed successfully\n\n- All unit tests passing\n- Integration tests verified",
                format_type="markdown"
            )
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None

        try:
            work_items_client = WorkItemsClient(ado_client_instance)

            comment = work_items_client.add_work_item_comment(
                project_id=project_id, work_item_id=work_item_id, text=text, format_type=format_type
            )

            logger.info(f"Successfully added comment to work item #{work_item_id}")
            return comment

        except Exception as e:
            logger.error(f"Failed to add comment to work item {work_item_id}: {e}")
            raise

    @mcp_instance.tool
    def get_work_item_comments(
        project_id: str,
        work_item_id: int,
        top: Optional[int] = None,
        skip: Optional[int] = None,
        include_deleted: bool = False,
    ) -> Optional[List[WorkItemComment]]:
        """
        Get comments for a work item.

        This tool retrieves all comments for a specific work item, with support
        for pagination and optional inclusion of deleted comments.

        Args:
            project_id: The ID or name of the project.
            work_item_id: The ID of the work item to get comments for.
            top: Maximum number of comments to return (for pagination).
            skip: Number of comments to skip (for pagination).
            include_deleted: Whether to include deleted comments in the results.
                           Default is False.

        Returns:
            List[WorkItemComment]: List of comments for the work item,
                                 or None if client unavailable.

        Examples:
            # Get all comments for a work item
            get_work_item_comments(
                project_id="MyProject",
                work_item_id=123
            )

            # Get paginated comments (10 comments starting from the 5th)
            get_work_item_comments(
                project_id="MyProject",
                work_item_id=123,
                top=10,
                skip=5
            )

            # Include deleted comments
            get_work_item_comments(
                project_id="MyProject",
                work_item_id=123,
                include_deleted=True
            )
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None

        try:
            work_items_client = WorkItemsClient(ado_client_instance)

            comments = work_items_client.get_work_item_comments(
                project_id=project_id,
                work_item_id=work_item_id,
                top=top,
                skip=skip,
                include_deleted=include_deleted,
            )

            logger.info(
                f"Successfully retrieved {len(comments)} comments for work item #{work_item_id}"
            )
            return comments

        except Exception as e:
            logger.error(f"Failed to get comments for work item {work_item_id}: {e}")
            raise

    @mcp_instance.tool
    def get_work_item_history(
        project_id: str,
        work_item_id: int,
        top: Optional[int] = None,
        skip: Optional[int] = None,
        expand: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> Optional[List[WorkItemRevision]]:
        """
        Get revision history for a work item with optional date filtering.

        This tool retrieves the complete revision history for a work item, showing
        what changed, when, and by whom. Each revision represents a snapshot of
        the work item at a specific point in time.

        Args:
            project_id: The ID or name of the project.
            work_item_id: The ID of the work item to get history for.
            top: Maximum number of revisions to return (for pagination).
            skip: Number of revisions to skip (for pagination).
            expand: Additional data to include (e.g., "fields" for detailed field information).
            from_date: Filter revisions from this date onwards (ISO 8601 format).
            to_date: Filter revisions up to this date (ISO 8601 format).

        Returns:
            List[WorkItemRevision]: List of revisions for the work item,
                                  or None if client unavailable.

        Examples:
            # Get full revision history
            get_work_item_history(
                project_id="MyProject",
                work_item_id=123
            )

            # Get recent revisions (last 5)
            get_work_item_history(
                project_id="MyProject",
                work_item_id=123,
                top=5
            )

            # Get revisions with expanded field information
            get_work_item_history(
                project_id="MyProject",
                work_item_id=123,
                expand="fields"
            )

            # Get revisions within a date range
            get_work_item_history(
                project_id="MyProject",
                work_item_id=123,
                from_date="2024-01-01T00:00:00Z",
                to_date="2024-01-31T23:59:59Z"
            )
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None

        try:
            work_items_client = WorkItemsClient(ado_client_instance)

            revisions = work_items_client.get_work_item_revisions(
                project_id=project_id,
                work_item_id=work_item_id,
                top=top,
                skip=skip,
                expand=expand,
                from_date=from_date,
                to_date=to_date,
            )

            logger.info(
                f"Successfully retrieved {len(revisions)} revisions for work item #{work_item_id}"
            )
            return revisions

        except Exception as e:
            logger.error(f"Failed to get history for work item {work_item_id}: {e}")
            raise

    @mcp_instance.tool
    def link_work_items(
        project_id: str,
        source_work_item_id: int,
        target_work_item_id: int,
        relationship_type: str,
        comment: Optional[str] = None,
    ) -> Optional[WorkItem]:
        """
        Create a link between two work items.

        This tool creates a relationship between two work items. Common relationship types
        include parent-child hierarchies, dependencies, and general related links.

        Args:
            project_id: The ID or name of the project.
            source_work_item_id: The ID of the source work item (the one getting the new relationship).
            target_work_item_id: The ID of the target work item (the one being linked to).
            relationship_type: The type of relationship. Common types:
                             - "System.LinkTypes.Hierarchy-Forward" (Parent -> Child)
                             - "System.LinkTypes.Hierarchy-Reverse" (Child -> Parent)
                             - "System.LinkTypes.Related" (Related)
                             - "System.LinkTypes.Dependency-Forward" (Predecessor -> Successor)
                             - "System.LinkTypes.Dependency-Reverse" (Successor -> Predecessor)
            comment: Optional comment to describe the relationship.

        Returns:
            WorkItem: The updated source work item with the new relationship,
                     or None if client unavailable.

        Examples:
            # Create a parent-child relationship
            link_work_items(
                project_id="MyProject",
                source_work_item_id=123,  # Parent
                target_work_item_id=124,  # Child
                relationship_type="System.LinkTypes.Hierarchy-Forward",
                comment="Breaking down epic into user story"
            )

            # Create a dependency relationship
            link_work_items(
                project_id="MyProject",
                source_work_item_id=125,  # Predecessor
                target_work_item_id=126,  # Successor
                relationship_type="System.LinkTypes.Dependency-Forward",
                comment="This task must complete before the next one"
            )

            # Create a related link
            link_work_items(
                project_id="MyProject",
                source_work_item_id=127,
                target_work_item_id=128,
                relationship_type="System.LinkTypes.Related",
                comment="These work items are related"
            )
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None

        try:
            work_items_client = WorkItemsClient(ado_client_instance)

            # Validate relationship type first
            if not WorkItemValidator.validate_relationship_type(relationship_type):
                logger.error(f"Invalid relationship type: {relationship_type}")
                valid_types = WorkItemValidator.get_valid_relationship_types()
                raise ValueError(
                    f"Invalid relationship type '{relationship_type}'. Valid types: {', '.join(valid_types[:5])}..."
                )

            # Get work item types for validation
            try:
                source_work_item = work_items_client.get_work_item(project_id, source_work_item_id)
                target_work_item = work_items_client.get_work_item(project_id, target_work_item_id)

                source_type = source_work_item.fields.get("System.WorkItemType", "Unknown")
                target_type = target_work_item.fields.get("System.WorkItemType", "Unknown")

                # Validate relationship constraints
                is_valid, error_message = WorkItemValidator.validate_relationship_constraints(
                    source_type, target_type, relationship_type
                )

                if not is_valid and error_message:
                    logger.warning(f"Relationship constraint warning: {error_message}")
                    # Get suggestions for better user experience
                    suggestions = WorkItemValidator.suggest_relationship_types(
                        source_type, target_type
                    )
                    if suggestions:
                        suggestion_text = ", ".join(
                            [f"{rel} ({desc})" for rel, desc in suggestions[:3]]
                        )
                        logger.info(
                            f"Suggested relationships for {source_type} -> {target_type}: {suggestion_text}"
                        )

            except Exception as validation_error:
                # Don't fail the operation if validation fails, just log
                logger.warning(f"Could not validate relationship constraints: {validation_error}")

            updated_work_item = work_items_client.link_work_items(
                project_id=project_id,
                source_work_item_id=source_work_item_id,
                target_work_item_id=target_work_item_id,
                relationship_type=relationship_type,
                comment=comment,
            )

            logger.info(
                f"Successfully linked work item #{source_work_item_id} to #{target_work_item_id} with relationship '{relationship_type}'"
            )
            return updated_work_item

        except Exception as e:
            logger.error(
                f"Failed to link work items {source_work_item_id} -> {target_work_item_id}: {e}"
            )
            raise

    @mcp_instance.tool
    def get_work_item_relations(
        project_id: str, work_item_id: int, depth: int = 1
    ) -> Optional[List[WorkItemRelation]]:
        """
        Get relationships for a work item.

        This tool retrieves all relationships (links) for a specific work item, including
        parent-child hierarchies, dependencies, and related links.

        Args:
            project_id: The ID or name of the project.
            work_item_id: The ID of the work item to get relationships for.
            depth: Depth of relationships to retrieve (currently only depth=1 is supported).

        Returns:
            List[WorkItemRelation]: List of relationships for the work item,
                                  or None if client unavailable.

        Examples:
            # Get all relationships for a work item
            get_work_item_relations(
                project_id="MyProject",
                work_item_id=123
            )

            # Get relationships (depth parameter for future expansion)
            get_work_item_relations(
                project_id="MyProject",
                work_item_id=123,
                depth=1
            )
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None

        try:
            work_items_client = WorkItemsClient(ado_client_instance)

            relations = work_items_client.get_work_item_relations(
                project_id=project_id, work_item_id=work_item_id, depth=depth
            )

            logger.info(
                f"Successfully retrieved {len(relations)} relationships for work item #{work_item_id}"
            )
            return relations

        except Exception as e:
            logger.error(f"Failed to get relationships for work item {work_item_id}: {e}")
            raise