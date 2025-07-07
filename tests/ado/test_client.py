# tests/test_client.py
import os
import pytest
import requests
from ado.client import AdoClient

# These environment variables are expected to be set by your Taskfile
ADO_ORGANIZATION_URL = os.environ.get("ADO_ORGANIZATION_URL")
ADO_PAT = os.environ.get("AZURE_DEVOPS_EXT_PAT")

requires_ado_creds = pytest.mark.skipif(
    not all([ADO_ORGANIZATION_URL, ADO_PAT]),
    reason="Skipping E2E test: ADO_ORGANIZATION_URL or AZURE_DEVOPS_EXT_PAT not set."
)


@requires_ado_creds
def test_ado_client_connects_successfully():
    client = AdoClient(organization_url=ADO_ORGANIZATION_URL)
    response = client.check_authentication()

    assert response is not None, "The API response should not be None."
    assert response is True, "The Client Authentication returned False with a valid token"


def test_ado_client_raises_error_if_token_is_invalid(monkeypatch):
    monkeypatch.setenv("AZURE_DEVOPS_EXT_PAT", "this-is-not-a-real-token")

    client = AdoClient(organization_url=ADO_ORGANIZATION_URL)

    response = client.check_authentication()
    assert response is not None, "The API response should not be None."
    assert response is not True, "The Client Authentication returned True with a bad token"


def test_ado_client_init_raises_error_if_pat_is_missing(monkeypatch):
    monkeypatch.delenv("AZURE_DEVOPS_EXT_PAT", raising=False)

    with pytest.raises(ValueError, match="AZURE_DEVOPS_EXT_PAT environment variable not set."):
        AdoClient(organization_url=ADO_ORGANIZATION_URL)
