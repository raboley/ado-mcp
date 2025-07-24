"""Client methods for Azure DevOps Work Items Type Introspection API operations."""

import logging

from opentelemetry import trace

from ado.cache import ado_cache
from ado.client import AdoClient
from ado.errors import AdoError
from ado.work_items.models import (
    ClassificationNode,
    WorkItemField,
    WorkItemType,
)

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class TypeClient:
    """Client for Azure DevOps Work Items Type Introspection API operations."""

    def __init__(self, client: AdoClient):
        """
        Initialize the TypeClient.

        Args:
            client: The AdoClient instance to use for API calls.
        """
        self.client = client
        self.auth_manager = client.auth_manager
        self.organization_url = client.organization_url

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
        # Check cache first
        cached_types = ado_cache.get_work_item_types(project_id)
        if cached_types is not None:
            logger.info(
                f"Returning {len(cached_types)} cached work item types for project '{project_id}'"
            )
            return cached_types

        url = f"{self.organization_url}/{project_id}/_apis/wit/workitemtypes"
        params = {"api-version": "7.1"}

        logger.info(f"Getting work item types from API for project '{project_id}'")

        try:
            data = self.client._send_request(method="GET", url=url, params=params)

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
            raise AdoError(
                f"Failed to get work item types: {e}", "work_item_types_get_failed"
            ) from e

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
        # Check cache first
        cache_key = f"work_item_type_detailed:{project_id}:{work_item_type}"
        cached_result = ado_cache._get(cache_key)
        if cached_result:
            logger.info(
                f"Returning cached detailed work item type '{work_item_type}' for project '{project_id}'"
            )
            return WorkItemType(**cached_result)

        url = f"{self.organization_url}/{project_id}/_apis/wit/workitemtypes/{work_item_type}"
        params = {
            "api-version": "7.1",
            "expand": "states,transitions",  # Get detailed state and transition information
        }

        logger.info(f"Getting detailed work item type '{work_item_type}' in project '{project_id}'")

        try:
            data = self.client._send_request(method="GET", url=url, params=params)

            logger.info(
                f"Successfully retrieved detailed information for work item type '{work_item_type}'"
            )

            work_item_type_obj = WorkItemType(**data)

            # Cache the result for 1 hour
            ado_cache._set(cache_key, work_item_type_obj.model_dump(), 3600)

            return work_item_type_obj

        except Exception as e:
            logger.error(f"Failed to get work item type details: {e}")
            raise AdoError(
                f"Failed to get work item type details: {e}", "work_item_type_details_get_failed"
            ) from e

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
        url = (
            f"{self.organization_url}/{project_id}/_apis/wit/workitemtypes/{work_item_type}/fields"
        )
        params = {"api-version": "7.1"}

        logger.info(
            f"Getting fields for work item type '{work_item_type}' in project '{project_id}'"
        )

        try:
            data = self.client._send_request(method="GET", url=url, params=params)

            fields_data = data.get("value", [])
            logger.info(
                f"Successfully retrieved {len(fields_data)} fields for work item type '{work_item_type}'"
            )

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
            raise AdoError(
                f"Failed to get work item type fields: {e}", "work_item_type_fields_get_failed"
            ) from e

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
        # Check cache first
        cache_key = f"work_item_type_field:{project_id}:{work_item_type}:{field_reference_name}"
        cached_result = ado_cache._get(cache_key)
        if cached_result:
            logger.info(
                f"Returning cached field '{field_reference_name}' for work item type '{work_item_type}' in project '{project_id}'"
            )
            return WorkItemField(**cached_result)

        url = f"{self.organization_url}/{project_id}/_apis/wit/workitemtypes/{work_item_type}/fields/{field_reference_name}"
        params = {"api-version": "7.1"}

        logger.info(
            f"Getting field '{field_reference_name}' for work item type '{work_item_type}' in project '{project_id}'"
        )

        try:
            data = self.client._send_request(method="GET", url=url, params=params)

            logger.info(
                f"Successfully retrieved field '{field_reference_name}' for work item type '{work_item_type}'"
            )

            field = WorkItemField(**data)

            # Cache the result for 1 hour
            ado_cache._set(cache_key, field.model_dump(), 3600)

            return field

        except Exception as e:
            logger.error(f"Failed to get work item type field: {e}")
            raise AdoError(
                f"Failed to get work item type field: {e}", "work_item_type_field_get_failed"
            ) from e

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
        # Only use cache when depth is None (full tree)
        if depth is None:
            cached_paths = ado_cache.get_area_paths(project_id)
            if cached_paths is not None:
                logger.info(f"Returning cached area paths for project '{project_id}'")
                return cached_paths

        url = f"{self.organization_url}/{project_id}/_apis/wit/classificationnodes/areas"
        params = {"api-version": "7.1"}

        if depth is not None:
            params["$depth"] = depth

        logger.info(f"Getting area paths from API for project '{project_id}'")

        try:
            data = self.client._send_request(method="GET", url=url, params=params)

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
        # Only use cache when depth is None (full tree)
        if depth is None:
            cached_paths = ado_cache.get_iteration_paths(project_id)
            if cached_paths is not None:
                logger.info(f"Returning cached iteration paths for project '{project_id}'")
                return cached_paths

        url = f"{self.organization_url}/{project_id}/_apis/wit/classificationnodes/iterations"
        params = {"api-version": "7.1"}

        if depth is not None:
            params["$depth"] = depth

        logger.info(f"Getting iteration paths from API for project '{project_id}'")

        try:
            data = self.client._send_request(method="GET", url=url, params=params)

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
            raise AdoError(
                f"Failed to get iteration paths: {e}", "iteration_paths_get_failed"
            ) from e
