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

from opentelemetry import trace, metrics
from opentelemetry.trace import Status, StatusCode

from .models import Project, Pipeline
from .work_items.models import WorkItemType, ClassificationNode

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)


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

    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []  # For LRU tracking
        self.max_size = max_size

        # TTL settings (in seconds)
        self.PROJECT_TTL = 15 * 60  # 15 minutes - projects rarely change
        self.PIPELINE_TTL = 10 * 60  # 10 minutes - pipelines change occasionally
        self.SERVICE_CONN_TTL = 30 * 60  # 30 minutes - very stable
        self.RUN_TTL = 3 * 60  # 3 minutes - runs are dynamic
        self.WORK_ITEM_TYPE_TTL = 60 * 60  # 1 hour - work item types are very stable
        self.CLASSIFICATION_TTL = 60 * 60  # 1 hour - area/iteration paths rarely change

        # Initialize metrics
        self._cache_hit_counter = meter.create_counter(
            name="ado_cache_hits", description="Number of cache hits", unit="1"
        )

        self._cache_miss_counter = meter.create_counter(
            name="ado_cache_misses", description="Number of cache misses", unit="1"
        )

        self._cache_eviction_counter = meter.create_counter(
            name="ado_cache_evictions",
            description="Number of expired cache entries evicted",
            unit="1",
        )

        self._cache_size_gauge = meter.create_up_down_counter(
            name="ado_cache_size", description="Current size of the cache", unit="1"
        )

    def _get_cache_key(self, *parts: str) -> str:
        """Generate a cache key from parts."""
        return ":".join(str(part) for part in parts)

    def _is_valid(self, key: str) -> bool:
        """Check if a cache entry exists and is not expired."""
        entry = self._cache.get(key)
        return entry is not None and not entry.is_expired()

    def _set(self, key: str, data: Any, ttl_seconds: int) -> None:
        """Set a cache entry with TTL and LRU eviction."""
        # Extract cache type from key for metrics labeling
        cache_type = key.split(":")[0] if ":" in key else "unknown"

        # Check if we're replacing an existing entry
        is_new = key not in self._cache

        # Update access order for LRU
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

        # Set the cache entry
        expires_at = time.time() + ttl_seconds
        self._cache[key] = CacheEntry(data=data, expires_at=expires_at)

        # Update cache size metric only for new entries
        if is_new:
            self._cache_size_gauge.add(1, {"cache_type": cache_type})

        # Enforce size limit with LRU eviction
        self._enforce_size_limit()

        logger.debug(f"Cached {key} for {ttl_seconds}s")

    def _get(self, key: str) -> Optional[Any]:
        """Get a cache entry if it exists and is valid."""
        with tracer.start_as_current_span("cache_get") as span:
            span.set_attribute("cache.key", key)
            # Extract cache type from key for metrics labeling
            cache_type = key.split(":")[0] if ":" in key else "unknown"

            if self._is_valid(key):
                span.set_attribute("cache.hit", True)
                self._cache_hit_counter.add(1, {"cache_type": cache_type})
                logger.debug(f"Cache hit for key: {key}")
                
                # Update LRU order on access
                if key in self._access_order:
                    self._access_order.remove(key)
                    self._access_order.append(key)
                
                return self._cache[key].data
            elif key in self._cache:
                # Remove expired entry
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                self._cache_size_gauge.add(-1, {"cache_type": cache_type})
                self._cache_eviction_counter.add(1, {"cache_type": cache_type, "reason": "expired"})
                logger.debug(f"Removed expired cache entry: {key}")
                span.set_attribute("cache.hit", False)
                span.set_attribute("cache.expired", True)
                self._cache_miss_counter.add(1, {"cache_type": cache_type, "reason": "expired"})
            else:
                span.set_attribute("cache.hit", False)
                span.set_attribute("cache.expired", False)
                self._cache_miss_counter.add(1, {"cache_type": cache_type, "reason": "not_found"})
                logger.debug(f"Cache miss for key: {key}")
            return None

    def _enforce_size_limit(self) -> None:
        """Enforce cache size limit using LRU eviction."""
        while len(self._cache) > self.max_size:
            # Remove least recently used entry
            if not self._access_order:
                break
            
            lru_key = self._access_order.pop(0)
            if lru_key in self._cache:
                cache_type = lru_key.split(":")[0] if ":" in lru_key else "unknown"
                del self._cache[lru_key]
                self._cache_size_gauge.add(-1, {"cache_type": cache_type})
                self._cache_eviction_counter.add(1, {"cache_type": cache_type, "reason": "lru_eviction"})
                logger.debug(f"Evicted LRU cache entry: {lru_key}")

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

    def find_pipeline_by_name(
        self, project_id: str, name: str, fuzzy: bool = True
    ) -> Optional[Pipeline]:
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

    def find_pipeline_by_name_and_project(
        self, project_name: str, pipeline_name: str
    ) -> Optional[Tuple[str, int]]:
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

    # Work item types caching
    def get_work_item_types(self, project_id: str) -> Optional[List[WorkItemType]]:
        """Get cached work item types for a project."""
        key = f"work_item_types:{project_id}"
        return self._get(key)

    def set_work_item_types(self, project_id: str, work_item_types: List[WorkItemType]) -> None:
        """Cache work item types for a project."""
        key = f"work_item_types:{project_id}"
        self._set(key, work_item_types, self.WORK_ITEM_TYPE_TTL)

        # Create name mapping for fast lookups
        name_map = {wit.name.lower(): wit for wit in work_item_types}
        name_key = f"work_item_types:{project_id}:name_map"
        self._set(name_key, name_map, self.WORK_ITEM_TYPE_TTL)

        logger.info(f"Cached {len(work_item_types)} work item types for project {project_id}")

    def find_work_item_type_by_name(
        self, project_id: str, name: str, fuzzy: bool = True
    ) -> Optional[WorkItemType]:
        """
        Find a work item type by name within a project.

        Args:
            project_id: Project ID to search within
            name: Work item type name to search for
            fuzzy: Enable fuzzy matching

        Returns:
            WorkItemType object if found, None otherwise
        """
        work_item_types = self.get_work_item_types(project_id)
        if not work_item_types:
            return None

        name_lower = name.lower()

        # Exact match first
        for wit in work_item_types:
            if wit.name.lower() == name_lower:
                return wit

        # Fuzzy matching
        if fuzzy:
            wit_names = [wit.name for wit in work_item_types]
            matches = get_close_matches(name, wit_names, n=1, cutoff=0.6)
            if matches:
                match_name = matches[0]
                for wit in work_item_types:
                    if wit.name == match_name:
                        logger.info(f"Fuzzy matched '{name}' to work item type '{match_name}'")
                        return wit

        return None

    # Classification nodes caching (area and iteration paths)
    def get_area_paths(self, project_id: str) -> Optional[List[ClassificationNode]]:
        """Get cached area paths for a project."""
        key = f"area_paths:{project_id}"
        return self._get(key)

    def set_area_paths(self, project_id: str, area_paths: List[ClassificationNode]) -> None:
        """Cache area paths for a project."""
        key = f"area_paths:{project_id}"
        self._set(key, area_paths, self.CLASSIFICATION_TTL)
        logger.info(f"Cached area paths for project {project_id}")

    def get_iteration_paths(self, project_id: str) -> Optional[List[ClassificationNode]]:
        """Get cached iteration paths for a project."""
        key = f"iteration_paths:{project_id}"
        return self._get(key)

    def set_iteration_paths(
        self, project_id: str, iteration_paths: List[ClassificationNode]
    ) -> None:
        """Cache iteration paths for a project."""
        key = f"iteration_paths:{project_id}"
        self._set(key, iteration_paths, self.CLASSIFICATION_TTL)
        logger.info(f"Cached iteration paths for project {project_id}")

    # Cache management
    def clear_expired(self) -> int:
        """Remove all expired cache entries. Returns number of entries removed."""
        before_count = len(self._cache)
        expired_keys = [key for key, entry in self._cache.items() if entry.is_expired()]

        for key in expired_keys:
            cache_type = key.split(":")[0] if ":" in key else "unknown"
            del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)
            self._cache_size_gauge.add(-1, {"cache_type": cache_type})
            self._cache_eviction_counter.add(
                1, {"cache_type": cache_type, "reason": "manual_clear"}
            )

        removed_count = len(expired_keys)
        if removed_count > 0:
            logger.info(f"Removed {removed_count} expired cache entries")

        return removed_count

    def clear_all(self) -> None:
        """Clear all cache entries."""
        # Count entries by type before clearing
        type_counts = {}
        for key in self._cache:
            cache_type = key.split(":")[0] if ":" in key else "unknown"
            type_counts[cache_type] = type_counts.get(cache_type, 0) + 1

        # Update metrics for each type
        for cache_type, count in type_counts.items():
            self._cache_size_gauge.add(-count, {"cache_type": cache_type})
            self._cache_eviction_counter.add(
                count, {"cache_type": cache_type, "reason": "manual_clear_all"}
            )

        self._cache.clear()
        self._access_order.clear()
        logger.info("Cleared all cache entries")

    def invalidate_pipelines(self, project_id: str) -> None:
        """Invalidate pipeline cache for a specific project."""
        key = f"pipelines:{project_id}"
        name_map_key = f"pipeline_names:{project_id}"
        
        if key in self._cache:
            del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)
            self._cache_size_gauge.add(-1, {"cache_type": "pipelines"})
            self._cache_eviction_counter.add(1, {"cache_type": "pipelines", "reason": "manual_invalidate"})
            logger.info(f"Invalidated pipeline cache for project {project_id}")
        
        if name_map_key in self._cache:
            del self._cache[name_map_key]
            if name_map_key in self._access_order:
                self._access_order.remove(name_map_key)
            self._cache_size_gauge.add(-1, {"cache_type": "pipeline_names"})
            self._cache_eviction_counter.add(1, {"cache_type": "pipeline_names", "reason": "manual_invalidate"})

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics including hit/miss rates."""
        total_entries = len(self._cache)
        expired_entries = sum(1 for entry in self._cache.values() if entry.is_expired())

        # Group cache entries by type
        entries_by_type = {}
        for key in self._cache:
            cache_type = key.split(":")[0] if ":" in key else "unknown"
            entries_by_type[cache_type] = entries_by_type.get(cache_type, 0) + 1

        return {
            "total_entries": total_entries,
            "active_entries": total_entries - expired_entries,
            "expired_entries": expired_entries,
            "entries_by_type": entries_by_type,
            "cache_keys": list(self._cache.keys()),
            # Note: Hit/miss rates are tracked via OpenTelemetry metrics
            # and should be queried from the metrics backend
            "metrics_info": "Hit/miss rates are tracked via OpenTelemetry metrics",
        }


# Global cache instance
ado_cache = AdoCache()
