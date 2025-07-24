"""Field validation functionality for work items."""

import logging
import re
from typing import Any

from ado.cache import ado_cache

logger = logging.getLogger(__name__)


class FieldValidator:
    """Validator for work item field operations."""

    @staticmethod
    def validate_work_item_type(project_id: str, work_item_type: str) -> bool:
        """
        Validate that a work item type exists in the project.

        Args:
            project_id: The project ID to validate against
            work_item_type: The work item type name (e.g., "Bug", "Task")

        Returns:
            True if the work item type is valid
        """
        if not work_item_type:
            return False

        cached_types = ado_cache.get_work_item_types(project_id)
        if cached_types:
            for wit in cached_types:
                if wit.name == work_item_type:
                    return True
            return False

        # Reason: Fallback to common types when cache is empty to avoid API calls
        common_types = ["Bug", "Task", "User Story", "Feature", "Epic", "Test Case", "Issue"]
        return work_item_type in common_types

    @staticmethod
    def validate_field_value(
        field_name: str, field_value: Any, field_type: str | None = None
    ) -> bool:
        """
        Validate a field value based on its type.

        Args:
            field_name: The field reference name
            field_value: The value to validate
            field_type: The field type (if known)

        Returns:
            True if the value is valid for the field type
        """
        if field_value is None:
            return True  # Reason: Azure DevOps allows null for most optional fields

        if field_name == "System.Priority":
            if isinstance(field_value, int):
                return 1 <= field_value <= 4
            return False

        if field_name == "System.Tags":
            return isinstance(field_value, str)

        if field_name in ["System.AssignedTo", "System.CreatedBy", "System.ChangedBy"]:
            return isinstance(field_value, str) and len(field_value) > 0

        if field_type:
            if field_type in ["String", "PlainText", "HTML"]:
                return isinstance(field_value, str)
            elif field_type == "Integer":
                return isinstance(field_value, int)
            elif field_type == "Double":
                return isinstance(field_value, int | float)
            elif field_type == "DateTime":
                if isinstance(field_value, str):
                    try:
                        return bool(re.match(r"^\d{4}-\d{2}-\d{2}", field_value))
                    except:
                        return False
                return False
            elif field_type == "Boolean":
                return isinstance(field_value, bool)

        # Reason: Be permissive for unknown field types to avoid breaking custom fields
        return True
