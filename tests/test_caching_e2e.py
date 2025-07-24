import os
import time
from typing import Any

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from ado.cache import ado_cache
from ado.client import AdoClient
from tests.ado.test_client import requires_ado_creds


class SpanAnalyzer:
    def __init__(self, spans: list[Any]):
        self.spans = spans

    def find_spans_by_name(self, name: str) -> list[Any]:
        return [span for span in self.spans if span.name == name]

    def get_span_attributes(self, span: Any) -> dict[str, Any]:
        return dict(span.attributes or {})

    def count_cache_hits(self) -> int:
        cache_get_spans = self.find_spans_by_name("cache_get")
        return sum(
            1 for span in cache_get_spans if self.get_span_attributes(span).get("cache.hit") is True
        )

    def count_cache_misses(self) -> int:
        cache_get_spans = self.find_spans_by_name("cache_get")
        return sum(
            1
            for span in cache_get_spans
            if self.get_span_attributes(span).get("cache.hit") is False
        )

    def count_api_calls(self) -> int:
        api_spans = self.find_spans_by_name("ado_list_projects")
        return len(api_spans)

    def was_data_fetched_from_cache(self, operation: str) -> bool:
        ensure_spans = self.find_spans_by_name(f"ensure_{operation}_cached")
        if ensure_spans:
            latest_span = ensure_spans[-1]
            attrs = self.get_span_attributes(latest_span)
            return attrs.get("cache.source") == "cache"
        return False

    def was_data_fetched_from_api(self, operation: str) -> bool:
        ensure_spans = self.find_spans_by_name(f"ensure_{operation}_cached")
        if ensure_spans:
            latest_span = ensure_spans[-1]
            attrs = self.get_span_attributes(latest_span)
            return attrs.get("cache.source") == "api"
        return False


@pytest.fixture
def telemetry_setup():
    memory_exporter = InMemorySpanExporter()

    current_provider = trace.get_tracer_provider()
    if not hasattr(current_provider, "add_span_processor"):
        provider = TracerProvider()
        trace.set_tracer_provider(provider)
        current_provider = provider

    processor = SimpleSpanProcessor(memory_exporter)
    current_provider.add_span_processor(processor)

    yield memory_exporter

    memory_exporter.clear()


@pytest.fixture
def fresh_cache():
    ado_cache.clear_all()
    yield
    ado_cache.clear_all()


@requires_ado_creds
class TestCachingE2E:
    def test_project_list_caching_behavior(self, telemetry_setup, fresh_cache):
        memory_exporter = telemetry_setup

        client = AdoClient(
            organization_url=os.environ["ADO_ORGANIZATION_URL"],
            pat=os.environ["AZURE_DEVOPS_EXT_PAT"],
        )

        projects1 = client.list_available_projects()

        spans_after_first = memory_exporter.get_finished_spans()
        analyzer1 = SpanAnalyzer(spans_after_first)

        assert analyzer1.was_data_fetched_from_api("projects"), (
            "First call should fetch from API, but data was retrieved from cache"
        )
        assert analyzer1.count_api_calls() == 1, (
            f"Expected 1 API call on first request, but got {analyzer1.count_api_calls()}"
        )
        assert analyzer1.count_cache_misses() > 0, (
            f"First call should have cache misses, but got {analyzer1.count_cache_misses()} misses"
        )

        memory_exporter.clear()

        projects2 = client.list_available_projects()

        spans_after_second = memory_exporter.get_finished_spans()
        analyzer2 = SpanAnalyzer(spans_after_second)

        assert analyzer2.was_data_fetched_from_cache("projects"), (
            "Second call should use cache, but data was fetched from API"
        )
        assert analyzer2.count_api_calls() == 0, (
            f"Expected 0 API calls on cached request, but got {analyzer2.count_api_calls()} calls"
        )
        assert analyzer2.count_cache_hits() > 0, (
            f"Second call should have cache hits, but got {analyzer2.count_cache_hits()} hits"
        )

        assert projects1 == projects2, (
            f"Projects from API and cache should be identical. API returned {projects1} but cache returned {projects2}"
        )

    def test_pipeline_caching_with_name_lookup(self, telemetry_setup, fresh_cache):
        memory_exporter = telemetry_setup

        client = AdoClient(
            organization_url=os.environ["ADO_ORGANIZATION_URL"],
            pat=os.environ["AZURE_DEVOPS_EXT_PAT"],
        )

        # Get available projects first
        projects = client.list_available_projects()
        if not projects:
            pytest.skip("No projects available for testing")

        project_name = projects[0]

        memory_exporter.clear()

        pipelines1 = client.list_available_pipelines(project_name)

        spans_after_first = memory_exporter.get_finished_spans()
        SpanAnalyzer(spans_after_first)

        api_calls = len(
            [s for s in spans_after_first if "ado_" in s.name and "pipelines" in str(s.attributes)]
        )
        assert api_calls > 0, (
            f"First pipeline lookup should make API calls, but got {api_calls} calls"
        )

        memory_exporter.clear()

        pipelines2 = client.list_available_pipelines(project_name)

        spans_after_second = memory_exporter.get_finished_spans()
        SpanAnalyzer(spans_after_second)

        api_calls_second = len(
            [s for s in spans_after_second if "ado_" in s.name and "pipelines" in str(s.attributes)]
        )
        assert api_calls_second == 0, (
            f"Cached pipeline lookup should not make API calls, but made {api_calls_second} calls"
        )

        assert pipelines1 == pipelines2, (
            f"Pipelines from API and cache should be identical. API returned {pipelines1} but cache returned {pipelines2}"
        )

    def test_cache_expiration_behavior(self, telemetry_setup, fresh_cache):
        memory_exporter = telemetry_setup

        original_ttl = ado_cache.PROJECT_TTL
        ado_cache.PROJECT_TTL = 2

        try:
            client = AdoClient(
                organization_url=os.environ["ADO_ORGANIZATION_URL"],
                pat=os.environ["AZURE_DEVOPS_EXT_PAT"],
            )

            projects1 = client.list_available_projects()
            memory_exporter.clear()

            client.list_available_projects()
            analyzer_cached = SpanAnalyzer(memory_exporter.get_finished_spans())
            assert analyzer_cached.was_data_fetched_from_cache("projects"), (
                "Second call should use cache, but data was fetched from API"
            )

            time.sleep(2.5)
            memory_exporter.clear()

            projects3 = client.list_available_projects()
            analyzer_expired = SpanAnalyzer(memory_exporter.get_finished_spans())
            assert analyzer_expired.was_data_fetched_from_api("projects"), (
                "Call after expiration should hit API, but data was retrieved from cache"
            )

            assert projects1 == projects3, (
                f"Projects should be consistent even after cache expiration. Initial call returned {projects1} but post-expiration call returned {projects3}"
            )

        finally:
            ado_cache.PROJECT_TTL = original_ttl

    def test_fuzzy_matching_performance(self, telemetry_setup, fresh_cache):
        memory_exporter = telemetry_setup

        client = AdoClient(
            organization_url=os.environ["ADO_ORGANIZATION_URL"],
            pat=os.environ["AZURE_DEVOPS_EXT_PAT"],
        )

        projects = client.list_available_projects()
        if not projects:
            pytest.skip("No projects available for testing")

        project_name = projects[0]
        memory_exporter.clear()

        test_names = [
            project_name.lower(),
            project_name.upper(),
            project_name[:3],
        ]

        for test_name in test_names:
            if len(project_name) > 3 or test_name != project_name[:3]:
                client.find_project_by_name(test_name)

                current_spans = memory_exporter.get_finished_spans()
                api_calls = len([s for s in current_spans if "ado_list_projects" in s.name])
                assert api_calls == 0, (
                    f"Fuzzy match '{test_name}' should not make API calls but made {api_calls} calls"
                )

                memory_exporter.clear()

    def test_name_based_pipeline_execution(self, telemetry_setup, fresh_cache):
        memory_exporter = telemetry_setup

        client = AdoClient(
            organization_url=os.environ["ADO_ORGANIZATION_URL"],
            pat=os.environ["AZURE_DEVOPS_EXT_PAT"],
        )

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

        result = client.find_pipeline_by_name(project_name, pipeline_name)
        assert result is not None, (
            f"Should find pipeline '{pipeline_name}' in project '{project_name}' but got None"
        )

        spans = memory_exporter.get_finished_spans()
        analyzer = SpanAnalyzer(spans)

        assert analyzer.count_cache_hits() > 0, (
            f"Should have cache hits when finding cached pipeline, but got {analyzer.count_cache_hits()} hits"
        )
        api_spans = [s for s in spans if s.name.startswith("ado_")]
        assert len(api_spans) == 0, (
            f"Should not make API calls when data is cached, but made {len(api_spans)} API calls"
        )

    def test_cache_statistics_accuracy(self, telemetry_setup, fresh_cache):
        memory_exporter = telemetry_setup

        client = AdoClient(
            organization_url=os.environ["ADO_ORGANIZATION_URL"],
            pat=os.environ["AZURE_DEVOPS_EXT_PAT"],
        )

        projects = client.list_available_projects()
        client.list_available_projects()

        if projects:
            client.find_project_by_name(projects[0])

        stats = ado_cache.get_stats()

        assert stats["total_entries"] > 0, (
            f"Cache should have entries but got {stats['total_entries']} entries"
        )
        assert stats["active_entries"] > 0, (
            f"Cache should have active entries but got {stats['active_entries']} active entries"
        )

        spans = memory_exporter.get_finished_spans()
        analyzer = SpanAnalyzer(spans)

        assert analyzer.count_cache_hits() > 0, (
            f"Should have cache hits recorded in telemetry but got {analyzer.count_cache_hits()} hits"
        )
        assert analyzer.count_cache_misses() > 0, (
            f"Should have cache misses for initial load but got {analyzer.count_cache_misses()} misses"
        )
