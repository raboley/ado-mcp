"""Validation helpers for work item operations."""

import logging
from typing import Any

from .field_validators import FieldValidator
from .path_validators import PathValidator
from .relationship_validators import RelationshipValidator
from .state_validators import StateValidator

logger = logging.getLogger(__name__)


class WorkItemValidator:
    """Validator for work item operations."""

    @staticmethod
    def validate_area_path(project_id: str, area_path: str) -> bool:
        """
        Validate that an area path exists in the project.

        Args:
            project_id: The project ID to validate against
            area_path: The area path to validate (e.g., "Project\\Team\\Component")

        Returns:
            True if the area path is valid, False otherwise
        """
        return PathValidator.validate_area_path(project_id, area_path)

    @staticmethod
    def validate_iteration_path(project_id: str, iteration_path: str) -> bool:
        """
        Validate that an iteration path exists in the project.

        Args:
            project_id: The project ID to validate against
            iteration_path: The iteration path to validate (e.g., "Project\\Sprint 1")

        Returns:
            True if the iteration path is valid, False otherwise
        """
        return PathValidator.validate_iteration_path(project_id, iteration_path)

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
        return FieldValidator.validate_work_item_type(project_id, work_item_type)

    @staticmethod
    def validate_state_transition(
        project_id: str, work_item_type: str, from_state: str, to_state: str
    ) -> bool:
        """
        Validate that a state transition is allowed for a work item type.

        This method uses the detailed work item type information including
        state transition rules to validate whether a state change is allowed.

        Args:
            project_id: The project ID
            work_item_type: The work item type name
            from_state: The current state
            to_state: The target state

        Returns:
            True if the transition is allowed, False otherwise
        """
        return StateValidator.validate_state_transition(
            project_id, work_item_type, from_state, to_state
        )

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
        return FieldValidator.validate_field_value(field_name, field_value, field_type)

    @staticmethod
    def sanitize_path(path: str) -> str:
        """
        Sanitize a path by removing invalid characters and normalizing.

        Args:
            path: The path to sanitize

        Returns:
            The sanitized path
        """
        return PathValidator.sanitize_path(path)

    @staticmethod
    def suggest_valid_paths(
        project_id: str, partial_path: str, path_type: str = "area"
    ) -> list[str]:
        """
        Suggest valid paths based on a partial path.

        Args:
            project_id: The project ID
            partial_path: The partial path to match
            path_type: Either "area" or "iteration"

        Returns:
            List of suggested valid paths
        """
        return PathValidator.suggest_valid_paths(project_id, partial_path, path_type)

    @staticmethod
    def validate_relationship_constraints(
        source_work_item_type: str, target_work_item_type: str, relationship_type: str
    ) -> tuple[bool, str | None]:
        """
        Validate constraints for work item relationships.

        Args:
            source_work_item_type: The source work item type
            target_work_item_type: The target work item type
            relationship_type: The relationship type

        Returns:
            Tuple of (is_valid, error_message)
        """
        return RelationshipValidator.validate_relationship_constraints(
            source_work_item_type, target_work_item_type, relationship_type
        )

    @staticmethod
    def validate_relationship_type(relationship_type: str) -> bool:
        """
        Validate that a relationship type is supported.

        Args:
            relationship_type: The relationship type to validate

        Returns:
            True if the relationship type is valid
        """
        return RelationshipValidator.validate_relationship_type(relationship_type)

    @staticmethod
    def get_valid_relationship_types() -> list[str]:
        """
        Get list of all valid relationship types.

        Returns:
            List of valid relationship type strings
        """
        return RelationshipValidator.get_valid_relationship_types()

    @staticmethod
    def suggest_relationship_types(
        source_work_item_type: str, target_work_item_type: str
    ) -> list[tuple[str, str]]:
        """
        Suggest appropriate relationship types for two work item types.

        Args:
            source_work_item_type: The source work item type
            target_work_item_type: The target work item type

        Returns:
            List of (relationship_type, description) tuples
        """
        return RelationshipValidator.suggest_relationship_types(
            source_work_item_type, target_work_item_type
        )
