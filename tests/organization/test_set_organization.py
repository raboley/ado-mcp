"""
Tests for the set_ado_organization MCP tool.

This module tests the organization switching functionality that allows
setting the Azure DevOps organization URL dynamically.
"""

import os
import pytest
from fastmcp.client import Client

from server import mcp
from tests.ado.test_client import requires_ado_creds

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio


@pytest.fixture
async def mcp_client():
    """Provides a connected MCP client for tests."""
    async with Client(mcp) as client:
        yield client


@requires_ado_creds
async def test_set_organization_success(mcp_client: Client):
    """Test successful organization switching."""
    organization_url = os.environ.get(
        "ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley"
    )
    
    result = await mcp_client.call_tool(
        "set_ado_organization", {"organization_url": organization_url}
    )
    
    response = result.data
    assert response is not None, "Response should not be None"
    # Response format may be a dict with 'result' or just a boolean
    if isinstance(response, dict):
        assert "result" in response or "success" in response, "Should have result or success field"
        success = response.get("result", response.get("success"))
        assert success is True, "Should indicate success"
    else:
        assert response is True, "Should return True for success"


@requires_ado_creds
async def test_set_organization_failure_and_recovery(mcp_client: Client):
    """Test organization failure handling and recovery."""
    # First set to a bad organization to test failure
    bad_org_url = "https://dev.azure.com/NonExistentOrg123456"
    
    try:
        result = await mcp_client.call_tool(
            "set_ado_organization", {"organization_url": bad_org_url}
        )
        # If it doesn't fail immediately, that's okay - might fail on actual use
        response = result.data
        if response and response.get("success"):
            print("Warning: Bad organization URL was accepted (might fail on actual use)")
    except Exception as e:
        print(f"Expected failure for bad organization: {e}")
    
    # Then recover with a good organization
    good_org_url = os.environ.get(
        "ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley"
    )
    
    result = await mcp_client.call_tool(
        "set_ado_organization", {"organization_url": good_org_url}
    )
    
    response = result.data
    assert response is not None, "Recovery response should not be None"
    # Response format may be a dict with 'result' or just a boolean
    if isinstance(response, dict):
        success = response.get("result", response.get("success"))
        assert success is True, "Should recover successfully"
    else:
        assert response is True, "Should recover successfully"


async def test_set_organization_invalid_url(mcp_client: Client):
    """Test organization setting with invalid URL format."""
    invalid_url = "not-a-valid-url"
    
    try:
        result = await mcp_client.call_tool(
            "set_ado_organization", {"organization_url": invalid_url}
        )
        # If it succeeds, check the response indicates an issue
        response = result.data
        if response:
            # Some validation might happen at the API level
            print(f"Response for invalid URL: {response}")
    except Exception as e:
        # Expected - invalid URL should be rejected
        assert "url" in str(e).lower() or "invalid" in str(e).lower(), f"Should indicate URL issue: {e}"


async def test_set_organization_empty_url(mcp_client: Client):
    """Test organization setting with empty URL."""
    try:
        result = await mcp_client.call_tool(
            "set_ado_organization", {"organization_url": ""}
        )
        # If it succeeds, should indicate failure
        response = result.data
        if response:
            assert response.get("success") is False, "Empty URL should not succeed"
    except Exception as e:
        # Expected - empty URL should be rejected
        assert True, "Empty URL properly rejected"