"""Simplified tests for comprehensive error handling in work items operations."""

import pytest
from unittest.mock import Mock, patch
import requests
from requests.exceptions import HTTPError, Timeout, ConnectionError

from ado.client import AdoClient
from ado.work_items.client import WorkItemsClient
from ado.errors import (
    AdoRateLimitError,
    AdoNetworkError,
    AdoTimeoutError,
    AdoAuthenticationError,
    AdoError,
)
from ado.config import AdoMcpConfig, RetryConfig


@pytest.fixture
def mock_config():
    """Create a test configuration with shorter timeouts."""
    config = AdoMcpConfig()
    config.retry.max_retries = 1
    config.retry.initial_delay = 0.01
    config.retry.max_delay = 0.1
    config.request_timeout_seconds = 1
    return config


@pytest.fixture
def mock_client(mock_config):
    """Create a mock AdoClient for testing."""
    with patch("ado.auth.AuthManager") as mock_auth:
        mock_auth.return_value.get_auth_headers.return_value = {
            "Authorization": "Basic dGVzdA==",
            "Content-Type": "application/json",
        }
        mock_auth.return_value.get_auth_method.return_value = "pat"

        client = AdoClient(
            organization_url="https://dev.azure.com/test", pat="test-pat", config=mock_config
        )
        return client


@pytest.fixture
def work_items_client(mock_client):
    """Create a WorkItemsClient for testing."""
    return WorkItemsClient(mock_client)


class TestWorkItemErrorHandlingSimplified:
    def test_get_work_item_structured_error_context(self, work_items_client):
        """Test that get_work_item provides structured error context."""
        with patch.object(work_items_client.client, "_send_request") as mock_send:
            mock_send.side_effect = ConnectionError("Network unreachable")

            with pytest.raises(AdoError) as exc_info:
                work_items_client.get_work_item(project_id="test-project", work_item_id=456)

            error = exc_info.value
            assert error.error_code == "work_item_get_failed"
            assert "project_id" in error.context
            assert "work_item_id" in error.context
            assert error.context["project_id"] == "test-project"
            assert error.context["work_item_id"] == 456
            assert error.original_exception is not None

    def test_telemetry_spans_created_on_operations(self, work_items_client):
        """Test that telemetry spans are created for work item operations."""
        with (
            patch("ado.work_items.client.tracer") as mock_tracer,
            patch.object(work_items_client.client, "_send_request") as mock_send,
        ):
            mock_span = Mock()
            mock_tracer.start_as_current_span.return_value.__enter__ = Mock(return_value=mock_span)
            mock_tracer.start_as_current_span.return_value.__exit__ = Mock(return_value=None)

            mock_send.return_value = {"id": 789, "fields": {"System.Title": "Test"}}

            work_items_client.get_work_item(project_id="test-project", work_item_id=789)

            # Verify span was created and attributes were set
            mock_tracer.start_as_current_span.assert_called_with("get_work_item")
            mock_span.set_attribute.assert_any_call("work_item.id", 789)
            mock_span.set_attribute.assert_any_call("work_item.project_id", "test-project")

    def test_create_work_item_timeout_handling(self, work_items_client):
        """Test that timeout errors are properly handled by retry manager."""
        with patch("requests.request") as mock_request:
            mock_request.side_effect = Timeout("Request timed out")

            # The retry manager will convert this to AdoNetworkError after retries
            # (since Timeout inherits from RequestException)
            with pytest.raises(AdoNetworkError) as exc_info:
                work_items_client.create_work_item(
                    project_id="test-project",
                    work_item_type="Bug",
                    fields={"System.Title": "Test Bug"},
                )

            # Verify it was converted from a timeout
            error = exc_info.value
            assert "Network error on attempt" in str(error)
            assert error.original_exception is not None

    def test_comprehensive_error_context_in_exceptions(self, work_items_client):
        """Test that all operations include comprehensive error context."""
        operations_to_test = [
            (
                "create_work_item",
                {
                    "project_id": "test-project",
                    "work_item_type": "Bug",
                    "fields": {"System.Title": "Test"},
                },
            ),
            (
                "update_work_item",
                {"project_id": "test-project", "work_item_id": 123, "operations": []},
            ),
        ]

        for operation_name, kwargs in operations_to_test:
            with patch("requests.request") as mock_request:
                mock_request.side_effect = Exception("Test error")

                operation = getattr(work_items_client, operation_name)

                try:
                    operation(**kwargs)
                    pytest.fail(f"Expected {operation_name} to raise an exception")
                except Exception as e:
                    # All exceptions should be AdoError with proper context
                    assert isinstance(e, AdoError), f"{operation_name} should raise AdoError"
                    assert hasattr(e, "context"), f"{operation_name} error should have context"
                    assert hasattr(e, "original_exception"), (
                        f"{operation_name} error should have original_exception"
                    )
                    assert e.context is not None, f"{operation_name} context should not be None"

    def test_structured_error_exception_hierarchy(self, work_items_client):
        """Test that all custom exceptions inherit from AdoError."""
        from ado.errors import (
            AdoError,
            AdoRateLimitError,
            AdoNetworkError,
            AdoTimeoutError,
            AdoAuthenticationError,
        )

        error_classes = [
            AdoRateLimitError,
            AdoNetworkError,
            AdoTimeoutError,
            AdoAuthenticationError,
        ]

        for error_class in error_classes:
            # Create instance with minimal args
            if error_class == AdoRateLimitError:
                error = error_class("Test message", retry_after=30)
            else:
                error = error_class("Test message")

            # Verify inheritance
            assert isinstance(error, AdoError), (
                f"{error_class.__name__} should inherit from AdoError"
            )
            assert hasattr(error, "error_code"), f"{error_class.__name__} should have error_code"
            assert hasattr(error, "context"), f"{error_class.__name__} should have context"
            assert error.context is not None, f"{error_class.__name__} context should not be None"
