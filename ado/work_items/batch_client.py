"""Batch client methods for Azure DevOps Work Items API operations."""

import logging
from typing import Any, Dict, List, Optional

from ado.client import AdoClient
from ado.errors import AdoError
from ado.work_items.models import (
    JsonPatchOperation,
    WorkItem,
)

logger = logging.getLogger(__name__)


class BatchClient:
    """Client for batch Azure DevOps Work Items API operations."""

    def __init__(self, client: AdoClient):
        """
        Initialize the BatchClient.

        Args:
            client: The AdoClient instance to use for API calls.
        """
        self.client = client
        self.auth_manager = client.auth_manager
        self.organization_url = client.organization_url

    def get_work_items_batch(
        self,
        project_id: str,
        work_item_ids: List[int],
        fields: Optional[List[str]] = None,
        expand_relations: bool = False,
        as_of: Optional[str] = None,
        error_policy: str = "omit",
    ) -> List[WorkItem]:
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
        if len(work_item_ids) > 200:
            raise ValueError("Cannot retrieve more than 200 work items in a single batch request")

        if not work_item_ids:
            logger.info("No work item IDs provided, returning empty list")
            return []

        # Build parameters
        params = {
            "ids": ",".join(map(str, work_item_ids)),
            "api-version": "7.1",
            "errorPolicy": error_policy,
        }

        if fields:
            params["fields"] = ",".join(fields)

        if expand_relations:
            params["$expand"] = "relations"

        if as_of:
            params["asOf"] = as_of

        url = f"{self.organization_url}/{project_id}/_apis/wit/workitems"

        logger.info(
            f"Getting batch of {len(work_item_ids)} work items from project '{project_id}' "
            f"(error_policy: {error_policy})"
        )

        try:
            data = self.client._send_request(method="GET", url=url, params=params)

            work_items = []
            if data and "value" in data:
                for item_data in data["value"]:
                    try:
                        work_items.append(WorkItem(**item_data))
                    except Exception as e:
                        logger.warning(f"Failed to parse work item data: {item_data}. Error: {e}")
                        if error_policy == "fail":
                            raise AdoError(
                                f"Failed to parse work item data: {e}", "work_item_parse_failed"
                            ) from e
                        # If error_policy is "omit", just skip this item
                        continue

            logger.info(
                f"Successfully retrieved {len(work_items)} work items out of {len(work_item_ids)} requested"
            )
            return work_items

        except Exception as e:
            logger.error(f"Failed to get work items batch: {e}")
            raise AdoError(f"Failed to get work items batch: {e}", "work_items_batch_failed") from e

    def update_work_items_batch(
        self,
        project_id: str,
        work_item_updates: List[Dict[str, Any]],
        validate_only: bool = False,
        bypass_rules: bool = False,
        suppress_notifications: bool = False,
        error_policy: str = "fail",
    ) -> List[WorkItem]:
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
        if len(work_item_updates) > 200:
            raise ValueError("Cannot update more than 200 work items in a single batch request")

        if not work_item_updates:
            logger.info("No work item updates provided, returning empty list")
            return []

        updated_work_items = []
        failed_updates = []
        processed_work_items = []  # Track successfully updated items for potential rollback

        logger.info(
            f"Starting batch update of {len(work_item_updates)} work items in project '{project_id}' "
            f"(error_policy: {error_policy})"
        )

        try:
            for i, update in enumerate(work_item_updates):
                if "work_item_id" not in update:
                    error_msg = f"Update {i} missing required 'work_item_id' field"
                    if error_policy == "fail":
                        raise ValueError(error_msg)
                    else:
                        logger.warning(f"Skipping update {i}: missing work_item_id")
                        failed_updates.append(error_msg)
                        continue

                if "operations" not in update:
                    error_msg = f"Update {i} missing required 'operations' field"
                    if error_policy == "fail":
                        raise ValueError(error_msg)
                    else:
                        logger.warning(f"Skipping update {i}: missing operations")
                        failed_updates.append(error_msg)
                        continue

                work_item_id = update["work_item_id"]
                operations = update["operations"]

                # Convert operations to JsonPatchOperation objects
                patch_operations = []
                for op in operations:
                    if isinstance(op, JsonPatchOperation):
                        patch_operations.append(op)
                    else:
                        # Convert dict to JsonPatchOperation
                        patch_operations.append(JsonPatchOperation(**op))

                try:
                    # Use the CRUD client's update method through the main client
                    updated_work_item = self._update_work_item_single(
                        project_id=project_id,
                        work_item_id=work_item_id,
                        operations=patch_operations,
                        validate_only=validate_only,
                        bypass_rules=bypass_rules,
                        suppress_notifications=suppress_notifications,
                    )

                    updated_work_items.append(updated_work_item)
                    processed_work_items.append((work_item_id, updated_work_item))

                except Exception as e:
                    error_msg = f"Failed to update work item {work_item_id}: {e}"
                    failed_updates.append(error_msg)

                    if error_policy == "fail":
                        logger.error(f"Batch update failed on item {i} (ID: {work_item_id}): {e}")
                        raise AdoError(
                            f"Batch update failed on item {i}: {e}", "batch_update_failed"
                        ) from e
                    else:
                        logger.warning(f"Skipping failed update for work item {work_item_id}: {e}")
                        continue

            if failed_updates and error_policy == "omit":
                logger.warning(f"Some updates failed but were omitted: {failed_updates}")

            logger.info(
                f"Successfully updated {len(updated_work_items)} work items out of {len(work_item_updates)} requested"
            )
            return updated_work_items

        except Exception as e:
            # If error_policy is "fail" and we've already updated some items,
            # we could implement rollback here, but Azure DevOps doesn't support transactions
            # so we'll just log the partial state
            if processed_work_items and error_policy == "fail":
                logger.warning(
                    f"Batch update failed after successfully updating {len(processed_work_items)} items. "
                    f"Updated work item IDs: {[item[0] for item in processed_work_items]}. "
                    f"Consider manual rollback if needed."
                )

            logger.error(f"Failed to update work items batch: {e}")
            raise AdoError(
                f"Failed to update work items batch: {e}", "work_items_batch_update_failed"
            ) from e

    def delete_work_items_batch(
        self,
        project_id: str,
        work_item_ids: List[int],
        destroy: bool = False,
        error_policy: str = "fail",
    ) -> List[bool]:
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
        if len(work_item_ids) > 200:
            raise ValueError("Cannot delete more than 200 work items in a single batch request")

        if not work_item_ids:
            logger.info("No work item IDs provided, returning empty list")
            return []

        deletion_results = []
        failed_deletions = []
        processed_work_items = []  # Track successfully deleted items for potential rollback info

        logger.info(
            f"Starting batch deletion of {len(work_item_ids)} work items in project '{project_id}' "
            f"(destroy: {destroy}, error_policy: {error_policy})"
        )

        try:
            for i, work_item_id in enumerate(work_item_ids):
                try:
                    # Use the CRUD client's delete method through the main client
                    success = self._delete_work_item_single(
                        project_id=project_id, work_item_id=work_item_id, destroy=destroy
                    )

                    deletion_results.append(success)
                    processed_work_items.append(work_item_id)

                except Exception as e:
                    error_msg = f"Failed to delete work item {work_item_id}: {e}"
                    failed_deletions.append(error_msg)

                    if error_policy == "fail":
                        logger.error(f"Batch deletion failed on item {i} (ID: {work_item_id}): {e}")
                        raise AdoError(
                            f"Batch deletion failed on item {i}: {e}", "batch_delete_failed"
                        ) from e
                    else:
                        logger.warning(
                            f"Skipping failed deletion for work item {work_item_id}: {e}"
                        )
                        deletion_results.append(False)
                        continue

            if failed_deletions and error_policy == "omit":
                logger.warning(f"Some deletions failed but were omitted: {failed_deletions}")

            successful_deletions = sum(deletion_results)
            logger.info(
                f"Successfully deleted {successful_deletions} work items out of {len(work_item_ids)} requested"
            )
            return deletion_results

        except Exception as e:
            # Log partial state for manual cleanup if needed
            if processed_work_items and error_policy == "fail":
                logger.warning(
                    f"Batch deletion failed after successfully deleting {len(processed_work_items)} items. "
                    f"Deleted work item IDs: {processed_work_items}. "
                    f"Note: Deleted items cannot be automatically restored (check recycle bin if not destroyed)."
                )

            logger.error(f"Failed to delete work items batch: {e}")
            raise AdoError(
                f"Failed to delete work items batch: {e}", "work_items_batch_delete_failed"
            ) from e

    def _update_work_item_single(
        self,
        project_id: str,
        work_item_id: int,
        operations: List[JsonPatchOperation],
        validate_only: bool = False,
        bypass_rules: bool = False,
        suppress_notifications: bool = False,
    ) -> WorkItem:
        """
        Helper method to update a single work item.

        This method delegates to the CRUD client for consistent behavior
        with the main WorkItemsClient.

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
        # Import here to avoid circular imports
        from ado.work_items.crud_client import CrudClient

        crud_client = CrudClient(self.client)
        return crud_client.update_work_item(
            project_id=project_id,
            work_item_id=work_item_id,
            operations=operations,
            validate_only=validate_only,
            bypass_rules=bypass_rules,
            suppress_notifications=suppress_notifications,
        )

    def _delete_work_item_single(
        self,
        project_id: str,
        work_item_id: int,
        destroy: bool = False,
    ) -> bool:
        """
        Helper method to delete a single work item.

        This method delegates to the CRUD client for consistent behavior
        with the main WorkItemsClient.

        Args:
            project_id: The ID or name of the project.
            work_item_id: The ID of the work item to delete.
            destroy: If true, permanently destroy the work item.

        Returns:
            True if deletion was successful.

        Raises:
            AdoError: If the API request fails.
        """
        # Import here to avoid circular imports
        from ado.work_items.crud_client import CrudClient

        crud_client = CrudClient(self.client)
        return crud_client.delete_work_item(
            project_id=project_id,
            work_item_id=work_item_id,
            destroy=destroy,
        )