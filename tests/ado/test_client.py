import logging
import os

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
    Tests that a ValueError is raised if the PAT is not provided either
    directly or via environment variables.
    """
    # Ensure the environment variable is not set
    monkeypatch.delenv("AZURE_DEVOPS_EXT_PAT", raising=False)

    with pytest.raises(ValueError, match="Personal Access Token .* not provided or found"):
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
    assert "AdoClient initialized." in caplog.text


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
