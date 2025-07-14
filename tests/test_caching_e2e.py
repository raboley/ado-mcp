"""
End-to-end tests for caching functionality using OpenTelemetry observability.

These tests verify cache behavior through telemetry spans rather than mocks,
testing the system as a black box like real users would experience it.
"""

import os
import time
import pytest
from typing import List, Dict, Any
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from ado.client import AdoClient
from ado.cache import ado_cache
from tests.ado.test_client import requires_ado_creds


class SpanAnalyzer:
    """Helper class to analyze OpenTelemetry spans for testing."""
    
    def __init__(self, spans: List[Any]):
        self.spans = spans
    
    def find_spans_by_name(self, name: str) -> List[Any]:
        """Find all spans with the given name."""
        return [span for span in self.spans if span.name == name]
    
    def get_span_attributes(self, span: Any) -> Dict[str, Any]:
        """Get all attributes from a span."""
        return dict(span.attributes or {})
    
    def count_cache_hits(self) -> int:
        """Count the number of cache hits in the spans."""
        cache_get_spans = self.find_spans_by_name("cache_get")
        return sum(1 for span in cache_get_spans 
                  if self.get_span_attributes(span).get("cache.hit") is True)
    
    def count_cache_misses(self) -> int:
        """Count the number of cache misses in the spans."""
        cache_get_spans = self.find_spans_by_name("cache_get")
        return sum(1 for span in cache_get_spans 
                  if self.get_span_attributes(span).get("cache.hit") is False)
    
    def count_api_calls(self) -> int:
        """Count the number of actual API calls made."""
        # Count spans that indicate API calls
        api_spans = self.find_spans_by_name("ado_list_projects")
        return len(api_spans)
    
    def was_data_fetched_from_cache(self, operation: str) -> bool:
        """Check if a specific operation used cached data."""
        ensure_spans = self.find_spans_by_name(f"ensure_{operation}_cached")
        if ensure_spans:
            latest_span = ensure_spans[-1]
            attrs = self.get_span_attributes(latest_span)
            return attrs.get("cache.source") == "cache"
        return False
    
    def was_data_fetched_from_api(self, operation: str) -> bool:
        """Check if a specific operation fetched from API."""
        ensure_spans = self.find_spans_by_name(f"ensure_{operation}_cached")
        if ensure_spans:
            latest_span = ensure_spans[-1]
            attrs = self.get_span_attributes(latest_span)
            return attrs.get("cache.source") == "api"
        return False


@pytest.fixture
def telemetry_setup():
    """Set up OpenTelemetry for testing with in-memory span export."""
    # Create an in-memory span exporter
    memory_exporter = InMemorySpanExporter()
    
    # Get current tracer provider or create new one
    current_provider = trace.get_tracer_provider()
    if not hasattr(current_provider, 'add_span_processor'):
        # Only create new provider if none exists
        provider = TracerProvider()
        trace.set_tracer_provider(provider)
        current_provider = provider
    
    # Add our processor
    processor = SimpleSpanProcessor(memory_exporter)
    current_provider.add_span_processor(processor)
    
    yield memory_exporter
    
    # Clean up
    memory_exporter.clear()


@pytest.fixture
def fresh_cache():
    """Ensure cache is cleared before each test."""
    ado_cache.clear_all()
    yield
    ado_cache.clear_all()


@requires_ado_creds
class TestCachingE2E:
    """End-to-end caching tests using real API calls and telemetry."""
    
    def test_project_list_caching_behavior(self, telemetry_setup, fresh_cache):
        """Test that first call hits API, second call uses cache."""
        memory_exporter = telemetry_setup
        
        client = AdoClient(
            organization_url=os.environ["ADO_ORGANIZATION_URL"],
            pat=os.environ["AZURE_DEVOPS_EXT_PAT"]
        )
        
        # First call - should hit API
        projects1 = client.list_available_projects()
        
        # Get spans after first call
        spans_after_first = memory_exporter.get_finished_spans()
        analyzer1 = SpanAnalyzer(spans_after_first)
        
        # Verify first call went to API
        assert analyzer1.was_data_fetched_from_api("projects")
        assert analyzer1.count_api_calls() == 1
        assert analyzer1.count_cache_misses() > 0
        
        # Clear spans for clean second measurement
        memory_exporter.clear()
        
        # Second call - should use cache
        projects2 = client.list_available_projects()
        
        # Get spans after second call
        spans_after_second = memory_exporter.get_finished_spans()
        analyzer2 = SpanAnalyzer(spans_after_second)
        
        # Verify second call used cache
        assert analyzer2.was_data_fetched_from_cache("projects")
        assert analyzer2.count_api_calls() == 0  # No new API calls
        assert analyzer2.count_cache_hits() > 0
        
        # Verify data is consistent
        assert projects1 == projects2
    
    def test_pipeline_caching_with_name_lookup(self, telemetry_setup, fresh_cache):
        """Test pipeline lookups cache properly when using name-based functions."""
        memory_exporter = telemetry_setup
        
        client = AdoClient(
            organization_url=os.environ["ADO_ORGANIZATION_URL"],
            pat=os.environ["AZURE_DEVOPS_EXT_PAT"]
        )
        
        # Get available projects first
        projects = client.list_available_projects()
        if not projects:
            pytest.skip("No projects available for testing")
        
        project_name = projects[0]
        
        # Clear spans to focus on pipeline operations
        memory_exporter.clear()
        
        # First pipeline lookup - should hit API
        pipelines1 = client.list_available_pipelines(project_name)
        
        spans_after_first = memory_exporter.get_finished_spans()
        analyzer1 = SpanAnalyzer(spans_after_first)
        
        # Should have made an API call for pipelines
        # (projects should already be cached from previous call)
        api_calls = len([s for s in spans_after_first 
                        if "ado_" in s.name and "pipelines" in str(s.attributes)])
        assert api_calls > 0
        
        memory_exporter.clear()
        
        # Second pipeline lookup - should use cache
        pipelines2 = client.list_available_pipelines(project_name)
        
        spans_after_second = memory_exporter.get_finished_spans()
        analyzer2 = SpanAnalyzer(spans_after_second)
        
        # Should not make new API calls
        api_calls_second = len([s for s in spans_after_second 
                               if "ado_" in s.name and "pipelines" in str(s.attributes)])
        assert api_calls_second == 0
        
        # Data should be consistent
        assert pipelines1 == pipelines2
    
    def test_cache_expiration_behavior(self, telemetry_setup, fresh_cache):
        """Test that cache properly expires and refetches data."""
        memory_exporter = telemetry_setup
        
        # Temporarily reduce cache TTL for testing
        original_ttl = ado_cache.PROJECT_TTL
        ado_cache.PROJECT_TTL = 2  # 2 seconds for testing
        
        try:
            client = AdoClient(
                organization_url=os.environ["ADO_ORGANIZATION_URL"],
                pat=os.environ["AZURE_DEVOPS_EXT_PAT"]
            )
            
            # First call
            projects1 = client.list_available_projects()
            memory_exporter.clear()
            
            # Second call immediately - should use cache
            projects2 = client.list_available_projects()
            analyzer_cached = SpanAnalyzer(memory_exporter.get_finished_spans())
            assert analyzer_cached.was_data_fetched_from_cache("projects")
            
            # Wait for cache to expire
            time.sleep(2.5)
            memory_exporter.clear()
            
            # Third call after expiration - should hit API again
            projects3 = client.list_available_projects()
            analyzer_expired = SpanAnalyzer(memory_exporter.get_finished_spans())
            assert analyzer_expired.was_data_fetched_from_api("projects")
            
            # Data should still be consistent
            assert projects1 == projects3
            
        finally:
            # Restore original TTL
            ado_cache.PROJECT_TTL = original_ttl
    
    def test_fuzzy_matching_performance(self, telemetry_setup, fresh_cache):
        """Test that fuzzy name matching uses cache effectively."""
        memory_exporter = telemetry_setup
        
        client = AdoClient(
            organization_url=os.environ["ADO_ORGANIZATION_URL"],
            pat=os.environ["AZURE_DEVOPS_EXT_PAT"]
        )
        
        # Prime the cache
        projects = client.list_available_projects()
        if not projects:
            pytest.skip("No projects available for testing")
        
        project_name = projects[0]
        memory_exporter.clear()
        
        # Try various fuzzy matches - all should use cache
        test_names = [
            project_name.lower(),  # Case variation
            project_name.upper(),  # Case variation
            project_name[:3],      # Prefix (if long enough)
        ]
        
        for test_name in test_names:
            if len(project_name) > 3 or test_name != project_name[:3]:
                project = client.find_project_by_name(test_name)
                
                # Check that no API calls were made
                current_spans = memory_exporter.get_finished_spans()
                api_calls = len([s for s in current_spans if "ado_list_projects" in s.name])
                assert api_calls == 0, f"Unexpected API call for fuzzy match '{test_name}'"
                
                memory_exporter.clear()
    
    def test_name_based_pipeline_execution(self, telemetry_setup, fresh_cache):
        """Test that name-based pipeline operations use cache effectively."""
        memory_exporter = telemetry_setup
        
        client = AdoClient(
            organization_url=os.environ["ADO_ORGANIZATION_URL"],
            pat=os.environ["AZURE_DEVOPS_EXT_PAT"]
        )
        
        # Find a project with pipelines
        projects = client.list_available_projects()
        pipeline_found = False
        
        for project_name in projects:
            pipelines = client.list_available_pipelines(project_name)
            if pipelines:
                pipeline_name = pipelines[0]
                pipeline_found = True
                break
        
        if not pipeline_found:
            pytest.skip("No pipelines found in any project")
        
        memory_exporter.clear()
        
        # Find pipeline by name - should use cached data
        result = client.find_pipeline_by_name(project_name, pipeline_name)
        assert result is not None
        
        # Analyze spans
        spans = memory_exporter.get_finished_spans()
        analyzer = SpanAnalyzer(spans)
        
        # Should have cache hits, no API calls
        assert analyzer.count_cache_hits() > 0
        api_spans = [s for s in spans if s.name.startswith("ado_")]
        assert len(api_spans) == 0, "Should not make API calls when data is cached"
    
    def test_cache_statistics_accuracy(self, telemetry_setup, fresh_cache):
        """Test that cache statistics match telemetry observations."""
        memory_exporter = telemetry_setup
        
        client = AdoClient(
            organization_url=os.environ["ADO_ORGANIZATION_URL"],
            pat=os.environ["AZURE_DEVOPS_EXT_PAT"]
        )
        
        # Perform several operations
        projects = client.list_available_projects()
        projects_again = client.list_available_projects()  # Should hit cache
        
        if projects:
            client.find_project_by_name(projects[0])  # Should hit cache
        
        # Get cache stats
        stats = ado_cache.get_stats()
        
        # Verify cache has entries
        assert stats["total_entries"] > 0
        assert stats["active_entries"] > 0
        
        # Analyze telemetry
        spans = memory_exporter.get_finished_spans()
        analyzer = SpanAnalyzer(spans)
        
        # Cache hits should be recorded in telemetry
        assert analyzer.count_cache_hits() > 0
        assert analyzer.count_cache_misses() > 0  # At least one miss for initial load