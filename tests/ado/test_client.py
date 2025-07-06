# tests/test_client.py
import os
import pytest
import requests
from ado.client import AdoClient

# These environment variables are expected to be set by your Taskfile
ADO_ORGANIZATION_URL = os.environ.get("ADO_ORGANIZATION_URL")
ADO_PAT = os.environ.get("AZURE_DEVOPS_EXT_PAT")

# This is a pytest marker that will skip the test if the credentials are not found.
# This prevents test failures in environments where secrets aren't configured.
requires_ado_creds = pytest.mark.skipif(
    not all([ADO_ORGANIZATION_URL, ADO_PAT]),
    reason="Skipping E2E test: ADO_ORGANIZATION_URL or AZURE_DEVOPS_EXT_PAT not set."
)


@requires_ado_creds
def test_ado_client_connects_successfully():
    """
    Validates that the AdoClient can be initialized and can successfully
    authenticate against the Azure DevOps API using environment credentials.
    """
    # 1. Initialize the client
    # This will raise a ValueError if the PAT is missing, but our skipif marker handles that.
    client = AdoClient(organization_url=ADO_ORGANIZATION_URL)

    # 2. Make a live API call to check the connection
    # This will raise an HTTPError if authentication fails.
    response = client.check_authentication()

    # 3. Assert that the connection was successful
    assert response is not None, "The API response should not be None."
    assert "authenticatedUser" in response, "A successful connection should return user data."
    print(f"\nSuccessfully authenticated as: {response['authenticatedUser']['providerDisplayName']}")

def test_ado_client_init_raises_error_if_pat_is_missing(monkeypatch):
    """
    Verifies that the AdoClient constructor raises a ValueError
    if the AZURE_DEVOPS_EXT_PAT environment variable is not set.
    """
    # ARRANGE: Temporarily remove the environment variable for this test.
    # The `raising=False` argument prevents an error if the variable wasn't set to begin with.
    monkeypatch.delenv("AZURE_DEVOPS_EXT_PAT", raising=False)

    # ACT & ASSERT: Check that initializing the client raises the correct error.
    with pytest.raises(ValueError, match="AZURE_DEVOPS_EXT_PAT environment variable not set."):
        AdoClient(organization_url="https://dev.azure.com/anyorg")

@pytest.fixture
def mock_ado_client(monkeypatch) -> AdoClient:
    """
    Provides an AdoClient instance for unit tests.
    It uses monkeypatch to set a dummy PAT, so no real credentials are needed.
    """
    # We don't need a real PAT for these tests, so we set a dummy value.
    monkeypatch.setenv("AZURE_DEVOPS_EXT_PAT", "dummy-pat-for-testing")
    return AdoClient(organization_url="https://dev.azure.com/mockorg")


# --- Unit Tests for Failure Branches ---

def test_send_request_logs_details_on_http_error(mocker, capsys, mock_ado_client):
    """
    Verifies that when a 4xx/5xx error occurs, the detailed response
    from the server is captured and printed.
    """
    # 1. ARRANGE: Create a mock response and configure it to raise an HTTPError.
    # We simulate the server returning a 404 Not Found error.
    mock_response = mocker.Mock()
    error_body = '{"$id":"1", "message":"Page not found."}'
    http_error = requests.exceptions.HTTPError(response=mock_response)

    # Configure the mock response object to behave like a real error response
    mock_response.text = error_body
    mock_response.raise_for_status.side_effect = http_error

    # Patch `requests.request` to return our controlled, failing response
    mocker.patch("requests.request", return_value=mock_response)

    # 2. ACT & ASSERT: Call the client and verify it raises the expected exception.
    with pytest.raises(requests.exceptions.HTTPError):
        mock_ado_client.check_authentication()

    # 3. ASSERT (LOGS): Check that our detailed error logging was printed.
    captured = capsys.readouterr()
    assert "--- HTTP Error Details ---" in captured.out
    assert f"API Response Body: {error_body}" in captured.out


def test_send_request_handles_network_connection_error(mocker, capsys, mock_ado_client):
    """
    Verifies that a generic network error (like a DNS failure or connection
    refused) is caught and logged correctly.
    """
    # 1. ARRANGE: Patch `requests.request` to raise a ConnectionError directly.
    error_message = "Failed to establish a new connection"
    mocker.patch(
        "requests.request",
        side_effect=requests.exceptions.ConnectionError(error_message)
    )

    # 2. ACT & ASSERT: Call the client and verify it raises the right exception.
    with pytest.raises(requests.exceptions.ConnectionError):
        mock_ado_client.check_authentication()

    # 3. ASSERT (LOGS): Check that the generic network error message was printed.
    captured = capsys.readouterr()
    assert "An unexpected network error occurred" in captured.out
    assert error_message in captured.out
