import os

import pytest
from fastmcp.client import Client

from server import mcp
from tests.ado.test_client import requires_ado_creds

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def mcp_client():
    async with Client(mcp) as client:
        initial_org_url = os.environ.get(
            "ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley"
        )
        await client.call_tool("set_ado_organization", {"organization_url": initial_org_url})
        yield client


@requires_ado_creds
async def test_check_authentication_success(mcp_client: Client):
    result = await mcp_client.call_tool("check_ado_authentication")

    auth_result = result.data
    assert auth_result is True, (
        f"Expected authentication to succeed with valid credentials but got: {auth_result}"
    )


@requires_ado_creds
async def test_check_authentication_after_org_change(mcp_client: Client):
    result = await mcp_client.call_tool("check_ado_authentication")
    assert result.data is True, f"Expected initial authentication to work but got: {result.data}"

    org_url = os.environ.get("ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley")
    await mcp_client.call_tool("set_ado_organization", {"organization_url": org_url})

    result = await mcp_client.call_tool("check_ado_authentication")
    assert result.data is True, (
        f"Expected authentication to still work after organization change but got: {result.data}"
    )
