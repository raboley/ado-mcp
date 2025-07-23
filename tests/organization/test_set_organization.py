import os
import pytest
from fastmcp.client import Client

from server import mcp
from tests.ado.test_client import requires_ado_creds

pytestmark = pytest.mark.asyncio

@pytest.fixture
async def mcp_client():
    async with Client(mcp) as client:
        yield client

@requires_ado_creds
async def test_set_organization_success(mcp_client: Client):
    organization_url = os.environ.get("ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley")

    result = await mcp_client.call_tool(
        "set_ado_organization", {"organization_url": organization_url}
    )

    response = result.data
    assert response is not None, f"Expected response data but got None"
    if isinstance(response, dict):
        assert "result" in response or "success" in response, (
            f"Expected 'result' or 'success' field in response but got: {response}"
        )
        success = response.get("result", response.get("success"))
        assert success is True, f"Expected organization setting to succeed but got: {success}"
    else:
        assert response is True, (
            f"Expected True for organization setting success but got: {response}"
        )

@requires_ado_creds
async def test_set_organization_failure_and_recovery(mcp_client: Client):
    bad_org_url = "https://dev.azure.com/NonExistentOrg123456"

    try:
        result = await mcp_client.call_tool(
            "set_ado_organization", {"organization_url": bad_org_url}
        )
        response = result.data
    except Exception:
        pass

    good_org_url = os.environ.get("ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley")

    result = await mcp_client.call_tool("set_ado_organization", {"organization_url": good_org_url})

    response = result.data
    assert response is not None, f"Expected recovery response data but got None"
    if isinstance(response, dict):
        success = response.get("result", response.get("success"))
        assert success is True, (
            f"Expected successful recovery to valid organization but got: {success}"
        )
    else:
        assert response is True, f"Expected True for recovery success but got: {response}"

async def test_set_organization_invalid_url(mcp_client: Client):
    invalid_url = "not-a-valid-url"

    try:
        result = await mcp_client.call_tool(
            "set_ado_organization", {"organization_url": invalid_url}
        )
        response = result.data
    except Exception as e:
        error_msg = str(e).lower()
        assert "url" in error_msg or "invalid" in error_msg, (
            f"Expected error message to mention URL validation issue but got: {e}"
        )

async def test_set_organization_empty_url(mcp_client: Client):
    try:
        result = await mcp_client.call_tool("set_ado_organization", {"organization_url": ""})
        response = result.data
        if response and isinstance(response, dict):
            success = response.get("success")
            assert success is False, f"Expected empty URL to be rejected but success was: {success}"
    except Exception:
        pass
