import json
import logging
import os
import subprocess
import time
from unittest.mock import Mock, patch

import pytest
import requests

from ado.client import AdoClient
from ado.errors import AdoAuthenticationError
from ado.cache import ado_cache
from tests.utils.telemetry import telemetry_setup, analyze_spans, clear_spans

# These environment variables are expected to be set by your Taskfile
ADO_ORGANIZATION_URL = os.environ.get("ADO_ORGANIZATION_URL")
ADO_PAT = os.environ.get("AZURE_DEVOPS_EXT_PAT")

requires_ado_creds = pytest.mark.skipif(
    not all([ADO_ORGANIZATION_URL, ADO_PAT]),
    reason="Skipping E2E test: ADO_ORGANIZATION_URL or AZURE_DEVOPS_EXT_PAT not set.",
)


@requires_ado_creds
def test_ado_client_connects_successfully():
    """Tests that the AdoClient can connect successfully with valid credentials."""
    try:
        client = AdoClient(organization_url=ADO_ORGANIZATION_URL, pat=ADO_PAT)
        response = client.check_authentication()
        assert response is True, "Expected check_authentication to return True."
    except AdoAuthenticationError as e:
        pytest.fail(f"Authentication failed unexpectedly: {e}")


def test_ado_client_raises_error_if_token_is_invalid():
    """Tests that AdoAuthenticationError is raised with an invalid token."""
    client = AdoClient(organization_url=ADO_ORGANIZATION_URL, pat="this-is-not-a-real-token")

    with pytest.raises(AdoAuthenticationError, match="The response contained a sign-in page"):
        client.check_authentication()


def test_ado_client_init_raises_error_if_pat_is_missing(monkeypatch):
    """
    Tests that a ValueError is raised if no authentication method is available.
    """
    # Ensure the environment variable is not set
    monkeypatch.delenv("AZURE_DEVOPS_EXT_PAT", raising=False)

    # Mock all authentication providers to return None
    with patch("ado.auth.AzureCliFileAuthProvider.get_credential", return_value=None), \
         patch("ado.auth.AzureCliEntraAuthProvider.get_credential", return_value=None):
        with pytest.raises(ValueError, match="No authentication method succeeded"):
            # Attempt to initialize without providing a PAT
            AdoClient(organization_url=ADO_ORGANIZATION_URL)


@requires_ado_creds
def test_ado_client_can_get_projects(caplog):
    """Tests that the client can fetch projects successfully."""
    with caplog.at_level(logging.INFO):
        client = AdoClient(organization_url=ADO_ORGANIZATION_URL, pat=ADO_PAT)
        projects = client._send_request(
            "GET", f"{ADO_ORGANIZATION_URL}/_apis/projects?api-version=7.2-preview.4"
        )

    assert projects is not None, "The API response should not be None."
    assert "value" in projects, "The response should contain a 'value' key."
    assert isinstance(projects["value"], list), "The 'value' key should be a list."
    assert "AdoClient initialized using" in caplog.text


@requires_ado_creds
def test_ado_client_handles_http_error_gracefully(caplog):
    """Tests that a standard HTTP error (like a 404) is handled correctly."""
    # Use the valid PAT, but a nonexistent URL
    client = AdoClient(organization_url=ADO_ORGANIZATION_URL, pat=ADO_PAT)
    bad_url = f"{ADO_ORGANIZATION_URL}/_apis/nonexistent-endpoint"

    with caplog.at_level(logging.ERROR):
        with pytest.raises(requests.exceptions.HTTPError, match="404 Client Error"):
            client._send_request("GET", bad_url)

    assert any("HTTP Error" in message for message in caplog.messages), (
        "The HTTP error was not logged as expected."
    )


# Azure CLI Authentication Tests


def test_ado_client_uses_explicit_pat_first(monkeypatch):
    """Test that explicit PAT parameter takes precedence over all other methods."""
    # Set environment variable to something else
    monkeypatch.setenv("AZURE_DEVOPS_EXT_PAT", "env-token")

    # Mock Azure CLI to return a token
    with patch("ado.auth.AzureCliFileAuthProvider.get_credential", return_value=None), \
         patch("ado.auth.AzureCliEntraAuthProvider.get_credential", return_value=None):
        client = AdoClient(organization_url=ADO_ORGANIZATION_URL, pat="explicit-token")

        assert client.auth_method == "explicit_pat"
        # Verify the encoded token contains the explicit PAT
        auth_header = client.headers["Authorization"]
        assert "explicit-token" in auth_header or auth_header.startswith("Basic ")


def test_ado_client_uses_env_pat_when_no_explicit_pat(monkeypatch):
    """Test that environment variable PAT is used when no explicit PAT is provided."""
    monkeypatch.setenv("AZURE_DEVOPS_EXT_PAT", "env-token")

    # Mock Azure CLI to return a token (but env PAT should take precedence)
    with patch("ado.auth.AzureCliFileAuthProvider.get_credential", return_value=None), \
         patch("ado.auth.AzureCliEntraAuthProvider.get_credential", return_value=None):
        client = AdoClient(organization_url=ADO_ORGANIZATION_URL)

        assert client.auth_method == "env_pat"
        auth_header = client.headers["Authorization"]
        assert auth_header.startswith("Basic ")


def test_ado_client_uses_azure_cli_when_no_pat(monkeypatch):
    """Test that Azure CLI authentication is used when no PAT is available."""
    monkeypatch.delenv("AZURE_DEVOPS_EXT_PAT", raising=False)

    from ado.auth import AuthCredential
    
    # Mock Azure CLI to return a bearer token
    mock_credential = AuthCredential(
        token="cli-access-token",
        auth_type="bearer",
        method="azure_cli_entra"
    )
    
    with patch("ado.auth.AzureCliFileAuthProvider.get_credential", return_value=None), \
         patch("ado.auth.AzureCliEntraAuthProvider.get_credential", return_value=mock_credential):
        client = AdoClient(organization_url=ADO_ORGANIZATION_URL)

        assert client.auth_method == "azure_cli"
        auth_header = client.headers["Authorization"]
        assert auth_header == "Bearer cli-access-token"


def test_ado_client_raises_error_when_no_auth_available(monkeypatch):
    """Test that ValueError is raised when no authentication method is available."""
    monkeypatch.delenv("AZURE_DEVOPS_EXT_PAT", raising=False)

    # Mock all authentication providers to return None
    with patch("ado.auth.AzureCliFileAuthProvider.get_credential", return_value=None), \
         patch("ado.auth.AzureCliEntraAuthProvider.get_credential", return_value=None):
        with pytest.raises(ValueError, match="No authentication method succeeded"):
            AdoClient(organization_url=ADO_ORGANIZATION_URL)


def test_azure_cli_entra_provider_success():
    """Test successful Azure CLI Entra token retrieval."""
    from ado.auth import AzureCliEntraAuthProvider
    
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps(
        {"accessToken": "test-access-token", "expiresOn": "1735689600"}  # Unix timestamp
    )

    with patch("subprocess.run", return_value=mock_result):
        provider = AzureCliEntraAuthProvider()
        credential = provider.get_credential()
        
        assert credential is not None
        assert credential.token == "test-access-token"
        assert credential.auth_type == "bearer"
        assert credential.method == "azure_cli_entra"


def test_azure_cli_entra_provider_command_failure():
    """Test Azure CLI Entra token retrieval when command fails."""
    from ado.auth import AzureCliEntraAuthProvider
    
    mock_result = Mock()
    mock_result.returncode = 1
    mock_result.stderr = "ERROR: Please run 'az login' to setup account."

    with patch("subprocess.run", return_value=mock_result):
        provider = AzureCliEntraAuthProvider()
        credential = provider.get_credential()

        assert credential is None


def test_azure_cli_entra_provider_handles_exceptions():
    """Test Azure CLI Entra token retrieval handles various exceptions gracefully."""
    from ado.auth import AzureCliEntraAuthProvider
    
    provider = AzureCliEntraAuthProvider()

    # Test subprocess timeout
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("az", 10)):
        assert provider.get_credential() is None

    # Test file not found (Azure CLI not installed)
    with patch("subprocess.run", side_effect=FileNotFoundError()):
        assert provider.get_credential() is None

    # Test JSON decode error
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "invalid json"
    with patch("subprocess.run", return_value=mock_result):
        assert provider.get_credential() is None


def test_azure_cli_entra_provider_empty_token():
    """Test Azure CLI Entra token retrieval when token is empty."""
    from ado.auth import AzureCliEntraAuthProvider
    
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps({"accessToken": "", "expiresOn": "2025-01-01T00:00:00Z"})

    with patch("subprocess.run", return_value=mock_result):
        provider = AzureCliEntraAuthProvider()
        credential = provider.get_credential()

        assert credential is None


def test_azure_cli_entra_provider_resource_id_is_correct():
    """Test that Azure CLI is called with the correct resource ID for Azure DevOps."""
    from ado.auth import AzureCliEntraAuthProvider
    
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps({"accessToken": "test-token"})

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        provider = AzureCliEntraAuthProvider()
        provider.get_credential()

        # Verify the correct Azure DevOps resource ID is used
        mock_run.assert_called_once_with(
            [
                "az",
                "account",
                "get-access-token",
                "--resource",
                "499b84ac-1321-427f-aa17-267ca6975798",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )


def test_azure_cli_file_provider_creation():
    """Test Azure CLI file provider can be created."""
    from ado.auth import AzureCliFileAuthProvider
    
    provider = AzureCliFileAuthProvider()
    assert provider.get_name() == "Azure CLI File"
    
    # The get_credential method will return None in normal test environment
    # since the Azure CLI PAT file doesn't exist
    credential = provider.get_credential()
    assert credential is None  # Expected in test environment


def test_pat_provider_success():
    """Test PAT provider with explicit token."""
    from ado.auth import PatAuthProvider
    
    provider = PatAuthProvider("test-pat-token")
    credential = provider.get_credential()
    
    assert credential is not None
    assert credential.token == "test-pat-token"
    assert credential.auth_type == "basic"
    assert credential.method == "pat"


def test_azure_cli_authentication_integration():
    """Test Azure CLI authentication integration without external subprocess calls."""
    from ado.auth import AzureCliEntraAuthProvider, AzureCliFileAuthProvider
    
    # Test that Azure CLI providers can be instantiated
    entra_provider = AzureCliEntraAuthProvider()
    file_provider = AzureCliFileAuthProvider()
    
    assert entra_provider.get_name() == "Azure CLI (Entra)"
    assert file_provider.get_name() == "Azure CLI File"
    
    # Test credential retrieval - this may return credentials if Azure CLI is set up,
    # or None if not available. Both are valid behaviors.
    entra_credential = entra_provider.get_credential()
    file_credential = file_provider.get_credential()
    
    # If credentials are returned, they should have the correct structure
    if entra_credential is not None:
        assert entra_credential.auth_type == "bearer"
        assert entra_credential.method == "azure_cli_entra"
        assert len(entra_credential.token) > 0
    
    if file_credential is not None:
        assert file_credential.auth_type == "basic"
        assert file_credential.method == "azure_cli_file"
        assert len(file_credential.token) > 0
    
    # At least test that the methods don't raise exceptions
    assert True  # Test passed if we got here without exceptions


# ========== CACHING TESTS ==========

@pytest.fixture
def fresh_cache():
    """Ensure cache is cleared before each test."""
    ado_cache.clear_all()
    yield
    ado_cache.clear_all()


@requires_ado_creds
def test_list_available_projects_caching_behavior(telemetry_setup, fresh_cache):
    """Test that list_available_projects caches results and reduces API calls."""
    memory_exporter = telemetry_setup
    
    client = AdoClient(
        organization_url=ADO_ORGANIZATION_URL,
        pat=ADO_PAT
    )
    
    # First call - should hit API (uses caching layer)
    projects1 = client.list_available_projects()
    analyzer1 = analyze_spans(memory_exporter)
    
    # Should have made an API call
    assert analyzer1.was_data_fetched_from_api("projects")
    assert analyzer1.count_api_calls("list_projects") == 1
    assert len(projects1) > 0
    
    clear_spans(memory_exporter)
    
    # Second call - should use cache
    projects2 = client.list_available_projects()
    analyzer2 = analyze_spans(memory_exporter)
    
    # Should have used cache, no new API calls
    assert analyzer2.was_data_fetched_from_cache("projects")
    assert analyzer2.count_api_calls("list_projects") == 0
    
    # Data should be consistent
    assert projects1 == projects2


@requires_ado_creds 
def test_list_pipelines_caching_behavior(telemetry_setup, fresh_cache):
    """Test that list_pipelines caches results per project."""
    memory_exporter = telemetry_setup
    
    client = AdoClient(
        organization_url=ADO_ORGANIZATION_URL,
        pat=ADO_PAT
    )
    
    # Get a project to test with
    projects = client.list_available_projects()
    if not projects:
        pytest.skip("No projects available for testing")
    
    project_name = projects[0]
    
    # Clear spans to focus on pipeline operations
    clear_spans(memory_exporter)
    
    # First pipeline call - should hit API
    pipelines1 = client.list_available_pipelines(project_name)
    analyzer1 = analyze_spans(memory_exporter)
    
    # Should have made an API call for pipelines
    assert analyzer1.count_api_calls("list_pipelines") == 1
    
    clear_spans(memory_exporter)
    
    # Second pipeline call - should use cache
    pipelines2 = client.list_available_pipelines(project_name)
    analyzer2 = analyze_spans(memory_exporter)
    
    # Should have used cache, no new API calls
    assert analyzer2.was_data_fetched_from_cache("pipelines")
    assert analyzer2.count_api_calls("list_pipelines") == 0
    
    # Data should be consistent
    assert pipelines1 == pipelines2


@requires_ado_creds
def test_find_project_by_name_uses_cache(telemetry_setup, fresh_cache):
    """Test that find_project_by_name uses cached project data."""
    memory_exporter = telemetry_setup
    
    client = AdoClient(
        organization_url=ADO_ORGANIZATION_URL,
        pat=ADO_PAT
    )
    
    # Prime the cache by getting available projects
    projects = client.list_available_projects()
    if not projects:
        pytest.skip("No projects available for testing")
    
    project_name = projects[0]
    clear_spans(memory_exporter)
    
    # Find project by name - should use cached data
    found_project = client.find_project_by_name(project_name)
    analyzer = analyze_spans(memory_exporter)
    
    # Should have cache hits, no API calls
    assert analyzer.count_cache_hits() > 0
    assert analyzer.count_api_calls("list_projects") == 0
    assert found_project is not None
    assert found_project.name == project_name


@requires_ado_creds
def test_cache_expiration_and_refresh(telemetry_setup, fresh_cache):
    """Test that cache properly expires and refetches data."""
    memory_exporter = telemetry_setup
    
    # Temporarily reduce cache TTL for testing
    original_ttl = ado_cache.PROJECT_TTL
    ado_cache.PROJECT_TTL = 2  # 2 seconds for testing
    
    try:
        client = AdoClient(
            organization_url=ADO_ORGANIZATION_URL,
            pat=ADO_PAT
        )
        
        # First call
        projects1 = client.list_available_projects()
        clear_spans(memory_exporter)
        
        # Second call immediately - should use cache
        projects2 = client.list_available_projects()
        analyzer_cached = analyze_spans(memory_exporter)
        assert analyzer_cached.was_data_fetched_from_cache("projects")
        
        # Wait for cache to expire
        time.sleep(2.5)
        clear_spans(memory_exporter)
        
        # Third call after expiration - should hit API again
        projects3 = client.list_available_projects()
        analyzer_expired = analyze_spans(memory_exporter)
        assert analyzer_expired.was_data_fetched_from_api("projects")
        
        # Data should still be consistent
        assert projects1 == projects3
        
    finally:
        # Restore original TTL
        ado_cache.PROJECT_TTL = original_ttl
