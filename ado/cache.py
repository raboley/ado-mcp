"""
Caching layer for Azure DevOps data to minimize API calls and improve UX.

This module provides intelligent caching for:
- Projects (name -> ID mapping)
- Pipelines (name -> ID mapping per project)
- Service connections
- Recent pipeline runs

The cache uses TTL-based expiration and fuzzy name matching for better user experience.
"""

import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from difflib import get_close_matches

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from .models import Project, Pipeline

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


@dataclass
class CacheEntry:
    """A cache entry with data and expiration time."""
    data: Any
    expires_at: float
    
    def is_expired(self) -> bool:
        """Check if this cache entry has expired."""
        return time.time() > self.expires_at


class AdoCache:
    """
    Intelligent caching layer for Azure DevOps data.
    
    Provides fast name-to-ID lookups with fuzzy matching and TTL-based expiration.
    Designed to minimize API calls while keeping data reasonably fresh.
    """
    
    def __init__(self):
        self._cache: Dict[str, CacheEntry] = {}
        
        # TTL settings (in seconds)
        self.PROJECT_TTL = 15 * 60      # 15 minutes - projects rarely change
        self.PIPELINE_TTL = 10 * 60     # 10 minutes - pipelines change occasionally  
        self.SERVICE_CONN_TTL = 30 * 60 # 30 minutes - very stable
        self.RUN_TTL = 3 * 60           # 3 minutes - runs are dynamic
    
    def _get_cache_key(self, *parts: str) -> str:
        """Generate a cache key from parts."""
        return ":".join(str(part) for part in parts)
    
    def _is_valid(self, key: str) -> bool:
        """Check if a cache entry exists and is not expired."""
        entry = self._cache.get(key)
        return entry is not None and not entry.is_expired()
    
    def _set(self, key: str, data: Any, ttl_seconds: int) -> None:
        """Set a cache entry with TTL."""
        expires_at = time.time() + ttl_seconds
        self._cache[key] = CacheEntry(data=data, expires_at=expires_at)
        logger.debug(f"Cached {key} for {ttl_seconds}s")
    
    def _get(self, key: str) -> Optional[Any]:
        """Get a cache entry if it exists and is valid."""
        with tracer.start_as_current_span("cache_get") as span:
            span.set_attribute("cache.key", key)
            
            if self._is_valid(key):
                span.set_attribute("cache.hit", True)
                logger.debug(f"Cache hit for key: {key}")
                return self._cache[key].data
            elif key in self._cache:
                # Remove expired entry
                del self._cache[key]
                logger.debug(f"Removed expired cache entry: {key}")
                span.set_attribute("cache.hit", False)
                span.set_attribute("cache.expired", True)
            else:
                span.set_attribute("cache.hit", False)
                span.set_attribute("cache.expired", False)
                logger.debug(f"Cache miss for key: {key}")
            return None
    
    # Project caching
    def get_projects(self) -> Optional[List[Project]]:
        """Get cached projects list."""
        return self._get("projects")
    
    def set_projects(self, projects: List[Project]) -> None:
        """Cache projects list and create name-to-ID mapping."""
        self._set("projects", projects, self.PROJECT_TTL)
        
        # Create name mapping for fast lookups
        name_map = {project.name.lower(): project.id for project in projects}
        self._set("projects:name_map", name_map, self.PROJECT_TTL)
        
        logger.info(f"Cached {len(projects)} projects")
    
    def find_project_by_name(self, name: str, fuzzy: bool = True) -> Optional[Project]:
        """
        Find a project by name with optional fuzzy matching.
        
        Args:
            name: Project name to search for
            fuzzy: Enable fuzzy matching for typos/partial names
            
        Returns:
            Project object if found, None otherwise
        """
        projects = self.get_projects()
        if not projects:
            return None
        
        name_lower = name.lower()
        
        # Exact match first
        for project in projects:
            if project.name.lower() == name_lower:
                return project
        
        # Fuzzy matching if enabled
        if fuzzy:
            project_names = [p.name for p in projects]
            matches = get_close_matches(name, project_names, n=1, cutoff=0.6)
            if matches:
                match_name = matches[0]
                for project in projects:
                    if project.name == match_name:
                        logger.info(f"Fuzzy matched '{name}' to project '{match_name}'")
                        return project
        
        return None
    
    def get_project_id_by_name(self, name: str) -> Optional[str]:
        """Get project ID by name."""
        project = self.find_project_by_name(name)
        return project.id if project else None
    
    # Pipeline caching  
    def get_pipelines(self, project_id: str) -> Optional[List[Pipeline]]:
        """Get cached pipelines for a project."""
        key = f"pipelines:{project_id}"
        return self._get(key)
    
    def set_pipelines(self, project_id: str, pipelines: List[Pipeline]) -> None:
        """Cache pipelines for a project."""
        key = f"pipelines:{project_id}"
        self._set(key, pipelines, self.PIPELINE_TTL)
        
        # Create name mapping
        name_map = {pipeline.name.lower(): pipeline.id for pipeline in pipelines}
        name_key = f"pipelines:{project_id}:name_map"
        self._set(name_key, name_map, self.PIPELINE_TTL)
        
        logger.info(f"Cached {len(pipelines)} pipelines for project {project_id}")
    
    def find_pipeline_by_name(self, project_id: str, name: str, fuzzy: bool = True) -> Optional[Pipeline]:
        """
        Find a pipeline by name within a project.
        
        Args:
            project_id: Project ID to search within
            name: Pipeline name to search for
            fuzzy: Enable fuzzy matching
            
        Returns:
            Pipeline object if found, None otherwise
        """
        pipelines = self.get_pipelines(project_id)
        if not pipelines:
            return None
        
        name_lower = name.lower()
        
        # Exact match first
        for pipeline in pipelines:
            if pipeline.name.lower() == name_lower:
                return pipeline
        
        # Fuzzy matching
        if fuzzy:
            pipeline_names = [p.name for p in pipelines]
            matches = get_close_matches(name, pipeline_names, n=1, cutoff=0.6)
            if matches:
                match_name = matches[0]
                for pipeline in pipelines:
                    if pipeline.name == match_name:
                        logger.info(f"Fuzzy matched '{name}' to pipeline '{match_name}'")
                        return pipeline
        
        return None
    
    def get_pipeline_id_by_name(self, project_id: str, name: str) -> Optional[int]:
        """Get pipeline ID by name within a project."""
        pipeline = self.find_pipeline_by_name(project_id, name)
        return pipeline.id if pipeline else None
    
    def find_pipeline_by_name_and_project(self, project_name: str, pipeline_name: str) -> Optional[Tuple[str, int]]:
        """
        Find pipeline by project name and pipeline name.
        
        Returns:
            Tuple of (project_id, pipeline_id) if found, None otherwise
        """
        project = self.find_project_by_name(project_name)
        if not project:
            return None
        
        pipeline = self.find_pipeline_by_name(project.id, pipeline_name)
        if not pipeline:
            return None
        
        return (project.id, pipeline.id)
    
    # Service connections caching
    def get_service_connections(self, project_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached service connections for a project."""
        key = f"service_connections:{project_id}"
        return self._get(key)
    
    def set_service_connections(self, project_id: str, connections: List[Dict[str, Any]]) -> None:
        """Cache service connections for a project."""
        key = f"service_connections:{project_id}"
        self._set(key, connections, self.SERVICE_CONN_TTL)
        logger.info(f"Cached {len(connections)} service connections for project {project_id}")
    
    # Cache management
    def clear_expired(self) -> int:
        """Remove all expired cache entries. Returns number of entries removed."""
        before_count = len(self._cache)
        expired_keys = [key for key, entry in self._cache.items() if entry.is_expired()]
        
        for key in expired_keys:
            del self._cache[key]
        
        removed_count = len(expired_keys)
        if removed_count > 0:
            logger.info(f"Removed {removed_count} expired cache entries")
        
        return removed_count
    
    def clear_all(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        logger.info("Cleared all cache entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_entries = len(self._cache)
        expired_entries = sum(1 for entry in self._cache.values() if entry.is_expired())
        
        return {
            "total_entries": total_entries,
            "active_entries": total_entries - expired_entries,
            "expired_entries": expired_entries,
            "cache_keys": list(self._cache.keys())
        }


# Global cache instance
ado_cache = AdoCache()