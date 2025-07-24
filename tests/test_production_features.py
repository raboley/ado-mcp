import os
import time
from unittest.mock import MagicMock, Mock, patch

import pytest
from requests.exceptions import HTTPError, RequestException, Timeout

from ado.auth import AuthManager, EnvironmentPatAuthProvider, PatAuthProvider
from ado.client import AdoClient
from ado.config import AdoMcpConfig, AuthConfig, RetryConfig, TelemetryConfig
from ado.errors import (
    AdoAuthenticationError,
    AdoConfigurationError,
    AdoError,
    AdoNetworkError,
    AdoRateLimitError,
    AdoTimeoutError,
)
from ado.retry import RetryManager
from ado.telemetry import TelemetryManager


class TestStructuredErrors:
    def test_ado_error_structure(self):
        error = AdoError(
            message="Test error",
            error_code="TEST_ERROR",
            context={"key": "value"},
            original_exception=ValueError("original"),
        )

        assert str(error) == "Test error", f"Expected 'Test error' but got '{str(error)}'"
        assert error.error_code == "TEST_ERROR", (
            f"Expected 'TEST_ERROR' but got '{error.error_code}'"
        )
        assert error.context == {"key": "value"}, (
            f"Expected {{'key': 'value'}} but got {error.context}"
        )
        assert isinstance(error.original_exception, ValueError), (
            f"Expected ValueError but got {type(error.original_exception)}"
        )

    def test_authentication_error_structure(self):
        error = AdoAuthenticationError(
            message="Auth failed",
            context={"method": "pat"},
            original_exception=ValueError("original"),
        )

        assert error.error_code == "ADO_AUTH_FAILED", (
            f"Expected 'ADO_AUTH_FAILED' but got '{error.error_code}'"
        )
        assert error.context == {"method": "pat"}, (
            f"Expected {{'method': 'pat'}} but got {error.context}"
        )
        assert isinstance(error.original_exception, ValueError), (
            f"Expected ValueError but got {type(error.original_exception)}"
        )

    def test_rate_limit_error_structure(self):
        error = AdoRateLimitError(
            message="Rate limited",
            retry_after=60,
            context={"url": "test"},
            original_exception=HTTPError("original"),
        )

        assert error.error_code == "ADO_RATE_LIMIT", (
            f"Expected 'ADO_RATE_LIMIT' but got '{error.error_code}'"
        )
        assert error.retry_after == 60, f"Expected retry_after 60 but got {error.retry_after}"
        assert error.context["retry_after"] == 60, (
            f"Expected context retry_after 60 but got {error.context['retry_after']}"
        )
        assert error.context["url"] == "test", (
            f"Expected context url 'test' but got '{error.context['url']}'"
        )
        assert isinstance(error.original_exception, HTTPError), (
            f"Expected HTTPError but got {type(error.original_exception)}"
        )


class TestConfiguration:
    def test_default_config_creation(self):
        config = AdoMcpConfig()

        assert config.retry.max_retries == 3, (
            f"Expected max_retries 3 but got {config.retry.max_retries}"
        )
        assert config.retry.initial_delay == 1.0, (
            f"Expected initial_delay 1.0 but got {config.retry.initial_delay}"
        )
        assert config.retry.backoff_multiplier == 2.0, (
            f"Expected backoff_multiplier 2.0 but got {config.retry.backoff_multiplier}"
        )
        assert config.auth.timeout_seconds == 30, (
            f"Expected auth timeout 30 but got {config.auth.timeout_seconds}"
        )
        assert config.telemetry.enabled, (
            f"Expected telemetry enabled True but got {config.telemetry.enabled}"
        )
        assert config.request_timeout_seconds == 30, (
            f"Expected request timeout 30 but got {config.request_timeout_seconds}"
        )

    def test_config_from_environment(self):
        with patch.dict(
            os.environ,
            {
                "ADO_ORGANIZATION_URL": "https://test.visualstudio.com",
                "AZURE_DEVOPS_EXT_PAT": "test-pat",
                "ADO_RETRY_MAX_RETRIES": "5",
                "ADO_RETRY_INITIAL_DELAY": "2.0",
                "ADO_AUTH_TIMEOUT": "45",
                "ADO_TELEMETRY_ENABLED": "false",
            },
        ):
            config = AdoMcpConfig()

            assert config.organization_url == "https://test.visualstudio.com", (
                f"Expected organization_url 'https://test.visualstudio.com' but got '{config.organization_url}'"
            )
            assert config.pat == "test-pat", f"Expected pat 'test-pat' but got '{config.pat}'"
            assert config.retry.max_retries == 5, (
                f"Expected max_retries 5 but got {config.retry.max_retries}"
            )
            assert config.retry.initial_delay == 2.0, (
                f"Expected initial_delay 2.0 but got {config.retry.initial_delay}"
            )
            assert config.auth.timeout_seconds == 45, (
                f"Expected auth timeout 45 but got {config.auth.timeout_seconds}"
            )
            assert not config.telemetry.enabled, (
                f"Expected telemetry enabled False but got {config.telemetry.enabled}"
            )

    def test_config_validation(self):
        with pytest.raises(AdoConfigurationError) as exc_info:
            RetryConfig(max_retries=-1)

        assert exc_info.value.error_code == "ADO_CONFIG_ERROR", (
            f"Expected error_code 'ADO_CONFIG_ERROR' but got '{exc_info.value.error_code}'"
        )
        assert "max_retries must be non-negative" in str(exc_info.value), (
            f"Expected 'max_retries must be non-negative' in error message but got '{str(exc_info.value)}'"
        )

    def test_config_overrides(self):
        config = AdoMcpConfig.from_env(
            organization_url="https://override.visualstudio.com", request_timeout_seconds=60
        )

        assert config.organization_url == "https://override.visualstudio.com", (
            f"Expected organization_url 'https://override.visualstudio.com' but got '{config.organization_url}'"
        )
        assert config.request_timeout_seconds == 60, (
            f"Expected request_timeout_seconds 60 but got {config.request_timeout_seconds}"
        )


class TestAuthenticationChaining:
    def test_auth_manager_provider_chain(self):
        config = AuthConfig()
        auth_manager = AuthManager(config)

        auth_manager.add_provider(PatAuthProvider("test-pat"))
        auth_manager.add_provider(EnvironmentPatAuthProvider("FAKE_VAR"))

        credential = auth_manager.get_credential()
        assert credential.method == "pat", f"Expected method 'pat' but got '{credential.method}'"
        assert credential.token == "test-pat", (
            f"Expected token 'test-pat' but got '{credential.token}'"
        )
        assert credential.auth_type == "basic", (
            f"Expected auth_type 'basic' but got '{credential.auth_type}'"
        )

    def test_auth_manager_fallback(self):
        config = AuthConfig()
        auth_manager = AuthManager(config)

        auth_manager.add_provider(PatAuthProvider(""))

        with patch.dict(os.environ, {"AZURE_DEVOPS_EXT_PAT": "env-pat"}):
            auth_manager.add_provider(EnvironmentPatAuthProvider())

            credential = auth_manager.get_credential()
            assert credential.method == "env_pat", (
                f"Expected method 'env_pat' but got '{credential.method}'"
            )
            assert credential.token == "env-pat", (
                f"Expected token 'env-pat' but got '{credential.token}'"
            )

    def test_auth_manager_no_providers_succeed(self):
        config = AuthConfig()
        auth_manager = AuthManager(config)

        auth_manager.add_provider(PatAuthProvider(""))
        auth_manager.add_provider(EnvironmentPatAuthProvider("NONEXISTENT_VAR"))

        with pytest.raises(AdoAuthenticationError) as exc_info:
            auth_manager.get_credential()

        assert exc_info.value.error_code == "ADO_AUTH_FAILED", (
            f"Expected error_code 'ADO_AUTH_FAILED' but got '{exc_info.value.error_code}'"
        )
        assert "No authentication method succeeded" in str(exc_info.value), (
            f"Expected 'No authentication method succeeded' in error message but got '{str(exc_info.value)}'"
        )

    def test_auth_manager_credential_caching(self):
        config = AuthConfig(cache_ttl_seconds=10)
        auth_manager = AuthManager(config)

        mock_provider = Mock()
        mock_provider.get_name.return_value = "Mock Provider"
        mock_provider.get_credential.return_value = Mock(
            token="test-token",
            auth_type="basic",
            method="mock",
            is_expired=Mock(return_value=False),
        )

        auth_manager.add_provider(mock_provider)

        credential1 = auth_manager.get_credential()
        assert mock_provider.get_credential.call_count == 1, (
            f"Expected provider called 1 time after first call but was called {mock_provider.get_credential.call_count} times"
        )

        credential2 = auth_manager.get_credential()
        assert mock_provider.get_credential.call_count == 1, (
            f"Expected provider called 1 time after cache hit but was called {mock_provider.get_credential.call_count} times"
        )
        assert credential1.token == credential2.token, (
            f"Expected cached credential token '{credential1.token}' but got '{credential2.token}'"
        )

    def test_auth_manager_cache_invalidation(self):
        config = AuthConfig(cache_ttl_seconds=10)
        auth_manager = AuthManager(config)

        auth_manager.add_provider(PatAuthProvider("test-pat"))

        credential1 = auth_manager.get_credential()

        auth_manager.invalidate_cache()

        credential2 = auth_manager.get_credential()
        assert credential1.token == credential2.token, (
            f"Expected same token '{credential1.token}' from fresh credential but got '{credential2.token}'"
        )


class TestRetryMechanism:
    def test_retry_manager_success_no_retry(self):
        config = RetryConfig(max_retries=3)
        retry_manager = RetryManager(config)

        @retry_manager.retry_on_failure
        def successful_function():
            return "success"

        result = successful_function()
        assert result == "success", f"Expected result 'success' but got '{result}'"

    def test_retry_manager_eventual_success(self):
        config = RetryConfig(max_retries=3, initial_delay=0.1)
        retry_manager = RetryManager(config)

        call_count = 0

        @retry_manager.retry_on_failure
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise AdoNetworkError("Network error")
            return "success"

        result = flaky_function()
        assert result == "success", f"Expected result 'success' but got '{result}'"
        assert call_count == 3, (
            f"Expected function called 3 times but was called {call_count} times"
        )

    def test_retry_manager_max_retries_exceeded(self):
        config = RetryConfig(max_retries=2, initial_delay=0.1)
        retry_manager = RetryManager(config)

        @retry_manager.retry_on_failure
        def always_failing_function():
            raise AdoNetworkError("Network error")

        with pytest.raises(AdoNetworkError) as exc_info:
            always_failing_function()

        assert "Network error" in str(exc_info.value), (
            f"Expected 'Network error' in exception message but got '{str(exc_info.value)}'"
        )

    def test_retry_manager_rate_limit_handling(self):
        config = RetryConfig(max_retries=3, initial_delay=0.1)
        retry_manager = RetryManager(config)

        call_count = 0

        @retry_manager.retry_on_failure
        def rate_limited_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise AdoRateLimitError("Rate limited", retry_after=1)
            return "success"

        result = rate_limited_function()
        assert result == "success", f"Expected result 'success' but got '{result}'"
        assert call_count == 3, (
            f"Expected function called 3 times but was called {call_count} times"
        )

    def test_retry_manager_non_retryable_error(self):
        config = RetryConfig(max_retries=3)
        retry_manager = RetryManager(config)

        @retry_manager.retry_on_failure
        def non_retryable_function():
            response = Mock()
            response.status_code = 404
            error = HTTPError("Not found")
            error.response = response
            raise error

        with pytest.raises(HTTPError) as exc_info:
            non_retryable_function()

        assert "Not found" in str(exc_info.value), (
            f"Expected 'Not found' in exception message but got '{str(exc_info.value)}'"
        )

    def test_retry_manager_circuit_breaker(self):
        config = RetryConfig(max_retries=2, initial_delay=0.1)
        retry_manager = RetryManager(config)

        retry_manager._failure_count = 5
        retry_manager._circuit_open = True
        retry_manager._last_failure_time = time.time()

        @retry_manager.retry_on_failure
        def function_with_circuit_open():
            raise AdoNetworkError("Network error")

        with pytest.raises(AdoNetworkError) as exc_info:
            function_with_circuit_open()

        assert "Network error" in str(exc_info.value), (
            f"Expected 'Network error' in exception message but got '{str(exc_info.value)}'"
        )


class TestTelemetryIntegration:
    def test_telemetry_manager_initialization(self):
        config = TelemetryConfig(enabled=True)
        telemetry = TelemetryManager(config)

        assert telemetry.config.enabled, (
            f"Expected telemetry enabled True but got {telemetry.config.enabled}"
        )
        assert telemetry.config.service_name == "ado-mcp", (
            f"Expected service_name 'ado-mcp' but got '{telemetry.config.service_name}'"
        )

    def test_telemetry_disabled(self):
        config = TelemetryConfig(enabled=False)
        telemetry = TelemetryManager(config)

        assert telemetry.tracer is None, (
            f"Expected tracer to be None when disabled but got {telemetry.tracer}"
        )
        assert telemetry.meter is None, (
            f"Expected meter to be None when disabled but got {telemetry.meter}"
        )

    def test_telemetry_trace_context(self):
        config = TelemetryConfig(enabled=True)
        telemetry = TelemetryManager(config)

        try:
            with telemetry.trace_api_call("test_operation", test_attr="value"):
                pass
            context_works = True
        except Exception as e:
            context_works = False
            error_msg = str(e)

        assert context_works, (
            f"Expected trace context manager to work without errors but got exception: {error_msg if not context_works else 'none'}"
        )

    def test_telemetry_auth_recording(self):
        config = TelemetryConfig(enabled=True)
        telemetry = TelemetryManager(config)

        try:
            telemetry.record_auth_attempt("pat", True)
            telemetry.record_auth_attempt("azure_cli", False)
            recording_works = True
        except Exception as e:
            recording_works = False
            error_msg = str(e)

        assert recording_works, (
            f"Expected auth recording to work without errors but got exception: {error_msg if not recording_works else 'none'}"
        )


class TestClientIntegration:
    def test_client_with_production_config(self):
        config = AdoMcpConfig(
            organization_url="https://test.visualstudio.com",
            retry=RetryConfig(max_retries=5),
            auth=AuthConfig(timeout_seconds=45),
            telemetry=TelemetryConfig(enabled=False),
        )

        client = AdoClient(
            organization_url="https://test.visualstudio.com", pat="test-pat", config=config
        )

        assert client.organization_url == "https://test.visualstudio.com", (
            f"Expected organization_url 'https://test.visualstudio.com' but got '{client.organization_url}'"
        )
        assert client.auth_method == "explicit_pat", (
            f"Expected auth_method 'explicit_pat' but got '{client.auth_method}'"
        )
        assert client.config.retry.max_retries == 5, (
            f"Expected max_retries 5 but got {client.config.retry.max_retries}"
        )
        assert client.config.auth.timeout_seconds == 45, (
            f"Expected auth timeout 45 but got {client.config.auth.timeout_seconds}"
        )

    def test_client_authentication_refresh(self):
        config = AdoMcpConfig(
            organization_url="https://test.visualstudio.com",
            telemetry=TelemetryConfig(enabled=False),
        )

        client = AdoClient(
            organization_url="https://test.visualstudio.com", pat="test-pat", config=config
        )

        client.refresh_authentication()

        assert client.auth_method == "explicit_pat", (
            f"Expected auth_method to remain 'explicit_pat' after refresh but got '{client.auth_method}'"
        )

    def test_client_handles_rate_limiting(self):
        config = AdoMcpConfig(
            organization_url="https://test.visualstudio.com",
            retry=RetryConfig(max_retries=2, initial_delay=0.1),
            telemetry=TelemetryConfig(enabled=False),
        )

        client = AdoClient(
            organization_url="https://test.visualstudio.com", pat="test-pat", config=config
        )

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "1"}
        mock_response.text = ""
        mock_response.url = "https://test.visualstudio.com/_apis/test"
        mock_response.content = b""
        mock_response.raise_for_status.return_value = None

        # Patch both requests.request and remove session to trigger fallback
        with patch("requests.request", return_value=mock_response):
            # Ensure we don't have a session to trigger the fallback path
            if hasattr(client, "session"):
                delattr(client, "session")
            with pytest.raises(AdoRateLimitError) as exc_info:
                client._send_request("GET", "https://test.visualstudio.com/_apis/test")

            assert exc_info.value.error_code == "ADO_RATE_LIMIT", (
                f"Expected error_code 'ADO_RATE_LIMIT' but got '{exc_info.value.error_code}'"
            )
            assert exc_info.value.retry_after == 1, (
                f"Expected retry_after 1 but got {exc_info.value.retry_after}"
            )

    def test_client_handles_network_errors(self):
        config = AdoMcpConfig(
            organization_url="https://test.visualstudio.com",
            retry=RetryConfig(max_retries=1, initial_delay=0.1),
            telemetry=TelemetryConfig(enabled=False),
        )

        client = AdoClient(
            organization_url="https://test.visualstudio.com", pat="test-pat", config=config
        )

        # Create a RequestException without response attribute to trigger network error handling
        network_error = RequestException("Network error")

        with patch("requests.request", side_effect=network_error):
            # Ensure we don't have a session to trigger the fallback path
            if hasattr(client, "session"):
                delattr(client, "session")
            with pytest.raises(AdoNetworkError) as exc_info:
                client._send_request("GET", "https://test.visualstudio.com/_apis/test")

            assert exc_info.value.error_code == "ADO_NETWORK_ERROR", (
                f"Expected error_code 'ADO_NETWORK_ERROR' but got '{exc_info.value.error_code}'"
            )
            assert "Network error" in str(exc_info.value), (
                f"Expected 'Network error' in exception message but got '{str(exc_info.value)}'"
            )

    def test_client_handles_timeout_errors(self):
        config = AdoMcpConfig(
            organization_url="https://test.visualstudio.com",
            retry=RetryConfig(max_retries=1, initial_delay=0.1),
            telemetry=TelemetryConfig(enabled=False),
        )

        client = AdoClient(
            organization_url="https://test.visualstudio.com", pat="test-pat", config=config
        )

        timeout_error = Timeout("Request timeout")

        with patch("requests.request", side_effect=timeout_error):
            # Ensure we don't have a session to trigger the fallback path
            if hasattr(client, "session"):
                delattr(client, "session")
            with pytest.raises(AdoTimeoutError) as exc_info:
                client._send_request("GET", "https://test.visualstudio.com/_apis/test")

            assert exc_info.value.error_code == "ADO_TIMEOUT", (
                f"Expected error_code 'ADO_TIMEOUT' but got '{exc_info.value.error_code}'"
            )
            assert exc_info.value.timeout_seconds == config.request_timeout_seconds, (
                f"Expected timeout_seconds {config.request_timeout_seconds} but got {exc_info.value.timeout_seconds}"
            )

    def test_client_correlation_id_tracking(self):
        config = AdoMcpConfig(
            organization_url="https://test.visualstudio.com",
            telemetry=TelemetryConfig(enabled=False),
        )

        client = AdoClient(
            organization_url="https://test.visualstudio.com", pat="test-pat", config=config
        )

        assert client.correlation_id is not None, (
            f"Expected correlation_id to not be None but got {client.correlation_id}"
        )
        assert len(client.correlation_id) > 0, (
            f"Expected correlation_id to have length > 0 but got length {len(client.correlation_id)}"
        )

        client2 = AdoClient(
            organization_url="https://test.visualstudio.com", pat="test-pat", config=config
        )
        assert client.correlation_id != client2.correlation_id, (
            f"Expected different correlation_ids but both clients have '{client.correlation_id}'"
        )
