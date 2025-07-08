from fastmcp.client import Client
from server import mcp, ado_client
import pytest

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio

async def test_check_ado_authentication_tool():
    """Tests the check_ado_authentication tool."""
    # This test will only run if the ado_client was successfully initialized.
    if not ado_client:
        pytest.skip("ADO client not initialized, skipping authentication tool test.")

    async with Client(mcp) as client:
        result = await client.call_tool("check_ado_authentication")
        assert result.content[0].text == "true"
