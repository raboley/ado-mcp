"""
Enhanced tools package for Azure DevOps MCP server.

This package contains enhanced tool implementations with fuzzy matching
and intelligent error responses for better LLM interaction.
"""

from .projects import EnhancedProjectTools, ProjectDiscoveryError

__all__ = ["EnhancedProjectTools", "ProjectDiscoveryError"]
