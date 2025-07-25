"""
Enhanced project discovery tools with fuzzy matching and intelligent suggestions.

This module provides LLM-friendly project operations that accept both IDs and names,
with fuzzy matching capabilities to help users find projects even with typos or
partial name matches.
"""

import logging
from typing import Any

from ..cache import ado_cache
from ..client import AdoClient
from ..models import Project
from ..utils.fuzzy_matching import FuzzyMatcher, create_suggestion_error_message
from ..utils.token_estimation import limit_suggestions_by_tokens

logger = logging.getLogger(__name__)


class ProjectDiscoveryError(Exception):
    """Exception raised when project discovery fails with suggestions."""

    def __init__(self, message: str, suggestions: list[dict[str, Any]] | None = None):
        super().__init__(message)
        self.suggestions = suggestions


class EnhancedProjectTools:
    """
    Enhanced project discovery tools with fuzzy matching and intelligent error responses.

    Provides unified project operations that accept both IDs and names while offering
    intelligent suggestions when exact matches aren't found.
    """

    def __init__(self, client: AdoClient):
        """
        Initialize enhanced project tools.

        Args:
            client: The ADO client instance for API operations
        """
        self.client = client
        self.fuzzy_matcher = FuzzyMatcher(
            similarity_threshold=0.5,  # 50% similarity minimum for suggestions
            max_suggestions=10,  # Limit suggestions for readability
            performance_threshold_ms=200,  # Performance monitoring
        )

    def find_project_by_id_or_name(
        self, identifier: str, include_suggestions: bool = True
    ) -> Project | None:
        """
        Find a project by either ID or name with fuzzy matching support.

        Args:
            identifier: Project ID (UUID format) or project name
            include_suggestions: Whether to include fuzzy match suggestions in errors

        Returns:
            Project object if found, None otherwise

        Raises:
            ProjectDiscoveryError: When project not found but suggestions are available
        """
        logger.info(f"Searching for project: {identifier}")

        # Try to determine if this is an ID (UUID format) or name
        if self._is_project_id(identifier):
            return self._find_project_by_id(identifier, include_suggestions)
        else:
            return self._find_project_by_name(identifier, include_suggestions)

    def list_all_projects_with_metadata(self) -> list[dict[str, Any]]:
        """
        List all projects with enhanced metadata for better LLM understanding.

        Returns:
            List of project dictionaries with additional metadata
        """
        logger.info("Retrieving all projects with enhanced metadata")

        try:
            projects = self.client.list_projects()
            logger.info(f"Retrieved {len(projects)} projects from API")

            enhanced_projects = []
            for project in projects:
                enhanced_project = {
                    "id": project.id,
                    "name": project.name,
                    "description": getattr(project, "description", "No description available"),
                    "url": getattr(project, "url", None),
                    "state": getattr(project, "state", "Unknown"),
                    "visibility": getattr(project, "visibility", "Unknown"),
                }
                enhanced_projects.append(enhanced_project)

            # Sort by name for consistent ordering
            enhanced_projects.sort(key=lambda x: x["name"].lower())

            logger.info(f"Enhanced metadata for {len(enhanced_projects)} projects")
            return enhanced_projects

        except Exception as e:
            logger.error(f"Error retrieving projects with metadata: {e}")
            raise

    def get_project_suggestions(
        self, query: str, max_suggestions: int = 10, max_tokens: int = 1000
    ) -> dict[str, Any]:
        """
        Get fuzzy match suggestions for a project query.

        Args:
            query: The project name query that failed
            max_suggestions: Maximum number of suggestions to return
            max_tokens: Maximum tokens allowed in response

        Returns:
            Dictionary with suggestions and metadata
        """
        logger.info(f"Getting project suggestions for query: {query}")

        try:
            # Get all projects for fuzzy matching
            projects = self.client.list_projects()
            logger.info(f"Loaded {len(projects)} projects for suggestion matching")

            # Perform fuzzy matching
            matches = self.fuzzy_matcher.find_matches(
                query=query,
                candidates=projects,
                name_extractor=lambda x: x.name,
                id_extractor=lambda x: x.id,
            )

            logger.info(f"Found {len(matches)} fuzzy matches for '{query}'")

            if not matches:
                return {
                    "query": query,
                    "found": False,
                    "suggestions": [],
                    "message": f"Project '{query}' not found. No similar projects available.",
                }

            # Convert matches to suggestion format first, then limit by tokens
            initial_suggestions = []
            for match in matches[:max_suggestions] if max_suggestions else matches:
                project = match.item
                suggestion = {
                    "id": project.id,
                    "name": project.name,
                    "similarity": round(match.similarity, 3),
                    "match_type": match.match_type,
                    "description": getattr(project, "description", "No description available"),
                }
                initial_suggestions.append(suggestion)

            # Create user-friendly error message
            error_message = create_suggestion_error_message(
                query, "Project", matches, max_suggestions=5
            )

            # Limit suggestions by token count to prevent context overflow
            limited_suggestions = limit_suggestions_by_tokens(
                initial_suggestions, error_message=error_message, max_tokens=max_tokens
            )

            result = {
                "query": query,
                "found": False,
                "suggestions": limited_suggestions,
                "message": error_message,
                "total_matches": len(matches),
                "limited_by_tokens": len(initial_suggestions) > len(limited_suggestions),
            }

            logger.info(
                f"Generated {len(limited_suggestions)} project suggestions "
                f"(limited from {len(matches)} total matches)"
            )

            return result

        except Exception as e:
            logger.error(f"Error generating project suggestions: {e}")
            return {
                "query": query,
                "found": False,
                "suggestions": [],
                "message": f"Error searching for project '{query}': {str(e)}",
                "error": True,
            }

    def _is_project_id(self, identifier: str) -> bool:
        """
        Determine if an identifier is a project ID (UUID format) or name.

        Args:
            identifier: The identifier to check

        Returns:
            True if identifier appears to be a UUID, False otherwise
        """
        # Azure DevOps project IDs are UUIDs (36 characters with hyphens)
        if len(identifier) == 36 and identifier.count("-") == 4:
            try:
                # Basic UUID format validation
                parts = identifier.split("-")
                return (
                    len(parts) == 5
                    and len(parts[0]) == 8
                    and len(parts[1]) == 4
                    and len(parts[2]) == 4
                    and len(parts[3]) == 4
                    and len(parts[4]) == 12
                    and all(c.isalnum() for part in parts for c in part)
                )
            except Exception:
                return False
        return False

    def _find_project_by_id(
        self, project_id: str, include_suggestions: bool = True
    ) -> Project | None:
        """
        Find a project by its ID.

        Args:
            project_id: The project UUID
            include_suggestions: Whether to include suggestions on failure

        Returns:
            Project object if found, None otherwise

        Raises:
            ProjectDiscoveryError: When project not found but suggestions available
        """
        logger.info(f"Searching for project by ID: {project_id}")

        try:
            # Try to get project directly by ID
            projects = self.client.list_projects()
            project = next((p for p in projects if p.id == project_id), None)

            if project:
                logger.info(f"Found project by ID: {project.name} ({project.id})")
                return project

            logger.warning(f"Project with ID '{project_id}' not found")

            if include_suggestions:
                # For ID lookups that fail, we can't provide meaningful fuzzy suggestions
                # since IDs are exact matches. Just provide a helpful error.
                raise ProjectDiscoveryError(
                    f"Project with ID '{project_id}' not found. "
                    "Please verify the project ID is correct.",
                    suggestions=[],
                )

            return None

        except ProjectDiscoveryError:
            raise
        except Exception as e:
            logger.error(f"Error finding project by ID '{project_id}': {e}")
            if include_suggestions:
                raise ProjectDiscoveryError(
                    f"Error searching for project ID '{project_id}': {str(e)}", suggestions=[]
                ) from e
            return None

    def _find_project_by_name(
        self, project_name: str, include_suggestions: bool = True
    ) -> Project | None:
        """
        Find a project by its name with fuzzy matching.

        Args:
            project_name: The project name to search for
            include_suggestions: Whether to include fuzzy match suggestions on failure

        Returns:
            Project object if found, None otherwise

        Raises:
            ProjectDiscoveryError: When project not found but suggestions are available
        """
        logger.info(f"Searching for project by name: {project_name}")

        try:
            # First try cached lookup for exact match
            cached_project = ado_cache.find_project_by_name(project_name, fuzzy=False)
            if cached_project:
                logger.info(f"Found project in cache: {cached_project.name} ({cached_project.id})")
                return cached_project

            # Try fuzzy matching from cache
            fuzzy_project = ado_cache.find_project_by_name(project_name, fuzzy=True)
            if fuzzy_project:
                logger.info(
                    f"Found project via fuzzy matching: {fuzzy_project.name} ({fuzzy_project.id})"
                )
                return fuzzy_project

            logger.warning(f"Project '{project_name}' not found in cache")

            if include_suggestions:
                # Generate suggestions using fuzzy matching
                suggestions_data = self.get_project_suggestions(project_name)
                if suggestions_data["suggestions"]:
                    raise ProjectDiscoveryError(
                        suggestions_data["message"], suggestions=suggestions_data["suggestions"]
                    )

            return None

        except ProjectDiscoveryError:
            raise
        except Exception as e:
            logger.error(f"Error finding project by name '{project_name}': {e}")
            if include_suggestions:
                raise ProjectDiscoveryError(
                    f"Error searching for project '{project_name}': {str(e)}", suggestions=[]
                ) from e
            return None
