"""CRUD client methods for Azure DevOps Work Items API operations."""

import logging
from typing import Any, Dict, List, Optional

from ado.client import AdoClient
from ado.errors import (
    AdoError,
    AdoRateLimitError,
    AdoNetworkError,
    AdoTimeoutError,
    AdoAuthenticationError,
)
from opentelemetry import trace
from ado.work_items.models import (
    JsonPatchOperation,
    WorkItem,
)

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class CrudClient:
    """Client for Azure DevOps Work Items CRUD operations."""

    def __init__(self, client: AdoClient):
        """
        Initialize the CrudClient.

        Args:
            client: The AdoClient instance to use for API calls.
        """
        self.client = client
        self.auth_manager = client.auth_manager
        self.organization_url = client.organization_url

    def create_work_item(
        self,
        project_id: str,
        work_item_type: str,
        fields: Dict[str, Any],
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
        # Convert fields to JSON Patch format
        operations = []
        for field_path, value in fields.items():
            operations.append(
                JsonPatchOperation(op="add", path=f"/fields/{field_path}", value=value)
            )

        patch_document = [op.model_dump(exclude_none=True, by_alias=True) for op in operations]

        # Build query parameters
        params = {
            "validateOnly": validate_only,
            "bypassRules": bypass_rules,
            "suppressNotifications": suppress_notifications,
            "api-version": "7.1",
        }

        url = f"{self.organization_url}/{project_id}/_apis/wit/workitems/${work_item_type}"

        logger.info(
            f"Creating work item of type '{work_item_type}' in project '{project_id}' "
            f"with {len(operations)} fields"
        )

        try:
            # Build merged headers with content type for JSON patch
            request_headers = self.client.headers.copy()
            request_headers["Content-Type"] = "application/json-patch+json"

            # Use the client's retry-enabled _send_request method with proper headers
            with tracer.start_as_current_span("create_work_item") as span:
                span.set_attribute("work_item.type", work_item_type)
                span.set_attribute("work_item.project_id", project_id)
                span.set_attribute("work_item.field_count", len(operations))

                # Use client's session for connection pooling with retry wrapper
                import requests

                @self.client.retry_manager.retry_on_failure
                def make_create_request():
                    # Use session for connection pooling if available
                    request_func = (
                        self.client.session.request
                        if hasattr(self.client, "session") and self.client.session != requests
                        else requests.request
                    )
                    response = request_func(
                        method="POST",
                        url=url,
                        headers=request_headers,
                        json=patch_document,
                        params=params,
                        timeout=self.client.config.request_timeout_seconds,
                    )

                    # Handle specific status codes with proper error types
                    if response.status_code == 401:
                        raise AdoAuthenticationError(
                            "Authentication failed for work item creation",
                            context={"project_id": project_id, "work_item_type": work_item_type},
                        )
                    elif response.status_code == 429:
                        retry_after = response.headers.get("Retry-After")
                        raise AdoRateLimitError(
                            "Rate limit exceeded during work item creation",
                            retry_after=int(retry_after) if retry_after else None,
                            context={"project_id": project_id, "work_item_type": work_item_type},
                        )
                    elif response.status_code >= 500:
                        raise AdoNetworkError(
                            f"Server error during work item creation: {response.status_code}",
                            context={
                                "project_id": project_id,
                                "work_item_type": work_item_type,
                                "status_code": response.status_code,
                            },
                        )

                    response.raise_for_status()
                    return response.json() if response.content else None

                data = make_create_request()
                span.set_attribute("work_item.id", data.get("id"))

            logger.info(f"Successfully created work item ID: {data.get('id')}")
            return WorkItem(**data)

        except (AdoAuthenticationError, AdoRateLimitError, AdoNetworkError, AdoTimeoutError):
            # Re-raise our structured exceptions
            raise
        except Exception as e:
            logger.error(f"Failed to create work item: {e}")
            raise AdoError(
                f"Failed to create work item: {e}",
                "work_item_creation_failed",
                context={"project_id": project_id, "work_item_type": work_item_type},
                original_exception=e,
            ) from e

    def get_work_item(
        self,
        project_id: str,
        work_item_id: int,
        fields: Optional[List[str]] = None,
        as_of: Optional[str] = None,
        expand: Optional[str] = None,
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
        params = {"api-version": "7.1"}

        if fields:
            params["fields"] = ",".join(fields)
        if as_of:
            params["asOf"] = as_of
        if expand:
            params["$expand"] = expand

        url = f"{self.organization_url}/{project_id}/_apis/wit/workitems/{work_item_id}"

        logger.info(f"Getting work item {work_item_id} from project '{project_id}'")

        try:
            with tracer.start_as_current_span("get_work_item") as span:
                span.set_attribute("work_item.id", work_item_id)
                span.set_attribute("work_item.project_id", project_id)

                data = self.client._send_request(method="GET", url=url, params=params)

            logger.info(f"Successfully retrieved work item {work_item_id}")
            return WorkItem(**data)

        except (AdoAuthenticationError, AdoRateLimitError, AdoNetworkError, AdoTimeoutError):
            # Re-raise our structured exceptions
            raise
        except Exception as e:
            logger.error(f"Failed to get work item {work_item_id}: {e}")
            raise AdoError(
                f"Failed to get work item {work_item_id}: {e}",
                "work_item_get_failed",
                context={"project_id": project_id, "work_item_id": work_item_id},
                original_exception=e,
            ) from e

    def update_work_item(
        self,
        project_id: str,
        work_item_id: int,
        operations: List[JsonPatchOperation],
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
        patch_document = [op.model_dump(exclude_none=True, by_alias=True) for op in operations]

        params = {
            "validateOnly": validate_only,
            "bypassRules": bypass_rules,
            "suppressNotifications": suppress_notifications,
            "api-version": "7.1",
        }

        url = f"{self.organization_url}/{project_id}/_apis/wit/workitems/{work_item_id}"

        logger.info(
            f"Updating work item {work_item_id} in project '{project_id}' "
            f"with {len(operations)} operations"
        )

        try:
            with tracer.start_as_current_span("update_work_item") as span:
                span.set_attribute("work_item.id", work_item_id)
                span.set_attribute("work_item.project_id", project_id)
                span.set_attribute("work_item.operations_count", len(operations))

                # Build merged headers with content type for JSON patch
                request_headers = self.client.headers.copy()
                request_headers["Content-Type"] = "application/json-patch+json"

                # Use retry wrapper for update operations
                import requests

                @self.client.retry_manager.retry_on_failure
                def make_update_request():
                    # Use session for connection pooling if available
                    request_func = (
                        self.client.session.request
                        if hasattr(self.client, "session") and self.client.session != requests
                        else requests.request
                    )
                    response = request_func(
                        method="PATCH",
                        url=url,
                        headers=request_headers,
                        json=patch_document,
                        params=params,
                        timeout=self.client.config.request_timeout_seconds,
                    )

                    # Handle specific status codes
                    if response.status_code == 401:
                        raise AdoAuthenticationError(
                            "Authentication failed for work item update",
                            context={"project_id": project_id, "work_item_id": work_item_id},
                        )
                    elif response.status_code == 429:
                        retry_after = response.headers.get("Retry-After")
                        raise AdoRateLimitError(
                            "Rate limit exceeded during work item update",
                            retry_after=int(retry_after) if retry_after else None,
                            context={"project_id": project_id, "work_item_id": work_item_id},
                        )
                    elif response.status_code >= 500:
                        raise AdoNetworkError(
                            f"Server error during work item update: {response.status_code}",
                            context={
                                "project_id": project_id,
                                "work_item_id": work_item_id,
                                "status_code": response.status_code,
                            },
                        )

                    response.raise_for_status()
                    return response.json() if response.content else None

                data = make_update_request()

            logger.info(f"Successfully updated work item {work_item_id}")
            return WorkItem(**data)

        except (AdoAuthenticationError, AdoRateLimitError, AdoNetworkError, AdoTimeoutError):
            # Re-raise our structured exceptions
            raise
        except Exception as e:
            logger.error(f"Failed to update work item {work_item_id}: {e}")
            raise AdoError(
                f"Failed to update work item {work_item_id}: {e}",
                "work_item_update_failed",
                context={
                    "project_id": project_id,
                    "work_item_id": work_item_id,
                    "operations_count": len(operations),
                },
                original_exception=e,
            ) from e

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
        params = {"destroy": destroy, "api-version": "7.1"}

        url = f"{self.organization_url}/{project_id}/_apis/wit/workitems/{work_item_id}"

        logger.info(
            f"{'Destroying' if destroy else 'Deleting'} work item {work_item_id} "
            f"from project '{project_id}'"
        )

        try:
            self.client._send_request(method="DELETE", url=url, params=params)

            logger.info(f"Successfully deleted work item {work_item_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete work item {work_item_id}: {e}")
            raise AdoError(
                f"Failed to delete work item {work_item_id}: {e}", "work_item_delete_failed"
            ) from e