"""MCP tool definitions for Azure DevOps Work Items batch operations."""

import logging
from typing import Any, Dict, List, Optional

from ado.work_items.client import WorkItemsClient
from ado.work_items.models import WorkItem

logger = logging.getLogger(__name__)


def register_batch_tools(mcp_instance, client_container):
    """
    Register batch operation tools with the FastMCP instance.

    Args:
        mcp_instance: The FastMCP instance to register tools with.
        client_container: Dictionary holding the AdoClient instance.
    """

    @mcp_instance.tool
    def get_work_items_batch(
        project_id: str,
        work_item_ids: List[int],
        fields: Optional[List[str]] = None,
        expand_relations: bool = False,
        as_of: Optional[str] = None,
        error_policy: str = "omit",
    ) -> Optional[List[WorkItem]]:
        """
        Get multiple work items by their IDs in a single API call.

        This tool provides efficient batch retrieval of work items, allowing you to
        fetch up to 200 work items in a single request. Perfect for getting full
        details of work items when you have their IDs from queries.

        Args:
            project_id: The ID or name of the project.
            work_item_ids: List of work item IDs to retrieve (max 200).
            fields: List of specific fields to return (e.g., ["System.Title", "System.State"]).
                   If not specified, all fields are returned.
            expand_relations: If true, include related work items information.
            as_of: Retrieve work items as they were at a specific date/time (ISO 8601 format).
            error_policy: How to handle errors for individual items:
                        - "omit" (default): Skip items that can't be retrieved
                        - "fail": Fail the entire request if any item can't be retrieved

        Returns:
            List of WorkItem objects (may be fewer than requested if some IDs are invalid)

        Examples:
            # Get basic info for multiple work items
            get_work_items_batch(
                project_id="MyProject",
                work_item_ids=[123, 124, 125]
            )

            # Get specific fields only
            get_work_items_batch(
                project_id="MyProject",
                work_item_ids=[123, 124],
                fields=["System.Title", "System.State", "System.AssignedTo"]
            )

            # Get with relationships and fail on any error
            get_work_items_batch(
                project_id="MyProject",
                work_item_ids=[123, 124],
                expand_relations=True,
                error_policy="fail"
            )
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None

        try:
            import time

            # Validate inputs
            if not work_item_ids:
                logger.info("No work item IDs provided, returning empty list")
                return []

            if len(work_item_ids) > 200:
                raise ValueError(
                    "Cannot retrieve more than 200 work items in a single batch request"
                )

            # Start performance timing
            start_time = time.time()

            work_items_client = WorkItemsClient(ado_client_instance)

            # Log batch operation metrics with enhanced context
            batch_operation_context = {
                "operation_type": "batch_get",
                "project_id": project_id,
                "item_count": len(work_item_ids),
                "work_item_ids_sample": work_item_ids[:5]
                if len(work_item_ids) <= 10
                else work_item_ids[:3] + ["..."] + work_item_ids[-2:],
                "has_field_filter": fields is not None,
                "field_count": len(fields) if fields else 0,
                "fields_sample": fields[:5]
                if fields and len(fields) <= 10
                else (
                    fields[:3] + ["..."] + fields[-2:] if fields and len(fields) > 10 else fields
                ),
                "expand_relations": expand_relations,
                "error_policy": error_policy,
                "has_historical_query": as_of is not None,
                "as_of_date": as_of,
                "operation_id": f"batch_get_{project_id}_{int(start_time)}",
            }

            logger.info(f"Starting batch retrieval operation: {batch_operation_context}")

            # Execute batch retrieval with timing
            api_start_time = time.time()
            work_items = work_items_client.get_work_items_batch(
                project_id=project_id,
                work_item_ids=work_item_ids,
                fields=fields,
                expand_relations=expand_relations,
                as_of=as_of,
                error_policy=error_policy,
            )
            api_duration = time.time() - api_start_time

            # Calculate performance metrics
            total_duration = time.time() - start_time
            result_count = len(work_items)
            success_rate = (result_count / len(work_item_ids)) * 100 if work_item_ids else 100

            # Calculate additional batch metrics
            batch_metrics = {
                "batch_size": len(work_item_ids),
                "batch_efficiency": round((result_count / len(work_item_ids)) * 100, 1)
                if work_item_ids
                else 100,
                "fields_requested": len(fields) if fields else 0,
                "has_field_filtering": fields is not None,
                "has_relations": expand_relations,
                "is_historical_query": as_of is not None,
            }

            # Log comprehensive performance metrics
            performance_metrics = {
                "total_duration_ms": round(total_duration * 1000, 2),
                "api_duration_ms": round(api_duration * 1000, 2),
                "requested_count": len(work_item_ids),
                "returned_count": result_count,
                "success_rate_percent": round(success_rate, 1),
                "throughput_items_per_sec": round(result_count / total_duration, 2)
                if total_duration > 0
                else 0,
                "avg_ms_per_item": round((total_duration * 1000) / result_count, 2)
                if result_count > 0
                else 0,
                **batch_metrics,
            }

            logger.info(f"Batch retrieval performance: {performance_metrics}")

            # Log warnings for inefficient operations
            if success_rate < 80:
                logger.warning(
                    f"Low success rate: {success_rate:.1f}% - many work items may not exist"
                )
            if total_duration > 5.0:  # 5 second threshold for batch operations
                logger.warning(
                    f"Slow batch retrieval: {total_duration:.2f}s for {result_count} items"
                )

            logger.info(
                f"Successfully retrieved {result_count} out of {len(work_item_ids)} requested work items"
            )
            return work_items

        except Exception as e:
            logger.error(f"Failed to get work items batch: {e}")
            raise

    @mcp_instance.tool
    def update_work_items_batch(
        project_id: str,
        work_item_updates: List[Dict[str, Any]],
        validate_only: bool = False,
        bypass_rules: bool = False,
        suppress_notifications: bool = False,
        error_policy: str = "fail",
    ) -> Optional[List[WorkItem]]:
        """
        Update multiple work items in a single batch operation with transaction-like behavior.

        This tool provides efficient bulk updating of work items with comprehensive error handling
        and performance monitoring. It uses the Azure DevOps batch API for optimal performance.

        Args:
            project_id: The ID or name of the project.
            work_item_updates: List of work item update operations, each containing:
                             - work_item_id: ID of the work item to update
                             - operations: List of JSON Patch operations to apply
                             Example:
                             [
                                 {
                                     "work_item_id": 123,
                                     "operations": [
                                         {"op": "replace", "path": "/fields/System.Title", "value": "New Title"},
                                         {"op": "replace", "path": "/fields/System.State", "value": "Active"}
                                     ]
                                 }
                             ]
            validate_only: If true, only validate the request without updating.
            bypass_rules: If true, bypass rules validation.
            suppress_notifications: If true, suppress notifications.
            error_policy: How to handle errors for individual items. Options:
                        - "fail" (default): Fail the entire request if any item fails
                        - "omit": Skip items that can't be updated and continue with others

        Returns:
            List of updated work item dictionaries, or None if client unavailable.

        Examples:
            # Update multiple work items' states
            update_work_items_batch(
                project_id="MyProject",
                work_item_updates=[
                    {
                        "work_item_id": 123,
                        "operations": [
                            {"op": "replace", "path": "/fields/System.State", "value": "Active"}
                        ]
                    },
                    {
                        "work_item_id": 124,
                        "operations": [
                            {"op": "replace", "path": "/fields/System.State", "value": "Resolved"}
                        ]
                    }
                ]
            )

            # Bulk assignment with omit error policy
            update_work_items_batch(
                project_id="MyProject",
                work_item_updates=[...],
                error_policy="omit"
            )
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None

        try:
            import time
            from datetime import datetime

            # Validate input
            if len(work_item_updates) > 200:
                raise ValueError("Cannot update more than 200 work items in a single batch request")

            if not work_item_updates:
                logger.info("No work item updates provided, returning empty list")
                return []

            # Start performance tracking
            start_time = time.time()
            api_start_time = datetime.utcnow()
            update_count = len(work_item_updates)

            # Log batch operation details with structured data
            batch_operation_context = {
                "operation_type": "batch_update",
                "project_id": project_id,
                "item_count": update_count,
                "validate_only": validate_only,
                "bypass_rules": bypass_rules,
                "suppress_notifications": suppress_notifications,
                "error_policy": error_policy,
                "operation_id": f"batch_update_{project_id}_{int(start_time)}",
            }

            logger.info(f"Starting batch update operation: {batch_operation_context}")

            # Log individual operation details for debugging
            operation_types = {}
            for i, update in enumerate(work_item_updates):
                work_item_id = update.get("work_item_id", "unknown")
                operations = update.get("operations", [])
                for op in operations:
                    op_type = (
                        f"{op.get('op', 'unknown')}:{op.get('path', 'unknown').split('/')[-1]}"
                    )
                    operation_types[op_type] = operation_types.get(op_type, 0) + 1

                # Log first few operations for detailed debugging
                if i < 3:
                    logger.info(
                        f"Update {i + 1} - WorkItem {work_item_id}: {len(operations)} operations"
                    )

            logger.info(f"Operation breakdown: {operation_types}")

            # Execute batch update
            work_items_client = WorkItemsClient(ado_client_instance)

            updated_work_items = work_items_client.update_work_items_batch(
                project_id=project_id,
                work_item_updates=work_item_updates,
                validate_only=validate_only,
                bypass_rules=bypass_rules,
                suppress_notifications=suppress_notifications,
                error_policy=error_policy,
            )

            # Debug logging
            logger.info(f"Client returned {len(updated_work_items)} work items")
            if updated_work_items:
                logger.info(f"First work item type: {type(updated_work_items[0])}")
                logger.info(f"First work item ID: {getattr(updated_work_items[0], 'id', 'NO_ID')}")

            # Calculate performance metrics
            total_duration = time.time() - start_time
            api_end_time = datetime.utcnow()
            api_duration = (api_end_time - api_start_time).total_seconds()

            result_count = len(updated_work_items)
            success_rate = (result_count / update_count) * 100 if update_count > 0 else 0
            updates_per_second = result_count / total_duration if total_duration > 0 else 0

            # Log comprehensive performance metrics
            logger.info(
                f"Batch update performance metrics: "
                f"total_duration={total_duration:.3f}s, "
                f"api_duration={api_duration:.3f}s, "
                f"requested_updates={update_count}, "
                f"successful_updates={result_count}, "
                f"success_rate={success_rate:.1f}%, "
                f"updates_per_second={updates_per_second:.2f}, "
                f"avg_time_per_update={total_duration / update_count:.3f}s"
            )

            # Performance warnings
            if success_rate < 90.0 and error_policy == "omit":
                logger.warning(
                    f"Low success rate: {success_rate:.1f}% - many work items may have failed to update"
                )
            if total_duration > 10.0:  # 10 second threshold for batch updates
                logger.warning(f"Slow batch update: {total_duration:.2f}s for {update_count} items")

            logger.info(
                f"Successfully updated {result_count} out of {update_count} requested work items"
            )
            return updated_work_items

        except Exception as e:
            logger.error(f"Failed to update work items batch: {e}")
            raise

    @mcp_instance.tool
    def delete_work_items_batch(
        project_id: str, work_item_ids: List[int], destroy: bool = False, error_policy: str = "fail"
    ) -> Optional[List[bool]]:
        """
        Delete multiple work items in a single batch operation with transaction-like behavior.

        This tool provides efficient bulk deletion of work items with comprehensive error handling
        and performance monitoring. It uses individual Azure DevOps API calls for optimal reliability.

        Args:
            project_id: The ID or name of the project.
            work_item_ids: List of work item IDs to delete (max 200).
            destroy: If true, permanently destroy the work items instead of moving to recycle bin.
                   WARNING: Destroyed work items cannot be recovered!
            error_policy: How to handle errors for individual items:
                        - "fail" (default): Fail the entire request if any item fails
                        - "omit": Skip items that can't be deleted, continue with others

        Returns:
            List of boolean values indicating success/failure for each work item ID (in order)

        Examples:
            # Soft delete multiple work items (to recycle bin)
            delete_work_items_batch(
                project_id="MyProject",
                work_item_ids=[123, 124, 125]
            )

            # Permanently destroy work items
            delete_work_items_batch(
                project_id="MyProject",
                work_item_ids=[123, 124, 125],
                destroy=True
            )

            # Delete with partial failure tolerance
            delete_work_items_batch(
                project_id="MyProject",
                work_item_ids=[123, 999999, 125],  # 999999 doesn't exist
                error_policy="omit"
            )
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None

        try:
            import time
            from datetime import datetime

            # Validate input
            if len(work_item_ids) > 200:
                raise ValueError("Cannot delete more than 200 work items in a single batch request")

            if not work_item_ids:
                logger.info("No work item IDs provided, returning empty list")
                return []

            # Start performance tracking
            start_time = time.time()
            api_start_time = datetime.utcnow()
            delete_count = len(work_item_ids)

            # Log batch operation details with structured data
            batch_operation_context = {
                "operation_type": "batch_delete",
                "project_id": project_id,
                "item_count": delete_count,
                "work_item_ids_sample": work_item_ids[:5]
                if len(work_item_ids) <= 10
                else work_item_ids[:3] + ["..."] + work_item_ids[-2:],
                "destroy": destroy,
                "error_policy": error_policy,
                "operation_id": f"batch_delete_{project_id}_{int(start_time)}",
            }

            logger.info(f"Starting batch deletion operation: {batch_operation_context}")

            # Execute batch deletion
            work_items_client = WorkItemsClient(ado_client_instance)

            deletion_results = work_items_client.delete_work_items_batch(
                project_id=project_id,
                work_item_ids=work_item_ids,
                destroy=destroy,
                error_policy=error_policy,
            )

            # Calculate performance metrics
            total_duration = time.time() - start_time
            api_end_time = datetime.utcnow()
            api_duration = (api_end_time - api_start_time).total_seconds()

            successful_deletions = sum(deletion_results)
            success_rate = (successful_deletions / delete_count) * 100 if delete_count > 0 else 0
            deletions_per_second = (
                successful_deletions / total_duration if total_duration > 0 else 0
            )

            # Log comprehensive performance metrics
            logger.info(
                f"Batch deletion performance metrics: "
                f"total_duration={total_duration:.3f}s, "
                f"api_duration={api_duration:.3f}s, "
                f"requested_deletions={delete_count}, "
                f"successful_deletions={successful_deletions}, "
                f"success_rate={success_rate:.1f}%, "
                f"deletions_per_second={deletions_per_second:.2f}, "
                f"avg_time_per_deletion={total_duration / delete_count:.3f}s"
            )

            # Performance warnings
            if success_rate < 90.0 and error_policy == "omit":
                logger.warning(
                    f"Low success rate: {success_rate:.1f}% - many work items may have failed to delete"
                )
            if total_duration > 10.0:  # 10 second threshold for batch deletions
                logger.warning(
                    f"Slow batch deletion: {total_duration:.2f}s for {delete_count} items"
                )

            logger.info(
                f"Successfully deleted {successful_deletions} out of {delete_count} requested work items"
            )
            return deletion_results

        except Exception as e:
            logger.error(f"Failed to delete work items batch: {e}")
            raise