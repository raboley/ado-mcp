
import pytest
import time

from ado.cache import AdoCache, ado_cache
from ado.models import Project, Pipeline
from tests.ado.test_client import requires_ado_creds


class TestAdoCache:
    
    def setup_method(self):
        self.cache = AdoCache()
    
    def test_cache_basic_operations(self):
        test_data = {"key": "value"}
        self.cache._set("test", test_data, 60)
        
        result = self.cache._get("test")
        assert result == test_data, f"Expected {test_data} but got {result}"
    
    def test_cache_expiration(self):
        test_data = {"key": "value"}
        self.cache._set("test", test_data, 1)
        
        retrieved = self.cache._get("test")
        assert retrieved == test_data, f"Cache entry should be available immediately. Expected {test_data} but got {retrieved}"
        
        time.sleep(1.1)
        expired_result = self.cache._get("test")
        assert expired_result is None, f"Cache entry should expire after TTL but got {expired_result}"
    
    def test_project_caching(self):
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
        
        cached_projects = self.cache.get_projects()
        assert len(cached_projects) == 2, f"Expected 2 projects but got {len(cached_projects)}"
        assert cached_projects[0].name == "ado-mcp", f"Expected first project name 'ado-mcp' but got '{cached_projects[0].name}'"
        
        project = self.cache.find_project_by_name("ado-mcp")
        assert project is not None, "Should find project by exact name but got None"
        assert project.id == "proj1", f"Expected project ID 'proj1' but got '{project.id}'"
        
        project = self.cache.find_project_by_name("ADO-MCP")
        assert project is not None, "Should find project by case insensitive name but got None"
        assert project.id == "proj1", f"Expected project ID 'proj1' but got '{project.id}'"
        
        project = self.cache.find_project_by_name("Learning")
        assert project is not None, "Should find Learning project but got None"
        assert project.id == "proj2", f"Expected project ID 'proj2' but got '{project.id}'"
        
        project = self.cache.find_project_by_name("NonExistent")
        assert project is None, f"Should not find non-existent project but got {project}"
    
    def test_pipeline_caching(self):
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
        
        cached_pipelines = self.cache.get_pipelines(project_id)
        assert len(cached_pipelines) == 2, f"Expected 2 pipelines, got {len(cached_pipelines)}"
        
        pipeline = self.cache.find_pipeline_by_name(project_id, "CI Pipeline")
        assert pipeline is not None, "Should find pipeline by exact name"
        assert pipeline.id == 1, f"Expected pipeline ID 1, got {pipeline.id}"
        
        pipeline = self.cache.find_pipeline_by_name(project_id, "CI Pipe")
        assert pipeline is not None, "Should find pipeline by partial name fuzzy matching"
        assert pipeline.id == 1, f"Expected pipeline ID 1, got {pipeline.id}"
        
        pipeline = self.cache.find_pipeline_by_name(project_id, "NonExistent")
        assert pipeline is None, "Should not find non-existent pipeline"
    
    def test_cache_stats(self):
        stats = self.cache.get_stats()
        assert stats["total_entries"] == 0, f"Expected 0 total entries, got {stats['total_entries']}"
        assert stats["active_entries"] == 0, f"Expected 0 active entries, got {stats['active_entries']}"
        
        self.cache._set("test1", "data1", 60)
        self.cache._set("test2", "data2", 1)
        
        stats = self.cache.get_stats()
        assert stats["total_entries"] == 2, f"Expected 2 total entries, got {stats['total_entries']}"
        assert stats["active_entries"] == 2, f"Expected 2 active entries, got {stats['active_entries']}"
        
        time.sleep(1.1)
        stats = self.cache.get_stats()
        assert stats["total_entries"] == 2, f"Expected 2 total entries after expiration, got {stats['total_entries']}"
        assert stats["expired_entries"] == 1, f"Expected 1 expired entry, got {stats['expired_entries']}"
    
    def test_clear_expired(self):
        self.cache._set("test1", "data1", 60)
        self.cache._set("test2", "data2", 1)
        
        assert self.cache.get_stats()["total_entries"] == 2, "Should have 2 entries before expiration"
        
        time.sleep(1.1)
        removed_count = self.cache.clear_expired()
        assert removed_count == 1, f"Expected to remove 1 expired entry, removed {removed_count}"
        assert self.cache.get_stats()["total_entries"] == 1, f"Expected 1 entry after cleanup, got {self.cache.get_stats()['total_entries']}"


@requires_ado_creds
class TestCachingIntegration:
    
    def test_name_based_project_lookup(self):
        from ado.client import AdoClient
        import os
        
        client = AdoClient(
            organization_url=os.environ["ADO_ORGANIZATION_URL"],
            pat=os.environ["AZURE_DEVOPS_EXT_PAT"]
        )
        
        ado_cache.clear_all()
        
        projects = client.list_available_projects()
        if projects:
            first_project_name = projects[0]
            
            project = client.find_project_by_name(first_project_name)
            assert project is not None, f"Should find project '{first_project_name}'"
            assert project.name == first_project_name, f"Expected project name '{first_project_name}', got '{project.name}'"
            
            project2 = client.find_project_by_name(first_project_name)
            assert project2 is not None, f"Cached lookup should find project '{first_project_name}'"
            assert project2.id == project.id, f"Cached project should have same ID {project.id}, got {project2.id}"
    
    def test_name_based_pipeline_lookup(self):
        from ado.client import AdoClient
        import os
        
        client = AdoClient(
            organization_url=os.environ["ADO_ORGANIZATION_URL"],
            pat=os.environ["AZURE_DEVOPS_EXT_PAT"]
        )
        
        ado_cache.clear_all()
        
        projects = client.list_available_projects()
        if projects:
            for project_name in projects:
                pipelines = client.list_available_pipelines(project_name)
                if pipelines:
                    pipeline_name = pipelines[0]
                    
                    result = client.find_pipeline_by_name(project_name, pipeline_name)
                    assert result is not None, f"Should find pipeline '{pipeline_name}' in project '{project_name}'"
                    
                    project, pipeline = result
                    assert project.name == project_name, f"Expected project name '{project_name}', got '{project.name}'"
                    assert pipeline.name == pipeline_name, f"Expected pipeline name '{pipeline_name}', got '{pipeline.name}'"
                    break
    
    def test_cache_performance(self):
        from ado.client import AdoClient
        import os
        import time
        
        client = AdoClient(
            organization_url=os.environ["ADO_ORGANIZATION_URL"],
            pat=os.environ["AZURE_DEVOPS_EXT_PAT"]
        )
        
        ado_cache.clear_all()
        
        start_time = time.time()
        projects1 = client.list_available_projects()
        first_call_time = time.time() - start_time
        
        start_time = time.time()
        projects2 = client.list_available_projects()
        second_call_time = time.time() - start_time
        
        assert projects1 == projects2, "Cached and uncached results should be identical"
        
        assert second_call_time < first_call_time / 2, f"Cached call ({second_call_time:.3f}s) should be faster than uncached call ({first_call_time:.3f}s)"
    
    def test_fuzzy_matching_with_real_data(self):
        from ado.client import AdoClient
        import os
        
        client = AdoClient(
            organization_url=os.environ["ADO_ORGANIZATION_URL"],
            pat=os.environ["AZURE_DEVOPS_EXT_PAT"]
        )
        
        projects = client.list_available_projects()
        if projects:
            full_name = projects[0]
            if len(full_name) > 3:
                partial_name = full_name[:3]
                
                project = client.find_project_by_name(partial_name)
                if project:
                    assert partial_name.lower() in project.name.lower(), f"Fuzzy match should contain partial name '{partial_name}' in found project '{project.name}'"