"""
Telemetry utilities for testing Azure DevOps operations with OpenTelemetry.

Provides tools for analyzing spans to verify cache behavior, API calls,
and performance characteristics in end-to-end tests.
"""

from typing import Any

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


class SpanAnalyzer:
    """
    Helper class to analyze OpenTelemetry spans for testing.

    Provides methods to verify cache behavior, API calls, and performance
    characteristics through telemetry data.
    """

    def __init__(self, spans: list[Any]):
        self.spans = spans

    def find_spans_by_name(self, name: str) -> list[Any]:
        """Find all spans with the given name."""
        return [span for span in self.spans if span.name == name]

    def get_span_attributes(self, span: Any) -> dict[str, Any]:
        """Get all attributes from a span."""
        return dict(span.attributes or {})

    def count_cache_hits(self) -> int:
        """Count the number of cache hits in the spans."""
        cache_get_spans = self.find_spans_by_name("cache_get")
        return sum(
            1 for span in cache_get_spans if self.get_span_attributes(span).get("cache.hit") is True
        )

    def count_cache_misses(self) -> int:
        """Count the number of cache misses in the spans."""
        cache_get_spans = self.find_spans_by_name("cache_get")
        return sum(
            1
            for span in cache_get_spans
            if self.get_span_attributes(span).get("cache.hit") is False
        )

    def count_api_calls(self, operation: str = None) -> int:
        """
        Count the number of actual API calls made.

        Args:
            operation: Optional specific operation to count (e.g., "list_projects")
        """
        if operation:
            api_spans = self.find_spans_by_name(f"ado_{operation}")
        else:
            # Count all ADO API spans
            api_spans = [span for span in self.spans if span.name.startswith("ado_")]
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

    def get_operation_count(self, operation: str) -> int:
        """Get the count of items returned by an operation."""
        ensure_spans = self.find_spans_by_name(f"ensure_{operation}_cached")
        if ensure_spans:
            latest_span = ensure_spans[-1]
            attrs = self.get_span_attributes(latest_span)
            return attrs.get(f"{operation}.count", 0)
        return 0

    def has_cache_operations(self) -> bool:
        """Check if any cache operations were recorded."""
        return len(self.find_spans_by_name("cache_get")) > 0

    def get_all_span_names(self) -> list[str]:
        """Get all span names for debugging."""
        return [span.name for span in self.spans]


@pytest.fixture
def telemetry_setup():
    """
    Set up OpenTelemetry for testing with in-memory span export.

    Yields:
        InMemorySpanExporter: Exporter to capture spans for analysis
    """
    # Create an in-memory span exporter
    memory_exporter = InMemorySpanExporter()

    # Get current tracer provider or create new one
    current_provider = trace.get_tracer_provider()
    if not hasattr(current_provider, "add_span_processor"):
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


def analyze_spans(memory_exporter: InMemorySpanExporter) -> SpanAnalyzer:
    """
    Create a SpanAnalyzer from the current spans in the exporter.

    Args:
        memory_exporter: The in-memory span exporter from telemetry_setup

    Returns:
        SpanAnalyzer: Analyzer for the captured spans
    """
    return SpanAnalyzer(memory_exporter.get_finished_spans())


def clear_spans(memory_exporter: InMemorySpanExporter) -> None:
    """Clear all captured spans from the exporter."""
    memory_exporter.clear()
