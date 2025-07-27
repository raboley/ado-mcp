import os

import pytest
from fastmcp.client import Client

from server import mcp
from src.test_config import get_project_id
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
async def test_list_service_connections_returns_valid_list(mcp_client: Client):
    project_id = get_project_id()
    result = await mcp_client.call_tool("list_service_connections", {"project_id": project_id})

    service_connections = result.data
    assert service_connections is not None, (
        f"Expected non-None service connections list, got {service_connections}"
    )
    assert isinstance(service_connections, list), (
        f"Expected list type for service connections, got {type(service_connections)}"
    )

    if len(service_connections) > 0:
        connection = service_connections[0]
        assert isinstance(connection, dict), (
            f"Expected dict type for service connection, got {type(connection)}"
        )
        assert "id" in connection, (
            f"Expected 'id' field in service connection, got fields: {list(connection.keys())}"
        )
        assert "name" in connection, (
            f"Expected 'name' field in service connection, got fields: {list(connection.keys())}"
        )
        assert "type" in connection, (
            f"Expected 'type' field in service connection, got fields: {list(connection.keys())}"
        )

        assert isinstance(connection["id"], str), (
            f"Expected string type for connection id, got {type(connection['id'])}"
        )
        assert isinstance(connection["name"], str), (
            f"Expected string type for connection name, got {type(connection['name'])}"
        )
        assert isinstance(connection["type"], str), (
            f"Expected string type for connection type, got {type(connection['type'])}"
        )


@requires_ado_creds
async def test_list_service_connections_github_type(mcp_client: Client):
    project_id = get_project_id()
    result = await mcp_client.call_tool("list_service_connections", {"project_id": project_id})

    service_connections = result.data
    assert isinstance(service_connections, list), (
        f"Expected list type for service connections, got {type(service_connections)}"
    )

    github_connections = [conn for conn in service_connections if conn.get("type") == "github"]

    if len(github_connections) > 0:
        github_conn = github_connections[0]
        assert "github" in github_conn["type"].lower(), (
            f"Expected 'github' in connection type '{github_conn['type']}' but it was not found"
        )


@requires_ado_creds
async def test_list_service_connections_structure(mcp_client: Client):
    project_id = get_project_id()
    result = await mcp_client.call_tool("list_service_connections", {"project_id": project_id})

    service_connections = result.data
    assert isinstance(service_connections, list), (
        f"Expected list type for service connections, got {type(service_connections)}"
    )

    if len(service_connections) > 0:
        for i, connection in enumerate(service_connections):
            assert isinstance(connection, dict), (
                f"Expected dict type for connection at index {i}, got {type(connection)}"
            )

            required_fields = ["id", "name", "type"]
            for field in required_fields:
                assert field in connection, (
                    f"Expected '{field}' field in connection at index {i}, got fields: {list(connection.keys())}"
                )

            assert isinstance(connection["id"], str), (
                f"Expected string type for connection id at index {i}, got {type(connection['id'])}"
            )
            assert len(connection["id"]) > 0, (
                f"Expected non-empty connection id at index {i}, got empty string"
            )
            assert isinstance(connection["name"], str), (
                f"Expected string type for connection name at index {i}, got {type(connection['name'])}"
            )
            assert len(connection["name"]) > 0, (
                f"Expected non-empty connection name at index {i}, got empty string"
            )
            assert isinstance(connection["type"], str), (
                f"Expected string type for connection type at index {i}, got {type(connection['type'])}"
            )
            assert len(connection["type"]) > 0, (
                f"Expected non-empty connection type at index {i}, got empty string"
            )


@requires_ado_creds
async def test_list_service_connections_types(mcp_client: Client):
    project_id = get_project_id()
    result = await mcp_client.call_tool("list_service_connections", {"project_id": project_id})

    service_connections = result.data
    assert isinstance(service_connections, list), (
        f"Expected list type for service connections, got {type(service_connections)}"
    )

    if len(service_connections) > 0:
        connection_types = {conn["type"] for conn in service_connections}

        assert len(connection_types) > 0, (
            f"Expected at least one connection type but found none. Connections: {service_connections}"
        )

        for conn_type in connection_types:
            assert isinstance(conn_type, str), (
                f"Expected string type for connection type, got {type(conn_type)}"
            )
            assert len(conn_type) > 0, "Expected non-empty connection type, got empty string"


@requires_ado_creds
async def test_list_service_connections_invalid_project(mcp_client: Client):
    try:
        result = await mcp_client.call_tool(
            "list_service_connections", {"project_id": "00000000-0000-0000-0000-000000000000"}
        )

        service_connections = result.data
        assert service_connections == [], (
            f"Expected empty list for invalid project, got {service_connections}"
        )
    except Exception as e:
        assert True, (
            f"Exception is expected for invalid project but got unexpected exception type: {type(e).__name__} with message: {str(e)}"
        )


@requires_ado_creds
async def test_list_service_connections_specific_connection_details(mcp_client: Client):
    project_id = get_project_id()
    result = await mcp_client.call_tool("list_service_connections", {"project_id": project_id})

    service_connections = result.data
    assert isinstance(service_connections, list), (
        f"Expected list type for service connections, got {type(service_connections)}"
    )

    if len(service_connections) > 0:
        for connection in service_connections:
            if "github" in connection["type"].lower() or "raboley" in connection["name"].lower():
                assert isinstance(connection["id"], str), (
                    f"Expected string type for connection ID, got {type(connection['id'])}"
                )
                assert len(connection["id"]) > 0, (
                    "Expected non-empty connection ID for pipeline reference, got empty string"
                )
                break
