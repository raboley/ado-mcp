"""Tests for work item relationship validation."""

from ado.work_items.validation import WorkItemValidator


class TestRelationshipTypeValidation:
    """Test relationship type validation."""

    def test_validate_relationship_type_valid_types(self):
        """Test validation of valid relationship types."""
        valid_types = [
            "System.LinkTypes.Hierarchy-Forward",
            "System.LinkTypes.Hierarchy-Reverse",
            "System.LinkTypes.Related",
            "System.LinkTypes.Dependency-Forward",
            "System.LinkTypes.Dependency-Reverse",
            "Microsoft.VSTS.Common.Affects-Forward",
            "Microsoft.VSTS.Common.TestedBy-Forward",
        ]

        for rel_type in valid_types:
            assert WorkItemValidator.validate_relationship_type(rel_type), (
                f"{rel_type} should be valid"
            )

    def test_validate_relationship_type_invalid_types(self):
        """Test validation of invalid relationship types."""
        invalid_types = ["Invalid.Type", "System.LinkTypes.NonExistent", "Random.String", "", None]

        for rel_type in invalid_types:
            assert not WorkItemValidator.validate_relationship_type(rel_type), (
                f"{rel_type} should be invalid"
            )

    def test_get_valid_relationship_types(self):
        """Test getting list of valid relationship types."""
        valid_types = WorkItemValidator.get_valid_relationship_types()

        assert isinstance(valid_types, list)
        assert len(valid_types) > 0
        assert "System.LinkTypes.Hierarchy-Forward" in valid_types
        assert "System.LinkTypes.Related" in valid_types


class TestRelationshipConstraintValidation:
    """Test relationship constraint validation."""

    def test_validate_hierarchy_forward_valid(self):
        """Test valid hierarchy forward relationships."""
        valid_cases = [
            ("Epic", "Feature", "System.LinkTypes.Hierarchy-Forward"),
            ("Epic", "User Story", "System.LinkTypes.Hierarchy-Forward"),
            ("Feature", "User Story", "System.LinkTypes.Hierarchy-Forward"),
            ("User Story", "Task", "System.LinkTypes.Hierarchy-Forward"),
        ]

        for source_type, target_type, rel_type in valid_cases:
            is_valid, error = WorkItemValidator.validate_relationship_constraints(
                source_type, target_type, rel_type
            )
            assert is_valid, (
                f"Should allow {source_type} -> {target_type} hierarchy relationship but got error: {error}"
            )

    def test_validate_hierarchy_forward_invalid(self):
        """Test invalid hierarchy forward relationships."""
        invalid_cases = [
            ("Task", "Epic", "System.LinkTypes.Hierarchy-Forward"),
            ("User Story", "Epic", "System.LinkTypes.Hierarchy-Forward"),
            ("Feature", "Epic", "System.LinkTypes.Hierarchy-Forward"),
            ("Task", "User Story", "System.LinkTypes.Hierarchy-Forward"),
            ("Epic", "Task", "System.LinkTypes.Hierarchy-Forward"),
            ("Feature", "Task", "System.LinkTypes.Hierarchy-Forward"),
        ]

        for source_type, target_type, rel_type in invalid_cases:
            is_valid, error = WorkItemValidator.validate_relationship_constraints(
                source_type, target_type, rel_type
            )
            assert not is_valid, (
                f"Should reject {source_type} -> {target_type} hierarchy relationship"
            )
            assert error is not None, "Should provide error message for invalid relationship"

    def test_validate_dependency_relationships(self):
        """Test dependency relationship validation."""
        valid_dependency_types = ["Task", "Bug", "User Story", "Feature"]

        # Valid dependency cases
        for source_type in valid_dependency_types:
            for target_type in valid_dependency_types:
                is_valid, error = WorkItemValidator.validate_relationship_constraints(
                    source_type, target_type, "System.LinkTypes.Dependency-Forward"
                )
                assert is_valid, (
                    f"Should allow dependency {source_type} -> {target_type} but got error: {error}"
                )

        # Invalid dependency cases
        invalid_cases = [
            ("Epic", "Task", "System.LinkTypes.Dependency-Forward"),
            ("Task", "Epic", "System.LinkTypes.Dependency-Forward"),
            ("Test Case", "Bug", "System.LinkTypes.Dependency-Forward"),
        ]

        for source_type, target_type, rel_type in invalid_cases:
            is_valid, error = WorkItemValidator.validate_relationship_constraints(
                source_type, target_type, rel_type
            )
            assert not is_valid, f"Should reject dependency {source_type} -> {target_type}"

    def test_validate_duplicate_relationships(self):
        """Test duplicate relationship validation."""
        work_item_types = ["Epic", "Feature", "User Story", "Task", "Bug", "Test Case"]

        # Valid duplicate cases (same type)
        for work_type in work_item_types:
            is_valid, error = WorkItemValidator.validate_relationship_constraints(
                work_type, work_type, "System.LinkTypes.Duplicate-Forward"
            )
            assert is_valid, (
                f"Should allow duplicate relationship for same type {work_type} but got error: {error}"
            )

        # Invalid duplicate cases (different types)
        invalid_cases = [
            ("Epic", "Feature", "System.LinkTypes.Duplicate-Forward"),
            ("Task", "Bug", "System.LinkTypes.Duplicate-Forward"),
            ("User Story", "Task", "System.LinkTypes.Duplicate-Forward"),
        ]

        for source_type, target_type, rel_type in invalid_cases:
            is_valid, error = WorkItemValidator.validate_relationship_constraints(
                source_type, target_type, rel_type
            )
            assert not is_valid, (
                f"Should reject duplicate relationship between different types {source_type} -> {target_type}"
            )

    def test_validate_test_relationships(self):
        """Test testing relationship validation."""
        # Valid test cases
        valid_cases = [
            ("Test Case", "Bug", "Microsoft.VSTS.Common.TestedBy-Forward"),
            ("Test Case", "User Story", "Microsoft.VSTS.Common.TestedBy-Forward"),
            ("Bug", "Test Case", "Microsoft.VSTS.Common.TestedBy-Reverse"),
            ("User Story", "Test Case", "Microsoft.VSTS.Common.TestedBy-Reverse"),
        ]

        for source_type, target_type, rel_type in valid_cases:
            is_valid, error = WorkItemValidator.validate_relationship_constraints(
                source_type, target_type, rel_type
            )
            assert is_valid, (
                f"Should allow test relationship {source_type} -> {target_type} but got error: {error}"
            )

        # Invalid test cases
        invalid_cases = [
            ("Bug", "User Story", "Microsoft.VSTS.Common.TestedBy-Forward"),
            ("User Story", "Bug", "Microsoft.VSTS.Common.TestedBy-Reverse"),
            ("Epic", "Test Case", "Microsoft.VSTS.Common.TestedBy-Forward"),
        ]

        for source_type, target_type, rel_type in invalid_cases:
            is_valid, error = WorkItemValidator.validate_relationship_constraints(
                source_type, target_type, rel_type
            )
            assert not is_valid, (
                f"Should reject invalid test relationship {source_type} -> {target_type}"
            )

    def test_validate_related_relationships_always_valid(self):
        """Test that related relationships are always valid."""
        work_item_types = ["Epic", "Feature", "User Story", "Task", "Bug", "Test Case"]

        for source_type in work_item_types:
            for target_type in work_item_types:
                is_valid, error = WorkItemValidator.validate_relationship_constraints(
                    source_type, target_type, "System.LinkTypes.Related"
                )
                assert is_valid, (
                    f"Related relationships should always be valid: {source_type} -> {target_type}"
                )

    def test_validate_unknown_relationship_type(self):
        """Test validation with unknown relationship type."""
        is_valid, error = WorkItemValidator.validate_relationship_constraints(
            "Epic", "Feature", "Unknown.Type"
        )

        assert not is_valid
        assert "Unknown relationship type" in error


class TestRelationshipSuggestions:
    """Test relationship type suggestions."""

    def test_suggest_relationship_types_hierarchy(self):
        """Test hierarchy relationship suggestions."""
        suggestions = WorkItemValidator.suggest_relationship_types("Epic", "User Story")

        # Should suggest hierarchy forward
        suggestion_types = [suggestion[0] for suggestion in suggestions]
        assert "System.LinkTypes.Hierarchy-Forward" in suggestion_types

        # Should always suggest related
        assert "System.LinkTypes.Related" in suggestion_types

        # Check reverse hierarchy
        suggestions = WorkItemValidator.suggest_relationship_types("User Story", "Epic")
        suggestion_types = [suggestion[0] for suggestion in suggestions]
        assert "System.LinkTypes.Hierarchy-Reverse" in suggestion_types

    def test_suggest_relationship_types_dependencies(self):
        """Test dependency relationship suggestions."""
        suggestions = WorkItemValidator.suggest_relationship_types("Task", "Bug")

        suggestion_types = [suggestion[0] for suggestion in suggestions]
        assert "System.LinkTypes.Dependency-Forward" in suggestion_types
        assert "System.LinkTypes.Dependency-Reverse" in suggestion_types
        assert "System.LinkTypes.Related" in suggestion_types

    def test_suggest_relationship_types_duplicates(self):
        """Test duplicate relationship suggestions."""
        suggestions = WorkItemValidator.suggest_relationship_types("Bug", "Bug")

        suggestion_types = [suggestion[0] for suggestion in suggestions]
        assert "System.LinkTypes.Duplicate-Forward" in suggestion_types
        assert "System.LinkTypes.Related" in suggestion_types

    def test_suggest_relationship_types_test_relationships(self):
        """Test test relationship suggestions."""
        # Test Case as source
        suggestions = WorkItemValidator.suggest_relationship_types("Test Case", "Bug")
        suggestion_types = [suggestion[0] for suggestion in suggestions]
        assert "Microsoft.VSTS.Common.TestedBy-Forward" in suggestion_types

        # Test Case as target
        suggestions = WorkItemValidator.suggest_relationship_types("Bug", "Test Case")
        suggestion_types = [suggestion[0] for suggestion in suggestions]
        assert "Microsoft.VSTS.Common.TestedBy-Reverse" in suggestion_types

    def test_suggest_relationship_types_descriptions(self):
        """Test that suggestions include descriptions."""
        suggestions = WorkItemValidator.suggest_relationship_types("Epic", "User Story")

        assert len(suggestions) > 0
        for suggestion in suggestions:
            assert len(suggestion) == 2  # (type, description)
            assert isinstance(suggestion[0], str)  # type
            assert isinstance(suggestion[1], str)  # description
            assert len(suggestion[1]) > 0  # non-empty description

    def test_suggest_relationship_types_same_level(self):
        """Test suggestions for work items at same hierarchy level."""
        suggestions = WorkItemValidator.suggest_relationship_types("Task", "Task")

        suggestion_types = [suggestion[0] for suggestion in suggestions]
        # Should suggest related, dependencies, and duplicates
        assert "System.LinkTypes.Related" in suggestion_types
        assert "System.LinkTypes.Dependency-Forward" in suggestion_types
        assert "System.LinkTypes.Dependency-Reverse" in suggestion_types
        assert "System.LinkTypes.Duplicate-Forward" in suggestion_types


class TestRelationshipValidationIntegration:
    """Test integration of relationship validation."""

    def test_validation_error_handling(self):
        """Test that validation handles errors gracefully."""
        # Should not crash with None values
        is_valid, error = WorkItemValidator.validate_relationship_constraints(
            None, "Task", "System.LinkTypes.Related"
        )
        # Should be permissive when validation fails
        assert is_valid

    def test_validation_with_unknown_work_item_types(self):
        """Test validation with unknown work item types."""
        is_valid, error = WorkItemValidator.validate_relationship_constraints(
            "CustomType", "AnotherCustomType", "System.LinkTypes.Related"
        )
        # Should allow related relationships for unknown types
        assert is_valid

    def test_validation_logging_and_permissiveness(self):
        """Test that validation is permissive for edge cases."""
        # Test with empty strings
        is_valid, error = WorkItemValidator.validate_relationship_constraints(
            "", "", "System.LinkTypes.Related"
        )
        # Should be permissive
        assert is_valid
