"""MCP tool definitions for Azure DevOps Work Items."""

import logging
from typing import Any, Dict, List, Optional

from ado.work_items.client import WorkItemsClient
from ado.work_items.models import JsonPatchOperation, WorkItem, WorkItemType, WorkItemField, ClassificationNode, WorkItemReference, WorkItemQueryResult
from ado.work_items.validation import WorkItemValidator

logger = logging.getLogger(__name__)


def register_work_item_tools(mcp_instance, client_container):
    """
    Register work item related tools with the FastMCP instance.
    
    Args:
        mcp_instance: The FastMCP instance to register tools with.
        client_container: Dictionary holding the AdoClient instance.
    """
    
    @mcp_instance.tool
    def create_work_item(
        project_id: str,
        work_item_type: str,
        title: str,
        description: Optional[str] = None,
        area_path: Optional[str] = None,
        iteration_path: Optional[str] = None,
        assigned_to: Optional[str] = None,
        state: Optional[str] = None,
        priority: Optional[int] = None,
        tags: Optional[str] = None,
        additional_fields: Optional[Dict[str, Any]] = None,
        validate_only: bool = False,
        bypass_rules: bool = False,
        suppress_notifications: bool = False,
    ) -> Optional[WorkItem]:
        """
        Create a new work item in Azure DevOps.
        
        This tool creates work items of any standard type (Bug, Task, User Story, etc.)
        with support for all common fields plus custom fields via additional_fields.
        
        Args:
            project_id: The ID or name of the project where the work item will be created.
            work_item_type: The type of work item (e.g., "Bug", "Task", "User Story", "Feature", "Epic").
            title: The title of the work item (required).
            description: The description or repro steps for the work item.
            area_path: The area path (e.g., "MyProject\\Team1\\Component").
            iteration_path: The iteration path (e.g., "MyProject\\Sprint 1").
            assigned_to: Email address or display name of the person to assign to.
            state: The initial state (e.g., "New", "Active"). Defaults to type's default.
            priority: Priority level (1=highest, 4=lowest).
            tags: Semicolon-separated list of tags (e.g., "tag1; tag2; tag3").
            additional_fields: Dictionary of additional fields using reference names as keys
                             (e.g., {"System.History": "Initial creation", "Custom.Field": "value"}).
            validate_only: If true, only validate without creating the work item.
            bypass_rules: If true, bypass validation rules (requires special permissions).
            suppress_notifications: If true, don't send email notifications.
            
        Returns:
            WorkItem: The created work item object, or None if client unavailable.
            
        Examples:
            # Create a simple bug
            create_work_item(
                project_id="MyProject",
                work_item_type="Bug",
                title="Login button not working",
                description="Users cannot click the login button on mobile devices",
                priority=2
            )
            
            # Create a user story with full details
            create_work_item(
                project_id="MyProject",
                work_item_type="User Story",
                title="As a user, I want to reset my password",
                description="Implement password reset functionality...",
                area_path="MyProject\\Web\\Authentication",
                iteration_path="MyProject\\Sprint 15",
                assigned_to="developer@company.com",
                state="Active",
                priority=1,
                tags="security; authentication"
            )
            
            # Create with custom fields
            create_work_item(
                project_id="MyProject",
                work_item_type="Task",
                title="Deploy to staging",
                additional_fields={
                    "Microsoft.VSTS.Common.Activity": "Deployment",
                    "Custom.Environment": "Staging"
                }
            )
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None
            
        try:
            if not bypass_rules and not WorkItemValidator.validate_work_item_type(project_id, work_item_type):
                logger.warning(f"Work item type '{work_item_type}' may not be valid for project '{project_id}'")
            
            fields = {
                "System.Title": title,
            }
            
            if description:
                fields["System.Description"] = description
            if area_path:
                area_path = WorkItemValidator.sanitize_path(area_path)
                if not bypass_rules and not WorkItemValidator.validate_area_path(project_id, area_path):
                    logger.warning(f"Area path '{area_path}' may not be valid for project '{project_id}'")
                    suggestions = WorkItemValidator.suggest_valid_paths(project_id, area_path, "area")
                    if suggestions:
                        logger.info(f"Suggested area paths: {', '.join(suggestions[:3])}")
                fields["System.AreaPath"] = area_path
            if iteration_path:
                iteration_path = WorkItemValidator.sanitize_path(iteration_path)
                if not bypass_rules and not WorkItemValidator.validate_iteration_path(project_id, iteration_path):
                    logger.warning(f"Iteration path '{iteration_path}' may not be valid for project '{project_id}'")
                    suggestions = WorkItemValidator.suggest_valid_paths(project_id, iteration_path, "iteration")
                    if suggestions:
                        logger.info(f"Suggested iteration paths: {', '.join(suggestions[:3])}")
                fields["System.IterationPath"] = iteration_path
            if assigned_to:
                fields["System.AssignedTo"] = assigned_to
            if state:
                fields["System.State"] = state
            if priority:
                if not bypass_rules and not WorkItemValidator.validate_field_value("System.Priority", priority, "Integer"):
                    raise ValueError(f"Invalid priority value: {priority}. Must be an integer between 1 and 4.")
                fields["System.Priority"] = priority
            if tags:
                fields["System.Tags"] = tags
                
            if additional_fields:
                if not bypass_rules:
                    for field_name, field_value in additional_fields.items():
                        if not WorkItemValidator.validate_field_value(field_name, field_value):
                            logger.warning(f"Field '{field_name}' value may not be valid: {field_value}")
                fields.update(additional_fields)
                
            work_items_client = WorkItemsClient(ado_client_instance)
            work_items_client = WorkItemsClient(ado_client_instance)
            
            # Create the work item
            work_item = work_items_client.create_work_item(
                project_id=project_id,
                work_item_type=work_item_type,
                fields=fields,
                validate_only=validate_only,
                bypass_rules=bypass_rules,
                suppress_notifications=suppress_notifications,
            )
            
            if validate_only:
                logger.info(f"Work item validation successful for type '{work_item_type}'")
            else:
                logger.info(
                    f"Created {work_item_type} work item #{work_item.id}: {title}"
                )
                
            return work_item
            
        except Exception as e:
            logger.error(f"Failed to create work item: {e}")
            raise
    
    @mcp_instance.tool
    def get_work_item(
        project_id: str,
        work_item_id: int,
        fields: Optional[List[str]] = None,
        expand_relations: bool = False,
        as_of: Optional[str] = None,
    ) -> Optional[WorkItem]:
        """
        Retrieve a single work item by ID.
        
        Args:
            project_id: The ID or name of the project.
            work_item_id: The ID of the work item to retrieve.
            fields: List of specific fields to return (e.g., ["System.Title", "System.State"]).
                   If not specified, all fields are returned.
            expand_relations: If true, include related work items information.
            as_of: Retrieve work item as it was at a specific date/time (ISO 8601 format).
            
        Returns:
            WorkItem: The work item object, or None if client unavailable.
            
        Examples:
            # Get basic work item
            get_work_item(project_id="MyProject", work_item_id=123)
            
            # Get specific fields only
            get_work_item(
                project_id="MyProject",
                work_item_id=123,
                fields=["System.Title", "System.State", "System.AssignedTo"]
            )
            
            # Get with relations
            get_work_item(
                project_id="MyProject",
                work_item_id=123,
                expand_relations=True
            )
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None
            
        try:
            work_items_client = WorkItemsClient(ado_client_instance)
            
            expand = "relations" if expand_relations else None
            
            work_item = work_items_client.get_work_item(
                project_id=project_id,
                work_item_id=work_item_id,
                fields=fields,
                as_of=as_of,
                expand=expand,
            )
            
            logger.info(f"Retrieved work item #{work_item_id}")
            return work_item
            
        except Exception as e:
            logger.error(f"Failed to get work item {work_item_id}: {e}")
            raise
    
    @mcp_instance.tool
    def update_work_item(
        project_id: str,
        work_item_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        state: Optional[str] = None,
        assigned_to: Optional[str] = None,
        priority: Optional[int] = None,
        area_path: Optional[str] = None,
        iteration_path: Optional[str] = None,
        tags: Optional[str] = None,
        fields_to_update: Optional[Dict[str, Any]] = None,
        fields_to_remove: Optional[List[str]] = None,
        validate_only: bool = False,
        bypass_rules: bool = False,
        suppress_notifications: bool = False,
    ) -> Optional[WorkItem]:
        """
        Update an existing work item.
        
        Args:
            project_id: The ID or name of the project.
            work_item_id: The ID of the work item to update.
            title: New title for the work item.
            description: New description.
            state: New state (e.g., "Active", "Resolved", "Closed").
            assigned_to: New assignee (email or display name).
            priority: New priority (1-4).
            area_path: New area path.
            iteration_path: New iteration path.
            tags: New tags (semicolon-separated).
            fields_to_update: Dictionary of additional fields to update.
            fields_to_remove: List of field reference names to remove.
            validate_only: If true, only validate without updating.
            bypass_rules: If true, bypass validation rules.
            suppress_notifications: If true, don't send notifications.
            
        Returns:
            WorkItem: The updated work item object, or None if client unavailable.
            
        Examples:
            # Update state and assignment
            update_work_item(
                project_id="MyProject",
                work_item_id=123,
                state="Active",
                assigned_to="developer@company.com"
            )
            
            # Update with custom fields
            update_work_item(
                project_id="MyProject",
                work_item_id=123,
                fields_to_update={
                    "Microsoft.VSTS.Common.Activity": "Development",
                    "Custom.ReviewStatus": "In Progress"
                }
            )
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None
            
        try:
            operations = []
            
            # Build update operations
            updates = {}
            if title is not None:
                updates["System.Title"] = title
            if description is not None:
                updates["System.Description"] = description
            if state is not None:
                updates["System.State"] = state
            if assigned_to is not None:
                updates["System.AssignedTo"] = assigned_to
            if priority is not None:
                if not bypass_rules and not WorkItemValidator.validate_field_value("System.Priority", priority, "Integer"):
                    raise ValueError(f"Invalid priority value: {priority}. Must be an integer between 1 and 4.")
                updates["System.Priority"] = priority
            if area_path is not None:
                area_path = WorkItemValidator.sanitize_path(area_path)
                if not bypass_rules and not WorkItemValidator.validate_area_path(project_id, area_path):
                    logger.warning(f"Area path '{area_path}' may not be valid for project '{project_id}'")
                    suggestions = WorkItemValidator.suggest_valid_paths(project_id, area_path, "area")
                    if suggestions:
                        logger.info(f"Suggested area paths: {', '.join(suggestions[:3])}")
                updates["System.AreaPath"] = area_path
            if iteration_path is not None:
                iteration_path = WorkItemValidator.sanitize_path(iteration_path)
                if not bypass_rules and not WorkItemValidator.validate_iteration_path(project_id, iteration_path):
                    logger.warning(f"Iteration path '{iteration_path}' may not be valid for project '{project_id}'")
                    suggestions = WorkItemValidator.suggest_valid_paths(project_id, iteration_path, "iteration")
                    if suggestions:
                        logger.info(f"Suggested iteration paths: {', '.join(suggestions[:3])}")
                updates["System.IterationPath"] = iteration_path
            if tags is not None:
                updates["System.Tags"] = tags
                
            if fields_to_update:
                if not bypass_rules:
                    for field_name, field_value in fields_to_update.items():
                        if not WorkItemValidator.validate_field_value(field_name, field_value):
                            logger.warning(f"Field '{field_name}' value may not be valid: {field_value}")
                updates.update(fields_to_update)
                
            for field_path, value in updates.items():
                operations.append(
                    JsonPatchOperation(
                        op="replace",
                        path=f"/fields/{field_path}",
                        value=value
                    )
                )
                
            if fields_to_remove:
                for field_path in fields_to_remove:
                    operations.append(
                        JsonPatchOperation(
                            op="remove",
                            path=f"/fields/{field_path}"
                        )
                    )
                    
            if not operations:
                logger.warning("No update operations specified")
                return None
                
            work_items_client = WorkItemsClient(ado_client_instance)
            
            work_item = work_items_client.update_work_item(
                project_id=project_id,
                work_item_id=work_item_id,
                operations=operations,
                validate_only=validate_only,
                bypass_rules=bypass_rules,
                suppress_notifications=suppress_notifications,
            )
            
            if validate_only:
                logger.info(f"Work item update validation successful for #{work_item_id}")
            else:
                logger.info(f"Updated work item #{work_item_id}")
                
            return work_item
            
        except Exception as e:
            logger.error(f"Failed to update work item {work_item_id}: {e}")
            raise
    
    @mcp_instance.tool
    def delete_work_item(
        project_id: str,
        work_item_id: int,
        destroy: bool = False,
    ) -> bool:
        """
        Delete a work item.
        
        By default, work items are moved to the recycle bin and can be restored.
        Use destroy=True to permanently delete (requires special permissions).
        
        Args:
            project_id: The ID or name of the project.
            work_item_id: The ID of the work item to delete.
            destroy: If true, permanently destroy the work item instead of moving to recycle bin.
            
        Returns:
            bool: True if deletion was successful, False if client unavailable.
            
        Examples:
            # Soft delete (to recycle bin)
            delete_work_item(project_id="MyProject", work_item_id=123)
            
            # Permanent delete
            delete_work_item(project_id="MyProject", work_item_id=123, destroy=True)
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return False
            
        try:
            work_items_client = WorkItemsClient(ado_client_instance)
            
            result = work_items_client.delete_work_item(
                project_id=project_id,
                work_item_id=work_item_id,
                destroy=destroy,
            )
            
            action = "destroyed" if destroy else "deleted"
            logger.info(f"Successfully {action} work item #{work_item_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to delete work item {work_item_id}: {e}")
            raise
    
    @mcp_instance.tool
    def list_work_item_types(
        project_id: str,
    ) -> List[WorkItemType]:
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
    ) -> List[WorkItemField]:
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
            
            logger.info(f"Getting fields for work item type '{work_item_type}' in project: {project_id}")
            
            fields = work_items_client.get_work_item_type_fields(project_id, work_item_type)
            
            logger.info(f"Successfully retrieved {len(fields)} fields for work item type '{work_item_type}'")
            return fields
            
        except Exception as e:
            logger.error(f"Failed to get work item type fields: {e}")
            raise
    
    @mcp_instance.tool
    def list_area_paths(
        project_id: str,
        depth: Optional[int] = None,
    ) -> List[ClassificationNode]:
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
        depth: Optional[int] = None,
    ) -> List[ClassificationNode]:
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
    
    @mcp_instance.tool
    def list_work_items(
        project_id: str,
        wiql_query: Optional[str] = None,
        top: Optional[int] = None,
    ) -> List[WorkItemReference]:
        """
        List work items in a project using WIQL (Work Item Query Language).
        
        This tool queries work items and returns a list of work item references.
        To get full work item details, use the get_work_item tool with the returned IDs.
        
        Args:
            project_id: The ID or name of the project.
            wiql_query: Optional WIQL query string. If not provided, lists all work items
                       with basic fields (ID, Title, Type, State, AssignedTo, CreatedDate).
            top: Maximum number of results to return.
            
        Returns:
            List of work item references with IDs and URLs.
            
        Examples:
            # List all work items in a project
            list_work_items(project_id="MyProject")
            
            # List only bugs
            list_work_items(
                project_id="MyProject", 
                wiql_query="SELECT [System.Id], [System.Title] FROM WorkItems WHERE [System.WorkItemType] = 'Bug'"
            )
            
            # List work items with limit
            list_work_items(project_id="MyProject", top=50)
            
            # List work items assigned to specific user
            list_work_items(
                project_id="MyProject",
                wiql_query="SELECT [System.Id], [System.Title] FROM WorkItems WHERE [System.AssignedTo] = 'user@example.com'"
            )
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return []
            
        try:
            work_items_client = WorkItemsClient(ado_client_instance)
            
            logger.info(f"Listing work items for project: {project_id}")
            
            query_result = work_items_client.query_work_items(
                project_id=project_id,
                wiql_query=wiql_query,
                top=top
            )
            
            # Return the list of WorkItemReference objects directly
            work_items = query_result.workItems
            
            logger.info(f"Successfully listed {len(work_items)} work items")
            return work_items
            
        except Exception as e:
            logger.error(f"Failed to list work items: {e}")
            raise
    
    @mcp_instance.tool
    def query_work_items(
        project_id: str,
        wiql_query: Optional[str] = None,
        top: Optional[int] = None,
        skip: Optional[int] = None,
        simple_filter: Optional[Dict[str, Any]] = None,
        page_size: Optional[int] = None,
        page_number: Optional[int] = None,
    ) -> Optional[WorkItemQueryResult]:
        """
        Query work items using WIQL or simple filtering with pagination support.
        
        This tool provides flexible work item querying with support for both
        custom WIQL queries and simple field-based filtering. Returns complete
        query results including metadata and column information. Supports
        pagination through multiple parameter options.
        
        Args:
            project_id: The ID or name of the project.
            wiql_query: Custom WIQL query string. Takes precedence over simple_filter.
            top: Maximum number of results to return (direct API parameter).
            skip: Number of results to skip (direct API parameter).
            simple_filter: Simple filtering options (alternative to WIQL):
                - work_item_type: Filter by work item type (e.g., "Bug", "Task")
                - state: Filter by state (e.g., "Active", "Closed")
                - assigned_to: Filter by assignee email or display name
                - area_path: Filter by area path
                - iteration_path: Filter by iteration path
                - tags: Filter by tags (semicolon-separated)
                - created_after: Filter by creation date (ISO format)
                - created_before: Filter by creation date (ISO format)
            page_size: Number of items per page (alternative to top/skip).
            page_number: Page number starting from 1 (alternative to top/skip).
            
        Returns:
            WorkItemQueryResult: Complete query results with metadata.
            
        Examples:
            # Custom WIQL query
            query_work_items(
                project_id="MyProject",
                wiql_query="SELECT [System.Id], [System.Title] FROM WorkItems WHERE [System.State] = 'Active'"
            )
            
            # Simple filtering with pagination
            query_work_items(
                project_id="MyProject",
                simple_filter={"work_item_type": "Bug"},
                page_size=20,
                page_number=2
            )
            
            # Direct pagination parameters
            query_work_items(project_id="MyProject", top=50, skip=100)
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None
            
        try:
            import time
            
            # Start performance timing
            start_time = time.time()
            
            work_items_client = WorkItemsClient(ado_client_instance)
            
            # Handle pagination parameter conversion
            if page_size is not None and page_number is not None:
                if top is not None or skip is not None:
                    logger.warning("Both page_size/page_number and top/skip provided. Using page_size/page_number.")
                top = page_size
                skip = (page_number - 1) * page_size
                logger.info(f"Pagination: page {page_number}, size {page_size} -> top={top}, skip={skip}")
            
            # Build WIQL query from simple filter if no custom query provided
            query_type = "custom_wiql" if wiql_query else "simple_filter"
            if wiql_query is None and simple_filter:
                wiql_query = _build_wiql_from_filter(simple_filter)
                logger.info(f"Generated WIQL from simple filter: {len(simple_filter)} conditions")
            
            # Log query complexity metrics
            query_complexity = _analyze_query_complexity(wiql_query, simple_filter, top, skip)
            logger.info(f"Query complexity metrics: {query_complexity}")
            
            logger.info(f"Querying work items for project: {project_id} (type: {query_type})")
            
            # Execute query with timing
            api_start_time = time.time()
            query_result = work_items_client.query_work_items(
                project_id=project_id,
                wiql_query=wiql_query,
                top=top,
                skip=skip
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
                "throughput_items_per_sec": round(result_count / total_duration, 2) if total_duration > 0 else 0,
                **query_complexity
            }
            
            logger.info(f"Query performance: {performance_metrics}")
            
            # Log warnings for slow queries
            if total_duration > 2.0:  # 2 second threshold
                logger.warning(f"Slow query detected: {total_duration:.2f}s for {result_count} items")
            
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
        work_item_type: Optional[str] = None,
        state: Optional[str] = None,
        assigned_to: Optional[str] = None,
        area_path: Optional[str] = None,
        order_by: str = "System.Id",
    ) -> Optional[Dict[str, Any]]:
        """
        Get a paginated list of work items with metadata about pagination.
        
        This tool provides a simplified interface for getting paginated work items
        with common filtering options. Returns both the work items and pagination
        metadata to help with building pagination UIs.
        
        Args:
            project_id: The ID or name of the project.
            page_number: Page number starting from 1 (default: 1).
            page_size: Number of items per page (default: 50, max: 200).
            work_item_type: Filter by work item type (e.g., "Bug", "Task").
            state: Filter by state (e.g., "Active", "Closed").
            assigned_to: Filter by assignee email or display name.
            area_path: Filter by area path.
            order_by: Field to order by (default: "System.Id").
            
        Returns:
            Dictionary containing:
            - work_items: List of work item references
            - pagination: Metadata about pagination (page, size, has_more, etc.)
            
        Examples:
            # Get first page of all work items
            get_work_items_page(project_id="MyProject")
            
            # Get second page of bugs
            get_work_items_page(
                project_id="MyProject",
                page_number=2,
                page_size=25,
                work_item_type="Bug"
            )
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
            
            # Use query_work_items to get the results
            work_items_client = WorkItemsClient(ado_client_instance)
            
            # Build WIQL query from filter
            if simple_filter:
                wiql_query = _build_wiql_from_filter(simple_filter)
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
            
            import time
            start_time = time.time()
            
            # Log pagination-specific metrics
            pagination_metrics = {
                "page_number": page_number,
                "page_size": page_size,
                "skip_items": skip,
                "filter_count": len(simple_filter),
                "has_ordering": order_by != "System.Id"
            }
            
            logger.info(f"Getting page {page_number} of work items (size: {page_size}) - {pagination_metrics}")
            
            query_result = work_items_client.query_work_items(
                project_id=project_id,
                wiql_query=wiql_query,
                top=top,
                skip=skip
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
                "pagination_efficiency": round(len(work_items) / page_size * 100, 1) if page_size > 0 else 0
            }
            
            result = {
                "work_items": work_items,
                "pagination": pagination_info,
                "query_metadata": {
                    "query_type": query_result.queryType,
                    "columns": query_result.columns,
                },
                "performance_metrics": final_pagination_metrics
            }
            
            logger.info(f"Pagination performance: {final_pagination_metrics}")
            logger.info(f"Successfully retrieved page {page_number} with {len(work_items)} items (has_more: {has_more})")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get work items page: {e}")
            raise

    @mcp_instance.tool
    def get_my_work_items(
        project_id: str,
        assigned_to: str,
        state: Optional[str] = None,
        work_item_type: Optional[str] = None,
        page_size: int = 50,
        page_number: int = 1,
    ) -> Optional[Dict[str, Any]]:
        """
        Get work items assigned to a specific user.
        
        This is a convenience tool that provides a simple interface for getting
        work items assigned to a specific user with common filtering options.
        
        Args:
            project_id: The ID or name of the project.
            assigned_to: Email address or display name of the assignee.
            state: Optional filter by state (e.g., "Active", "New", "Closed").
            work_item_type: Optional filter by work item type (e.g., "Bug", "Task").
            page_size: Number of items per page (default: 50, max: 200).
            page_number: Page number starting from 1 (default: 1).
            
        Returns:
            Dictionary containing:
            - work_items: List of work item references
            - pagination: Metadata about pagination
            - assignment_info: Information about the assignee filter
            
        Examples:
            # Get all work items assigned to me
            get_my_work_items(
                project_id="MyProject",
                assigned_to="user@example.com"
            )
            
            # Get only active bugs assigned to me
            get_my_work_items(
                project_id="MyProject",
                assigned_to="user@example.com",
                state="Active",
                work_item_type="Bug"
            )
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
            
            # Build filter for consistent filtering
            simple_filter = {"assigned_to": assigned_to}
            if state:
                simple_filter["state"] = state
            if work_item_type:
                simple_filter["work_item_type"] = work_item_type
            
            # Use the work items client directly to avoid circular calls
            work_items_client = WorkItemsClient(ado_client_instance)
            
            # Build WIQL query from filter
            wiql_query = _build_wiql_from_filter(simple_filter)
            
            # Calculate pagination
            skip = (page_number - 1) * page_size
            top = page_size
            
            # Execute query
            query_result = work_items_client.query_work_items(
                project_id=project_id,
                wiql_query=wiql_query,
                top=top,
                skip=skip
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
                }
            }
            
            if result:
                # Add assignment info to the result
                result["assignment_info"] = {
                    "assigned_to": assigned_to,
                    "state_filter": state,
                    "type_filter": work_item_type
                }
                
                logger.info(f"Successfully retrieved {len(result['work_items'])} work items for '{assigned_to}'")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get work items for '{assigned_to}': {e}")
            raise

    @mcp_instance.tool
    def get_recent_work_items(
        project_id: str,
        days: int = 7,
        work_item_type: Optional[str] = None,
        state: Optional[str] = None,
        page_size: int = 50,
        page_number: int = 1,
    ) -> Optional[Dict[str, Any]]:
        """
        Get work items created or modified recently.
        
        This is a convenience tool that provides a simple interface for getting
        recently created or modified work items with common filtering options.
        
        Args:
            project_id: The ID or name of the project.
            days: Number of days back to search (default: 7).
            work_item_type: Optional filter by work item type (e.g., "Bug", "Task").
            state: Optional filter by state (e.g., "Active", "New", "Closed").
            page_size: Number of items per page (default: 50, max: 200).
            page_number: Page number starting from 1 (default: 1).
            
        Returns:
            Dictionary containing:
            - work_items: List of work item references
            - pagination: Metadata about pagination
            - time_filter: Information about the time range used
            
        Examples:
            # Get all work items from the last 7 days
            get_recent_work_items(project_id="MyProject")
            
            # Get bugs created in the last 3 days
            get_recent_work_items(
                project_id="MyProject",
                days=3,
                work_item_type="Bug"
            )
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None
            
        try:
            from datetime import datetime, timedelta
            
            # Calculate the date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Format dates for WIQL (ISO format)
            start_date_str = start_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            
            logger.info(f"Getting work items from the last {days} days in project: {project_id}")
            
            # Build filter with date range
            simple_filter = {"created_after": start_date_str}
            if work_item_type:
                simple_filter["work_item_type"] = work_item_type
            if state:
                simple_filter["state"] = state
            
            # Use query_work_items for date filtering
            work_items_client = WorkItemsClient(ado_client_instance)
            
            # Build WIQL query from filter
            wiql_query = _build_wiql_from_filter(simple_filter)
            
            # Calculate skip value for pagination
            skip = (page_number - 1) * page_size
            top = page_size + 1  # Get one extra to check if there are more
            
            query_result = work_items_client.query_work_items(
                project_id=project_id,
                wiql_query=wiql_query,
                top=top,
                skip=skip
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
                    "end_date": end_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    "type_filter": work_item_type,
                    "state_filter": state
                },
                "query_metadata": {
                    "query_type": query_result.queryType,
                    "columns": query_result.columns,
                }
            }
            
            logger.info(f"Successfully retrieved {len(work_items)} recent work items (last {days} days)")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get recent work items: {e}")
            raise

    @mcp_instance.tool
    def get_work_items_batch(
        project_id: str,
        work_item_ids: List[int],
        fields: Optional[List[str]] = None,
        expand_relations: bool = False,
        as_of: Optional[str] = None,
        error_policy: str = "omit"
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
                raise ValueError("Cannot retrieve more than 200 work items in a single batch request")
            
            # Start performance timing
            start_time = time.time()
            
            work_items_client = WorkItemsClient(ado_client_instance)
            
            # Log batch operation metrics
            batch_metrics = {
                "item_count": len(work_item_ids),
                "has_field_filter": fields is not None,
                "field_count": len(fields) if fields else 0,
                "expand_relations": expand_relations,
                "error_policy": error_policy,
                "has_historical_query": as_of is not None
            }
            
            logger.info(f"Getting batch of {len(work_item_ids)} work items from project: {project_id} - {batch_metrics}")
            
            # Execute batch retrieval with timing
            api_start_time = time.time()
            work_items = work_items_client.get_work_items_batch(
                project_id=project_id,
                work_item_ids=work_item_ids,
                fields=fields,
                expand_relations=expand_relations,
                as_of=as_of,
                error_policy=error_policy
            )
            api_duration = time.time() - api_start_time
            
            # Calculate performance metrics
            total_duration = time.time() - start_time
            result_count = len(work_items)
            success_rate = (result_count / len(work_item_ids)) * 100 if work_item_ids else 100
            
            # Log comprehensive performance metrics
            performance_metrics = {
                "total_duration_ms": round(total_duration * 1000, 2),
                "api_duration_ms": round(api_duration * 1000, 2),
                "requested_count": len(work_item_ids),
                "returned_count": result_count,
                "success_rate_percent": round(success_rate, 1),
                "throughput_items_per_sec": round(result_count / total_duration, 2) if total_duration > 0 else 0,
                "avg_ms_per_item": round((total_duration * 1000) / result_count, 2) if result_count > 0 else 0,
                **batch_metrics
            }
            
            logger.info(f"Batch retrieval performance: {performance_metrics}")
            
            # Log warnings for inefficient operations
            if success_rate < 80:
                logger.warning(f"Low success rate: {success_rate:.1f}% - many work items may not exist")
            if total_duration > 5.0:  # 5 second threshold for batch operations
                logger.warning(f"Slow batch retrieval: {total_duration:.2f}s for {result_count} items")
            
            logger.info(f"Successfully retrieved {result_count} out of {len(work_item_ids)} requested work items")
            return work_items
            
        except Exception as e:
            logger.error(f"Failed to get work items batch: {e}")
            raise


def _build_wiql_from_filter(simple_filter: Dict[str, Any]) -> str:
    """
    Build a WIQL query from simple filter parameters.
    
    Args:
        simple_filter: Dictionary of filter criteria
        
    Returns:
        WIQL query string
    """
    # Base SELECT clause with common fields
    select_clause = (
        "SELECT [System.Id], [System.Title], [System.WorkItemType], "
        "[System.State], [System.AssignedTo], [System.CreatedDate], "
        "[System.AreaPath], [System.IterationPath], [System.Tags] "
        "FROM WorkItems"
    )
    
    conditions = []
    
    # Add conditions based on filter parameters
    if "work_item_type" in simple_filter:
        work_item_type = simple_filter["work_item_type"]
        conditions.append(f"[System.WorkItemType] = '{work_item_type}'")
    
    if "state" in simple_filter:
        state = simple_filter["state"]
        conditions.append(f"[System.State] = '{state}'")
    
    if "assigned_to" in simple_filter:
        assigned_to = simple_filter["assigned_to"]
        conditions.append(f"[System.AssignedTo] = '{assigned_to}'")
    
    if "area_path" in simple_filter:
        area_path = simple_filter["area_path"]
        conditions.append(f"[System.AreaPath] UNDER '{area_path}'")
    
    if "iteration_path" in simple_filter:
        iteration_path = simple_filter["iteration_path"]
        conditions.append(f"[System.IterationPath] UNDER '{iteration_path}'")
    
    if "tags" in simple_filter:
        tags = simple_filter["tags"]
        # Handle both single tag and semicolon-separated tags
        if ";" in tags:
            tag_conditions = []
            for tag in tags.split(";"):
                tag = tag.strip()
                if tag:
                    tag_conditions.append(f"[System.Tags] CONTAINS '{tag}'")
            if tag_conditions:
                conditions.append(f"({' OR '.join(tag_conditions)})")
        else:
            conditions.append(f"[System.Tags] CONTAINS '{tags.strip()}'")
    
    if "created_after" in simple_filter:
        created_after = simple_filter["created_after"]
        conditions.append(f"[System.CreatedDate] >= '{created_after}'")
    
    if "created_before" in simple_filter:
        created_before = simple_filter["created_before"]
        conditions.append(f"[System.CreatedDate] <= '{created_before}'")
    
    # Build final query
    if conditions:
        where_clause = " WHERE " + " AND ".join(conditions)
        query = select_clause + where_clause
    else:
        query = select_clause
    
    # Add ordering
    query += " ORDER BY [System.Id]"
    
    return query


def _analyze_query_complexity(wiql_query: Optional[str], simple_filter: Optional[Dict[str, Any]], top: Optional[int], skip: Optional[int]) -> Dict[str, Any]:
    """
    Analyze query complexity for performance metrics.
    
    Args:
        wiql_query: The WIQL query string
        simple_filter: Simple filter dictionary  
        top: Maximum results to return
        skip: Number of results to skip
        
    Returns:
        Dictionary with complexity metrics
    """
    complexity = {
        "filter_condition_count": 0,
        "has_text_search": False,
        "has_date_filter": False,
        "has_complex_joins": False,
        "estimated_complexity": "low"
    }
    
    # Analyze simple filter complexity
    if simple_filter:
        complexity["filter_condition_count"] = len(simple_filter)
        
        # Check for date filters
        if any(key in simple_filter for key in ["created_after", "created_before"]):
            complexity["has_date_filter"] = True
            
        # Check for text searches (tags, assigned_to)
        if any(key in simple_filter for key in ["tags", "assigned_to"]):
            complexity["has_text_search"] = True
    
    # Analyze WIQL query complexity
    if wiql_query:
        query_upper = wiql_query.upper()
        
        # Count WHERE conditions
        where_count = query_upper.count(" AND ") + query_upper.count(" OR ") + (1 if " WHERE " in query_upper else 0)
        complexity["filter_condition_count"] = max(complexity["filter_condition_count"], where_count)
        
        # Check for complex operations
        complex_operations = ["JOIN", "UNION", "CONTAINS", "LIKE", "UNDER", "IN"]
        for op in complex_operations:
            if op in query_upper:
                complexity["has_complex_joins"] = True
                break
                
        # Check for date operations
        if any(date_op in query_upper for date_op in ["CREATEDDATE", "CHANGEDDATE", ">", "<", ">=", "<="]):
            complexity["has_date_filter"] = True
            
        # Check for text search operations
        if any(text_op in query_upper for text_op in ["CONTAINS", "LIKE", "TAGS", "ASSIGNEDTO"]):
            complexity["has_text_search"] = True
    
    # Determine overall complexity
    complexity_score = 0
    if complexity["filter_condition_count"] > 3:
        complexity_score += 2
    elif complexity["filter_condition_count"] > 1:
        complexity_score += 1
        
    if complexity["has_text_search"]:
        complexity_score += 1
    if complexity["has_date_filter"]:
        complexity_score += 1  
    if complexity["has_complex_joins"]:
        complexity_score += 2
        
    # Large pagination can be expensive
    if skip and skip > 1000:
        complexity_score += 1
    if top and top > 500:
        complexity_score += 1
        
    if complexity_score >= 4:
        complexity["estimated_complexity"] = "high"
    elif complexity_score >= 2:
        complexity["estimated_complexity"] = "medium"
    else:
        complexity["estimated_complexity"] = "low"
        
    return complexity