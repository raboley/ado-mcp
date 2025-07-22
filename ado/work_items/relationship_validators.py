"""Relationship validation helpers for work item operations."""

import logging
from typing import List, Tuple, Optional

from .models import WorkItemRelationType

logger = logging.getLogger(__name__)


class RelationshipValidator:
    """Validator for work item relationship operations."""

    @staticmethod
    def validate_relationship_constraints(
        source_work_item_type: str, target_work_item_type: str, relationship_type: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate constraints for work item relationships.

        Args:
            source_work_item_type: The source work item type
            target_work_item_type: The target work item type
            relationship_type: The relationship type

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Validate relationship type using the actual string constants
            if not RelationshipValidator.validate_relationship_type(relationship_type):
                return False, f"Unknown relationship type: {relationship_type}"

            # Define work item hierarchy levels (higher number = higher in hierarchy)
            hierarchy_levels = {
                "Epic": 3,
                "Feature": 2,
                "User Story": 1,
                "Task": 0,
                "Bug": 0,
                "Test Case": 0,
                "Issue": 0,
            }

            source_level = hierarchy_levels.get(source_work_item_type, 0)
            target_level = hierarchy_levels.get(target_work_item_type, 0)

            # Validate hierarchy relationships
            if relationship_type == "System.LinkTypes.Hierarchy-Forward":
                # Parent -> Child: source should be higher level than target
                if source_level <= target_level:
                    return False, (
                        f"Invalid hierarchy: {source_work_item_type} cannot be parent of "
                        f"{target_work_item_type}. Parent must be at higher hierarchy level."
                    )

                # Epic can only have Feature or User Story children
                if source_work_item_type == "Epic" and target_work_item_type not in [
                    "Feature",
                    "User Story",
                ]:
                    return (
                        False,
                        f"Epic can only have Feature or User Story children, not {target_work_item_type}",
                    )

                # Feature can only have User Story children
                if source_work_item_type == "Feature" and target_work_item_type != "User Story":
                    return (
                        False,
                        f"Feature can only have User Story children, not {target_work_item_type}",
                    )

                # User Story can only have Task children
                if source_work_item_type == "User Story" and target_work_item_type != "Task":
                    return (
                        False,
                        f"User Story can only have Task children, not {target_work_item_type}",
                    )

            elif relationship_type == "System.LinkTypes.Hierarchy-Reverse":
                # Child -> Parent: target should be higher level than source
                if target_level <= source_level:
                    return False, (
                        f"Invalid hierarchy: {target_work_item_type} cannot be parent of "
                        f"{source_work_item_type}. Parent must be at higher hierarchy level."
                    )

            # Validate dependency relationships
            elif relationship_type in [
                "System.LinkTypes.Dependency-Forward",
                "System.LinkTypes.Dependency-Reverse",
            ]:
                # Dependencies are typically between work items at the same level
                valid_dependency_types = ["Task", "Bug", "User Story", "Feature"]
                if source_work_item_type not in valid_dependency_types:
                    return (
                        False,
                        f"Dependencies not typically supported for {source_work_item_type}",
                    )
                if target_work_item_type not in valid_dependency_types:
                    return (
                        False,
                        f"Dependencies not typically supported for {target_work_item_type}",
                    )

            # Validate blocking relationships
            elif relationship_type in [
                "Microsoft.VSTS.Common.Affects-Forward",
                "Microsoft.VSTS.Common.Affects-Reverse",
            ]:
                # Any work item can block or be blocked by any other work item
                pass

            # Validate duplicate relationships
            elif relationship_type in [
                "System.LinkTypes.Duplicate-Forward",
                "System.LinkTypes.Duplicate-Reverse",
            ]:
                # Duplicates should be of the same work item type
                if source_work_item_type != target_work_item_type:
                    return False, (
                        f"Duplicate relationships should be between same work item types. "
                        f"Got {source_work_item_type} and {target_work_item_type}"
                    )

            # Validate test relationships
            elif relationship_type in [
                "Microsoft.VSTS.Common.TestedBy-Forward",
                "Microsoft.VSTS.Common.TestedBy-Reverse",
            ]:
                if relationship_type == "Microsoft.VSTS.Common.TestedBy-Forward":
                    # Test Case tests other work items
                    if source_work_item_type != "Test Case":
                        return (
                            False,
                            f"Only Test Case can test other work items, not {source_work_item_type}",
                        )
                else:
                    # Other work items tested by Test Case
                    if target_work_item_type != "Test Case":
                        return (
                            False,
                            f"Work items can only be tested by Test Case, not {target_work_item_type}",
                        )

            return True, None

        except Exception as e:
            logger.warning(f"Error validating relationship constraints: {e}")
            # Reason: Be permissive if validation fails to avoid blocking valid operations
            return True, None

    @staticmethod
    def validate_relationship_type(relationship_type: str) -> bool:
        """
        Validate that a relationship type is supported.

        Args:
            relationship_type: The relationship type to validate

        Returns:
            True if the relationship type is valid
        """
        valid_types = [rel.value for rel in WorkItemRelationType]
        valid_types.extend(
            [
                "System.LinkTypes.Hierarchy-Forward",
                "System.LinkTypes.Hierarchy-Reverse",
                "System.LinkTypes.Related",
                "System.LinkTypes.Dependency-Forward",
                "System.LinkTypes.Dependency-Reverse",
                "System.LinkTypes.Duplicate-Forward",
                "System.LinkTypes.Duplicate-Reverse",
                "Microsoft.VSTS.Common.Affects-Forward",
                "Microsoft.VSTS.Common.Affects-Reverse",
                "Microsoft.VSTS.Common.TestedBy-Forward",
                "Microsoft.VSTS.Common.TestedBy-Reverse",
            ]
        )

        return relationship_type in valid_types

    @staticmethod
    def get_valid_relationship_types() -> List[str]:
        """
        Get list of all valid relationship types.

        Returns:
            List of valid relationship type strings
        """
        return [
            "System.LinkTypes.Hierarchy-Forward",
            "System.LinkTypes.Hierarchy-Reverse",
            "System.LinkTypes.Related",
            "System.LinkTypes.Dependency-Forward",
            "System.LinkTypes.Dependency-Reverse",
            "System.LinkTypes.Duplicate-Forward",
            "System.LinkTypes.Duplicate-Reverse",
            "Microsoft.VSTS.Common.Affects-Forward",
            "Microsoft.VSTS.Common.Affects-Reverse",
            "Microsoft.VSTS.Common.TestedBy-Forward",
            "Microsoft.VSTS.Common.TestedBy-Reverse",
        ]

    @staticmethod
    def suggest_relationship_types(
        source_work_item_type: str, target_work_item_type: str
    ) -> List[Tuple[str, str]]:
        """
        Suggest appropriate relationship types for two work item types.

        Args:
            source_work_item_type: The source work item type
            target_work_item_type: The target work item type

        Returns:
            List of (relationship_type, description) tuples
        """
        suggestions = []

        # Define work item hierarchy levels
        hierarchy_levels = {
            "Epic": 3,
            "Feature": 2,
            "User Story": 1,
            "Task": 0,
            "Bug": 0,
            "Test Case": 0,
            "Issue": 0,
        }

        source_level = hierarchy_levels.get(source_work_item_type, 0)
        target_level = hierarchy_levels.get(target_work_item_type, 0)

        # Suggest hierarchy relationships
        if source_level > target_level:
            suggestions.append(
                (
                    "System.LinkTypes.Hierarchy-Forward",
                    f"{source_work_item_type} contains {target_work_item_type}",
                )
            )
        elif target_level > source_level:
            suggestions.append(
                (
                    "System.LinkTypes.Hierarchy-Reverse",
                    f"{source_work_item_type} is contained by {target_work_item_type}",
                )
            )

        # Always suggest related
        suggestions.append(("System.LinkTypes.Related", "General relationship between work items"))

        # Suggest dependencies for appropriate types
        valid_dependency_types = ["Task", "Bug", "User Story", "Feature"]
        if (
            source_work_item_type in valid_dependency_types
            and target_work_item_type in valid_dependency_types
        ):
            suggestions.append(
                (
                    "System.LinkTypes.Dependency-Forward",
                    f"{source_work_item_type} blocks {target_work_item_type}",
                )
            )
            suggestions.append(
                (
                    "System.LinkTypes.Dependency-Reverse",
                    f"{source_work_item_type} depends on {target_work_item_type}",
                )
            )

        # Suggest duplicates for same type
        if source_work_item_type == target_work_item_type:
            suggestions.append(
                (
                    "System.LinkTypes.Duplicate-Forward",
                    f"{source_work_item_type} is duplicate of {target_work_item_type}",
                )
            )

        # Suggest test relationships
        if source_work_item_type == "Test Case":
            suggestions.append(
                (
                    "Microsoft.VSTS.Common.TestedBy-Forward",
                    f"Test Case tests {target_work_item_type}",
                )
            )
        elif target_work_item_type == "Test Case":
            suggestions.append(
                (
                    "Microsoft.VSTS.Common.TestedBy-Reverse",
                    f"{source_work_item_type} is tested by Test Case",
                )
            )

        return suggestions