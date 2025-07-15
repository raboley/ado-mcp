"""Production telemetry and observability for ADO-MCP."""

import logging
import os
import time
from typing import Optional, Dict, Any
from contextlib import contextmanager

from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes

from .config import TelemetryConfig

logger = logging.getLogger(__name__)


class TelemetryManager:
    """
    Manages production telemetry and observability for ADO-MCP.
    
    This class provides comprehensive telemetry including:
    - Distributed tracing with OpenTelemetry
    - Metrics collection for API performance
    - Error tracking and correlation
    - Performance monitoring
    """
    
    def __init__(self, config: TelemetryConfig):
        """
        Initialize telemetry manager.
        
        Args:
            config: Telemetry configuration
        """
        self.config = config
        self.tracer: Optional[trace.Tracer] = None
        self.meter: Optional[metrics.Meter] = None
        self._initialized = False
        
        # Metrics
        self._api_call_counter = None
        self._api_call_duration = None
        self._error_counter = None
        self._auth_counter = None
        
        if config.enabled:
            self._setup_telemetry()
    
    def _setup_telemetry(self):
        """Set up OpenTelemetry providers and exporters."""
        try:
            # Create resource
            resource = Resource(attributes={
                ResourceAttributes.SERVICE_NAME: self.config.service_name,
                ResourceAttributes.SERVICE_VERSION: self.config.service_version,
                ResourceAttributes.PROCESS_PID: os.getpid(),
            })
            
            # Setup tracing
            self._setup_tracing(resource)
            
            # Setup metrics
            if self.config.metrics_enabled:
                self._setup_metrics(resource)
            
            # Instrument requests library
            RequestsInstrumentor().instrument()
            
            self._initialized = True
            logger.info("Telemetry initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize telemetry: {e}")
            # Don't fail the application if telemetry setup fails
            self.config.enabled = False
    
    def _setup_tracing(self, resource: Resource):
        """Set up distributed tracing."""
        # Create tracer provider
        tracer_provider = TracerProvider(
            resource=resource,
            sampler=TraceIdRatioBased(self.config.trace_sampling_rate)
        )
        
        # Setup OTLP exporter if endpoint is configured
        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
        if otlp_endpoint:
            otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
            tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        
        # Set global tracer provider
        trace.set_tracer_provider(tracer_provider)
        self.tracer = trace.get_tracer(__name__)
    
    def _setup_metrics(self, resource: Resource):
        """Set up metrics collection."""
        # Setup OTLP metric exporter if endpoint is configured
        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT")
        if otlp_endpoint:
            metric_exporter = OTLPMetricExporter(endpoint=otlp_endpoint)
            metric_reader = PeriodicExportingMetricReader(
                exporter=metric_exporter,
                export_interval_millis=30000  # 30 seconds
            )
            
            # Create meter provider
            meter_provider = MeterProvider(
                resource=resource,
                metric_readers=[metric_reader]
            )
            
            # Set global meter provider
            metrics.set_meter_provider(meter_provider)
            self.meter = metrics.get_meter(__name__)
            
            # Create metrics
            self._create_metrics()
    
    def _create_metrics(self):
        """Create application-specific metrics."""
        if not self.meter:
            return
        
        # API call counter
        self._api_call_counter = self.meter.create_counter(
            name="ado_api_calls_total",
            description="Total number of ADO API calls",
            unit="1"
        )
        
        # API call duration histogram
        self._api_call_duration = self.meter.create_histogram(
            name="ado_api_call_duration_seconds",
            description="Duration of ADO API calls in seconds",
            unit="s"
        )
        
        # Error counter
        self._error_counter = self.meter.create_counter(
            name="ado_errors_total",
            description="Total number of errors",
            unit="1"
        )
        
        # Authentication counter
        self._auth_counter = self.meter.create_counter(
            name="ado_auth_attempts_total",
            description="Total number of authentication attempts",
            unit="1"
        )
    
    @contextmanager
    def trace_api_call(self, operation: str, **attributes):
        """
        Context manager for tracing API calls.
        
        Args:
            operation: Name of the operation
            **attributes: Additional span attributes
        """
        if not self._initialized or not self.tracer:
            yield
            return
        
        with self.tracer.start_as_current_span(f"ado_{operation}") as span:
            # Set common attributes
            span.set_attribute("ado.operation", operation)
            for key, value in attributes.items():
                span.set_attribute(key, value)
            
            start_time = time.time()
            
            try:
                yield span
                
                # Record success metrics
                if self._api_call_counter:
                    self._api_call_counter.add(1, {
                        "operation": operation,
                        "status": "success"
                    })
                
            except Exception as e:
                # Record error in span
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                
                # Record error metrics
                if self._error_counter:
                    self._error_counter.add(1, {
                        "operation": operation,
                        "error_type": type(e).__name__
                    })
                
                if self._api_call_counter:
                    self._api_call_counter.add(1, {
                        "operation": operation,
                        "status": "error"
                    })
                
                raise
            
            finally:
                # Record duration
                duration = time.time() - start_time
                if self._api_call_duration:
                    self._api_call_duration.record(duration, {
                        "operation": operation
                    })
    
    def record_auth_attempt(self, method: str, success: bool):
        """
        Record authentication attempt.
        
        Args:
            method: Authentication method used
            success: Whether authentication succeeded
        """
        if not self._initialized or not self._auth_counter:
            return
        
        self._auth_counter.add(1, {
            "method": method,
            "success": str(success).lower()
        })
    
    def add_correlation_id(self, correlation_id: str):
        """
        Add correlation ID to current span.
        
        Args:
            correlation_id: Unique identifier for request correlation
        """
        if not self._initialized:
            return
        
        current_span = trace.get_current_span()
        if current_span:
            current_span.set_attribute("correlation_id", correlation_id)
    
    def log_with_trace(self, level: int, message: str, **kwargs):
        """
        Log message with trace context.
        
        Args:
            level: Log level
            message: Log message
            **kwargs: Additional context
        """
        if not self._initialized:
            logger.log(level, message, **kwargs)
            return
        
        current_span = trace.get_current_span()
        if current_span:
            trace_context = {
                "trace_id": format(current_span.get_span_context().trace_id, "032x"),
                "span_id": format(current_span.get_span_context().span_id, "016x"),
            }
            kwargs.update(trace_context)
        
        logger.log(level, message, **kwargs)
    
    def shutdown(self):
        """Shutdown telemetry providers."""
        if not self._initialized:
            return
        
        try:
            # Shutdown tracing
            if hasattr(trace, 'get_tracer_provider'):
                provider = trace.get_tracer_provider()
                if hasattr(provider, 'shutdown'):
                    provider.shutdown()
            
            # Shutdown metrics
            if hasattr(metrics, 'get_meter_provider'):
                provider = metrics.get_meter_provider()
                if hasattr(provider, 'shutdown'):
                    provider.shutdown()
            
            logger.info("Telemetry shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during telemetry shutdown: {e}")


# Global telemetry manager instance
_telemetry_manager: Optional[TelemetryManager] = None


def initialize_telemetry(config: TelemetryConfig) -> TelemetryManager:
    """
    Initialize global telemetry manager.
    
    Args:
        config: Telemetry configuration
        
    Returns:
        TelemetryManager: Initialized telemetry manager
    """
    global _telemetry_manager
    _telemetry_manager = TelemetryManager(config)
    return _telemetry_manager


def get_telemetry_manager() -> Optional[TelemetryManager]:
    """
    Get the global telemetry manager.
    
    Returns:
        Optional[TelemetryManager]: The telemetry manager if initialized
    """
    return _telemetry_manager


def shutdown_telemetry():
    """Shutdown the global telemetry manager."""
    global _telemetry_manager
    if _telemetry_manager:
        _telemetry_manager.shutdown()
        _telemetry_manager = None