import os
import pytest
import requests
from ado.client import AdoClient
from ado.errors import AdoAuthenticationError
import logging

# These environment variables are expected to be set by your Taskfile
ADO_ORGANIZATION_URL = os.environ.get("ADO_ORGANIZATION_URL")
ADO_PAT = os.environ.get("AZURE_DEVOPS_EXT_PAT")

requires_ado_creds = pytest.mark.skipif(
    not all([ADO_ORGANIZATION_URL, ADO_PAT]),
    reason="Skipping E2E test: ADO_ORGANIZATION_URL or AZURE_DEVOPS_EXT_PAT not set."
)


@requires_ado_creds
def test_ado_client_connects_successfully(caplog):
    """Tests that the AdoClient can connect successfully with valid credentials."""
    try:
        client = AdoClient(organization_url=ADO_ORGANIZATION_URL)
        response = client.check_authentication()
        assert response is True, "Expected check_authentication to return True."
    except AdoAuthenticationError as e:
        pytest.fail(f"Authentication failed unexpectedly: {e}")


def test_ado_client_raises_error_if_token_is_invalid(monkeypatch):
    """Tests that AdoAuthenticationError is raised with an invalid token."""
    monkeypatch.setenv("AZURE_DEVOPS_EXT_PAT", "this-is-not-a-real-token")
    client = AdoClient(organization_url=ADO_ORGANIZATION_URL)

    with pytest.raises(AdoAuthenticationError, match="The response contained a sign-in page"):
        client.check_authentication()


def test_ado_client_init_raises_error_if_pat_is_missing(monkeypatch):
    monkeypatch.delenv("AZURE_DEVOPS_EXT_PAT", raising=False)

    with pytest.raises(ValueError, match="AZURE_DEVOPS_EXT_PAT environment variable not set."):
        AdoClient(organization_url=ADO_ORGANIZATION_URL)


@requires_ado_creds
def test_ado_client_can_get_projects(caplog):
    """Tests that the client can fetch projects successfully."""
    with caplog.at_level(logging.INFO):
        client = AdoClient(organization_url=ADO_ORGANIZATION_URL)
        projects = client._send_request("GET", f"{ADO_ORGANIZATION_URL}/_apis/projects?api-version=7.2-preview.4")

    assert projects is not None, "The API response should not be None."
    assert "value" in projects, "The response should contain a 'value' key."
    assert isinstance(projects["value"], list), "The 'value' key should be a list."
    assert len(caplog.messages) > 0, "Logs should have captured some activity."


@requires_ado_creds
def test_ado_client_handles_http_error_gracefully(monkeypatch, caplog):
    """Tests that HTTP errors are logged and raised correctly."""
    monkeypatch.setenv("AZURE_DEVOPS_EXT_PAT", "invalid-pat")
    client = AdoClient(organization_url=ADO_ORGANIZATION_URL)
    bad_url = f"{ADO_ORGANIZATION_URL}/_apis/nonexistent-endpoint"

    with caplog.at_level(logging.ERROR):
        with pytest.raises(requests.exceptions.HTTPError):
            client._send_request("GET", bad_url)

    assert any("HTTP Error" in message for message in caplog.messages), \
        "The HTTP error was not logged as expected."
