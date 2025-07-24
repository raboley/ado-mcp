import json
import logging
import os
import subprocess
import time
from unittest.mock import Mock, patch

import pytest
import requests

from ado.cache import ado_cache
from ado.client import AdoClient
from ado.errors import AdoAuthenticationError
from tests.utils.telemetry import analyze_spans, clear_spans

ADO_ORGANIZATION_URL = os.environ.get("ADO_ORGANIZATION_URL")
ADO_PAT = os.environ.get("AZURE_DEVOPS_EXT_PAT")

requires_ado_creds = pytest.mark.skipif(
    not all([ADO_ORGANIZATION_URL, ADO_PAT]),
    reason="Skipping E2E test: ADO_ORGANIZATION_URL or AZURE_DEVOPS_EXT_PAT not set.",
)


@requires_ado_creds
def test_ado_client_connects_successfully():
    try:
        client = AdoClient(organization_url=ADO_ORGANIZATION_URL, pat=ADO_PAT)
        response = client.check_authentication()
        assert response is True, f"Authentication check failed: expected True but got {response}"
    except AdoAuthenticationError as e:
        pytest.fail(f"Authentication failed unexpectedly: {e}")


def test_ado_client_raises_error_if_token_is_invalid():
    client = AdoClient(organization_url=ADO_ORGANIZATION_URL, pat="this-is-not-a-real-token")

    with pytest.raises(AdoAuthenticationError, match="The response contained a sign-in page"):
        client.check_authentication()


def test_ado_client_init_raises_error_if_pat_is_missing(monkeypatch):
    monkeypatch.delenv("AZURE_DEVOPS_EXT_PAT", raising=False)

    with (
        patch("ado.auth.AzureCliFileAuthProvider.get_credential", return_value=None),
        patch("ado.auth.AzureCliEntraAuthProvider.get_credential", return_value=None),
    ):
        with pytest.raises(ValueError, match="No authentication method succeeded"):
            AdoClient(organization_url=ADO_ORGANIZATION_URL)


@requires_ado_creds
def test_ado_client_can_get_projects(caplog):
    with caplog.at_level(logging.INFO):
        client = AdoClient(organization_url=ADO_ORGANIZATION_URL, pat=ADO_PAT)
        projects = client._send_request(
            "GET", f"{ADO_ORGANIZATION_URL}/_apis/projects?api-version=7.2-preview.4"
        )

    assert projects is not None, "API response was None, expected a dictionary with projects data"
    assert "value" in projects, f"Response missing 'value' key: {list(projects.keys())}"
    assert isinstance(projects["value"], list), (
        f"'value' should be list but got {type(projects['value'])}"
    )
    assert "AdoClient initialized using" in caplog.text, (
        f"Initialization log not found in: {caplog.text}"
    )


@requires_ado_creds
def test_ado_client_handles_http_error_gracefully(caplog):
    client = AdoClient(organization_url=ADO_ORGANIZATION_URL, pat=ADO_PAT)
    bad_url = f"{ADO_ORGANIZATION_URL}/_apis/nonexistent-endpoint"

    with caplog.at_level(logging.ERROR):
        with pytest.raises(requests.exceptions.HTTPError, match="404 Client Error"):
            client._send_request("GET", bad_url)

    assert any("HTTP Error" in message for message in caplog.messages), (
        f"HTTP error not logged as expected. Log messages: {caplog.messages}"
    )


def test_ado_client_uses_explicit_pat_first(monkeypatch):
    monkeypatch.setenv("AZURE_DEVOPS_EXT_PAT", "env-token")

    with (
        patch("ado.auth.AzureCliFileAuthProvider.get_credential", return_value=None),
        patch("ado.auth.AzureCliEntraAuthProvider.get_credential", return_value=None),
    ):
        client = AdoClient(organization_url=ADO_ORGANIZATION_URL, pat="explicit-token")

        assert client.auth_method == "explicit_pat", (
            f"Expected 'explicit_pat' but got '{client.auth_method}'"
        )
        auth_header = client.headers["Authorization"]
        assert "explicit-token" in auth_header or auth_header.startswith("Basic "), (
            f"Auth header should contain explicit token or Basic auth: {auth_header}"
        )


def test_ado_client_uses_env_pat_when_no_explicit_pat(monkeypatch):
    monkeypatch.setenv("AZURE_DEVOPS_EXT_PAT", "env-token")

    with (
        patch("ado.auth.AzureCliFileAuthProvider.get_credential", return_value=None),
        patch("ado.auth.AzureCliEntraAuthProvider.get_credential", return_value=None),
    ):
        client = AdoClient(organization_url=ADO_ORGANIZATION_URL)

        assert client.auth_method == "env_pat", f"Expected 'env_pat' but got '{client.auth_method}'"
        auth_header = client.headers["Authorization"]
        assert auth_header.startswith("Basic "), (
            f"Expected Basic auth header but got: {auth_header}"
        )


def test_ado_client_uses_azure_cli_when_no_pat(monkeypatch):
    monkeypatch.delenv("AZURE_DEVOPS_EXT_PAT", raising=False)

    from ado.auth import AuthCredential

    mock_credential = AuthCredential(
        token="cli-access-token", auth_type="bearer", method="azure_cli_entra"
    )

    with (
        patch("ado.auth.AzureCliFileAuthProvider.get_credential", return_value=None),
        patch("ado.auth.AzureCliEntraAuthProvider.get_credential", return_value=mock_credential),
    ):
        client = AdoClient(organization_url=ADO_ORGANIZATION_URL)

        assert client.auth_method == "azure_cli", (
            f"Expected 'azure_cli' but got '{client.auth_method}'"
        )
        auth_header = client.headers["Authorization"]
        assert auth_header == "Bearer cli-access-token", (
            f"Expected Bearer token but got: {auth_header}"
        )


def test_ado_client_raises_error_when_no_auth_available(monkeypatch):
    monkeypatch.delenv("AZURE_DEVOPS_EXT_PAT", raising=False)

    with (
        patch("ado.auth.AzureCliFileAuthProvider.get_credential", return_value=None),
        patch("ado.auth.AzureCliEntraAuthProvider.get_credential", return_value=None),
    ):
        with pytest.raises(ValueError, match="No authentication method succeeded"):
            AdoClient(organization_url=ADO_ORGANIZATION_URL)


def test_azure_cli_entra_provider_success():
    from ado.auth import AzureCliEntraAuthProvider

    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps({"accessToken": "test-access-token", "expiresOn": "1735689600"})

    with patch("subprocess.run", return_value=mock_result):
        provider = AzureCliEntraAuthProvider()
        credential = provider.get_credential()

        assert credential is not None, "Expected credential object but got None"
        assert credential.token == "test-access-token", (
            f"Expected 'test-access-token' but got '{credential.token}'"
        )
        assert credential.auth_type == "bearer", (
            f"Expected 'bearer' but got '{credential.auth_type}'"
        )
        assert credential.method == "azure_cli_entra", (
            f"Expected 'azure_cli_entra' but got '{credential.method}'"
        )


def test_azure_cli_entra_provider_command_failure():
    from ado.auth import AzureCliEntraAuthProvider

    mock_result = Mock()
    mock_result.returncode = 1
    mock_result.stderr = "ERROR: Please run 'az login' to setup account."

    with patch("subprocess.run", return_value=mock_result):
        provider = AzureCliEntraAuthProvider()
        credential = provider.get_credential()

        assert credential is None, "Expected None when command fails but got a credential"


def test_azure_cli_entra_provider_handles_exceptions():
    from ado.auth import AzureCliEntraAuthProvider

    provider = AzureCliEntraAuthProvider()

    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("az", 10)):
        result = provider.get_credential()
        assert result is None, "Expected None on timeout but got a credential"

    with patch("subprocess.run", side_effect=FileNotFoundError()):
        result = provider.get_credential()
        assert result is None, "Expected None when CLI not found but got a credential"

    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "invalid json"
    with patch("subprocess.run", return_value=mock_result):
        result = provider.get_credential()
        assert result is None, "Expected None on JSON parse error but got a credential"


def test_azure_cli_entra_provider_empty_token():
    from ado.auth import AzureCliEntraAuthProvider

    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps({"accessToken": "", "expiresOn": "2025-01-01T00:00:00Z"})

    with patch("subprocess.run", return_value=mock_result):
        provider = AzureCliEntraAuthProvider()
        credential = provider.get_credential()

        assert credential is None, "Expected None for empty token but got a credential"


def test_azure_cli_entra_provider_resource_id_is_correct():
    from ado.auth import AzureCliEntraAuthProvider

    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps({"accessToken": "test-token"})

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        provider = AzureCliEntraAuthProvider()
        provider.get_credential()

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
    from ado.auth import AzureCliFileAuthProvider

    provider = AzureCliFileAuthProvider()
    assert provider.get_name() == "Azure CLI File", (
        f"Expected 'Azure CLI File' but got '{provider.get_name()}'"
    )

    credential = provider.get_credential()
    assert credential is None, "Expected None in test environment where CLI PAT file doesn't exist"


def test_pat_provider_success():
    from ado.auth import PatAuthProvider

    provider = PatAuthProvider("test-pat-token")
    credential = provider.get_credential()

    assert credential is not None, "Expected credential object but got None"
    assert credential.token == "test-pat-token", (
        f"Expected 'test-pat-token' but got '{credential.token}'"
    )
    assert credential.auth_type == "basic", f"Expected 'basic' but got '{credential.auth_type}'"
    assert credential.method == "pat", f"Expected 'pat' but got '{credential.method}'"


def test_azure_cli_authentication_integration():
    from ado.auth import AzureCliEntraAuthProvider, AzureCliFileAuthProvider

    entra_provider = AzureCliEntraAuthProvider()
    file_provider = AzureCliFileAuthProvider()

    assert entra_provider.get_name() == "Azure CLI (Entra)", (
        f"Expected 'Azure CLI (Entra)' but got '{entra_provider.get_name()}'"
    )
    assert file_provider.get_name() == "Azure CLI File", (
        f"Expected 'Azure CLI File' but got '{file_provider.get_name()}'"
    )

    entra_credential = entra_provider.get_credential()
    file_credential = file_provider.get_credential()

    if entra_credential is not None:
        assert entra_credential.auth_type == "bearer", (
            f"Expected 'bearer' but got '{entra_credential.auth_type}'"
        )
        assert entra_credential.method == "azure_cli_entra", (
            f"Expected 'azure_cli_entra' but got '{entra_credential.method}'"
        )
        assert len(entra_credential.token) > 0, "Token should not be empty"

    if file_credential is not None:
        assert file_credential.auth_type == "basic", (
            f"Expected 'basic' but got '{file_credential.auth_type}'"
        )
        assert file_credential.method == "azure_cli_file", (
            f"Expected 'azure_cli_file' but got '{file_credential.method}'"
        )
        assert len(file_credential.token) > 0, "Token should not be empty"

    assert True


@pytest.fixture
def fresh_cache():
    ado_cache.clear_all()
    yield
    ado_cache.clear_all()


@requires_ado_creds
def test_list_available_projects_caching_behavior(telemetry_setup, fresh_cache):
    memory_exporter = telemetry_setup

    client = AdoClient(organization_url=ADO_ORGANIZATION_URL, pat=ADO_PAT)

    projects1 = client.list_available_projects()
    analyzer1 = analyze_spans(memory_exporter)

    assert analyzer1.was_data_fetched_from_api("projects"), (
        "First call should have fetched data from API"
    )
    assert analyzer1.count_api_calls("list_projects") == 1, (
        f"Expected 1 API call but got {analyzer1.count_api_calls('list_projects')}"
    )
    assert len(projects1) > 0, "Should have retrieved at least one project"

    clear_spans(memory_exporter)

    projects2 = client.list_available_projects()
    analyzer2 = analyze_spans(memory_exporter)

    assert analyzer2.was_data_fetched_from_cache("projects"), "Second call should have used cache"
    assert analyzer2.count_api_calls("list_projects") == 0, (
        f"Expected 0 API calls but got {analyzer2.count_api_calls('list_projects')}"
    )

    assert projects1 == projects2, "Cached data should match original data"


@requires_ado_creds
def test_list_pipelines_caching_behavior(telemetry_setup, fresh_cache):
    memory_exporter = telemetry_setup

    client = AdoClient(organization_url=ADO_ORGANIZATION_URL, pat=ADO_PAT)

    projects = client.list_available_projects()
    if not projects:
        pytest.skip("No projects available for testing")

    project_name = projects[0]

    clear_spans(memory_exporter)

    pipelines1 = client.list_available_pipelines(project_name)
    analyzer1 = analyze_spans(memory_exporter)

    assert analyzer1.count_api_calls("list_pipelines") == 1, (
        f"Expected 1 API call but got {analyzer1.count_api_calls('list_pipelines')}"
    )

    clear_spans(memory_exporter)

    pipelines2 = client.list_available_pipelines(project_name)
    analyzer2 = analyze_spans(memory_exporter)

    assert analyzer2.was_data_fetched_from_cache("pipelines"), "Second call should have used cache"
    assert analyzer2.count_api_calls("list_pipelines") == 0, (
        f"Expected 0 API calls but got {analyzer2.count_api_calls('list_pipelines')}"
    )

    assert pipelines1 == pipelines2, "Cached data should match original data"


@requires_ado_creds
def test_find_project_by_name_uses_cache(telemetry_setup, fresh_cache):
    memory_exporter = telemetry_setup

    client = AdoClient(organization_url=ADO_ORGANIZATION_URL, pat=ADO_PAT)

    projects = client.list_available_projects()
    if not projects:
        pytest.skip("No projects available for testing")

    project_name = projects[0]
    clear_spans(memory_exporter)

    found_project = client.find_project_by_name(project_name)
    analyzer = analyze_spans(memory_exporter)

    assert analyzer.count_cache_hits() > 0, "Should have cache hits when finding project by name"
    assert analyzer.count_api_calls("list_projects") == 0, (
        f"Expected 0 API calls but got {analyzer.count_api_calls('list_projects')}"
    )
    assert found_project is not None, f"Should have found project '{project_name}' but got None"
    assert found_project.name == project_name, (
        f"Found project name '{found_project.name}' doesn't match expected '{project_name}'"
    )


@requires_ado_creds
def test_cache_expiration_and_refresh(telemetry_setup, fresh_cache):
    memory_exporter = telemetry_setup

    original_ttl = ado_cache.PROJECT_TTL
    ado_cache.PROJECT_TTL = 2

    try:
        client = AdoClient(organization_url=ADO_ORGANIZATION_URL, pat=ADO_PAT)

        projects1 = client.list_available_projects()
        clear_spans(memory_exporter)

        client.list_available_projects()
        analyzer_cached = analyze_spans(memory_exporter)
        assert analyzer_cached.was_data_fetched_from_cache("projects"), (
            "Immediate second call should use cache"
        )

        time.sleep(2.5)
        clear_spans(memory_exporter)

        projects3 = client.list_available_projects()
        analyzer_expired = analyze_spans(memory_exporter)
        assert analyzer_expired.was_data_fetched_from_api("projects"), (
            "Call after expiration should fetch from API"
        )

        assert projects1 == projects3, "Data should be consistent before and after cache expiration"

    finally:
        ado_cache.PROJECT_TTL = original_ttl
