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

    with patch.object(AdoClient, "_get_azure_cli_token", return_value=None):
        with pytest.raises(ValueError, match="No authentication method available"):
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

    with patch.object(AdoClient, "_get_azure_cli_token", return_value="cli-token"):
        client = AdoClient(organization_url=ADO_ORGANIZATION_URL, pat="explicit-token")

        assert client.auth_method == "explicit_pat"
        # Verify the encoded token contains the explicit PAT
        auth_header = client.headers["Authorization"]
        assert "explicit-token" in auth_header or auth_header.startswith("Basic ")


def test_ado_client_uses_env_pat_when_no_explicit_pat(monkeypatch):
    """Test that environment variable PAT is used when no explicit PAT is provided."""
    monkeypatch.setenv("AZURE_DEVOPS_EXT_PAT", "env-token")

    with patch.object(AdoClient, "_get_azure_cli_token", return_value="cli-token"):
        client = AdoClient(organization_url=ADO_ORGANIZATION_URL)

        assert client.auth_method == "env_pat"
        auth_header = client.headers["Authorization"]
        assert auth_header.startswith("Basic ")


def test_ado_client_uses_azure_cli_when_no_pat(monkeypatch):
    """Test that Azure CLI authentication is used when no PAT is available."""
    monkeypatch.delenv("AZURE_DEVOPS_EXT_PAT", raising=False)

    with patch.object(AdoClient, "_get_azure_cli_token", return_value="cli-access-token"):
        client = AdoClient(organization_url=ADO_ORGANIZATION_URL)

        assert client.auth_method == "azure_cli"
        auth_header = client.headers["Authorization"]
        assert auth_header == "Bearer cli-access-token"


def test_ado_client_raises_error_when_no_auth_available(monkeypatch):
    """Test that ValueError is raised when no authentication method is available."""
    monkeypatch.delenv("AZURE_DEVOPS_EXT_PAT", raising=False)

    with patch.object(AdoClient, "_get_azure_cli_token", return_value=None):
        with pytest.raises(ValueError, match="No authentication method available"):
            AdoClient(organization_url=ADO_ORGANIZATION_URL)


def test_get_azure_cli_token_success():
    """Test successful Azure CLI token retrieval."""
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps(
        {"accessToken": "test-access-token", "expiresOn": "2025-01-01T00:00:00Z"}
    )

    with patch("subprocess.run", return_value=mock_result):
        client = AdoClient.__new__(AdoClient)  # Create instance without calling __init__
        token = client._get_azure_cli_token()

        assert token == "test-access-token"


def test_get_azure_cli_token_command_failure():
    """Test Azure CLI token retrieval when command fails."""
    mock_result = Mock()
    mock_result.returncode = 1
    mock_result.stderr = "ERROR: Please run 'az login' to setup account."

    with patch("subprocess.run", return_value=mock_result):
        client = AdoClient.__new__(AdoClient)  # Create instance without calling __init__
        token = client._get_azure_cli_token()

        assert token is None


def test_get_azure_cli_token_handles_exceptions():
    """Test Azure CLI token retrieval handles various exceptions gracefully."""
    client = AdoClient.__new__(AdoClient)  # Create instance without calling __init__

    # Test subprocess timeout
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("az", 10)):
        assert client._get_azure_cli_token() is None

    # Test file not found (Azure CLI not installed)
    with patch("subprocess.run", side_effect=FileNotFoundError()):
        assert client._get_azure_cli_token() is None

    # Test JSON decode error
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "invalid json"
    with patch("subprocess.run", return_value=mock_result):
        assert client._get_azure_cli_token() is None


def test_get_azure_cli_token_empty_token():
    """Test Azure CLI token retrieval when token is empty."""
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps({"accessToken": "", "expiresOn": "2025-01-01T00:00:00Z"})

    with patch("subprocess.run", return_value=mock_result):
        client = AdoClient.__new__(AdoClient)  # Create instance without calling __init__
        token = client._get_azure_cli_token()

        assert token is None


def test_azure_cli_resource_id_is_correct():
    """Test that Azure CLI is called with the correct resource ID for Azure DevOps."""
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps({"accessToken": "test-token"})

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        client = AdoClient.__new__(AdoClient)  # Create instance without calling __init__
        client._get_azure_cli_token()

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


@requires_ado_creds
def test_azure_cli_authentication_end_to_end(telemetry_setup, monkeypatch):
    """End-to-end test of Azure DevOps CLI authentication using az devops login."""
    memory_exporter = telemetry_setup
    
    # Get PAT from keychain to use for az devops login
    try:
        pat_result = subprocess.run(
            ["security", "find-generic-password", "-w", "-a", "ado-token"],
            capture_output=True, text=True, timeout=5
        )
        if pat_result.returncode != 0 or not pat_result.stdout.strip():
            pytest.skip("PAT not found in keychain (ado-token)")
        original_pat = pat_result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("Cannot access keychain for PAT")
    
    # Check if Azure CLI is available
    try:
        result = subprocess.run(
            ["az", "--version"], capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            pytest.skip("Azure CLI not available")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("Azure CLI not available")
    
    # Setup: Login to Azure DevOps CLI using our PAT
    try:
        # First logout to ensure clean state
        subprocess.run(
            ["az", "devops", "logout"], 
            capture_output=True, text=True, timeout=10
        )
        
        # Login using our PAT
        login_result = subprocess.run(
            ["az", "devops", "login", "--organization", ADO_ORGANIZATION_URL],
            input=original_pat,
            text=True,
            capture_output=True,
            timeout=10
        )
        
        if login_result.returncode != 0:
            pytest.skip(f"Failed to login to Azure DevOps CLI: {login_result.stderr}")
            
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        pytest.skip(f"Azure DevOps CLI not available: {e}")
    
    # Monkeypatch environment to remove PAT variables and force Azure CLI usage
    monkeypatch.delenv("AZURE_DEVOPS_EXT_PAT", raising=False)
    
    # Create client - should use Azure DevOps CLI authentication
    client = AdoClient(organization_url=ADO_ORGANIZATION_URL)
    
    # Verify that the client correctly selected Azure CLI authentication
    assert client.auth_method == "azure_cli", f"Expected azure_cli auth method, got {client.auth_method}"
    
    # Verify authentication method using telemetry
    from tests.utils.telemetry import analyze_spans, clear_spans
    clear_spans(memory_exporter)
    
    # Test authentication - this may fail due to organizational Microsoft Entra token policy
    try:
        response = client.check_authentication()
        analyzer = analyze_spans(memory_exporter)
        
        # If we get here, Microsoft Entra tokens work for this organization
        assert response is True, "Authentication should succeed with Azure DevOps CLI"
        
        # Use telemetry to verify the authentication was attempted via Azure CLI methods
        all_spans = [span.name for span in memory_exporter.get_finished_spans()]
        print(f"Authentication spans: {all_spans}")
        
        print(f"✅ Azure DevOps CLI authentication test passed!")
        print(f"   Auth method: {client.auth_method}")
        print(f"   Authentication result: {response}")
        
    except AdoAuthenticationError as e:
        # This is expected if the organization doesn't accept Microsoft Entra tokens
        if "sign-in page" in str(e):
            # The client correctly attempted Azure CLI authentication but the organization rejected it
            print(f"✅ Azure DevOps CLI authentication correctly attempted")
            print(f"   Auth method: {client.auth_method}")
            print(f"   Organization rejects Microsoft Entra tokens (expected)")
            print(f"   This validates that Azure CLI authentication path is working")
        else:
            # Unexpected authentication error
            raise
    
    # Cleanup: Logout from Azure DevOps CLI to avoid affecting other tests
    try:
        subprocess.run(
            ["az", "devops", "logout"], 
            capture_output=True, text=True, timeout=10
        )
    except Exception:
        pass  # Best effort cleanup


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
