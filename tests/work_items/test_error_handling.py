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
    config = AdoMcpConfig()
    config.retry.max_retries = 2
    config.retry.initial_delay = 0.1
    config.retry.max_delay = 1.0
    config.request_timeout_seconds = 5
    return config


@pytest.fixture
def mock_client(mock_config):
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
    return WorkItemsClient(mock_client)


class TestWorkItemErrorHandling:
    def test_create_work_item_authentication_error(self, work_items_client):
        with patch("requests.request") as mock_request:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.headers = {}
            mock_response.content = True
            mock_response.text = "Unauthorized"
            mock_response.url = "https://dev.azure.com/test/test-project/_apis/wit/workitems/Bug"
            mock_response.raise_for_status.return_value = None
            mock_request.return_value = mock_response
            
            if hasattr(work_items_client.client, 'session'):
                delattr(work_items_client.client, 'session')

            with pytest.raises(AdoAuthenticationError) as exc_info:
                work_items_client.create_work_item(
                    project_id="test-project",
                    work_item_type="Bug",
                    fields={"System.Title": "Test Bug"},
                )

            error = exc_info.value
            assert error.error_code == "ADO_AUTH_FAILED", f"Expected error_code 'ADO_AUTH_FAILED' but got '{error.error_code}'"
            assert "project_id" in error.context, f"Expected 'project_id' in error context but context was {error.context}"
            assert "work_item_type" in error.context, f"Expected 'work_item_type' in error context but context was {error.context}"
            assert error.context["project_id"] == "test-project", f"Expected project_id 'test-project' but got '{error.context.get('project_id')}'"
            assert error.context["work_item_type"] == "Bug", f"Expected work_item_type 'Bug' but got '{error.context.get('work_item_type')}'"

    def test_create_work_item_rate_limit_error(self, work_items_client):
        with patch("requests.request") as mock_request:
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.headers = {"Retry-After": "60"}
            mock_response.content = True
            mock_response.text = "Rate limit exceeded"
            mock_response.url = "https://dev.azure.com/test/test-project/_apis/wit/workitems/Task"
            mock_response.raise_for_status.return_value = None
            mock_request.return_value = mock_response
            
            if hasattr(work_items_client.client, 'session'):
                delattr(work_items_client.client, 'session')

            with pytest.raises(AdoRateLimitError) as exc_info:
                work_items_client.create_work_item(
                    project_id="test-project",
                    work_item_type="Task",
                    fields={"System.Title": "Test Task"},
                )

            error = exc_info.value
            assert error.error_code == "ADO_RATE_LIMIT", f"Expected error_code 'ADO_RATE_LIMIT' but got '{error.error_code}'"
            assert error.retry_after == 60, f"Expected retry_after 60 but got {error.retry_after}"
            assert "project_id" in error.context, f"Expected 'project_id' in error context but context was {error.context}"
            assert "work_item_type" in error.context, f"Expected 'work_item_type' in error context but context was {error.context}"

    def test_create_work_item_server_error(self, work_items_client):
        with patch("requests.request") as mock_request:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.headers = {}
            mock_response.content = True
            mock_response.text = "Internal Server Error"
            mock_response.url = "https://dev.azure.com/test/test-project/_apis/wit/workitems/User%20Story"
            mock_response.raise_for_status.return_value = None
            mock_request.return_value = mock_response
            
            if hasattr(work_items_client.client, 'session'):
                delattr(work_items_client.client, 'session')

            with pytest.raises(AdoNetworkError) as exc_info:
                work_items_client.create_work_item(
                    project_id="test-project",
                    work_item_type="User Story",
                    fields={"System.Title": "Test Story"},
                )

            error = exc_info.value
            assert error.error_code == "ADO_NETWORK_ERROR", f"Expected error_code 'ADO_NETWORK_ERROR' but got '{error.error_code}'"
            assert "Server error during work item creation" in str(error), f"Expected 'Server error during work item creation' in error message but got '{str(error)}'"
            assert error.context["status_code"] == 500, f"Expected status_code 500 but got {error.context.get('status_code')}"

    def test_update_work_item_network_error_with_retry(self, work_items_client):
        with patch("requests.request") as mock_request:
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
            
            if hasattr(work_items_client.client, 'session'):
                delattr(work_items_client.client, 'session')

            from ado.work_items.models import JsonPatchOperation

            operations = [
                JsonPatchOperation(op="replace", path="/fields/System.Title", value="Updated Title")
            ]

            result = work_items_client.update_work_item(
                project_id="test-project", work_item_id=123, operations=operations
            )

            assert result.id == 123, f"Expected work item id 123 but got {result.id}"
            assert mock_request.call_count == 2, f"Expected 2 requests (one failure, one success) but got {mock_request.call_count}"

    def test_get_work_item_structured_error_context(self, work_items_client):
        with patch.object(work_items_client.client, "_send_request") as mock_send:
            mock_send.side_effect = ConnectionError("Network unreachable")

            from ado.errors import AdoError

            with pytest.raises(AdoError) as exc_info:
                work_items_client.get_work_item(project_id="test-project", work_item_id=456)

            error = exc_info.value
            assert error.error_code == "work_item_get_failed", f"Expected error_code 'work_item_get_failed' but got '{error.error_code}'"
            assert "project_id" in error.context, f"Expected 'project_id' in error context but context was {error.context}"
            assert "work_item_id" in error.context, f"Expected 'work_item_id' in error context but context was {error.context}"
            assert error.context["project_id"] == "test-project", f"Expected project_id 'test-project' but got '{error.context.get('project_id')}'"
            assert error.context["work_item_id"] == 456, f"Expected work_item_id 456 but got {error.context.get('work_item_id')}"
            assert error.original_exception is not None, f"Expected original_exception to be set but was None"

    def test_telemetry_spans_created_on_operations(self, work_items_client):
        with (
            patch("ado.work_items.crud_client.tracer") as mock_tracer,
            patch.object(work_items_client.client, "_send_request") as mock_send,
        ):
            mock_span = Mock()
            mock_tracer.start_as_current_span.return_value.__enter__ = Mock(return_value=mock_span)
            mock_tracer.start_as_current_span.return_value.__exit__ = Mock(return_value=None)

            mock_send.return_value = {"id": 789, "fields": {"System.Title": "Test"}}

            work_items_client.get_work_item(project_id="test-project", work_item_id=789)

            mock_tracer.start_as_current_span.assert_called_with("get_work_item")
            mock_span.set_attribute.assert_any_call("work_item.id", 789)
            mock_span.set_attribute.assert_any_call("work_item.project_id", "test-project")

    def test_error_handling_preserves_structured_exceptions(self, work_items_client):
        with patch("requests.request") as mock_request:
            timeout_error = Timeout("Request timed out")
            mock_request.side_effect = timeout_error
            
            if hasattr(work_items_client.client, 'session'):
                delattr(work_items_client.client, 'session')

            with pytest.raises(AdoNetworkError):
                work_items_client.create_work_item(
                    project_id="test-project",
                    work_item_type="Bug",
                    fields={"System.Title": "Test Bug"},
                )

    def test_comprehensive_error_context_in_exceptions(self, work_items_client):
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
                    from ado.errors import AdoError

                    assert isinstance(e, AdoError), f"{operation_name} should raise AdoError but raised {type(e)}"
                    assert hasattr(e, "context"), f"{operation_name} error should have context attribute"
                    assert hasattr(e, "original_exception"), f"{operation_name} error should have original_exception attribute"
                    assert e.context is not None, f"{operation_name} context should not be None but was {e.context}"
