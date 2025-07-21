"""Client methods for Azure DevOps Work Items API operations."""

import logging
from typing import Any, Dict, List, Optional, Union

from ado.client import AdoClient
from ado.errors import AdoError
from ado.cache import ado_cache
# Retry is handled by the client's _send_request method
# Telemetry is optional for now
from ado.work_items.models import (
    ClassificationNode,
    JsonPatchDocument,
    JsonPatchOperation,
    WorkItem,
    WorkItemComment,
    WorkItemField,
    WorkItemReference,
    WorkItemQueryResult,
    WorkItemRevision,
    WorkItemType,
    WorkItemTypeState,
    WorkItemTypeTransition,
)

logger = logging.getLogger(__name__)


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
                JsonPatchOperation(
                    op="add",
                    path=f"/fields/{field_path}",
                    value=value
                )
            )
        
        patch_document = [op.model_dump(exclude_none=True, by_alias=True) for op in operations]
        
        # Build query parameters
        params = {
            "validateOnly": validate_only,
            "bypassRules": bypass_rules,
            "suppressNotifications": suppress_notifications,
            "api-version": "7.1"
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
            
            # Use requests directly like the client's _send_request but with our headers
            import requests
            response = requests.request(
                method="POST",
                url=url,
                headers=request_headers,
                json=patch_document,
                params=params,
                timeout=self.client.config.request_timeout_seconds
            )
            response.raise_for_status()
            data = response.json() if response.content else None
            
            logger.info(f"Successfully created work item ID: {data.get('id')}")
            return WorkItem(**data)
            
        except Exception as e:
            logger.error(f"Failed to create work item: {e}")
            raise AdoError(f"Failed to create work item: {e}", "work_item_creation_failed") from e
    
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
        params = {
            "api-version": "7.1"
        }
        
        if fields:
            params["fields"] = ",".join(fields)
        if as_of:
            params["asOf"] = as_of
        if expand:
            params["$expand"] = expand
            
        url = f"{self.organization_url}/{project_id}/_apis/wit/workitems/{work_item_id}"
        
        logger.info(f"Getting work item {work_item_id} from project '{project_id}'")
        
        try:
            data = self.client._send_request(
                method="GET",
                url=url,
                params=params
            )
            
            logger.info(f"Successfully retrieved work item {work_item_id}")
            return WorkItem(**data)
            
        except Exception as e:
            logger.error(f"Failed to get work item {work_item_id}: {e}")
            raise AdoError(f"Failed to get work item {work_item_id}: {e}", "work_item_get_failed") from e
    
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
            "api-version": "7.1"
        }
        
        url = f"{self.organization_url}/{project_id}/_apis/wit/workitems/{work_item_id}"
        
        logger.info(
            f"Updating work item {work_item_id} in project '{project_id}' "
            f"with {len(operations)} operations"
        )
        
        try:
            # Build merged headers with content type for JSON patch
            request_headers = self.client.headers.copy()
            request_headers["Content-Type"] = "application/json-patch+json"
            
            # Use requests directly like the client's _send_request but with our headers
            import requests
            response = requests.request(
                method="PATCH",
                url=url,
                headers=request_headers,
                json=patch_document,
                params=params,
                timeout=self.client.config.request_timeout_seconds
            )
            response.raise_for_status()
            data = response.json() if response.content else None
            
            logger.info(f"Successfully updated work item {work_item_id}")
            return WorkItem(**data)
            
        except Exception as e:
            logger.error(f"Failed to update work item {work_item_id}: {e}")
            raise AdoError(f"Failed to update work item {work_item_id}: {e}", "work_item_update_failed") from e
    
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
        params = {
            "destroy": destroy,
            "api-version": "7.1"
        }
        
        url = f"{self.organization_url}/{project_id}/_apis/wit/workitems/{work_item_id}"
        
        logger.info(
            f"{'Destroying' if destroy else 'Deleting'} work item {work_item_id} "
            f"from project '{project_id}'"
        )
        
        try:
            self.client._send_request(
                method="DELETE",
                url=url,
                params=params
            )
            
            logger.info(f"Successfully deleted work item {work_item_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete work item {work_item_id}: {e}")
            raise AdoError(f"Failed to delete work item {work_item_id}: {e}", "work_item_delete_failed") from e
    
    def list_work_item_types(
        self,
        project_id: str,
    ) -> List[WorkItemType]:
        """
        Get all work item types for a project.
        
        Args:
            project_id: The ID or name of the project.
            
        Returns:
            List of WorkItemType objects.
            
        Raises:
            AdoError: If the API request fails.
        """
        # Check cache first
        cached_types = ado_cache.get_work_item_types(project_id)
        if cached_types is not None:
            logger.info(f"Returning {len(cached_types)} cached work item types for project '{project_id}'")
            return cached_types
        
        url = f"{self.organization_url}/{project_id}/_apis/wit/workitemtypes"
        params = {
            "api-version": "7.1"
        }
        
        logger.info(f"Getting work item types from API for project '{project_id}'")
        
        try:
            data = self.client._send_request(
                method="GET",
                url=url,
                params=params
            )
            
            work_item_types_data = data.get("value", [])
            logger.info(f"Successfully retrieved {len(work_item_types_data)} work item types")
            
            work_item_types = []
            for wit_data in work_item_types_data:
                try:
                    work_item_type = WorkItemType(**wit_data)
                    work_item_types.append(work_item_type)
                except Exception as e:
                    logger.warning(f"Failed to parse work item type data: {wit_data}. Error: {e}")
            
            # Cache the results
            ado_cache.set_work_item_types(project_id, work_item_types)
            
            return work_item_types
            
        except Exception as e:
            logger.error(f"Failed to get work item types: {e}")
            raise AdoError(f"Failed to get work item types: {e}", "work_item_types_get_failed") from e
    
    def get_work_item_type_fields(
        self,
        project_id: str,
        work_item_type: str,
    ) -> List[WorkItemField]:
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
        url = f"{self.organization_url}/{project_id}/_apis/wit/workitemtypes/{work_item_type}/fields"
        params = {
            "api-version": "7.1"
        }
        
        logger.info(f"Getting fields for work item type '{work_item_type}' in project '{project_id}'")
        
        try:
            data = self.client._send_request(
                method="GET",
                url=url,
                params=params
            )
            
            fields_data = data.get("value", [])
            logger.info(f"Successfully retrieved {len(fields_data)} fields for work item type '{work_item_type}'")
            
            fields = []
            for field_data in fields_data:
                try:
                    field = WorkItemField(**field_data)
                    fields.append(field)
                except Exception as e:
                    logger.warning(f"Failed to parse field data: {field_data}. Error: {e}")
            
            return fields
            
        except Exception as e:
            logger.error(f"Failed to get work item type fields: {e}")
            raise AdoError(f"Failed to get work item type fields: {e}", "work_item_type_fields_get_failed") from e
    
    def list_area_paths(
        self,
        project_id: str,
        depth: Optional[int] = None,
    ) -> List[ClassificationNode]:
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
        # Only use cache when depth is None (full tree)
        if depth is None:
            cached_paths = ado_cache.get_area_paths(project_id)
            if cached_paths is not None:
                logger.info(f"Returning cached area paths for project '{project_id}'")
                return cached_paths
        
        url = f"{self.organization_url}/{project_id}/_apis/wit/classificationnodes/areas"
        params = {
            "api-version": "7.1"
        }
        
        if depth is not None:
            params["$depth"] = depth
        
        logger.info(f"Getting area paths from API for project '{project_id}'")
        
        try:
            data = self.client._send_request(
                method="GET",
                url=url,
                params=params
            )
            
            logger.info(f"Successfully retrieved area paths for project '{project_id}'")
            
            # Parse as ClassificationNode
            result = []
            if data:
                try:
                    node = ClassificationNode(**data)
                    result = [node]
                except Exception as e:
                    logger.warning(f"Failed to parse area path data: {data}. Error: {e}")
                    result = []
            
            # Cache the results if we got the full tree
            if depth is None and result:
                ado_cache.set_area_paths(project_id, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get area paths: {e}")
            raise AdoError(f"Failed to get area paths: {e}", "area_paths_get_failed") from e
    
    def list_iteration_paths(
        self,
        project_id: str,
        depth: Optional[int] = None,
    ) -> List[ClassificationNode]:
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
        # Only use cache when depth is None (full tree)
        if depth is None:
            cached_paths = ado_cache.get_iteration_paths(project_id)
            if cached_paths is not None:
                logger.info(f"Returning cached iteration paths for project '{project_id}'")
                return cached_paths
        
        url = f"{self.organization_url}/{project_id}/_apis/wit/classificationnodes/iterations"
        params = {
            "api-version": "7.1"
        }
        
        if depth is not None:
            params["$depth"] = depth
        
        logger.info(f"Getting iteration paths from API for project '{project_id}'")
        
        try:
            data = self.client._send_request(
                method="GET",
                url=url,
                params=params
            )
            
            logger.info(f"Successfully retrieved iteration paths for project '{project_id}'")
            
            # Parse as ClassificationNode
            result = []
            if data:
                try:
                    node = ClassificationNode(**data)
                    result = [node]
                except Exception as e:
                    logger.warning(f"Failed to parse iteration path data: {data}. Error: {e}")
                    result = []
            
            # Cache the results if we got the full tree
            if depth is None and result:
                ado_cache.set_iteration_paths(project_id, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get iteration paths: {e}")
            raise AdoError(f"Failed to get iteration paths: {e}", "iteration_paths_get_failed") from e
    
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
        params = {
            "api-version": "7.1"
        }
        
        if top is not None:
            params["$top"] = top
        
        if skip is not None:
            params["$skip"] = skip
        
        request_body = {
            "query": wiql_query
        }
        
        logger.info(f"Querying work items in project '{project_id}' with query: {wiql_query[:100]}...")
        
        try:
            data = self.client._send_request(
                method="POST",
                url=url,
                params=params,
                json=request_body
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
            
    def get_work_items_batch(
        self,
        project_id: str,
        work_item_ids: List[int],
        fields: Optional[List[str]] = None,
        expand_relations: bool = False,
        as_of: Optional[str] = None,
        error_policy: str = "omit"
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
            "errorPolicy": error_policy
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
            data = self.client._send_request(
                method="GET",
                url=url,
                params=params
            )
            
            work_items = []
            if data and "value" in data:
                for item_data in data["value"]:
                    try:
                        work_items.append(WorkItem(**item_data))
                    except Exception as e:
                        logger.warning(f"Failed to parse work item data: {item_data}. Error: {e}")
                        if error_policy == "fail":
                            raise AdoError(f"Failed to parse work item data: {e}", "work_item_parse_failed") from e
                        # If error_policy is "omit", just skip this item
                        continue
            
            logger.info(f"Successfully retrieved {len(work_items)} work items out of {len(work_item_ids)} requested")
            return work_items
            
        except Exception as e:
            logger.error(f"Failed to get work items batch: {e}")
            raise AdoError(f"Failed to get work items batch: {e}", "work_items_batch_failed") from e