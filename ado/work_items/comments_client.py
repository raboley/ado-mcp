"""Client methods for Azure DevOps Work Items comments and relationships API operations."""

import logging
from datetime import datetime

from ado.client import AdoClient
from ado.errors import AdoError
from ado.work_items.models import (
    JsonPatchOperation,
    WorkItem,
    WorkItemComment,
    WorkItemRelation,
    WorkItemRevision,
)

logger = logging.getLogger(__name__)


class CommentsClient:
    """Client for Azure DevOps Work Items comments and relationships API operations."""

    def __init__(self, client: AdoClient):
        """
        Initialize the CommentsClient.

        Args:
            client: The AdoClient instance to use for API calls.
        """
        self.client = client
        self.auth_manager = client.auth_manager
        self.organization_url = client.organization_url

    def add_work_item_comment(
        self, project_id: str, work_item_id: int, text: str, format_type: str = "html"
    ) -> WorkItemComment:
        """
        Add a comment to a work item.

        Args:
            project_id: The ID or name of the project
            work_item_id: The ID of the work item to add a comment to
            text: The comment text (supports HTML/Markdown formatting)
            format_type: The format of the comment text ("html" or "markdown")

        Returns:
            WorkItemComment: The created comment

        Raises:
            AdoError: If the API call fails
        """
        url = f"{self.organization_url}/{project_id}/_apis/wit/workitems/{work_item_id}/comments"

        # Prepare comment data
        comment_data = {"text": text, "format": format_type}

        logger.info(f"Adding comment to work item {work_item_id} in project '{project_id}'")

        try:
            data = self.client._send_request(
                method="POST", url=url, params={"api-version": "7.1-preview.3"}, json=comment_data
            )

            # Convert response to WorkItemComment model
            comment = WorkItemComment(
                id=data.get("id"),
                work_item_id=work_item_id,
                text=data.get("text", text),
                created_by=data.get("createdBy"),
                created_date=data.get("createdDate"),
                modified_by=data.get("modifiedBy"),
                modified_date=data.get("modifiedDate"),
                format=data.get("format", format_type),
            )

            logger.info(f"Successfully added comment {comment.id} to work item {work_item_id}")
            return comment

        except Exception as e:
            logger.error(f"Failed to add comment to work item {work_item_id}: {e}")
            raise AdoError(
                f"Failed to add comment to work item {work_item_id}: {e}", "add_comment_failed"
            ) from e

    def get_work_item_comments(
        self,
        project_id: str,
        work_item_id: int,
        top: int | None = None,
        skip: int | None = None,
        include_deleted: bool = False,
    ) -> list[WorkItemComment]:
        """
        Get comments for a work item.

        Args:
            project_id: The ID or name of the project
            work_item_id: The ID of the work item to get comments for
            top: Maximum number of comments to return
            skip: Number of comments to skip (for pagination)
            include_deleted: Whether to include deleted comments

        Returns:
            List[WorkItemComment]: List of comments for the work item

        Raises:
            AdoError: If the API call fails
        """
        url = f"{self.organization_url}/{project_id}/_apis/wit/workitems/{work_item_id}/comments"

        params = {"api-version": "7.1-preview.3"}
        if top is not None:
            params["$top"] = top
        if skip is not None:
            params["$skip"] = skip
        if include_deleted:
            params["includeDeleted"] = "true"

        logger.info(f"Getting comments for work item {work_item_id} in project '{project_id}'")

        try:
            data = self.client._send_request(method="GET", url=url, params=params)

            comments = []
            for comment_data in data.get("comments", []):
                comment = WorkItemComment(
                    id=comment_data.get("id"),
                    work_item_id=work_item_id,
                    text=comment_data.get("text", ""),
                    created_by=comment_data.get("createdBy"),
                    created_date=comment_data.get("createdDate"),
                    modified_by=comment_data.get("modifiedBy"),
                    modified_date=comment_data.get("modifiedDate"),
                    format=comment_data.get("format", "html"),
                )
                comments.append(comment)

            # Add telemetry for comment access patterns
            telemetry_data = {
                "comments_count": len(comments),
                "has_pagination": bool(top or skip),
            }

            logger.info(
                f"Successfully retrieved {len(comments)} comments for work item {work_item_id} "
                f"[has_pagination: {telemetry_data['has_pagination']}]"
            )
            return comments

        except Exception as e:
            logger.error(f"Failed to get comments for work item {work_item_id}: {e}")
            raise AdoError(
                f"Failed to get comments for work item {work_item_id}: {e}", "get_comments_failed"
            ) from e

    def get_work_item_revisions(
        self,
        project_id: str,
        work_item_id: int,
        top: int | None = None,
        skip: int | None = None,
        expand: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> list[WorkItemRevision]:
        """
        Get revision history for a work item with optional date filtering.

        Args:
            project_id: The ID or name of the project
            work_item_id: The ID of the work item to get revisions for
            top: Maximum number of revisions to return
            skip: Number of revisions to skip (for pagination)
            expand: Additional data to include (e.g., "fields")
            from_date: Filter revisions from this date onwards (ISO 8601 format)
            to_date: Filter revisions up to this date (ISO 8601 format)

        Returns:
            List[WorkItemRevision]: List of revisions for the work item

        Raises:
            AdoError: If the API call fails
        """
        url = f"{self.organization_url}/{project_id}/_apis/wit/workitems/{work_item_id}/revisions"

        params = {"api-version": "7.1"}
        if top is not None:
            params["$top"] = top
        if skip is not None:
            params["$skip"] = skip
        if expand is not None:
            params["$expand"] = expand

        logger.info(
            f"Getting revision history for work item {work_item_id} in project '{project_id}'"
        )

        try:
            data = self.client._send_request(method="GET", url=url, params=params)

            revisions = []
            for revision_data in data.get("value", []):
                revision = WorkItemRevision(
                    id=revision_data.get("id"),
                    rev=revision_data.get("rev"),
                    fields=revision_data.get("fields", {}),
                    url=revision_data.get("url"),
                    revised_by=revision_data.get("fields", {}).get("System.ChangedBy"),
                    revised_date=revision_data.get("fields", {}).get("System.ChangedDate"),
                )
                revisions.append(revision)

            # Filter by date range if specified
            if from_date or to_date:
                filtered_revisions = []
                for revision in revisions:
                    revision_date = revision.revised_date
                    if not revision_date:
                        continue

                    # Parse revision date if it's a string
                    if isinstance(revision_date, str):
                        try:
                            revision_dt = datetime.fromisoformat(
                                revision_date.replace("Z", "+00:00")
                            )
                        except ValueError:
                            continue
                    else:
                        revision_dt = revision_date

                    # Check date filters
                    if from_date:
                        from_dt = datetime.fromisoformat(from_date.replace("Z", "+00:00"))
                        if revision_dt < from_dt:
                            continue

                    if to_date:
                        to_dt = datetime.fromisoformat(to_date.replace("Z", "+00:00"))
                        if revision_dt > to_dt:
                            continue

                    filtered_revisions.append(revision)

                revisions = filtered_revisions

            # Add telemetry for history access patterns
            telemetry_data = {
                "revisions_count": len(revisions),
                "date_filtered": bool(from_date or to_date),
                "has_pagination": bool(top or skip),
                "expanded_fields": bool(expand),
            }

            if from_date or to_date:
                telemetry_data["filter_type"] = (
                    "range" if from_date and to_date else "from" if from_date else "to"
                )

            logger.info(
                f"Successfully retrieved {len(revisions)} revisions for work item {work_item_id} "
                f"[date_filtered: {telemetry_data['date_filtered']}, "
                f"has_pagination: {telemetry_data['has_pagination']}, "
                f"expanded_fields: {telemetry_data['expanded_fields']}]"
            )
            return revisions

        except Exception as e:
            logger.error(f"Failed to get revisions for work item {work_item_id}: {e}")
            raise AdoError(
                f"Failed to get revisions for work item {work_item_id}: {e}", "get_revisions_failed"
            ) from e

    def link_work_items(
        self,
        project_id: str,
        source_work_item_id: int,
        target_work_item_id: int,
        relationship_type: str,
        comment: str | None = None,
    ) -> WorkItem:
        """
        Create a link between two work items.

        Args:
            project_id: The ID or name of the project
            source_work_item_id: The ID of the source work item
            target_work_item_id: The ID of the target work item
            relationship_type: The type of relationship (e.g., "System.LinkTypes.Hierarchy-Forward",
                             "System.LinkTypes.Related", "System.LinkTypes.Dependency-Forward")
            comment: Optional comment for the link

        Returns:
            WorkItem: The updated source work item

        Raises:
            AdoError: If the API call fails
        """
        # Build the target work item URL
        target_url = (
            f"{self.organization_url}/{project_id}/_apis/wit/workitems/{target_work_item_id}"
        )

        # Create the relationship operation
        operations = [
            JsonPatchOperation(
                op="add",
                path="/relations/-",
                value={
                    "rel": relationship_type,
                    "url": target_url,
                    "attributes": {"comment": comment} if comment else {},
                },
            )
        ]

        logger.info(
            f"Linking work item {source_work_item_id} to {target_work_item_id} "
            f"with relationship '{relationship_type}' in project '{project_id}'"
        )

        try:
            # Need to import here to avoid circular imports
            from ado.work_items.crud_client import CrudClient

            crud_client = CrudClient(self.client)
            # Use the existing update method to add the relationship
            updated_work_item = crud_client.update_work_item(
                project_id=project_id, work_item_id=source_work_item_id, operations=operations
            )

            logger.info(
                f"Successfully linked work item {source_work_item_id} to {target_work_item_id} "
                f"with relationship '{relationship_type}'"
            )
            return updated_work_item

        except Exception as e:
            logger.error(
                f"Failed to link work items {source_work_item_id} -> {target_work_item_id}: {e}"
            )
            raise AdoError(
                f"Failed to link work items {source_work_item_id} -> {target_work_item_id}: {e}",
                "link_work_items_failed",
            ) from e

    def get_work_item_relations(
        self, project_id: str, work_item_id: int, depth: int = 1
    ) -> list[WorkItemRelation]:
        """
        Get relationships for a work item.

        Args:
            project_id: The ID or name of the project
            work_item_id: The ID of the work item
            depth: Depth of relationships to retrieve (1 = direct relationships only)

        Returns:
            List[WorkItemRelation]: List of relationships

        Raises:
            AdoError: If the API call fails
        """
        # Need to import here to avoid circular imports
        from ado.work_items.crud_client import CrudClient

        crud_client = CrudClient(self.client)
        # Get the work item with relations expanded
        work_item = crud_client.get_work_item(
            project_id=project_id, work_item_id=work_item_id, expand="relations"
        )

        relations = []
        # Check if work item has relations in the raw data
        raw_relations = None
        if hasattr(work_item, "relations") and work_item.relations:
            raw_relations = work_item.relations
        elif hasattr(work_item, "__dict__") and "relations" in work_item.__dict__:
            raw_relations = work_item.__dict__["relations"]
        elif isinstance(work_item, dict) and "relations" in work_item:
            raw_relations = work_item["relations"]

        if raw_relations:
            for relation_data in raw_relations:
                # Handle both dict and WorkItemRelation objects
                if isinstance(relation_data, dict):
                    relation = WorkItemRelation(
                        rel=relation_data.get("rel", ""),
                        url=relation_data.get("url", ""),
                        attributes=relation_data.get("attributes", {}),
                    )
                else:
                    # Already a WorkItemRelation object
                    relation = relation_data
                relations.append(relation)

        logger.info(
            f"Successfully retrieved {len(relations)} relationships for work item {work_item_id}"
        )
        return relations
