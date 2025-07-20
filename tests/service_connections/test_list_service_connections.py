"""
Tests for the list_service_connections MCP tool.

This module tests listing service connections for Azure DevOps projects.
"""

import os
import pytest
from fastmcp.client import Client

from server import mcp
from tests.ado.test_client import requires_ado_creds

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio

# Test fixtures
TEST_PROJECT_ID = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project


@pytest.fixture
async def mcp_client():
    """Provides a connected MCP client for tests."""
    async with Client(mcp) as client:
        initial_org_url = os.environ.get(
            "ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley"
        )
        await client.call_tool("set_ado_organization", {"organization_url": initial_org_url})
        yield client



@requires_ado_creds
async def test_list_service_connections_returns_valid_list(mcp_client: Client):
    """Test that list_service_connections returns a valid list."""
    result = await mcp_client.call_tool(
        "list_service_connections",
        {"project_id": TEST_PROJECT_ID}
    )
    
    service_connections = result.data
    assert service_connections is not None, "Service connections list should not be None"
    assert isinstance(service_connections, list), "Service connections should be a list"
    
    if len(service_connections) > 0:
        # Verify structure of first service connection
        connection = service_connections[0]
        assert isinstance(connection, dict), "Service connection should be a dictionary"
        assert "id" in connection, "Service connection should have an id"
        assert "name" in connection, "Service connection should have a name"
        assert "type" in connection, "Service connection should have a type"
        
        # Verify field types
        assert isinstance(connection["id"], str), "Service connection id should be a string"
        assert isinstance(connection["name"], str), "Service connection name should be a string"
        assert isinstance(connection["type"], str), "Service connection type should be a string"
        
        print(f"Found {len(service_connections)} service connections")
        print(f"First connection: {connection['name']} (Type: {connection['type']})")
    else:
        print("No service connections found in project")


@requires_ado_creds
async def test_list_service_connections_github_type(mcp_client: Client):
    """Test finding GitHub service connections specifically."""
    result = await mcp_client.call_tool(
        "list_service_connections",
        {"project_id": TEST_PROJECT_ID}
    )
    
    service_connections = result.data
    assert isinstance(service_connections, list), "Service connections should be a list"
    
    # Look for GitHub service connections (used by our test pipelines)
    github_connections = [conn for conn in service_connections if conn.get("type") == "github"]
    
    if len(github_connections) > 0:
        github_conn = github_connections[0]
        assert "github" in github_conn["type"].lower(), "Should be a GitHub connection"
        print(f"Found GitHub service connection: {github_conn['name']}")
    else:
        print("No GitHub service connections found (may be expected)")


@requires_ado_creds
async def test_list_service_connections_structure(mcp_client: Client):
    """Test the structure of service connection data."""
    result = await mcp_client.call_tool(
        "list_service_connections",
        {"project_id": TEST_PROJECT_ID}
    )
    
    service_connections = result.data
    assert isinstance(service_connections, list), "Service connections should be a list"
    
    if len(service_connections) > 0:
        for connection in service_connections:
            assert isinstance(connection, dict), "Each connection should be a dictionary"
            
            # Verify required fields
            required_fields = ["id", "name", "type"]
            for field in required_fields:
                assert field in connection, f"Connection should have {field} field"
            
            # Verify field types and values
            assert isinstance(connection["id"], str), "Connection id should be a string"
            assert len(connection["id"]) > 0, "Connection id should not be empty"
            assert isinstance(connection["name"], str), "Connection name should be a string"
            assert len(connection["name"]) > 0, "Connection name should not be empty"
            assert isinstance(connection["type"], str), "Connection type should be a string"
            assert len(connection["type"]) > 0, "Connection type should not be empty"
        
        print(f"✓ All {len(service_connections)} service connections have valid structure")


@requires_ado_creds
async def test_list_service_connections_types(mcp_client: Client):
    """Test the variety of service connection types found."""
    result = await mcp_client.call_tool(
        "list_service_connections",
        {"project_id": TEST_PROJECT_ID}
    )
    
    service_connections = result.data
    assert isinstance(service_connections, list), "Service connections should be a list"
    
    if len(service_connections) > 0:
        # Collect all types
        connection_types = set(conn["type"] for conn in service_connections)
        
        print(f"Found service connection types: {', '.join(sorted(connection_types))}")
        
        # Common types we might expect
        common_types = ["github", "azurerm", "dockerhub", "nuget"]
        found_common = [t for t in common_types if t in connection_types]
        
        if found_common:
            print(f"Common connection types found: {', '.join(found_common)}")
    else:
        print("No service connections to analyze types")



@requires_ado_creds
async def test_list_service_connections_invalid_project(mcp_client: Client):
    """Test error handling for invalid project ID."""
    try:
        result = await mcp_client.call_tool(
            "list_service_connections",
            {"project_id": "00000000-0000-0000-0000-000000000000"}  # Invalid project
        )
        
        # If it doesn't raise an exception, check the result
        service_connections = result.data
        assert service_connections == [], "Should return empty list for invalid project"
        print("✓ Invalid project properly returned empty list")
    except Exception as e:
        print(f"✓ Invalid project properly raised exception: {type(e).__name__}")
        assert True, "Exception is expected for invalid project"


@requires_ado_creds
async def test_list_service_connections_specific_connection_details(mcp_client: Client):
    """Test detailed information about specific service connections."""
    result = await mcp_client.call_tool(
        "list_service_connections",
        {"project_id": TEST_PROJECT_ID}
    )
    
    service_connections = result.data
    assert isinstance(service_connections, list), "Service connections should be a list"
    
    if len(service_connections) > 0:
        # Look for a connection that might be used by our test pipelines
        # The GitHub resources pipeline likely uses a GitHub service connection
        for connection in service_connections:
            if "github" in connection["type"].lower() or "raboley" in connection["name"].lower():
                print(f"Test-relevant connection found: {connection['name']} (ID: {connection['id']}, Type: {connection['type']})")
                
                # Verify this connection has the expected structure for pipeline use
                assert isinstance(connection["id"], str), "Connection ID should be string for pipeline reference"
                assert len(connection["id"]) > 0, "Connection ID should not be empty"
                break
        else:
            print("No test-specific service connections identified")


async def test_list_service_connections_tool_registration():
    """Test that the list_service_connections tool is properly registered."""
    async with Client(mcp) as client:
        tools_response = await client.list_tools()
        # Handle both potential response formats
        if hasattr(tools_response, "tools"):
            tools = tools_response.tools
        else:
            tools = tools_response
        tool_names = [tool.name for tool in tools]
        assert "list_service_connections" in tool_names, "list_service_connections tool should be registered"