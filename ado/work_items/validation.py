"""Validation helpers for work item operations."""

import logging
import re
from typing import Optional, List, Dict, Any, Tuple

from ado.cache import ado_cache
from ado.errors import AdoError
from .models import WorkItemRelationType

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
            
        cached_areas = ado_cache.get_area_paths(project_id)
        if cached_areas:
            return WorkItemValidator._path_exists_in_tree(area_path, cached_areas)
        
        # Reason: Avoid making API calls during validation for performance
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
            
        cached_iterations = ado_cache.get_iteration_paths(project_id)
        if cached_iterations:
            return WorkItemValidator._path_exists_in_tree(iteration_path, cached_iterations)
        
        # Reason: Avoid making API calls during validation for performance
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
        
        if path.startswith("\\") or path.endswith("\\"):
            return False
        
        segments = path.split("\\")
        if any(not segment.strip() for segment in segments):
            return False
        
        # Reason: Azure DevOps paths have specific character restrictions
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
        
        for node in nodes:
            if hasattr(node, 'path') and node.path == path:
                return True
            
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
    def validate_state_transition(
        project_id: str,
        work_item_type: str,
        from_state: str,
        to_state: str
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
        try:
            from ado.work_items.client import WorkItemsClient
            from ado.client_container import get_ado_client
            
            # If states are the same, always allow (no transition)
            if from_state == to_state:
                logger.debug(f"State transition validation: {from_state} -> {to_state} (no change, allowed)")
                return True
            
            # Get the ADO client
            ado_client = get_ado_client()
            if not ado_client:
                logger.warning("ADO client not available for state transition validation, allowing transition")
                return True
                
            work_items_client = WorkItemsClient(ado_client)
            
            # Get detailed work item type information including transitions
            try:
                work_item_type_details = work_items_client.get_work_item_type(project_id, work_item_type)
            except Exception as e:
                logger.warning(f"Failed to get work item type details for transition validation: {e}, allowing transition")
                return True
                
            # Check if we have transition information
            if not hasattr(work_item_type_details, 'transitions') or not work_item_type_details.transitions:
                logger.debug(f"No transition information available for {work_item_type}, allowing transition")
                return True
                
            transitions = work_item_type_details.transitions
            
            # Azure DevOps transitions are organized by from_state
            # Each from_state has a list of possible transitions
            if from_state not in transitions:
                logger.debug(f"No transitions defined from state '{from_state}' for {work_item_type}, allowing transition")
                return True
                
            from_state_transitions = transitions[from_state]
            if not isinstance(from_state_transitions, list):
                logger.debug(f"Invalid transition format for state '{from_state}', allowing transition")
                return True
                
            # Check if any transition allows moving to the target state
            for transition in from_state_transitions:
                if isinstance(transition, dict) and transition.get('to') == to_state:
                    logger.debug(f"State transition validation: {from_state} -> {to_state} (allowed)")
                    return True
                    
            # No valid transition found
            logger.info(f"State transition validation: {from_state} -> {to_state} (not allowed for {work_item_type})")
            return False
            
        except Exception as e:
            logger.error(f"Error during state transition validation: {e}, allowing transition as fallback")
            # In case of error, allow the transition to avoid breaking workflows
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
                return isinstance(field_value, (int, float))
            elif field_type == "DateTime":
                if isinstance(field_value, str):
                    try:
                        return bool(re.match(r'^\d{4}-\d{2}-\d{2}', field_value))
                    except:
                        return False
                return False
            elif field_type == "Boolean":
                return isinstance(field_value, bool)
        
        # Reason: Be permissive for unknown field types to avoid breaking custom fields
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
        
        path = path.strip()
        path = path.strip("\\")
        path = re.sub(r'\\+', r'\\', path)
        path = re.sub(r'[<>:"/|?*\x00-\x1f]', '', path)
        
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
        
        if path_type == "area":
            cached_nodes = ado_cache.get_area_paths(project_id)
        else:
            cached_nodes = ado_cache.get_iteration_paths(project_id)
        
        if not cached_nodes:
            return suggestions
        
        all_paths = WorkItemValidator._collect_all_paths(cached_nodes)
        
        partial_lower = partial_path.lower()
        for path in all_paths:
            if partial_lower in path.lower():
                suggestions.append(path)
        
        # Reason: Prioritize exact prefix matches for better UX
        suggestions.sort(key=lambda p: (
            not p.lower().startswith(partial_lower),
            len(p),
            p.lower()
        ))
        
        return suggestions[:5]
    
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
                current_path = f"{parent_path}\\{node.name}" if parent_path else node.name
                paths.append(current_path)
                
                if hasattr(node, 'children') and node.children:
                    child_paths = WorkItemValidator._collect_all_paths(
                        node.children, current_path
                    )
                    paths.extend(child_paths)
        
        return paths
    
    @staticmethod
    def validate_relationship_constraints(
        source_work_item_type: str,
        target_work_item_type: str,
        relationship_type: str
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
            if not WorkItemValidator.validate_relationship_type(relationship_type):
                return False, f"Unknown relationship type: {relationship_type}"
            
            # Define work item hierarchy levels (higher number = higher in hierarchy)
            hierarchy_levels = {
                "Epic": 3,
                "Feature": 2,  
                "User Story": 1,
                "Task": 0,
                "Bug": 0,
                "Test Case": 0,
                "Issue": 0
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
                if source_work_item_type == "Epic" and target_work_item_type not in ["Feature", "User Story"]:
                    return False, f"Epic can only have Feature or User Story children, not {target_work_item_type}"
                
                # Feature can only have User Story children
                if source_work_item_type == "Feature" and target_work_item_type != "User Story":
                    return False, f"Feature can only have User Story children, not {target_work_item_type}"
                
                # User Story can only have Task children
                if source_work_item_type == "User Story" and target_work_item_type != "Task":
                    return False, f"User Story can only have Task children, not {target_work_item_type}"
                
            elif relationship_type == "System.LinkTypes.Hierarchy-Reverse":
                # Child -> Parent: target should be higher level than source
                if target_level <= source_level:
                    return False, (
                        f"Invalid hierarchy: {target_work_item_type} cannot be parent of "
                        f"{source_work_item_type}. Parent must be at higher hierarchy level."
                    )
            
            # Validate dependency relationships
            elif relationship_type in ["System.LinkTypes.Dependency-Forward", "System.LinkTypes.Dependency-Reverse"]:
                # Dependencies are typically between work items at the same level
                valid_dependency_types = ["Task", "Bug", "User Story", "Feature"]
                if source_work_item_type not in valid_dependency_types:
                    return False, f"Dependencies not typically supported for {source_work_item_type}"
                if target_work_item_type not in valid_dependency_types:
                    return False, f"Dependencies not typically supported for {target_work_item_type}"
            
            # Validate blocking relationships
            elif relationship_type in ["Microsoft.VSTS.Common.Affects-Forward", "Microsoft.VSTS.Common.Affects-Reverse"]:
                # Any work item can block or be blocked by any other work item
                pass
            
            # Validate duplicate relationships
            elif relationship_type in ["System.LinkTypes.Duplicate-Forward", "System.LinkTypes.Duplicate-Reverse"]:
                # Duplicates should be of the same work item type
                if source_work_item_type != target_work_item_type:
                    return False, (
                        f"Duplicate relationships should be between same work item types. "
                        f"Got {source_work_item_type} and {target_work_item_type}"
                    )
            
            # Validate test relationships
            elif relationship_type in ["Microsoft.VSTS.Common.TestedBy-Forward", "Microsoft.VSTS.Common.TestedBy-Reverse"]:
                if relationship_type == "Microsoft.VSTS.Common.TestedBy-Forward":
                    # Test Case tests other work items
                    if source_work_item_type != "Test Case":
                        return False, f"Only Test Case can test other work items, not {source_work_item_type}"
                else:
                    # Other work items tested by Test Case
                    if target_work_item_type != "Test Case":
                        return False, f"Work items can only be tested by Test Case, not {target_work_item_type}"
            
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
        valid_types.extend([
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
            "Microsoft.VSTS.Common.TestedBy-Reverse"
        ])
        
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
            "Microsoft.VSTS.Common.TestedBy-Reverse"
        ]
    
    @staticmethod
    def suggest_relationship_types(
        source_work_item_type: str,
        target_work_item_type: str
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
            "Issue": 0
        }
        
        source_level = hierarchy_levels.get(source_work_item_type, 0)
        target_level = hierarchy_levels.get(target_work_item_type, 0)
        
        # Suggest hierarchy relationships
        if source_level > target_level:
            suggestions.append((
                "System.LinkTypes.Hierarchy-Forward",
                f"{source_work_item_type} contains {target_work_item_type}"
            ))
        elif target_level > source_level:
            suggestions.append((
                "System.LinkTypes.Hierarchy-Reverse", 
                f"{source_work_item_type} is contained by {target_work_item_type}"
            ))
        
        # Always suggest related
        suggestions.append((
            "System.LinkTypes.Related",
            "General relationship between work items"
        ))
        
        # Suggest dependencies for appropriate types
        valid_dependency_types = ["Task", "Bug", "User Story", "Feature"]
        if (source_work_item_type in valid_dependency_types and 
            target_work_item_type in valid_dependency_types):
            suggestions.append((
                "System.LinkTypes.Dependency-Forward",
                f"{source_work_item_type} blocks {target_work_item_type}"
            ))
            suggestions.append((
                "System.LinkTypes.Dependency-Reverse",
                f"{source_work_item_type} depends on {target_work_item_type}"
            ))
        
        # Suggest duplicates for same type
        if source_work_item_type == target_work_item_type:
            suggestions.append((
                "System.LinkTypes.Duplicate-Forward",
                f"{source_work_item_type} is duplicate of {target_work_item_type}"
            ))
        
        # Suggest test relationships
        if source_work_item_type == "Test Case":
            suggestions.append((
                "Microsoft.VSTS.Common.TestedBy-Forward",
                f"Test Case tests {target_work_item_type}"
            ))
        elif target_work_item_type == "Test Case":
            suggestions.append((
                "Microsoft.VSTS.Common.TestedBy-Reverse",
                f"{source_work_item_type} is tested by Test Case"
            ))
        
        return suggestions