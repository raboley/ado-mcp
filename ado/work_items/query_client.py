"""Query client methods for Azure DevOps Work Items API operations."""

import logging
from typing import Any, Dict, List, Optional

from ado.client import AdoClient
from ado.errors import AdoError
from opentelemetry import trace
from ado.work_items.models import WorkItemQueryResult

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class QueryClient:
    """Client for Azure DevOps Work Items Query API operations."""

    def __init__(self, client: AdoClient):
        """
        Initialize the QueryClient.

        Args:
            client: The AdoClient instance to use for API calls.
        """
        self.client = client
        self.auth_manager = client.auth_manager
        self.organization_url = client.organization_url

    def query_work_items(
        self,
        project_id: str,
        wiql_query: Optional[str] = None,
        top: Optional[int] = None,
        skip: Optional[int] = None,
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
        # Default query to list all work items if none provided
        if wiql_query is None:
            wiql_query = (
                "SELECT [System.Id], [System.Title], [System.WorkItemType], "
                "[System.State], [System.AssignedTo], [System.CreatedDate] "
                "FROM WorkItems ORDER BY [System.Id]"
            )

        url = f"{self.organization_url}/{project_id}/_apis/wit/wiql"
        params = {"api-version": "7.1"}

        if top is not None:
            params["$top"] = top

        if skip is not None:
            params["$skip"] = skip

        request_body = {"query": wiql_query}

        logger.info(
            f"Querying work items in project '{project_id}' with query: {wiql_query[:100]}..."
        )

        try:
            data = self.client._send_request(
                method="POST", url=url, params=params, json=request_body
            )

            logger.info(f"Successfully queried work items for project '{project_id}'")

            # Parse as WorkItemQueryResult
            if data:
                try:
                    return WorkItemQueryResult(**data)
                except Exception as e:
                    logger.warning(f"Failed to parse query result data: {data}. Error: {e}")
                    return WorkItemQueryResult(queryType="flat", asOf="", columns=[], workItems=[])
            else:
                return WorkItemQueryResult(queryType="flat", asOf="", columns=[], workItems=[])

        except Exception as e:
            logger.error(f"Failed to query work items: {e}")
            raise AdoError(f"Failed to query work items: {e}", "work_items_query_failed") from e