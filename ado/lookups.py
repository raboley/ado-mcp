"""
User-friendly lookup functions that hide ID complexity from users and LLMs.

These functions provide natural language interfaces to Azure DevOps operations,
automatically handling name-to-ID mapping with intelligent caching.
"""

import logging
from typing import Optional, Tuple, List

from opentelemetry import trace

from .cache import ado_cache
from .models import Project, Pipeline, FailureSummary, PipelineRun, PipelineOutcome

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class AdoLookups:
    """
    High-level lookup functions that provide name-based access to Azure DevOps.
    
    These functions automatically handle:
    - Name-to-ID mapping with fuzzy matching
    - Intelligent caching to minimize API calls
    - Error handling and fallbacks
    """
    
    def __init__(self, client):
        """Initialize with reference to the AdoClient."""
        self.client = client
    
    # Project lookups
    def ensure_projects_cached(self) -> List[Project]:
        """Ensure projects are cached, fetching if needed."""
        with tracer.start_as_current_span("ensure_projects_cached") as span:
            projects = ado_cache.get_projects()
            if projects is None:
                span.set_attribute("cache.source", "api")
                logger.info("Projects not cached, fetching from API...")
                projects = self.client.list_projects()
                ado_cache.set_projects(projects)
            else:
                span.set_attribute("cache.source", "cache")
                logger.info("Projects loaded from cache")
            
            span.set_attribute("projects.count", len(projects))
            return projects
    
    def find_project(self, name: str) -> Optional[Project]:
        """
        Find a project by name with intelligent caching and fuzzy matching.
        
        Args:
            name: Project name (fuzzy matching enabled)
            
        Returns:
            Project object if found, None otherwise
        """
        self.ensure_projects_cached()
        return ado_cache.find_project_by_name(name)
    
    def get_project_id(self, name: str) -> Optional[str]:
        """Get project ID by name."""
        project = self.find_project(name)
        return project.id if project else None
    
    # Pipeline lookups
    def ensure_pipelines_cached(self, project_id: str) -> List[Pipeline]:
        """Ensure pipelines are cached for a project, fetching if needed."""
        with tracer.start_as_current_span("ensure_pipelines_cached") as span:
            span.set_attribute("project_id", project_id)
            pipelines = ado_cache.get_pipelines(project_id)
            if pipelines is None:
                span.set_attribute("cache.source", "api")
                logger.info(f"Pipelines not cached for project {project_id}, fetching from API...")
                pipelines = self.client.list_pipelines(project_id)
                ado_cache.set_pipelines(project_id, pipelines)
            else:
                span.set_attribute("cache.source", "cache")
                logger.info(f"Pipelines loaded from cache for project {project_id}")
            
            span.set_attribute("pipelines.count", len(pipelines))
            return pipelines
    
    def find_pipeline(self, project_name: str, pipeline_name: str) -> Optional[Tuple[Project, Pipeline]]:
        """
        Find a pipeline by project name and pipeline name.
        
        Args:
            project_name: Project name (fuzzy matching enabled)
            pipeline_name: Pipeline name (fuzzy matching enabled)
            
        Returns:
            Tuple of (Project, Pipeline) if found, None otherwise
        """
        # Find project first
        project = self.find_project(project_name)
        if not project:
            logger.warning(f"Project '{project_name}' not found")
            return None
        
        # Ensure pipelines are cached for this project
        self.ensure_pipelines_cached(project.id)
        
        # Find pipeline
        pipeline = ado_cache.find_pipeline_by_name(project.id, pipeline_name)
        if not pipeline:
            logger.warning(f"Pipeline '{pipeline_name}' not found in project '{project.name}'")
            return None
        
        return (project, pipeline)
    
    def get_pipeline_ids(self, project_name: str, pipeline_name: str) -> Optional[Tuple[str, int]]:
        """
        Get project ID and pipeline ID by names.
        
        Returns:
            Tuple of (project_id, pipeline_id) if found, None otherwise
        """
        result = self.find_pipeline(project_name, pipeline_name)
        if result:
            project, pipeline = result
            return (project.id, pipeline.id)
        return None
    
    # High-level operations using names
    def run_pipeline_by_name(self, project_name: str, pipeline_name: str) -> Optional[PipelineRun]:
        """
        Run a pipeline by project and pipeline names.
        
        Args:
            project_name: Project name
            pipeline_name: Pipeline name
            
        Returns:
            PipelineRun object if successful, None otherwise
        """
        ids = self.get_pipeline_ids(project_name, pipeline_name)
        if not ids:
            return None
        
        project_id, pipeline_id = ids
        logger.info(f"Running pipeline '{pipeline_name}' in project '{project_name}'")
        return self.client.run_pipeline(project_id, pipeline_id)
    
    def get_pipeline_failure_summary_by_name(
        self, 
        project_name: str, 
        pipeline_name: str, 
        run_id: int, 
        max_lines: int = 100
    ) -> Optional[FailureSummary]:
        """
        Get pipeline failure summary by names.
        
        Args:
            project_name: Project name
            pipeline_name: Pipeline name  
            run_id: Pipeline run ID
            max_lines: Maximum log lines to return
            
        Returns:
            FailureSummary if found, None otherwise
        """
        ids = self.get_pipeline_ids(project_name, pipeline_name)
        if not ids:
            return None
        
        project_id, pipeline_id = ids
        return self.client.get_pipeline_failure_summary(project_id, pipeline_id, run_id, max_lines)
    
    def run_pipeline_and_get_outcome_by_name(
        self,
        project_name: str,
        pipeline_name: str,
        timeout_seconds: int = 300,
        max_lines: int = 100
    ) -> Optional[PipelineOutcome]:
        """
        Run a pipeline by name and wait for outcome.
        
        Args:
            project_name: Project name
            pipeline_name: Pipeline name
            timeout_seconds: Max wait time
            max_lines: Maximum log lines to return
            
        Returns:
            PipelineOutcome if successful, None otherwise
        """
        ids = self.get_pipeline_ids(project_name, pipeline_name)
        if not ids:
            return None
        
        project_id, pipeline_id = ids
        logger.info(f"Running pipeline '{pipeline_name}' in project '{project_name}' and waiting for outcome")
        return self.client.run_pipeline_and_get_outcome(project_id, pipeline_id, timeout_seconds, max_lines)
    
    # Utility functions
    def list_available_projects(self) -> List[str]:
        """Get list of available project names."""
        projects = self.ensure_projects_cached()
        return [project.name for project in projects]
    
    def list_available_pipelines(self, project_name: str) -> List[str]:
        """Get list of available pipeline names for a project."""
        project = self.find_project(project_name)
        if not project:
            return []
        
        pipelines = self.ensure_pipelines_cached(project.id)
        return [pipeline.name for pipeline in pipelines]
    
    def suggest_similar_projects(self, name: str, limit: int = 3) -> List[str]:
        """Get similar project names for typo suggestions."""
        from difflib import get_close_matches
        projects = self.ensure_projects_cached()
        project_names = [p.name for p in projects]
        return get_close_matches(name, project_names, n=limit, cutoff=0.4)
    
    def suggest_similar_pipelines(self, project_name: str, pipeline_name: str, limit: int = 3) -> List[str]:
        """Get similar pipeline names for typo suggestions."""
        from difflib import get_close_matches
        project = self.find_project(project_name)
        if not project:
            return []
        
        pipelines = self.ensure_pipelines_cached(project.id)
        pipeline_names = [p.name for p in pipelines]
        return get_close_matches(pipeline_name, pipeline_names, n=limit, cutoff=0.4)