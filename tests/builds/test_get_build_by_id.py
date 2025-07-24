import os

import pytest
from fastmcp.client import Client

from server import mcp
from src.test_config import get_project_id, get_project_name
from tests.ado.test_client import requires_ado_creds
from tests.test_helpers import get_pipeline_id_by_name

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def mcp_client():
    async with Client(mcp) as client:
        initial_org_url = os.environ.get(
            "ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley"
        )
        await client.call_tool("set_ado_organization", {"organization_url": initial_org_url})
        yield client


@pytest.fixture
async def build_id(mcp_client):
    get_project_name()
    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_name": get_project_name(),
            "pipeline_name": "test_run_and_get_pipeline_run_details",
        },
    )

    pipeline_run = result.data
    assert pipeline_run is not None, f"Expected pipeline run to be created, got {pipeline_run}"
    assert pipeline_run["id"] is not None, (
        f"Expected pipeline run to have ID, got run data: {pipeline_run}"
    )

    return pipeline_run["id"]


@requires_ado_creds
async def test_get_build_by_id_valid_build(mcp_client: Client, build_id: int):
    project_id = get_project_id()

    result = await mcp_client.call_tool(
        "get_build_by_id", {"project_id": project_id, "build_id": build_id}
    )

    build_data = result.data
    assert build_data is not None, f"Expected build data for build {build_id}, got None"
    assert isinstance(build_data, dict), (
        f"Expected build data to be dict, got {type(build_data)}: {build_data}"
    )
    assert build_data["id"] == build_id, (
        f"Expected build ID {build_id}, got {build_data.get('id')} in build data: {build_data}"
    )

    assert "definition" in build_data, (
        f"Expected 'definition' field in build data, got fields: {list(build_data.keys())}"
    )
    definition = build_data["definition"]
    assert isinstance(definition, dict), (
        f"Expected definition to be dict, got {type(definition)}: {definition}"
    )
    assert "id" in definition, (
        f"Expected 'id' field in definition, got fields: {list(definition.keys())}"
    )
    assert "name" in definition, (
        f"Expected 'name' field in definition, got fields: {list(definition.keys())}"
    )


@requires_ado_creds
async def test_get_build_by_id_maps_to_correct_pipeline(mcp_client: Client, build_id: int):
    project_id = get_project_id()
    pipeline_id = await get_pipeline_id_by_name(mcp_client, "test_run_and_get_pipeline_run_details")
    result = await mcp_client.call_tool(
        "get_build_by_id", {"project_id": project_id, "build_id": build_id}
    )

    build_data = result.data
    assert build_data is not None, f"Expected build data for build {build_id}, got None"

    definition = build_data["definition"]
    assert definition["id"] == pipeline_id, (
        f"Expected build {build_id} to map to pipeline {pipeline_id}, got pipeline {definition['id']}"
    )


@requires_ado_creds
async def test_get_build_by_id_structure(mcp_client: Client, build_id: int):
    project_id = get_project_id()

    result = await mcp_client.call_tool(
        "get_build_by_id", {"project_id": project_id, "build_id": build_id}
    )

    build_data = result.data
    assert build_data is not None, f"Expected build data for build {build_id}, got None"

    required_fields = ["id", "definition", "status", "queueTime"]
    for field in required_fields:
        assert field in build_data, (
            f"Expected '{field}' field in build data, got fields: {list(build_data.keys())}"
        )

    definition = build_data["definition"]
    definition_required_fields = ["id", "name", "url", "project"]
    for field in definition_required_fields:
        assert field in definition, (
            f"Expected '{field}' field in definition, got fields: {list(definition.keys())}"
        )


@requires_ado_creds
async def test_get_build_by_id_status_field(mcp_client: Client, build_id: int):
    project_id = get_project_id()

    result = await mcp_client.call_tool(
        "get_build_by_id", {"project_id": project_id, "build_id": build_id}
    )

    build_data = result.data
    assert build_data is not None, f"Expected build data for build {build_id}, got None"

    valid_statuses = [
        "inProgress",
        "completed",
        "cancelling",
        "postponed",
        "notStarted",
        "cancelled",
    ]
    actual_status = build_data["status"]
    assert actual_status in valid_statuses, (
        f"Expected status to be one of {valid_statuses}, got '{actual_status}'"
    )


@requires_ado_creds
async def test_get_build_by_id_nonexistent_build(mcp_client: Client):
    project_id = get_project_id()

    try:
        result = await mcp_client.call_tool(
            "get_build_by_id", {"project_id": project_id, "build_id": 999999999}
        )

        if result.data is not None:
            raise AssertionError(
                f"Expected None for non-existent build 999999999, got {result.data}"
            )
    except Exception as e:
        assert True, (
            f"Expected exception for non-existent build 999999999, got {type(e).__name__}: {e}"
        )


@requires_ado_creds
async def test_get_build_by_id_invalid_project(mcp_client: Client):
    try:
        result = await mcp_client.call_tool(
            "get_build_by_id",
            {"project_id": "00000000-0000-0000-0000-000000000000", "build_id": 123456},
        )

        if result.data is not None:
            raise AssertionError(
                f"Expected None for invalid project 00000000-0000-0000-0000-000000000000, got {result.data}"
            )
    except Exception as e:
        assert True, (
            f"Expected exception for invalid project 00000000-0000-0000-0000-000000000000, got {type(e).__name__}: {e}"
        )


@requires_ado_creds
async def test_get_build_by_id_url_resolution_scenario(mcp_client: Client, build_id: int):
    project_id = get_project_id()

    result = await mcp_client.call_tool(
        "get_build_by_id", {"project_id": project_id, "build_id": build_id}
    )

    build_data = result.data
    assert build_data is not None, (
        f"Expected build data for URL resolution of build {build_id}, got None"
    )

    pipeline_id = build_data["definition"]["id"]
    pipeline_name = build_data["definition"]["name"]

    assert isinstance(pipeline_id, int), (
        f"Expected pipeline ID to be int for URL resolution, got {type(pipeline_id)}: {pipeline_id}"
    )
    assert isinstance(pipeline_name, str), (
        f"Expected pipeline name to be str for URL resolution, got {type(pipeline_name)}: {pipeline_name}"
    )
    assert pipeline_id > 0, f"Expected positive pipeline ID for URL resolution, got {pipeline_id}"
    assert len(pipeline_name) > 0, (
        f"Expected non-empty pipeline name for URL resolution, got '{pipeline_name}'"
    )


async def test_get_build_by_id_tool_registration():
    async with Client(mcp) as client:
        tools_response = await client.list_tools()
        if hasattr(tools_response, "tools"):
            tools = tools_response.tools
        else:
            tools = tools_response
        tool_names = [tool.name for tool in tools]
        assert "get_build_by_id" in tool_names, (
            f"Expected 'get_build_by_id' in registered tools, got tools: {tool_names}"
        )
