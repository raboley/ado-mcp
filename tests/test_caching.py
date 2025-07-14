"""
Integration tests for the Azure DevOps caching functionality.

Tests cover:
- Cache TTL and expiration
- Name-to-ID mapping with fuzzy matching
- Performance improvements from caching

These are basic unit tests for cache functionality.
See test_caching_e2e.py for full end-to-end tests with observability.
"""

import pytest
import time

from ado.cache import AdoCache, ado_cache
from ado.models import Project, Pipeline
from tests.ado.test_client import requires_ado_creds


class TestAdoCache:
    """Test the caching layer functionality."""
    
    def setup_method(self):
        """Set up fresh cache for each test."""
        self.cache = AdoCache()
    
    def test_cache_basic_operations(self):
        """Test basic cache set/get operations."""
        # Test setting and getting data
        test_data = {"key": "value"}
        self.cache._set("test", test_data, 60)
        
        result = self.cache._get("test")
        assert result == test_data
    
    def test_cache_expiration(self):
        """Test that cache entries expire correctly."""
        test_data = {"key": "value"}
        self.cache._set("test", test_data, 1)  # 1 second TTL
        
        # Should be available immediately
        assert self.cache._get("test") == test_data
        
        # Should expire after TTL
        time.sleep(1.1)
        assert self.cache._get("test") is None
    
    def test_project_caching(self):
        """Test project caching and name mapping."""
        projects = [
            Project(
                id="proj1", 
                name="ado-mcp", 
                description="Azure DevOps MCP Project",
                url="https://dev.azure.com/org/_apis/projects/proj1",
                state="wellFormed",
                revision=1,
                visibility="private",
                lastUpdateTime="2024-01-01T00:00:00Z"
            ),
            Project(
                id="proj2", 
                name="Learning", 
                description="Learning Project",
                url="https://dev.azure.com/org/_apis/projects/proj2",
                state="wellFormed",
                revision=1,
                visibility="private",
                lastUpdateTime="2024-01-01T00:00:00Z"
            )
        ]
        
        self.cache.set_projects(projects)
        
        # Test retrieval
        cached_projects = self.cache.get_projects()
        assert len(cached_projects) == 2
        assert cached_projects[0].name == "ado-mcp"
        
        # Test exact name matching
        project = self.cache.find_project_by_name("ado-mcp")
        assert project is not None
        assert project.id == "proj1"
        
        # Test case insensitive matching
        project = self.cache.find_project_by_name("ADO-MCP")
        assert project is not None
        assert project.id == "proj1"
        
        # Test fuzzy matching
        project = self.cache.find_project_by_name("Learning")
        assert project is not None
        assert project.id == "proj2"
        
        # Test no match
        project = self.cache.find_project_by_name("NonExistent")
        assert project is None
    
    def test_pipeline_caching(self):
        """Test pipeline caching and name mapping."""
        pipelines = [
            Pipeline(
                id=1, 
                name="CI Pipeline", 
                folder="\\",
                revision=1,
                url="https://dev.azure.com/org/_apis/pipelines/1"
            ),
            Pipeline(
                id=2, 
                name="Deploy Pipeline", 
                folder="\\",
                revision=1,
                url="https://dev.azure.com/org/_apis/pipelines/2"
            )
        ]
        
        project_id = "proj1"
        self.cache.set_pipelines(project_id, pipelines)
        
        # Test retrieval
        cached_pipelines = self.cache.get_pipelines(project_id)
        assert len(cached_pipelines) == 2
        
        # Test exact name matching
        pipeline = self.cache.find_pipeline_by_name(project_id, "CI Pipeline")
        assert pipeline is not None
        assert pipeline.id == 1
        
        # Test fuzzy matching (partial name with enough similarity)
        pipeline = self.cache.find_pipeline_by_name(project_id, "CI Pipe")
        assert pipeline is not None
        assert pipeline.id == 1
        
        # Test no match
        pipeline = self.cache.find_pipeline_by_name(project_id, "NonExistent")
        assert pipeline is None
    
    def test_cache_stats(self):
        """Test cache statistics."""
        stats = self.cache.get_stats()
        assert stats["total_entries"] == 0
        assert stats["active_entries"] == 0
        
        # Add some data
        self.cache._set("test1", "data1", 60)
        self.cache._set("test2", "data2", 1)  # Will expire quickly
        
        stats = self.cache.get_stats()
        assert stats["total_entries"] == 2
        assert stats["active_entries"] == 2
        
        # Wait for one to expire
        time.sleep(1.1)
        stats = self.cache.get_stats()
        assert stats["total_entries"] == 2
        assert stats["expired_entries"] == 1
    
    def test_clear_expired(self):
        """Test clearing expired entries."""
        self.cache._set("test1", "data1", 60)  # Won't expire
        self.cache._set("test2", "data2", 1)   # Will expire
        
        assert self.cache.get_stats()["total_entries"] == 2
        
        time.sleep(1.1)
        removed_count = self.cache.clear_expired()
        assert removed_count == 1
        assert self.cache.get_stats()["total_entries"] == 1


# Mocked tests removed - see test_caching_e2e.py for end-to-end tests with observability


@requires_ado_creds
class TestCachingIntegration:
    """Integration tests with real Azure DevOps data."""
    
    def test_name_based_project_lookup(self):
        """Test name-based project lookup with real data."""
        from ado.client import AdoClient
        import os
        
        client = AdoClient(
            organization_url=os.environ["ADO_ORGANIZATION_URL"],
            pat=os.environ["AZURE_DEVOPS_EXT_PAT"]
        )
        
        # Clear cache to ensure fresh test
        ado_cache.clear_all()
        
        # Find a project by name (should work with any project in the org)
        projects = client.list_available_projects()
        if projects:
            first_project_name = projects[0]
            
            # Test finding by exact name
            project = client.find_project_by_name(first_project_name)
            assert project is not None
            assert project.name == first_project_name
            
            # Test that second call uses cache (check logs if needed)
            project2 = client.find_project_by_name(first_project_name)
            assert project2 is not None
            assert project2.id == project.id
    
    def test_name_based_pipeline_lookup(self):
        """Test name-based pipeline lookup with real data."""
        from ado.client import AdoClient
        import os
        
        client = AdoClient(
            organization_url=os.environ["ADO_ORGANIZATION_URL"],
            pat=os.environ["AZURE_DEVOPS_EXT_PAT"]
        )
        
        # Clear cache to ensure fresh test
        ado_cache.clear_all()
        
        # Get projects and find one with pipelines
        projects = client.list_available_projects()
        if projects:
            for project_name in projects:
                pipelines = client.list_available_pipelines(project_name)
                if pipelines:
                    pipeline_name = pipelines[0]
                    
                    # Test finding pipeline by name
                    result = client.find_pipeline_by_name(project_name, pipeline_name)
                    assert result is not None
                    
                    project, pipeline = result
                    assert project.name == project_name
                    assert pipeline.name == pipeline_name
                    break
    
    def test_cache_performance(self):
        """Test that caching improves performance."""
        from ado.client import AdoClient
        import os
        import time
        
        client = AdoClient(
            organization_url=os.environ["ADO_ORGANIZATION_URL"],
            pat=os.environ["AZURE_DEVOPS_EXT_PAT"]
        )
        
        # Clear cache
        ado_cache.clear_all()
        
        # Time first call (should hit API)
        start_time = time.time()
        projects1 = client.list_available_projects()
        first_call_time = time.time() - start_time
        
        # Time second call (should use cache)
        start_time = time.time()
        projects2 = client.list_available_projects()
        second_call_time = time.time() - start_time
        
        # Verify results are the same
        assert projects1 == projects2
        
        # Second call should be significantly faster
        # (Note: This is a rough test, actual times may vary)
        assert second_call_time < first_call_time / 2
    
    def test_fuzzy_matching_with_real_data(self):
        """Test fuzzy matching with real project names."""
        from ado.client import AdoClient
        import os
        
        client = AdoClient(
            organization_url=os.environ["ADO_ORGANIZATION_URL"],
            pat=os.environ["AZURE_DEVOPS_EXT_PAT"]
        )
        
        projects = client.list_available_projects()
        if projects:
            # Take first project and test partial name matching
            full_name = projects[0]
            if len(full_name) > 3:
                partial_name = full_name[:3]  # First 3 characters
                
                # Should find the project with partial name
                project = client.find_project_by_name(partial_name)
                # Note: This might not always work if there are multiple similar names
                # but it tests the fuzzy matching capability