"""Path validation functionality for work item operations."""

import logging
import re
from typing import Optional, List, Any

from ado.cache import ado_cache

logger = logging.getLogger(__name__)


class PathValidator:
    """Validator for work item area and iteration paths."""

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
            return PathValidator._path_exists_in_tree(area_path, cached_areas)

        # Reason: Avoid making API calls during validation for performance
        return PathValidator._validate_path_format(area_path)

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
            return PathValidator._path_exists_in_tree(iteration_path, cached_iterations)

        # Reason: Avoid making API calls during validation for performance
        return PathValidator._validate_path_format(iteration_path)

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
            if hasattr(node, "path") and node.path == path:
                return True

            if hasattr(node, "children") and node.children:
                if PathValidator._path_exists_in_tree(path, node.children):
                    return True

        return False

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
        path = re.sub(r"\\+", r"\\", path)
        path = re.sub(r'[<>:"/|?*\x00-\x1f]', "", path)

        segments = path.split("\\")
        segments = [seg.strip() for seg in segments if seg.strip()]

        return "\\".join(segments)

    @staticmethod
    def suggest_valid_paths(
        project_id: str, partial_path: str, path_type: str = "area"
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

        all_paths = PathValidator._collect_all_paths(cached_nodes)

        partial_lower = partial_path.lower()
        for path in all_paths:
            if partial_lower in path.lower():
                suggestions.append(path)

        # Reason: Prioritize exact prefix matches for better UX
        suggestions.sort(key=lambda p: (not p.lower().startswith(partial_lower), len(p), p.lower()))

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
            if hasattr(node, "path"):
                paths.append(node.path)
            elif hasattr(node, "name"):
                current_path = f"{parent_path}\\{node.name}" if parent_path else node.name
                paths.append(current_path)

                if hasattr(node, "children") and node.children:
                    child_paths = PathValidator._collect_all_paths(node.children, current_path)
                    paths.extend(child_paths)

        return paths