"""Query operations for Azure DevOps Work Items."""

import logging
import time
from datetime import datetime, timedelta
from typing import Any

from ado.work_items.client import WorkItemsClient
from ado.work_items.models import WorkItemQueryResult, WorkItemReference
from ado.work_items.query_utils import analyze_query_complexity, build_wiql_from_filter

logger = logging.getLogger(__name__)


def register_query_tools(mcp_instance, client_container):
    """Register query-related work item tools with the FastMCP instance."""

    @mcp_instance.tool
    def list_work_items(
        project_id: str,
        wiql_query: str | None = None,
        top: int | None = None,
    ) -> list[WorkItemReference]:
        """
        List work items in a project using WIQL (Work Item Query Language).

        Returns a list of work item references. Use get_work_item for full details.
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return []

        try:
            work_items_client = WorkItemsClient(ado_client_instance)
            logger.info(f"Listing work items for project: {project_id}")

            query_result = work_items_client.query_work_items(
                project_id=project_id, wiql_query=wiql_query, top=top
            )

            work_items = query_result.workItems
            logger.info(f"Successfully listed {len(work_items)} work items")
            return work_items

        except Exception as e:
            logger.error(f"Failed to list work items: {e}")
            raise

    @mcp_instance.tool
    def query_work_items(
        project_id: str,
        wiql_query: str | None = None,
        top: int | None = None,
        skip: int | None = None,
        simple_filter: dict[str, Any] | None = None,
        page_size: int | None = None,
        page_number: int | None = None,
    ) -> WorkItemQueryResult | None:
        """
        Query work items using WIQL or simple filtering with pagination support.

        Supports both custom WIQL queries and simple field-based filtering.
        Returns complete query results including metadata and column information.
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None

        try:
            start_time = time.time()
            work_items_client = WorkItemsClient(ado_client_instance)

            # Handle pagination parameter conversion
            if page_size is not None and page_number is not None:
                if top is not None or skip is not None:
                    logger.warning(
                        "Both page_size/page_number and top/skip provided. Using page_size/page_number."
                    )
                top = page_size
                skip = (page_number - 1) * page_size
                logger.info(
                    f"Pagination: page {page_number}, size {page_size} -> top={top}, skip={skip}"
                )

            # Build WIQL query from simple filter if no custom query provided
            query_type = "custom_wiql" if wiql_query else "simple_filter"
            if wiql_query is None and simple_filter:
                wiql_query = build_wiql_from_filter(simple_filter)
                logger.info(f"Generated WIQL from simple filter: {len(simple_filter)} conditions")

            # Log query complexity metrics
            query_complexity = analyze_query_complexity(wiql_query, simple_filter, top, skip)
            logger.info(f"Query complexity metrics: {query_complexity}")

            logger.info(f"Querying work items for project: {project_id} (type: {query_type})")

            # Execute query with timing
            api_start_time = time.time()
            query_result = work_items_client.query_work_items(
                project_id=project_id, wiql_query=wiql_query, top=top, skip=skip
            )
            api_duration = time.time() - api_start_time

            # Calculate total performance metrics
            total_duration = time.time() - start_time
            result_count = len(query_result.workItems)

            # Log comprehensive performance metrics
            performance_metrics = {
                "total_duration_ms": round(total_duration * 1000, 2),
                "api_duration_ms": round(api_duration * 1000, 2),
                "result_count": result_count,
                "query_type": query_type,
                "has_pagination": top is not None or skip is not None,
                "page_size": top,
                "skip_count": skip or 0,
                "throughput_items_per_sec": round(result_count / total_duration, 2)
                if total_duration > 0
                else 0,
                **query_complexity,
            }

            logger.info(f"Query performance: {performance_metrics}")

            # Log warnings for slow queries
            if total_duration > 2.0:  # 2 second threshold
                logger.warning(
                    f"Slow query detected: {total_duration:.2f}s for {result_count} items"
                )

            logger.info(f"Successfully queried {result_count} work items")
            return query_result

        except Exception as e:
            logger.error(f"Failed to query work items: {e}")
            raise

    @mcp_instance.tool
    def get_work_items_page(
        project_id: str,
        page_number: int = 1,
        page_size: int = 50,
        work_item_type: str | None = None,
        state: str | None = None,
        assigned_to: str | None = None,
        area_path: str | None = None,
        order_by: str = "System.Id",
    ) -> dict[str, Any] | None:
        """
        Get a paginated list of work items with metadata about pagination.

        Simplified interface for paginated work items with common filtering options.
        Returns both work items and pagination metadata.
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None

        try:
            # Validate pagination parameters
            if page_number < 1:
                page_number = 1
            if page_size < 1:
                page_size = 50
            if page_size > 200:
                page_size = 200

            # Build filter for simple cases
            simple_filter = {}
            if work_item_type:
                simple_filter["work_item_type"] = work_item_type
            if state:
                simple_filter["state"] = state
            if assigned_to:
                simple_filter["assigned_to"] = assigned_to
            if area_path:
                simple_filter["area_path"] = area_path

            work_items_client = WorkItemsClient(ado_client_instance)

            # Build WIQL query from filter
            if simple_filter:
                wiql_query = build_wiql_from_filter(simple_filter)
            else:
                wiql_query = (
                    "SELECT [System.Id], [System.Title], [System.WorkItemType], "
                    "[System.State], [System.AssignedTo], [System.CreatedDate] "
                    "FROM WorkItems"
                )

            # Add ordering
            wiql_query += f" ORDER BY [{order_by}]"

            # Calculate skip value
            skip = (page_number - 1) * page_size

            # Get one extra item to check if there are more pages
            top = page_size + 1

            start_time = time.time()

            # Log pagination-specific metrics
            pagination_metrics = {
                "page_number": page_number,
                "page_size": page_size,
                "skip_items": skip,
                "filter_count": len(simple_filter),
                "has_ordering": order_by != "System.Id",
            }

            logger.info(
                f"Getting page {page_number} of work items (size: {page_size}) - {pagination_metrics}"
            )

            query_result = work_items_client.query_work_items(
                project_id=project_id, wiql_query=wiql_query, top=top, skip=skip
            )

            work_items = query_result.workItems
            has_more = len(work_items) > page_size

            # Remove the extra item if present
            if has_more:
                work_items = work_items[:page_size]

            # Build pagination metadata
            pagination_info = {
                "page_number": page_number,
                "page_size": page_size,
                "items_count": len(work_items),
                "has_more": has_more,
                "has_previous": page_number > 1,
                "next_page": page_number + 1 if has_more else None,
                "previous_page": page_number - 1 if page_number > 1 else None,
            }

            # Calculate final performance metrics
            total_duration = time.time() - start_time
            final_pagination_metrics = {
                **pagination_metrics,
                "duration_ms": round(total_duration * 1000, 2),
                "items_returned": len(work_items),
                "has_more_pages": has_more,
                "pagination_efficiency": round(len(work_items) / page_size * 100, 1)
                if page_size > 0
                else 0,
            }

            result = {
                "work_items": work_items,
                "pagination": pagination_info,
                "query_metadata": {
                    "query_type": query_result.queryType,
                    "columns": query_result.columns,
                },
                "performance_metrics": final_pagination_metrics,
            }

            logger.info(f"Pagination performance: {final_pagination_metrics}")
            logger.info(
                f"Successfully retrieved page {page_number} with {len(work_items)} items (has_more: {has_more})"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to get work items page: {e}")
            raise

    @mcp_instance.tool
    def get_my_work_items(
        project_id: str,
        assigned_to: str,
        state: str | None = None,
        work_item_type: str | None = None,
        page_size: int = 50,
        page_number: int = 1,
    ) -> dict[str, Any] | None:
        """
        Get work items assigned to a specific user.

        Convenience tool for getting work items assigned to a specific user with filtering.
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None

        try:
            # Build filter
            simple_filter = {"assigned_to": assigned_to}
            if state:
                simple_filter["state"] = state
            if work_item_type:
                simple_filter["work_item_type"] = work_item_type

            logger.info(f"Getting work items assigned to '{assigned_to}' in project: {project_id}")

            work_items_client = WorkItemsClient(ado_client_instance)

            # Build WIQL query from filter
            wiql_query = build_wiql_from_filter(simple_filter)

            # Calculate pagination
            skip = (page_number - 1) * page_size
            top = page_size

            # Execute query
            query_result = work_items_client.query_work_items(
                project_id=project_id, wiql_query=wiql_query, top=top, skip=skip
            )

            if not query_result:
                return None

            # Build pagination info from query result
            work_items = query_result.workItems
            has_more = len(work_items) >= page_size  # Simplified check

            pagination_info = {
                "page_number": page_number,
                "page_size": page_size,
                "items_count": len(work_items),
                "has_more": has_more,
                "has_previous": page_number > 1,
                "next_page": page_number + 1 if has_more else None,
                "previous_page": page_number - 1 if page_number > 1 else None,
            }

            result = {
                "work_items": work_items,
                "pagination": pagination_info,
                "query_metadata": {
                    "query_type": query_result.queryType,
                    "columns": query_result.columns,
                },
                "assignment_info": {
                    "assigned_to": assigned_to,
                    "state_filter": state,
                    "type_filter": work_item_type,
                },
            }

            logger.info(
                f"Successfully retrieved {len(result['work_items'])} work items for '{assigned_to}'"
            )

            return result

        except Exception as e:
            logger.error(f"Failed to get work items for '{assigned_to}': {e}")
            raise

    @mcp_instance.tool
    def get_recent_work_items(
        project_id: str,
        days: int = 7,
        work_item_type: str | None = None,
        state: str | None = None,
        page_size: int = 50,
        page_number: int = 1,
    ) -> dict[str, Any] | None:
        """
        Get work items created or modified recently.

        Convenience tool for getting recently created or modified work items with filtering.
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None

        try:
            # Calculate the date range with some buffer for timing issues
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days, hours=1)  # Add 1 hour buffer

            # Format dates for WIQL - use start of day to be more inclusive
            start_date_str = start_date.strftime("%Y-%m-%d")

            logger.info(f"Getting work items from the last {days} days in project: {project_id}")

            # Build filter with date range
            simple_filter = {"created_after": start_date_str}
            if work_item_type:
                simple_filter["work_item_type"] = work_item_type
            if state:
                simple_filter["state"] = state

            work_items_client = WorkItemsClient(ado_client_instance)

            # Build WIQL query from filter
            wiql_query = build_wiql_from_filter(simple_filter)
            logger.info(f"Generated WIQL query: {wiql_query}")

            # Calculate skip value for pagination
            skip = (page_number - 1) * page_size
            top = page_size + 1  # Get one extra to check if there are more

            query_result = work_items_client.query_work_items(
                project_id=project_id, wiql_query=wiql_query, top=top, skip=skip
            )

            work_items = query_result.workItems
            has_more = len(work_items) > page_size

            # Remove the extra item if present
            if has_more:
                work_items = work_items[:page_size]

            # Build pagination metadata
            pagination_info = {
                "page_number": page_number,
                "page_size": page_size,
                "items_count": len(work_items),
                "has_more": has_more,
                "has_previous": page_number > 1,
                "next_page": page_number + 1 if has_more else None,
                "previous_page": page_number - 1 if page_number > 1 else None,
            }

            result = {
                "work_items": work_items,
                "pagination": pagination_info,
                "time_filter": {
                    "days": days,
                    "start_date": start_date_str,
                    "end_date": end_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "type_filter": work_item_type,
                    "state_filter": state,
                },
                "query_metadata": {
                    "query_type": query_result.queryType,
                    "columns": query_result.columns,
                },
            }

            logger.info(
                f"Successfully retrieved {len(work_items)} recent work items (last {days} days)"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to get recent work items: {e}")
            raise
