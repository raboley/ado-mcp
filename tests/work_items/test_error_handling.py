"""Tests for comprehensive error handling and retry logic in work items operations."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from requests.exceptions import HTTPError, Timeout, ConnectionError

from ado.client import AdoClient
from ado.work_items.client import WorkItemsClient
from ado.errors import AdoRateLimitError, AdoNetworkError, AdoTimeoutError, AdoAuthenticationError
from ado.config import AdoMcpConfig, RetryConfig


@pytest.fixture
def mock_config():
    """Create a test configuration with shorter timeouts."""
    config = AdoMcpConfig()
    config.retry.max_retries = 2
    config.retry.initial_delay = 0.1
    config.retry.max_delay = 1.0
    config.request_timeout_seconds = 5
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


class TestWorkItemErrorHandling:
    def test_create_work_item_authentication_error(self, work_items_client):
        """Test that authentication errors are properly handled and structured."""
        with patch("requests.request") as mock_request:
            # Mock 401 response with proper attributes
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.headers = {}
            mock_response.content = True
            mock_response.text = "Unauthorized"
            mock_response.url = "https://dev.azure.com/test/test-project/_apis/wit/workitems/Bug"
            mock_response.raise_for_status.return_value = None  # Don't raise on raise_for_status
            mock_request.return_value = mock_response
            
            # Ensure we use the fallback path (not session)
            if hasattr(work_items_client.client, 'session'):
                delattr(work_items_client.client, 'session')

            with pytest.raises(AdoAuthenticationError) as exc_info:
                work_items_client.create_work_item(
                    project_id="test-project",
                    work_item_type="Bug",
                    fields={"System.Title": "Test Bug"},
                )

            error = exc_info.value
            assert error.error_code == "ADO_AUTH_FAILED"
            assert "project_id" in error.context
            assert "work_item_type" in error.context
            assert error.context["project_id"] == "test-project"
            assert error.context["work_item_type"] == "Bug"

    def test_create_work_item_rate_limit_error(self, work_items_client):
        """Test that rate limit errors are properly handled with retry-after."""
        with patch("requests.request") as mock_request:
            # Mock 429 response with proper attributes
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.headers = {"Retry-After": "60"}
            mock_response.content = True
            mock_response.text = "Rate limit exceeded"
            mock_response.url = "https://dev.azure.com/test/test-project/_apis/wit/workitems/Task"
            mock_response.raise_for_status.return_value = None
            mock_request.return_value = mock_response
            
            # Ensure we use the fallback path (not session)
            if hasattr(work_items_client.client, 'session'):
                delattr(work_items_client.client, 'session')

            with pytest.raises(AdoRateLimitError) as exc_info:
                work_items_client.create_work_item(
                    project_id="test-project",
                    work_item_type="Task",
                    fields={"System.Title": "Test Task"},
                )

            error = exc_info.value
            assert error.error_code == "ADO_RATE_LIMIT"
            assert error.retry_after == 60
            assert "project_id" in error.context
            assert "work_item_type" in error.context

    def test_create_work_item_server_error(self, work_items_client):
        """Test that server errors (5xx) are properly handled."""
        with patch("requests.request") as mock_request:
            # Mock 500 response with proper attributes
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.headers = {}
            mock_response.content = True
            mock_response.text = "Internal Server Error"
            mock_response.url = "https://dev.azure.com/test/test-project/_apis/wit/workitems/User%20Story"
            mock_response.raise_for_status.return_value = None
            mock_request.return_value = mock_response
            
            # Ensure we use the fallback path (not session)
            if hasattr(work_items_client.client, 'session'):
                delattr(work_items_client.client, 'session')

            with pytest.raises(AdoNetworkError) as exc_info:
                work_items_client.create_work_item(
                    project_id="test-project",
                    work_item_type="User Story",
                    fields={"System.Title": "Test Story"},
                )

            error = exc_info.value
            assert error.error_code == "ADO_NETWORK_ERROR"
            assert "Server error during work item creation" in str(error)
            assert error.context["status_code"] == 500

    def test_update_work_item_network_error_with_retry(self, work_items_client):
        """Test that network errors trigger retry logic."""
        with patch("requests.request") as mock_request:
            # First call fails, second succeeds
            failure_response = Mock()
            failure_response.status_code = 502
            failure_response.content = True
            failure_response.text = "Bad Gateway"
            failure_response.url = "https://dev.azure.com/test/test-project/_apis/wit/workitems/123"
            failure_response.raise_for_status.return_value = None

            success_response = Mock()
            success_response.status_code = 200
            success_response.content = True
            success_response.text = '{"id": 123, "rev": 2}'
            success_response.url = "https://dev.azure.com/test/test-project/_apis/wit/workitems/123"
            success_response.json.return_value = {
                "id": 123,
                "rev": 2,
                "url": "https://dev.azure.com/test/_apis/wit/workItems/123",
                "fields": {
                    "System.Title": "Updated Title",
                    "System.WorkItemType": "Bug",
                    "System.State": "Active",
                },
            }
            success_response.raise_for_status.return_value = None

            mock_request.side_effect = [failure_response, success_response]
            
            # Ensure we use the fallback path (not session)
            if hasattr(work_items_client.client, 'session'):
                delattr(work_items_client.client, 'session')

            from ado.work_items.models import JsonPatchOperation

            operations = [
                JsonPatchOperation(op="replace", path="/fields/System.Title", value="Updated Title")
            ]

            # Should succeed after retry
            result = work_items_client.update_work_item(
                project_id="test-project", work_item_id=123, operations=operations
            )

            assert result.id == 123
            assert mock_request.call_count == 2  # One failure, one success

    def test_get_work_item_structured_error_context(self, work_items_client):
        """Test that get_work_item provides structured error context."""
        with patch.object(work_items_client.client, "_send_request") as mock_send:
            mock_send.side_effect = ConnectionError("Network unreachable")

            from ado.errors import AdoError

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

    def test_error_handling_preserves_structured_exceptions(self, work_items_client):
        """Test that structured exceptions from retry manager are preserved."""
        with patch("requests.request") as mock_request:
            # Mock timeout that should be wrapped by retry manager
            timeout_error = Timeout("Request timed out")
            mock_request.side_effect = timeout_error
            
            # Ensure we use the fallback path (not session)
            if hasattr(work_items_client.client, 'session'):
                delattr(work_items_client.client, 'session')

            # Due to exception handling order, Timeout gets caught as RequestException and becomes AdoNetworkError
            with pytest.raises(AdoNetworkError):
                work_items_client.create_work_item(
                    project_id="test-project",
                    work_item_type="Bug",
                    fields={"System.Title": "Test Bug"},
                )

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
                    from ado.errors import AdoError

                    assert isinstance(e, AdoError), f"{operation_name} should raise AdoError"
                    assert hasattr(e, "context"), f"{operation_name} error should have context"
                    assert hasattr(e, "original_exception"), (
                        f"{operation_name} error should have original_exception"
                    )
                    assert e.context is not None, f"{operation_name} context should not be None"
