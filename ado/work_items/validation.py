"""Validation helpers for work item operations."""

import logging
import re
from typing import Optional, List, Dict, Any

from ado.cache import ado_cache
from ado.errors import AdoError

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
        if not area_path:
            return False
            
        # Check cache for area paths
        cached_areas = ado_cache.get_area_paths(project_id)
        if cached_areas:
            return WorkItemValidator._path_exists_in_tree(area_path, cached_areas)
        
        # If not cached, we can't validate without making an API call
        # For now, we'll do basic format validation
        return WorkItemValidator._validate_path_format(area_path)
    
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
        if not iteration_path:
            return False
            
        # Check cache for iteration paths
        cached_iterations = ado_cache.get_iteration_paths(project_id)
        if cached_iterations:
            return WorkItemValidator._path_exists_in_tree(iteration_path, cached_iterations)
        
        # If not cached, we can't validate without making an API call
        # For now, we'll do basic format validation
        return WorkItemValidator._validate_path_format(iteration_path)
    
    @staticmethod
    def _validate_path_format(path: str) -> bool:
        """
        Validate basic path format.
        
        Args:
            path: The path to validate
            
        Returns:
            True if the path format is valid
        """
        if not path or not isinstance(path, str):
            return False
        
        # Path should not start or end with backslash
        if path.startswith("\\") or path.endswith("\\"):
            return False
        
        # Path segments should not be empty
        segments = path.split("\\")
        if any(not segment.strip() for segment in segments):
            return False
        
        # Path should not contain invalid characters
        # Azure DevOps paths typically allow alphanumeric, spaces, dots, dashes, underscores
        invalid_chars_pattern = r'[<>:"/|?*\x00-\x1f]'
        if re.search(invalid_chars_pattern, path):
            return False
        
        return True
    
    @staticmethod
    def _path_exists_in_tree(path: str, nodes: List[Any]) -> bool:
        """
        Check if a path exists in a classification node tree.
        
        Args:
            path: The path to find
            nodes: List of ClassificationNode objects
            
        Returns:
            True if the path exists in the tree
        """
        if not nodes:
            return False
        
        # For simplicity, check the path property of nodes
        for node in nodes:
            if hasattr(node, 'path') and node.path == path:
                return True
            
            # Check children recursively
            if hasattr(node, 'children') and node.children:
                if WorkItemValidator._path_exists_in_tree(path, node.children):
                    return True
        
        return False
    
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
        
        # Check cache for work item types
        cached_types = ado_cache.get_work_item_types(project_id)
        if cached_types:
            # Check exact match
            for wit in cached_types:
                if wit.name == work_item_type:
                    return True
            return False
        
        # If not cached, we can't validate without making an API call
        # Common work item types as fallback
        common_types = ["Bug", "Task", "User Story", "Feature", "Epic", "Test Case", "Issue"]
        return work_item_type in common_types
    
    @staticmethod
    def validate_state_transition(
        project_id: str,
        work_item_type: str,
        from_state: str,
        to_state: str
    ) -> bool:
        """
        Validate that a state transition is allowed for a work item type.
        
        Args:
            project_id: The project ID
            work_item_type: The work item type name
            from_state: The current state
            to_state: The target state
            
        Returns:
            True if the transition is allowed
        """
        # For now, we'll allow all transitions
        # In a real implementation, this would check the work item type's state transitions
        # from the cached metadata
        logger.debug(
            f"State transition validation for {work_item_type}: "
            f"{from_state} -> {to_state} (currently permissive)"
        )
        return True
    
    @staticmethod
    def validate_field_value(
        field_name: str,
        field_value: Any,
        field_type: Optional[str] = None
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
            return True  # Null values are generally allowed
        
        # Special field validations
        if field_name == "System.Priority":
            # Priority should be 1-4
            if isinstance(field_value, int):
                return 1 <= field_value <= 4
            return False
        
        if field_name == "System.Tags":
            # Tags should be a string
            return isinstance(field_value, str)
        
        if field_name in ["System.AssignedTo", "System.CreatedBy", "System.ChangedBy"]:
            # User fields should be strings (email or display name)
            return isinstance(field_value, str) and len(field_value) > 0
        
        # General type validations
        if field_type:
            if field_type in ["String", "PlainText", "HTML"]:
                return isinstance(field_value, str)
            elif field_type == "Integer":
                return isinstance(field_value, int)
            elif field_type == "Double":
                return isinstance(field_value, (int, float))
            elif field_type == "DateTime":
                # Should be a string in ISO format
                if isinstance(field_value, str):
                    try:
                        # Basic ISO date validation
                        return bool(re.match(r'^\d{4}-\d{2}-\d{2}', field_value))
                    except:
                        return False
                return False
            elif field_type == "Boolean":
                return isinstance(field_value, bool)
        
        # Default: allow any value
        return True
    
    @staticmethod
    def sanitize_path(path: str) -> str:
        """
        Sanitize a path by removing invalid characters and normalizing.
        
        Args:
            path: The path to sanitize
            
        Returns:
            The sanitized path
        """
        if not path:
            return ""
        
        # Remove leading/trailing whitespace
        path = path.strip()
        
        # Remove leading/trailing backslashes
        path = path.strip("\\")
        
        # Replace multiple backslashes with single
        path = re.sub(r'\\+', r'\\', path)
        
        # Remove invalid characters
        path = re.sub(r'[<>:"/|?*\x00-\x1f]', '', path)
        
        # Clean up segments
        segments = path.split("\\")
        segments = [seg.strip() for seg in segments if seg.strip()]
        
        return "\\".join(segments)
    
    @staticmethod
    def suggest_valid_paths(
        project_id: str,
        partial_path: str,
        path_type: str = "area"
    ) -> List[str]:
        """
        Suggest valid paths based on a partial path.
        
        Args:
            project_id: The project ID
            partial_path: The partial path to match
            path_type: Either "area" or "iteration"
            
        Returns:
            List of suggested valid paths
        """
        suggestions = []
        
        # Get cached paths
        if path_type == "area":
            cached_nodes = ado_cache.get_area_paths(project_id)
        else:
            cached_nodes = ado_cache.get_iteration_paths(project_id)
        
        if not cached_nodes:
            return suggestions
        
        # Collect all paths from the tree
        all_paths = WorkItemValidator._collect_all_paths(cached_nodes)
        
        # Filter by partial match
        partial_lower = partial_path.lower()
        for path in all_paths:
            if partial_lower in path.lower():
                suggestions.append(path)
        
        # Sort by relevance (paths that start with the partial first)
        suggestions.sort(key=lambda p: (
            not p.lower().startswith(partial_lower),
            len(p),
            p.lower()
        ))
        
        return suggestions[:5]  # Return top 5 suggestions
    
    @staticmethod
    def _collect_all_paths(nodes: List[Any], parent_path: str = "") -> List[str]:
        """
        Recursively collect all paths from a node tree.
        
        Args:
            nodes: List of ClassificationNode objects
            parent_path: The parent path for recursion
            
        Returns:
            List of all paths in the tree
        """
        paths = []
        
        for node in nodes:
            if hasattr(node, 'path'):
                paths.append(node.path)
            elif hasattr(node, 'name'):
                # Build path from parent
                current_path = f"{parent_path}\\{node.name}" if parent_path else node.name
                paths.append(current_path)
                
                # Recurse into children
                if hasattr(node, 'children') and node.children:
                    child_paths = WorkItemValidator._collect_all_paths(
                        node.children, current_path
                    )
                    paths.extend(child_paths)
        
        return paths