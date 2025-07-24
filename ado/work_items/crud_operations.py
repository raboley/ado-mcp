"""MCP tool definitions for Azure DevOps Work Items CRUD operations."""

import logging
from typing import Any

from ado.work_items.client import WorkItemsClient
from ado.work_items.models import WorkItem
from ado.work_items.validation import WorkItemValidator

logger = logging.getLogger(__name__)


def register_crud_tools(mcp_instance, client_container):
    """
    Register CRUD work item tools with the FastMCP instance.

    Args:
        mcp_instance: The FastMCP instance to register tools with.
        client_container: Dictionary holding the AdoClient instance.
    """

    @mcp_instance.tool
    def create_work_item(
        project_id: str,
        work_item_type: str,
        title: str,
        description: str | None = None,
        area_path: str | None = None,
        iteration_path: str | None = None,
        assigned_to: str | None = None,
        state: str | None = None,
        priority: int | None = None,
        tags: str | None = None,
        additional_fields: dict[str, Any] | None = None,
        validate_only: bool = False,
        bypass_rules: bool = False,
        suppress_notifications: bool = False,
    ) -> WorkItem | None:
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
            if not bypass_rules and not WorkItemValidator.validate_work_item_type(
                project_id, work_item_type
            ):
                logger.warning(
                    f"Work item type '{work_item_type}' may not be valid for project '{project_id}'"
                )

            fields = {
                "System.Title": title,
            }

            if description:
                fields["System.Description"] = description
            if area_path:
                area_path = WorkItemValidator.sanitize_path(area_path)
                if not bypass_rules and not WorkItemValidator.validate_area_path(
                    project_id, area_path
                ):
                    logger.warning(
                        f"Area path '{area_path}' may not be valid for project '{project_id}'"
                    )
                    suggestions = WorkItemValidator.suggest_valid_paths(
                        project_id, area_path, "area"
                    )
                    if suggestions:
                        logger.info(f"Suggested area paths: {', '.join(suggestions[:3])}")
                fields["System.AreaPath"] = area_path
            if iteration_path:
                iteration_path = WorkItemValidator.sanitize_path(iteration_path)
                if not bypass_rules and not WorkItemValidator.validate_iteration_path(
                    project_id, iteration_path
                ):
                    logger.warning(
                        f"Iteration path '{iteration_path}' may not be valid for project '{project_id}'"
                    )
                    suggestions = WorkItemValidator.suggest_valid_paths(
                        project_id, iteration_path, "iteration"
                    )
                    if suggestions:
                        logger.info(f"Suggested iteration paths: {', '.join(suggestions[:3])}")
                fields["System.IterationPath"] = iteration_path
            if assigned_to:
                fields["System.AssignedTo"] = assigned_to
            if state:
                fields["System.State"] = state
            if priority:
                if not bypass_rules and not WorkItemValidator.validate_field_value(
                    "System.Priority", priority, "Integer"
                ):
                    raise ValueError(
                        f"Invalid priority value: {priority}. Must be an integer between 1 and 4."
                    )
                fields["System.Priority"] = priority
            if tags:
                fields["System.Tags"] = tags

            if additional_fields:
                if not bypass_rules:
                    for field_name, field_value in additional_fields.items():
                        if not WorkItemValidator.validate_field_value(field_name, field_value):
                            logger.warning(
                                f"Field '{field_name}' value may not be valid: {field_value}"
                            )
                fields.update(additional_fields)

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
                logger.info(f"Created {work_item_type} work item #{work_item.id}: {title}")

            return work_item

        except Exception as e:
            logger.error(f"Failed to create work item: {e}")
            raise

    @mcp_instance.tool
    def get_work_item(
        project_id: str,
        work_item_id: int,
        fields: list[str] | None = None,
        expand_relations: bool = False,
        as_of: str | None = None,
    ) -> WorkItem | None:
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
        title: str | None = None,
        description: str | None = None,
        state: str | None = None,
        assigned_to: str | None = None,
        priority: int | None = None,
        area_path: str | None = None,
        iteration_path: str | None = None,
        tags: str | None = None,
        fields_to_update: dict[str, Any] | None = None,
        fields_to_remove: list[str] | None = None,
        validate_only: bool = False,
        bypass_rules: bool = False,
        suppress_notifications: bool = False,
    ) -> WorkItem | None:
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
            from ado.work_items.models import JsonPatchOperation

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
                if not bypass_rules and not WorkItemValidator.validate_field_value(
                    "System.Priority", priority, "Integer"
                ):
                    raise ValueError(
                        f"Invalid priority value: {priority}. Must be an integer between 1 and 4."
                    )
                updates["System.Priority"] = priority
            if area_path is not None:
                area_path = WorkItemValidator.sanitize_path(area_path)
                if not bypass_rules and not WorkItemValidator.validate_area_path(
                    project_id, area_path
                ):
                    logger.warning(
                        f"Area path '{area_path}' may not be valid for project '{project_id}'"
                    )
                    suggestions = WorkItemValidator.suggest_valid_paths(
                        project_id, area_path, "area"
                    )
                    if suggestions:
                        logger.info(f"Suggested area paths: {', '.join(suggestions[:3])}")
                updates["System.AreaPath"] = area_path
            if iteration_path is not None:
                iteration_path = WorkItemValidator.sanitize_path(iteration_path)
                if not bypass_rules and not WorkItemValidator.validate_iteration_path(
                    project_id, iteration_path
                ):
                    logger.warning(
                        f"Iteration path '{iteration_path}' may not be valid for project '{project_id}'"
                    )
                    suggestions = WorkItemValidator.suggest_valid_paths(
                        project_id, iteration_path, "iteration"
                    )
                    if suggestions:
                        logger.info(f"Suggested iteration paths: {', '.join(suggestions[:3])}")
                updates["System.IterationPath"] = iteration_path
            if tags is not None:
                updates["System.Tags"] = tags

            if fields_to_update:
                if not bypass_rules:
                    for field_name, field_value in fields_to_update.items():
                        if not WorkItemValidator.validate_field_value(field_name, field_value):
                            logger.warning(
                                f"Field '{field_name}' value may not be valid: {field_value}"
                            )
                updates.update(fields_to_update)

            for field_path, value in updates.items():
                operations.append(
                    JsonPatchOperation(op="replace", path=f"/fields/{field_path}", value=value)
                )

            if fields_to_remove:
                for field_path in fields_to_remove:
                    operations.append(JsonPatchOperation(op="remove", path=f"/fields/{field_path}"))

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
