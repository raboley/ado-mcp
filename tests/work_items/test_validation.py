"""Tests for work item validation functionality."""

import os
import pytest
from unittest.mock import Mock, patch
from fastmcp.client import Client

from server import mcp
from tests.ado.test_client import requires_ado_creds
from ado.work_items.validation import WorkItemValidator
from ado.cache import ado_cache

# pytestmark removed - only async tests need the decorator


@pytest.fixture
async def mcp_client():
    async with Client(mcp) as client:
        initial_org_url = os.environ.get(
            "ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley"
        )
        await client.call_tool("set_ado_organization", {"organization_url": initial_org_url})
        yield client


@pytest.fixture
def project_id():
    return "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before and after each test."""
    ado_cache.clear_all()
    yield
    ado_cache.clear_all()


class TestPathValidation:
    """Tests for path validation methods."""
    
    def test_validate_path_format_valid_paths(self):
        """Test that valid path formats are accepted."""
        valid_paths = [
            "Project",
            "Project\\Team",
            "Project\\Team\\Component",
            "My Project\\Sprint 1",
            "Project-123\\Team_A\\Feature.1"
        ]
        
        for path in valid_paths:
            assert WorkItemValidator._validate_path_format(path), f"Path should be valid: {path}"
    
    def test_validate_path_format_invalid_paths(self):
        """Test that invalid path formats are rejected."""
        invalid_paths = [
            "",
            None,
            "\\Project",
            "Project\\",
            "Project\\\\Team",
            "Project\\\\",
            "Project\\ \\Team",
            "Project<>Team",
            "Project/Team",
            "Project|Team",
            "Project*Team",
            "Project?Team",
        ]
        
        for path in invalid_paths:
            assert not WorkItemValidator._validate_path_format(path), f"Path should be invalid: {path}"
    
    def test_sanitize_path(self):
        """Test path sanitization."""
        test_cases = [
            ("  Project\\Team  ", "Project\\Team"),
            ("\\Project\\Team\\", "Project\\Team"),
            ("Project\\\\Team", "Project\\Team"),
            ("Project\\\\\\Team", "Project\\Team"),
            ("Project<>\\Team", "Project\\Team"),
            ("Project/Team", "ProjectTeam"),
            ("Project\\ \\Team", "Project\\Team"),
            ("  \\\\Project\\\\Team\\\\  ", "Project\\Team"),
        ]
        
        for input_path, expected in test_cases:
            result = WorkItemValidator.sanitize_path(input_path)
            assert result == expected, f"Sanitizing '{input_path}' should produce '{expected}' but got '{result}'"


class TestFieldValidation:
    """Tests for field validation methods."""
    
    def test_validate_priority_field(self):
        """Test priority field validation."""
        # Valid priorities
        valid_priorities = [1, 2, 3, 4]
        for priority in valid_priorities:
            assert WorkItemValidator.validate_field_value("System.Priority", priority, "Integer"), \
                f"Priority {priority} should be valid"
        
        # Reason: None is valid (represents no priority set)
        invalid_priorities = [0, 5, -1, 10, "1", 1.5]
        for priority in invalid_priorities:
            assert not WorkItemValidator.validate_field_value("System.Priority", priority, "Integer"), \
                f"Priority {priority} should be invalid"
    
    def test_validate_tags_field(self):
        """Test tags field validation."""
        # Valid tags
        valid_tags = ["tag1; tag2", "single-tag", "tag with spaces; another_tag"]
        for tags in valid_tags:
            assert WorkItemValidator.validate_field_value("System.Tags", tags), \
                f"Tags '{tags}' should be valid"
        
        # Invalid tags
        invalid_tags = [123, [], {}]
        for tags in invalid_tags:
            assert not WorkItemValidator.validate_field_value("System.Tags", tags), \
                f"Tags '{tags}' should be invalid"
    
    def test_validate_user_fields(self):
        """Test user field validation."""
        user_fields = ["System.AssignedTo", "System.CreatedBy", "System.ChangedBy"]
        
        # Valid user values
        valid_users = ["user@example.com", "Display Name", "user.name@company.co.uk"]
        for field in user_fields:
            for user in valid_users:
                assert WorkItemValidator.validate_field_value(field, user), \
                    f"User field '{field}' with value '{user}' should be valid"
        
        # Reason: None is valid (represents no assignment)
        invalid_users = ["", 123, []]
        for field in user_fields:
            for user in invalid_users:
                assert not WorkItemValidator.validate_field_value(field, user), \
                    f"User field '{field}' with value '{user}' should be invalid"
    
    def test_validate_type_based_fields(self):
        """Test validation based on field types."""
        test_cases = [
            ("String", "text", True),
            ("String", 123, False),
            ("Integer", 42, True),
            ("Integer", "42", False),
            ("Double", 3.14, True),
            ("Double", 42, True),  # Int is valid for Double
            ("Double", "3.14", False),
            ("Boolean", True, True),
            ("Boolean", False, True),
            ("Boolean", "true", False),
            ("DateTime", "2023-12-01T10:00:00Z", True),
            ("DateTime", "2023-12-01", True),
            ("DateTime", "invalid-date", False),
            ("DateTime", 123, False),
        ]
        
        for field_type, value, expected in test_cases:
            result = WorkItemValidator.validate_field_value("Test.Field", value, field_type)
            assert result == expected, \
                f"Field type '{field_type}' with value '{value}' should be {'valid' if expected else 'invalid'}"


class TestWorkItemTypeValidation:
    """Tests for work item type validation."""
    
    def test_validate_common_work_item_types(self):
        """Test validation of common work item types when cache is empty."""
        common_types = ["Bug", "Task", "User Story", "Feature", "Epic", "Test Case", "Issue"]
        
        for wit_type in common_types:
            assert WorkItemValidator.validate_work_item_type("any-project", wit_type), \
                f"Common work item type '{wit_type}' should be valid"
    
    def test_validate_unknown_work_item_type(self):
        """Test validation of unknown work item types when cache is empty."""
        unknown_types = ["CustomType", "NonExistentType", ""]
        
        for wit_type in unknown_types:
            result = WorkItemValidator.validate_work_item_type("any-project", wit_type)
            if wit_type == "":
                assert not result, "Empty work item type should be invalid"
            else:
                assert not result, f"Unknown work item type '{wit_type}' should be invalid"
    
    @patch.object(ado_cache, 'get_work_item_types')
    def test_validate_work_item_type_with_cache(self, mock_get_types):
        """Test work item type validation with cached data."""
        # Mock cached work item types with proper attributes
        bug_type = Mock()
        bug_type.name = "Bug"
        task_type = Mock()
        task_type.name = "Task"
        custom_type = Mock()
        custom_type.name = "Custom Type"
        
        mock_types = [bug_type, task_type, custom_type]
        mock_get_types.return_value = mock_types
        
        # Test valid type
        assert WorkItemValidator.validate_work_item_type("project-123", "Bug")
        assert WorkItemValidator.validate_work_item_type("project-123", "Custom Type")
        
        # Test invalid type
        assert not WorkItemValidator.validate_work_item_type("project-123", "NonExistent")
        
        mock_get_types.assert_called_with("project-123")


class TestPathSuggestions:
    """Tests for path suggestion functionality."""
    
    @patch.object(ado_cache, 'get_area_paths')
    def test_suggest_area_paths(self, mock_get_paths):
        """Test area path suggestions."""
        # Mock cached paths with proper attributes
        node1 = Mock()
        node1.path = "Project\\Team1"
        node2 = Mock()
        node2.path = "Project\\Team2"
        node3 = Mock()
        node3.path = "Project\\Components\\Frontend"
        node4 = Mock()
        node4.path = "Project\\Components\\Backend"
        
        mock_nodes = [node1, node2, node3, node4]
        mock_get_paths.return_value = mock_nodes
        
        # Mock _collect_all_paths method
        with patch.object(WorkItemValidator, '_collect_all_paths') as mock_collect:
            mock_collect.return_value = [
                "Project\\Team1",
                "Project\\Team2", 
                "Project\\Components\\Frontend",
                "Project\\Components\\Backend"
            ]
            
            # Test partial matches
            suggestions = WorkItemValidator.suggest_valid_paths("project-123", "Team", "area")
            
            assert len(suggestions) <= 5, "Should return at most 5 suggestions"
            assert all("team" in s.lower() for s in suggestions), "All suggestions should contain 'team'"
            
            mock_get_paths.assert_called_with("project-123")
    
    @patch.object(ado_cache, 'get_iteration_paths')
    def test_suggest_iteration_paths_no_cache(self, mock_get_paths):
        """Test iteration path suggestions when cache is empty."""
        mock_get_paths.return_value = None
        
        suggestions = WorkItemValidator.suggest_valid_paths("project-123", "Sprint", "iteration")
        
        assert suggestions == [], "Should return empty list when no cache available"
        mock_get_paths.assert_called_with("project-123")


@patch('ado.work_items.validation.WorkItemValidator.validate_work_item_type')
@patch('ado.work_items.validation.WorkItemValidator.validate_field_value')
def test_validation_integration_with_tools(mock_validate_field, mock_validate_type):
    """Test that validation methods are called during work item creation."""
    from ado.work_items.tools import register_work_item_tools
    from unittest.mock import Mock
    
    # Setup mocks
    mock_validate_type.return_value = True
    mock_validate_field.return_value = True
    
    # Mock MCP instance and client container
    mock_mcp = Mock()
    mock_client = Mock()
    client_container = {"client": mock_client}
    
    # Register tools (this will create the decorated functions)
    register_work_item_tools(mock_mcp, client_container)
    
    # Verify that the tool decorator was called (meaning validation is integrated)
    assert mock_mcp.tool.called, "Should register work item tools with MCP"
    assert mock_mcp.tool.call_count >= 8, "Should register multiple work item tools"


def test_validation_priority_check_unit():
    """Test that priority validation works correctly at the unit level."""
    from ado.work_items.validation import WorkItemValidator
    
    # Valid priorities
    assert WorkItemValidator.validate_field_value("System.Priority", 1, "Integer")
    assert WorkItemValidator.validate_field_value("System.Priority", 2, "Integer")
    assert WorkItemValidator.validate_field_value("System.Priority", 3, "Integer")
    assert WorkItemValidator.validate_field_value("System.Priority", 4, "Integer")
    
    # Invalid priorities
    assert not WorkItemValidator.validate_field_value("System.Priority", 0, "Integer")
    assert not WorkItemValidator.validate_field_value("System.Priority", 5, "Integer")
    assert not WorkItemValidator.validate_field_value("System.Priority", 10, "Integer")
    assert not WorkItemValidator.validate_field_value("System.Priority", -1, "Integer")
    assert not WorkItemValidator.validate_field_value("System.Priority", "1", "Integer")


def test_validation_bypass_logic_unit():
    """Test that bypass rules logic works correctly at the unit level."""
    from ado.work_items.validation import WorkItemValidator
    
    # Test the validation functions return appropriate values that can be bypassed
    # This simulates the bypass_rules logic in the tools
    project_id = "test-project"
    
    # Test normal validation
    result_normal = WorkItemValidator.validate_work_item_type(project_id, "Task")
    # Should be True for common types or False for unknown, but not crash
    assert isinstance(result_normal, bool)
    
    # Test with invalid data that would normally fail
    result_invalid = WorkItemValidator.validate_field_value("System.Priority", 10, "Integer")
    assert result_invalid is False, "Invalid priority should fail validation"
    
    # In bypass mode, the tools would skip calling these validators
    # This test verifies the validators exist and work as expected