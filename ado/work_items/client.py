"""Client methods for Azure DevOps Work Items API operations."""

import logging
from typing import Any

from opentelemetry import trace

from ado.client import AdoClient
from ado.work_items.batch_client import BatchClient
from ado.work_items.comments_client import CommentsClient
from ado.work_items.crud_client import CrudClient
from ado.work_items.models import (
    ClassificationNode,
    JsonPatchOperation,
    WorkItem,
    WorkItemComment,
    WorkItemField,
    WorkItemQueryResult,
    WorkItemRelation,
    WorkItemRevision,
    WorkItemType,
)
from ado.work_items.query_client import QueryClient
from ado.work_items.type_client import TypeClient

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class WorkItemsClient:
    """Client for Azure DevOps Work Items API operations."""

    def __init__(self, client: AdoClient):
        """
        Initialize the WorkItemsClient.

        Args:
            client: The AdoClient instance to use for API calls.
        """
        self.client = client
        self.auth_manager = client.auth_manager
        self.organization_url = client.organization_url
        self.crud_client = CrudClient(client)
        self.batch_client = BatchClient(client)
        self.query_client = QueryClient(client)
        self.type_client = TypeClient(client)
        self.comments_client = CommentsClient(client)

    def create_work_item(
        self,
        project_id: str,
        work_item_type: str,
        fields: dict[str, Any],
        validate_only: bool = False,
        bypass_rules: bool = False,
        suppress_notifications: bool = False,
    ) -> WorkItem:
        """
        Create a new work item in Azure DevOps.

        Args:
            project_id: The ID or name of the project.
            work_item_type: The type of work item to create (e.g., "Bug", "Task").
            fields: Dictionary of field values for the work item.
            validate_only: If true, only validate the request without creating.
            bypass_rules: If true, bypass rules validation.
            suppress_notifications: If true, suppress notifications.

        Returns:
            The created WorkItem object.

        Raises:
            AdoError: If the API request fails.
        """
        return self.crud_client.create_work_item(
            project_id=project_id,
            work_item_type=work_item_type,
            fields=fields,
            validate_only=validate_only,
            bypass_rules=bypass_rules,
            suppress_notifications=suppress_notifications,
        )

    def get_work_item(
        self,
        project_id: str,
        work_item_id: int,
        fields: list[str] | None = None,
        as_of: str | None = None,
        expand: str | None = None,
    ) -> WorkItem:
        """
        Get a single work item by ID.

        Args:
            project_id: The ID or name of the project.
            work_item_id: The ID of the work item.
            fields: List of field reference names to include.
            as_of: Get work item as of a specific date/time.
            expand: The expand parameters (e.g., "relations", "fields").

        Returns:
            The WorkItem object.

        Raises:
            AdoError: If the API request fails.
        """
        return self.crud_client.get_work_item(
            project_id=project_id,
            work_item_id=work_item_id,
            fields=fields,
            as_of=as_of,
            expand=expand,
        )

    def update_work_item(
        self,
        project_id: str,
        work_item_id: int,
        operations: list[JsonPatchOperation],
        validate_only: bool = False,
        bypass_rules: bool = False,
        suppress_notifications: bool = False,
    ) -> WorkItem:
        """
        Update an existing work item.

        Args:
            project_id: The ID or name of the project.
            work_item_id: The ID of the work item to update.
            operations: List of JSON Patch operations to apply.
            validate_only: If true, only validate the request.
            bypass_rules: If true, bypass rules validation.
            suppress_notifications: If true, suppress notifications.

        Returns:
            The updated WorkItem object.

        Raises:
            AdoError: If the API request fails.
        """
        return self.crud_client.update_work_item(
            project_id=project_id,
            work_item_id=work_item_id,
            operations=operations,
            validate_only=validate_only,
            bypass_rules=bypass_rules,
            suppress_notifications=suppress_notifications,
        )

    def delete_work_item(
        self,
        project_id: str,
        work_item_id: int,
        destroy: bool = False,
    ) -> bool:
        """
        Delete a work item.

        Args:
            project_id: The ID or name of the project.
            work_item_id: The ID of the work item to delete.
            destroy: If true, permanently destroy the work item.

        Returns:
            True if deletion was successful.

        Raises:
            AdoError: If the API request fails.
        """
        return self.crud_client.delete_work_item(
            project_id=project_id,
            work_item_id=work_item_id,
            destroy=destroy,
        )

    def list_work_item_types(
        self,
        project_id: str,
    ) -> list[WorkItemType]:
        """
        Get all work item types for a project.

        Args:
            project_id: The ID or name of the project.

        Returns:
            List of WorkItemType objects.

        Raises:
            AdoError: If the API request fails.
        """
        return self.type_client.list_work_item_types(project_id=project_id)

    def get_work_item_type(
        self,
        project_id: str,
        work_item_type: str,
    ) -> WorkItemType:
        """
        Get detailed information about a specific work item type.

        This returns comprehensive information including states, transitions,
        colors, icons, and field information for the specified work item type.

        Args:
            project_id: The ID or name of the project.
            work_item_type: The name of the work item type (e.g., "Bug", "Task").

        Returns:
            WorkItemType object with detailed information.

        Raises:
            AdoError: If the API request fails.
        """
        return self.type_client.get_work_item_type(
            project_id=project_id, work_item_type=work_item_type
        )

    def get_work_item_type_fields(
        self,
        project_id: str,
        work_item_type: str,
    ) -> list[WorkItemField]:
        """
        Get all fields for a specific work item type.

        Args:
            project_id: The ID or name of the project.
            work_item_type: The name of the work item type (e.g., "Bug", "Task").

        Returns:
            List of WorkItemField objects.

        Raises:
            AdoError: If the API request fails.
        """
        return self.type_client.get_work_item_type_fields(
            project_id=project_id, work_item_type=work_item_type
        )

    def get_work_item_type_field(
        self,
        project_id: str,
        work_item_type: str,
        field_reference_name: str,
    ) -> WorkItemField:
        """
        Get detailed information about a specific field for a work item type.

        This returns comprehensive information about a single field including
        allowed values, constraints, defaults, and validation rules.

        Args:
            project_id: The ID or name of the project.
            work_item_type: The name of the work item type (e.g., "Bug", "Task").
            field_reference_name: The reference name of the field (e.g., "System.Title", "System.State").

        Returns:
            WorkItemField object with detailed field information.

        Raises:
            AdoError: If the API request fails.
        """
        return self.type_client.get_work_item_type_field(
            project_id=project_id,
            work_item_type=work_item_type,
            field_reference_name=field_reference_name,
        )

    def list_area_paths(
        self,
        project_id: str,
        depth: int | None = None,
    ) -> list[ClassificationNode]:
        """
        Get area paths (classification nodes) for a project.

        Args:
            project_id: The ID or name of the project.
            depth: The depth of the tree to retrieve.

        Returns:
            List of area path dictionaries.

        Raises:
            AdoError: If the API request fails.
        """
        return self.type_client.list_area_paths(project_id=project_id, depth=depth)

    def list_iteration_paths(
        self,
        project_id: str,
        depth: int | None = None,
    ) -> list[ClassificationNode]:
        """
        Get iteration paths (classification nodes) for a project.

        Args:
            project_id: The ID or name of the project.
            depth: The depth of the tree to retrieve.

        Returns:
            List of iteration path dictionaries.

        Raises:
            AdoError: If the API request fails.
        """
        return self.type_client.list_iteration_paths(project_id=project_id, depth=depth)

    def query_work_items(
        self,
        project_id: str,
        wiql_query: str | None = None,
        top: int | None = None,
        skip: int | None = None,
    ) -> WorkItemQueryResult:
        """
        Query work items using WIQL (Work Item Query Language).

        Args:
            project_id: The ID or name of the project.
            wiql_query: The WIQL query string. If None, returns all work items.
            top: Maximum number of results to return.
            skip: Number of results to skip (for pagination).

        Returns:
            WorkItemQueryResult with query results.

        Raises:
            AdoError: If the API request fails.
        """
        return self.query_client.query_work_items(
            project_id=project_id,
            wiql_query=wiql_query,
            top=top,
            skip=skip,
        )

    def get_work_items_batch(
        self,
        project_id: str,
        work_item_ids: list[int],
        fields: list[str] | None = None,
        expand_relations: bool = False,
        as_of: str | None = None,
        error_policy: str = "omit",
    ) -> list[WorkItem]:
        """
        Get multiple work items by their IDs in a single API call.

        Args:
            project_id: The ID or name of the project.
            work_item_ids: List of work item IDs to retrieve (max 200).
            fields: List of specific fields to return. If not specified, all fields are returned.
            expand_relations: If true, include related work items information.
            as_of: Retrieve work items as they were at a specific date/time (ISO 8601 format).
            error_policy: How to handle errors for individual items. Options:
                        - "omit" (default): Skip items that can't be retrieved
                        - "fail": Fail the entire request if any item can't be retrieved

        Returns:
            List of WorkItem objects (may be fewer than requested if some IDs are invalid)

        Raises:
            AdoError: If the API call fails or error_policy is "fail" and any item fails
            ValueError: If more than 200 work item IDs are provided
        """
        return self.batch_client.get_work_items_batch(
            project_id=project_id,
            work_item_ids=work_item_ids,
            fields=fields,
            expand_relations=expand_relations,
            as_of=as_of,
            error_policy=error_policy,
        )

    def update_work_items_batch(
        self,
        project_id: str,
        work_item_updates: list[dict[str, Any]],
        validate_only: bool = False,
        bypass_rules: bool = False,
        suppress_notifications: bool = False,
        error_policy: str = "fail",
    ) -> list[WorkItem]:
        """
        Update multiple work items in a batch operation using individual API calls.

        Note: Azure DevOps doesn't have a true batch update API for work items,
        so this performs individual updates with transaction-like behavior based on error_policy.

        Args:
            project_id: The ID or name of the project.
            work_item_updates: List of work item update operations, each containing:
                             - work_item_id: ID of the work item to update
                             - operations: List of JSON Patch operations to apply
            validate_only: If true, only validate the request without updating.
            bypass_rules: If true, bypass rules validation.
            suppress_notifications: If true, suppress notifications.
            error_policy: How to handle errors for individual items. Options:
                        - "fail" (default): Fail the entire request if any item fails
                        - "omit": Skip items that can't be updated

        Returns:
            List of updated WorkItem objects

        Raises:
            AdoError: If the API call fails or error_policy is "fail" and any item fails
            ValueError: If more than 200 work item updates are provided
        """
        return self.batch_client.update_work_items_batch(
            project_id=project_id,
            work_item_updates=work_item_updates,
            validate_only=validate_only,
            bypass_rules=bypass_rules,
            suppress_notifications=suppress_notifications,
            error_policy=error_policy,
        )

    def delete_work_items_batch(
        self,
        project_id: str,
        work_item_ids: list[int],
        destroy: bool = False,
        error_policy: str = "fail",
    ) -> list[bool]:
        """
        Delete multiple work items in a batch operation using individual API calls.

        Note: Azure DevOps doesn't have a true batch delete API for work items,
        so this performs individual deletes with transaction-like behavior based on error_policy.

        Args:
            project_id: The ID or name of the project.
            work_item_ids: List of work item IDs to delete (max 200).
            destroy: If true, permanently destroy the work items instead of moving to recycle bin.
            error_policy: How to handle errors for individual items. Options:
                        - "fail" (default): Fail the entire request if any item fails
                        - "omit": Skip items that can't be deleted

        Returns:
            List of boolean values indicating success/failure for each work item

        Raises:
            AdoError: If the API call fails or error_policy is "fail" and any item fails
            ValueError: If more than 200 work item IDs are provided
        """
        return self.batch_client.delete_work_items_batch(
            project_id=project_id,
            work_item_ids=work_item_ids,
            destroy=destroy,
            error_policy=error_policy,
        )

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
        return self.comments_client.add_work_item_comment(
            project_id=project_id,
            work_item_id=work_item_id,
            text=text,
            format_type=format_type,
        )

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
        return self.comments_client.get_work_item_comments(
            project_id=project_id,
            work_item_id=work_item_id,
            top=top,
            skip=skip,
            include_deleted=include_deleted,
        )

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
        return self.comments_client.get_work_item_revisions(
            project_id=project_id,
            work_item_id=work_item_id,
            top=top,
            skip=skip,
            expand=expand,
            from_date=from_date,
            to_date=to_date,
        )

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
        return self.comments_client.link_work_items(
            project_id=project_id,
            source_work_item_id=source_work_item_id,
            target_work_item_id=target_work_item_id,
            relationship_type=relationship_type,
            comment=comment,
        )

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
        return self.comments_client.get_work_item_relations(
            project_id=project_id,
            work_item_id=work_item_id,
            depth=depth,
        )
