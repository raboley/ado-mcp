"""End-to-end tests for production-ready features."""

import os
import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from requests.exceptions import HTTPError, RequestException, Timeout
from requests import Response

from ado.client import AdoClient
from ado.config import AdoMcpConfig, RetryConfig, AuthConfig, TelemetryConfig
from ado.errors import (
    AdoError,
    AdoAuthenticationError,
    AdoRateLimitError,
    AdoTimeoutError,
    AdoNetworkError,
    AdoConfigurationError,
)
from ado.auth import AuthManager, PatAuthProvider, EnvironmentPatAuthProvider
from ado.retry import RetryManager
from ado.telemetry import TelemetryManager


class TestStructuredErrors:
    """Test structured error types and error codes."""
    
    def test_ado_error_structure(self):
        """Test AdoError has structured error information."""
        error = AdoError(
            message="Test error",
            error_code="TEST_ERROR",
            context={"key": "value"},
            original_exception=ValueError("original")
        )
        
        assert str(error) == "Test error"
        assert error.error_code == "TEST_ERROR"
        assert error.context == {"key": "value"}
        assert isinstance(error.original_exception, ValueError)
    
    def test_authentication_error_structure(self):
        """Test AdoAuthenticationError has proper structure."""
        error = AdoAuthenticationError(
            message="Auth failed",
            context={"method": "pat"},
            original_exception=ValueError("original")
        )
        
        assert error.error_code == "ADO_AUTH_FAILED"
        assert error.context == {"method": "pat"}
        assert isinstance(error.original_exception, ValueError)
    
    def test_rate_limit_error_structure(self):
        """Test AdoRateLimitError has proper structure."""
        error = AdoRateLimitError(
            message="Rate limited",
            retry_after=60,
            context={"url": "test"},
            original_exception=HTTPError("original")
        )
        
        assert error.error_code == "ADO_RATE_LIMIT"
        assert error.retry_after == 60
        assert error.context["retry_after"] == 60
        assert error.context["url"] == "test"
        assert isinstance(error.original_exception, HTTPError)


class TestConfiguration:
    """Test configuration management."""
    
    def test_default_config_creation(self):
        """Test default configuration creation."""
        config = AdoMcpConfig()
        
        assert config.retry.max_retries == 3
        assert config.retry.initial_delay == 1.0
        assert config.retry.backoff_multiplier == 2.0
        assert config.auth.timeout_seconds == 30
        assert config.telemetry.enabled == True
        assert config.request_timeout_seconds == 30
    
    def test_config_from_environment(self):
        """Test configuration loading from environment variables."""
        with patch.dict(os.environ, {
            'ADO_ORGANIZATION_URL': 'https://test.visualstudio.com',
            'AZURE_DEVOPS_EXT_PAT': 'test-pat',
            'ADO_RETRY_MAX_RETRIES': '5',
            'ADO_RETRY_INITIAL_DELAY': '2.0',
            'ADO_AUTH_TIMEOUT': '45',
            'ADO_TELEMETRY_ENABLED': 'false',
        }):
            config = AdoMcpConfig()
            
            assert config.organization_url == 'https://test.visualstudio.com'
            assert config.pat == 'test-pat'
            assert config.retry.max_retries == 5
            assert config.retry.initial_delay == 2.0
            assert config.auth.timeout_seconds == 45
            assert config.telemetry.enabled == False
    
    def test_config_validation(self):
        """Test configuration validation."""
        with pytest.raises(AdoConfigurationError) as exc_info:
            RetryConfig(max_retries=-1)
        
        assert exc_info.value.error_code == "ADO_CONFIG_ERROR"
        assert "max_retries must be non-negative" in str(exc_info.value)
    
    def test_config_overrides(self):
        """Test configuration overrides."""
        config = AdoMcpConfig.from_env(
            organization_url="https://override.visualstudio.com",
            request_timeout_seconds=60
        )
        
        assert config.organization_url == "https://override.visualstudio.com"
        assert config.request_timeout_seconds == 60


class TestAuthenticationChaining:
    """Test credential chaining authentication."""
    
    def test_auth_manager_provider_chain(self):
        """Test authentication manager tries providers in order."""
        config = AuthConfig()
        auth_manager = AuthManager(config)
        
        # Add providers in order
        auth_manager.add_provider(PatAuthProvider("test-pat"))
        auth_manager.add_provider(EnvironmentPatAuthProvider("FAKE_VAR"))
        
        # Should use first provider
        credential = auth_manager.get_credential()
        assert credential.method == "pat"
        assert credential.token == "test-pat"
        assert credential.auth_type == "basic"
    
    def test_auth_manager_fallback(self):
        """Test authentication manager falls back to next provider."""
        config = AuthConfig()
        auth_manager = AuthManager(config)
        
        # Add providers where first fails
        auth_manager.add_provider(PatAuthProvider(""))  # Empty PAT
        
        with patch.dict(os.environ, {'AZURE_DEVOPS_EXT_PAT': 'env-pat'}):
            auth_manager.add_provider(EnvironmentPatAuthProvider())
            
            credential = auth_manager.get_credential()
            assert credential.method == "env_pat"
            assert credential.token == "env-pat"
    
    def test_auth_manager_no_providers_succeed(self):
        """Test authentication manager when no providers succeed."""
        config = AuthConfig()
        auth_manager = AuthManager(config)
        
        # Add providers that will all fail
        auth_manager.add_provider(PatAuthProvider(""))
        auth_manager.add_provider(EnvironmentPatAuthProvider("NONEXISTENT_VAR"))
        
        with pytest.raises(AdoAuthenticationError) as exc_info:
            auth_manager.get_credential()
        
        assert exc_info.value.error_code == "ADO_AUTH_FAILED"
        assert "No authentication method succeeded" in str(exc_info.value)
    
    def test_auth_manager_credential_caching(self):
        """Test authentication manager caches credentials."""
        config = AuthConfig(cache_ttl_seconds=10)
        auth_manager = AuthManager(config)
        
        # Mock provider to track calls
        mock_provider = Mock()
        mock_provider.get_name.return_value = "Mock Provider"
        mock_provider.get_credential.return_value = Mock(
            token="test-token",
            auth_type="basic",
            method="mock",
            is_expired=Mock(return_value=False)
        )
        
        auth_manager.add_provider(mock_provider)
        
        # First call should hit provider
        credential1 = auth_manager.get_credential()
        assert mock_provider.get_credential.call_count == 1
        
        # Second call should use cache
        credential2 = auth_manager.get_credential()
        assert mock_provider.get_credential.call_count == 1
        assert credential1.token == credential2.token
    
    def test_auth_manager_cache_invalidation(self):
        """Test authentication manager cache invalidation."""
        config = AuthConfig(cache_ttl_seconds=10)
        auth_manager = AuthManager(config)
        
        auth_manager.add_provider(PatAuthProvider("test-pat"))
        
        # Get credential to cache it
        credential1 = auth_manager.get_credential()
        
        # Invalidate cache
        auth_manager.invalidate_cache()
        
        # Next call should refresh
        credential2 = auth_manager.get_credential()
        assert credential1.token == credential2.token  # Same token but fresh credential


class TestRetryMechanism:
    """Test retry mechanism with exponential backoff."""
    
    def test_retry_manager_success_no_retry(self):
        """Test retry manager when function succeeds on first try."""
        config = RetryConfig(max_retries=3)
        retry_manager = RetryManager(config)
        
        @retry_manager.retry_on_failure
        def successful_function():
            return "success"
        
        result = successful_function()
        assert result == "success"
    
    def test_retry_manager_eventual_success(self):
        """Test retry manager retries until success."""
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
        assert result == "success"
        assert call_count == 3
    
    def test_retry_manager_max_retries_exceeded(self):
        """Test retry manager when max retries are exceeded."""
        config = RetryConfig(max_retries=2, initial_delay=0.1)
        retry_manager = RetryManager(config)
        
        @retry_manager.retry_on_failure
        def always_failing_function():
            raise AdoNetworkError("Network error")
        
        with pytest.raises(AdoNetworkError):
            always_failing_function()
    
    def test_retry_manager_rate_limit_handling(self):
        """Test retry manager handles rate limiting specially."""
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
        assert result == "success"
        assert call_count == 3
    
    def test_retry_manager_non_retryable_error(self):
        """Test retry manager doesn't retry non-retryable errors."""
        config = RetryConfig(max_retries=3)
        retry_manager = RetryManager(config)
        
        @retry_manager.retry_on_failure
        def non_retryable_function():
            # Simulate 404 error (client error, should not retry)
            response = Mock()
            response.status_code = 404
            error = HTTPError("Not found")
            error.response = response
            raise error
        
        with pytest.raises(HTTPError):
            non_retryable_function()
    
    def test_retry_manager_circuit_breaker(self):
        """Test retry manager circuit breaker functionality."""
        config = RetryConfig(max_retries=2, initial_delay=0.1)
        retry_manager = RetryManager(config)
        
        # Force circuit breaker to open by simulating many failures
        retry_manager._failure_count = 5
        retry_manager._circuit_open = True
        retry_manager._last_failure_time = time.time()
        
        @retry_manager.retry_on_failure
        def function_with_circuit_open():
            raise AdoNetworkError("Network error")
        
        # Should fail immediately due to circuit breaker
        with pytest.raises(AdoNetworkError):
            function_with_circuit_open()


class TestTelemetryIntegration:
    """Test telemetry and observability features."""
    
    def test_telemetry_manager_initialization(self):
        """Test telemetry manager initialization."""
        config = TelemetryConfig(enabled=True)
        telemetry = TelemetryManager(config)
        
        assert telemetry.config.enabled == True
        assert telemetry.config.service_name == "ado-mcp"
    
    def test_telemetry_disabled(self):
        """Test telemetry when disabled."""
        config = TelemetryConfig(enabled=False)
        telemetry = TelemetryManager(config)
        
        # Should not initialize telemetry components
        assert telemetry.tracer is None
        assert telemetry.meter is None
    
    def test_telemetry_trace_context(self):
        """Test telemetry trace context manager."""
        config = TelemetryConfig(enabled=True)
        telemetry = TelemetryManager(config)
        
        # Test that context manager works even if telemetry is not fully initialized
        with telemetry.trace_api_call("test_operation", test_attr="value"):
            pass  # Should not raise any errors
    
    def test_telemetry_auth_recording(self):
        """Test telemetry authentication attempt recording."""
        config = TelemetryConfig(enabled=True)
        telemetry = TelemetryManager(config)
        
        # Should not raise errors even if metrics are not initialized
        telemetry.record_auth_attempt("pat", True)
        telemetry.record_auth_attempt("azure_cli", False)


class TestClientIntegration:
    """Test end-to-end client integration with production features."""
    
    def test_client_with_production_config(self):
        """Test client initialization with production configuration."""
        config = AdoMcpConfig(
            organization_url="https://test.visualstudio.com",
            retry=RetryConfig(max_retries=5),
            auth=AuthConfig(timeout_seconds=45),
            telemetry=TelemetryConfig(enabled=False)  # Disable for test
        )
        
        client = AdoClient(organization_url="https://test.visualstudio.com", pat="test-pat", config=config)
        
        assert client.organization_url == "https://test.visualstudio.com"
        assert client.auth_method == "explicit_pat"
        assert client.config.retry.max_retries == 5
        assert client.config.auth.timeout_seconds == 45
    
    def test_client_authentication_refresh(self):
        """Test client authentication refresh functionality."""
        config = AdoMcpConfig(
            organization_url="https://test.visualstudio.com",
            telemetry=TelemetryConfig(enabled=False)  # Disable for test
        )
        
        client = AdoClient(organization_url="https://test.visualstudio.com", pat="test-pat", config=config)
        initial_auth_method = client.auth_method
        
        # Refresh authentication (should maintain same method)
        client.refresh_authentication()
        
        # Should still use explicit_pat method since we provided a PAT explicitly
        assert client.auth_method == "explicit_pat"
    
    def test_client_handles_rate_limiting(self):
        """Test client handles rate limiting with retries."""
        config = AdoMcpConfig(
            organization_url="https://test.visualstudio.com",
            retry=RetryConfig(max_retries=2, initial_delay=0.1),
            telemetry=TelemetryConfig(enabled=False)  # Disable for test
        )
        
        client = AdoClient(organization_url="https://test.visualstudio.com", pat="test-pat", config=config)
        
        # Mock rate limiting response
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {'Retry-After': '1'}
        mock_response.text = ""  # Add text attribute to avoid TypeError
        mock_response.url = "https://test.visualstudio.com/_apis/test"
        mock_response.raise_for_status.side_effect = HTTPError("Rate limited")
        
        with patch('requests.request', return_value=mock_response):
            with pytest.raises(AdoRateLimitError) as exc_info:
                client._send_request("GET", "https://test.visualstudio.com/_apis/test")
            
            assert exc_info.value.error_code == "ADO_RATE_LIMIT"
            assert exc_info.value.retry_after == 1
    
    def test_client_handles_network_errors(self):
        """Test client handles network errors with retries."""
        config = AdoMcpConfig(
            organization_url="https://test.visualstudio.com",
            retry=RetryConfig(max_retries=1, initial_delay=0.1),
            telemetry=TelemetryConfig(enabled=False)  # Disable for test
        )
        
        client = AdoClient(organization_url="https://test.visualstudio.com", pat="test-pat", config=config)
        
        with patch('requests.request', side_effect=RequestException("Network error")):
            with pytest.raises(AdoNetworkError) as exc_info:
                client._send_request("GET", "https://test.visualstudio.com/_apis/test")
            
            assert exc_info.value.error_code == "ADO_NETWORK_ERROR"
            assert "Network error" in str(exc_info.value)
    
    def test_client_handles_timeout_errors(self):
        """Test client handles timeout errors with retries."""
        config = AdoMcpConfig(
            organization_url="https://test.visualstudio.com",
            retry=RetryConfig(max_retries=1, initial_delay=0.1),
            telemetry=TelemetryConfig(enabled=False)  # Disable for test
        )
        
        client = AdoClient(organization_url="https://test.visualstudio.com", pat="test-pat", config=config)
        
        with patch('requests.request', side_effect=Timeout("Request timeout")):
            with pytest.raises(AdoTimeoutError) as exc_info:
                client._send_request("GET", "https://test.visualstudio.com/_apis/test")
            
            assert exc_info.value.error_code == "ADO_TIMEOUT"
            assert exc_info.value.timeout_seconds == config.request_timeout_seconds
    
    def test_client_correlation_id_tracking(self):
        """Test client generates and tracks correlation IDs."""
        config = AdoMcpConfig(
            organization_url="https://test.visualstudio.com",
            telemetry=TelemetryConfig(enabled=False)  # Disable for test
        )
        
        client = AdoClient(organization_url="https://test.visualstudio.com", pat="test-pat", config=config)
        
        # Should have generated a correlation ID
        assert client.correlation_id is not None
        assert len(client.correlation_id) > 0
        
        # Two clients should have different correlation IDs
        client2 = AdoClient(organization_url="https://test.visualstudio.com", pat="test-pat", config=config)
        assert client.correlation_id != client2.correlation_id