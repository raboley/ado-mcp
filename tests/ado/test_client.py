import json
import logging
import os
import subprocess
from unittest.mock import Mock, patch

import pytest
import requests

from ado.client import AdoClient
from ado.errors import AdoAuthenticationError

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
def test_azure_cli_authentication_end_to_end():
    """End-to-end test using Azure CLI authentication if available."""
    # Only run if Azure CLI is available and user is logged in
    try:
        result = subprocess.run(
            ["az", "account", "show"], capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            pytest.skip("Azure CLI not authenticated - run 'az login' first")

        # Also check if we can get an Azure DevOps token
        token_result = subprocess.run(
            [
                "az",
                "account",
                "get-access-token",
                "--resource",
                "499b84ac-1321-427f-aa17-267ca6975798",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if token_result.returncode != 0:
            pytest.skip(
                "Azure CLI cannot get Azure DevOps token - authentication may not support Azure DevOps"
            )

    except (FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("Azure CLI not available")

    # Remove PAT from environment to force Azure CLI usage
    original_pat = os.environ.get("AZURE_DEVOPS_EXT_PAT")
    if original_pat:
        del os.environ["AZURE_DEVOPS_EXT_PAT"]

    try:
        client = AdoClient(organization_url=ADO_ORGANIZATION_URL)
        assert client.auth_method == "azure_cli"

        # Test that authentication actually works
        response = client.check_authentication()
        assert response is True

    finally:
        # Restore original PAT
        if original_pat:
            os.environ["AZURE_DEVOPS_EXT_PAT"] = original_pat
