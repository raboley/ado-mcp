"""MCP tool definitions for Azure DevOps Work Items type introspection."""

import logging

from ado.work_items.client import WorkItemsClient
from ado.work_items.models import (
    ClassificationNode,
    WorkItemField,
    WorkItemType,
)

logger = logging.getLogger(__name__)


def register_type_tools(mcp_instance, client_container):
    """
    Register work item type introspection tools with the FastMCP instance.

    Args:
        mcp_instance: The FastMCP instance to register tools with.
        client_container: Dictionary holding the AdoClient instance.
    """

    @mcp_instance.tool
    def list_work_item_types(
        project_id: str,
    ) -> list[WorkItemType]:
        """
        List all work item types available in a project.

        This tool returns metadata about work item types including their names,
        descriptions, colors, icons, and available states. Useful for discovering
        what types of work items can be created in a project.

        Args:
            project_id: The ID or name of the project.

        Returns:
            List of work item types with their properties.

        Examples:
            # Get all work item types for a project
            list_work_item_types(project_id="MyProject")

            # Result includes types like:
            # - Bug (for defects and issues)
            # - Task (for implementation work)
            # - User Story (for user requirements)
            # - Feature (for larger user capabilities)
            # - Epic (for major initiatives)
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return []

        try:
            work_items_client = WorkItemsClient(ado_client_instance)

            logger.info(f"Listing work item types for project: {project_id}")

            work_item_types = work_items_client.list_work_item_types(project_id)

            logger.info(f"Successfully listed {len(work_item_types)} work item types")
            return work_item_types

        except Exception as e:
            logger.error(f"Failed to list work item types: {e}")
            raise

    @mcp_instance.tool
    def get_work_item_type_fields(
        project_id: str,
        work_item_type: str,
    ) -> list[WorkItemField]:
        """
        Get all fields available for a specific work item type.

        This tool returns detailed information about all fields that can be used
        with a specific work item type, including field types, requirements,
        allowed values, and default values. Essential for understanding what
        fields are available when creating or updating work items.

        Args:
            project_id: The ID or name of the project.
            work_item_type: The name of the work item type (e.g., "Bug", "Task").

        Returns:
            List of field definitions for the work item type.

        Examples:
            # Get fields for Bug work items
            get_work_item_type_fields(project_id="MyProject", work_item_type="Bug")

            # Get fields for User Story work items
            get_work_item_type_fields(project_id="MyProject", work_item_type="User Story")

            # Fields typically include:
            # - System.Title (required text field)
            # - System.Description (optional HTML field)
            # - System.State (dropdown with allowed values)
            # - System.Priority (integer with allowed values)
            # - Custom fields specific to the organization
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return []

        try:
            work_items_client = WorkItemsClient(ado_client_instance)

            logger.info(
                f"Getting fields for work item type '{work_item_type}' in project: {project_id}"
            )

            fields = work_items_client.get_work_item_type_fields(project_id, work_item_type)

            logger.info(
                f"Successfully retrieved {len(fields)} fields for work item type '{work_item_type}'"
            )
            return fields

        except Exception as e:
            logger.error(f"Failed to get work item type fields: {e}")
            raise

    @mcp_instance.tool
    def get_work_item_type(
        project_id: str,
        work_item_type: str,
    ) -> WorkItemType:
        """
        Get detailed information about a specific work item type.

        This tool returns comprehensive information about a single work item type
        including states, transitions, colors, icons, and field information.
        This is more detailed than list_work_item_types which provides basic info
        for all types.

        Args:
            project_id: The ID or name of the project.
            work_item_type: The name of the work item type (e.g., "Bug", "Task").

        Returns:
            WorkItemType: Detailed work item type information.

        Examples:
            # Get detailed info for Bug work item type
            get_work_item_type(project_id="MyProject", work_item_type="Bug")

            # Get detailed info for User Story work item type
            get_work_item_type(project_id="MyProject", work_item_type="User Story")

            # The result includes:
            # - States and their colors/categories
            # - Valid state transitions
            # - Work item type color and icon
            # - Associated fields and constraints
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None

        try:
            work_items_client = WorkItemsClient(ado_client_instance)

            logger.info(
                f"Getting detailed work item type '{work_item_type}' in project: {project_id}"
            )

            work_item_type_details = work_items_client.get_work_item_type(
                project_id, work_item_type
            )

            logger.info(
                f"Successfully retrieved detailed information for work item type '{work_item_type}'"
            )
            return work_item_type_details

        except Exception as e:
            logger.error(f"Failed to get work item type details: {e}")
            raise

    @mcp_instance.tool
    def get_work_item_type_field(
        project_id: str,
        work_item_type: str,
        field_reference_name: str,
    ) -> WorkItemField:
        """
        Get detailed information about a specific field for a work item type.

        This tool returns comprehensive information about a single field including
        allowed values, constraints, defaults, and validation rules. This is more
        detailed than get_work_item_type_fields which returns basic info for all fields.

        Args:
            project_id: The ID or name of the project.
            work_item_type: The name of the work item type (e.g., "Bug", "Task").
            field_reference_name: The reference name of the field (e.g., "System.Title", "System.State").

        Returns:
            WorkItemField: Detailed field information.

        Examples:
            # Get detailed info for the State field of Bug work items
            get_work_item_type_field(
                project_id="MyProject",
                work_item_type="Bug",
                field_reference_name="System.State"
            )

            # Get detailed info for the Priority field
            get_work_item_type_field(
                project_id="MyProject",
                work_item_type="Task",
                field_reference_name="Microsoft.VSTS.Common.Priority"
            )

            # The result includes:
            # - Field type and constraints
            # - Allowed values for dropdown fields
            # - Default values
            # - Validation rules
            # - Help text and descriptions
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None

        try:
            work_items_client = WorkItemsClient(ado_client_instance)

            logger.info(
                f"Getting field '{field_reference_name}' for work item type '{work_item_type}' in project: {project_id}"
            )

            field_details = work_items_client.get_work_item_type_field(
                project_id, work_item_type, field_reference_name
            )

            logger.info(
                f"Successfully retrieved field details for '{field_reference_name}' in work item type '{work_item_type}'"
            )
            return field_details

        except Exception as e:
            logger.error(f"Failed to get work item type field details: {e}")
            raise

    @mcp_instance.tool
    def list_area_paths(
        project_id: str,
        depth: int | None = None,
    ) -> list[ClassificationNode]:
        """
        List area paths (classification nodes) for a project.

        Area paths are used to organize work items into logical groups representing
        product areas, teams, or components. They form a hierarchical tree structure
        that helps categorize and filter work items.

        Args:
            project_id: The ID or name of the project.
            depth: Maximum depth of the area path tree to retrieve (optional).
                  Use 1 for just the root areas, 2 for root + one level, etc.

        Returns:
            List of area path nodes with hierarchical structure.

        Examples:
            # Get all area paths
            list_area_paths(project_id="MyProject")

            # Get just the top-level areas
            list_area_paths(project_id="MyProject", depth=1)

            # Example area path structure:
            # MyProject
            # ├── Web
            # │   ├── Frontend
            # │   └── Backend
            # ├── Mobile
            # │   ├── iOS
            # │   └── Android
            # └── Infrastructure
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return []

        try:
            work_items_client = WorkItemsClient(ado_client_instance)

            logger.info(f"Listing area paths for project: {project_id}")

            area_paths = work_items_client.list_area_paths(project_id, depth)

            logger.info(f"Successfully retrieved area paths for project '{project_id}'")
            return area_paths

        except Exception as e:
            logger.error(f"Failed to list area paths: {e}")
            raise

    @mcp_instance.tool
    def list_iteration_paths(
        project_id: str,
        depth: int | None = None,
    ) -> list[ClassificationNode]:
        """
        List iteration paths (classification nodes) for a project.

        Iteration paths are used to organize work items into time-based groups
        representing sprints, releases, or other time-boxed periods. They form
        a hierarchical tree structure for project planning and tracking.

        Args:
            project_id: The ID or name of the project.
            depth: Maximum depth of the iteration path tree to retrieve (optional).
                  Use 1 for just the root iterations, 2 for root + one level, etc.

        Returns:
            List of iteration path nodes with hierarchical structure.

        Examples:
            # Get all iteration paths
            list_iteration_paths(project_id="MyProject")

            # Get just the top-level iterations
            list_iteration_paths(project_id="MyProject", depth=1)

            # Example iteration path structure:
            # MyProject
            # ├── Release 1.0
            # │   ├── Sprint 1
            # │   ├── Sprint 2
            # │   └── Sprint 3
            # ├── Release 2.0
            # │   ├── Sprint 4
            # │   └── Sprint 5
            # └── Backlog
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return []

        try:
            work_items_client = WorkItemsClient(ado_client_instance)

            logger.info(f"Listing iteration paths for project: {project_id}")

            iteration_paths = work_items_client.list_iteration_paths(project_id, depth)

            logger.info(f"Successfully retrieved iteration paths for project '{project_id}'")
            return iteration_paths

        except Exception as e:
            logger.error(f"Failed to list iteration paths: {e}")
            raise
