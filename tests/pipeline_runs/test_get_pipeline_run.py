import os
import pytest
from fastmcp.client import Client

from server import mcp
from src.test_config import get_project_id, get_basic_pipeline_id
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


@pytest.fixture
async def mcp_client_no_auth(monkeypatch):
    monkeypatch.delenv("AZURE_DEVOPS_EXT_PAT", raising=False)
    monkeypatch.delenv("ADO_ORGANIZATION_URL", raising=False)
    async with Client(mcp) as client:
        yield client


@pytest.fixture
async def pipeline_run_id(mcp_client):
    project_id = get_project_id()
    pipeline_id = get_basic_pipeline_id()
    
    result = await mcp_client.call_tool(
        "run_pipeline", {"project_id": project_id, "pipeline_id": pipeline_id}
    )

    pipeline_run = result.data
    assert pipeline_run is not None, f"Expected pipeline run to be created but got None"
    assert pipeline_run["id"] is not None, f"Expected pipeline run ID but got None"

    return pipeline_run["id"]


@requires_ado_creds
async def test_get_pipeline_run_with_valid_id(mcp_client: Client, pipeline_run_id: int):
    project_id = get_project_id()
    pipeline_id = get_basic_pipeline_id()
    
    result = await mcp_client.call_tool(
        "get_pipeline_run",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "run_id": pipeline_run_id,
        },
    )

    pipeline_run = result.data
    assert pipeline_run is not None, f"Expected pipeline run data but got None"
    assert isinstance(pipeline_run, dict), f"Expected dict but got {type(pipeline_run)}"
    assert pipeline_run["id"] == pipeline_run_id, (
        f"Expected run ID {pipeline_run_id} but got {pipeline_run['id']}"
    )
    assert "state" in pipeline_run, (
        f"Expected 'state' field in pipeline run but got fields: {list(pipeline_run.keys())}"
    )
    assert "pipeline" in pipeline_run, (
        f"Expected 'pipeline' field in pipeline run but got fields: {list(pipeline_run.keys())}"
    )
    assert "createdDate" in pipeline_run, (
        f"Expected 'createdDate' field in pipeline run but got fields: {list(pipeline_run.keys())}"
    )

    assert pipeline_run["pipeline"]["id"] == pipeline_id, (
        f"Expected pipeline ID {pipeline_id} but got {pipeline_run['pipeline']['id']}"
    )


@requires_ado_creds
async def test_get_pipeline_run_state_validation(mcp_client: Client, pipeline_run_id: int):
    project_id = get_project_id()
    pipeline_id = get_basic_pipeline_id()
    
    result = await mcp_client.call_tool(
        "get_pipeline_run",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "run_id": pipeline_run_id,
        },
    )

    pipeline_run = result.data
    assert pipeline_run is not None, f"Expected pipeline run data but got None"

    valid_states = ["unknown", "inProgress", "completed", "cancelling", "cancelled"]
    assert pipeline_run["state"] in valid_states, (
        f"Expected state to be one of {valid_states} but got '{pipeline_run['state']}'"
    )


@requires_ado_creds
async def test_get_pipeline_run_structure(mcp_client: Client, pipeline_run_id: int):
    project_id = get_project_id()
    pipeline_id = get_basic_pipeline_id()
    
    result = await mcp_client.call_tool(
        "get_pipeline_run",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "run_id": pipeline_run_id,
        },
    )

    pipeline_run = result.data
    assert pipeline_run is not None, f"Expected pipeline run data but got None"

    required_fields = ["id", "name", "state", "pipeline", "createdDate"]
    for field in required_fields:
        assert field in pipeline_run, (
            f"Expected field '{field}' in pipeline run but got fields: {list(pipeline_run.keys())}"
        )

    pipeline_info = pipeline_run["pipeline"]
    assert isinstance(pipeline_info, dict), (
        f"Expected pipeline info to be dict but got {type(pipeline_info)}"
    )
    assert "id" in pipeline_info, (
        f"Expected 'id' in pipeline info but got fields: {list(pipeline_info.keys())}"
    )
    assert "name" in pipeline_info, (
        f"Expected 'name' in pipeline info but got fields: {list(pipeline_info.keys())}"
    )


@requires_ado_creds
async def test_get_pipeline_run_with_authentication(mcp_client: Client, pipeline_run_id: int):
    project_id = get_project_id()
    pipeline_id = get_basic_pipeline_id()
    
    result = await mcp_client.call_tool(
        "get_pipeline_run",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "run_id": pipeline_run_id,
        },
    )

    pipeline_run = result.data
    assert pipeline_run is not None, f"Expected pipeline run with authentication but got None"
    assert pipeline_run["id"] == pipeline_run_id, (
        f"Expected run ID {pipeline_run_id} but got {pipeline_run['id']}"
    )


@requires_ado_creds
async def test_get_pipeline_run_nonexistent_run(mcp_client: Client):
    project_id = get_project_id()
    pipeline_id = get_basic_pipeline_id()
    
    try:
        result = await mcp_client.call_tool(
            "get_pipeline_run",
            {"project_id": project_id, "pipeline_id": pipeline_id, "run_id": 999999999},
        )

        if result.data is None:
            assert True, "Non-existent pipeline run correctly returned None"
        else:
            assert False, f"Expected None for non-existent pipeline run but got {result.data}"
    except Exception:
        assert True, "Non-existent pipeline run correctly raised exception"


@requires_ado_creds
async def test_get_pipeline_run_invalid_project(mcp_client: Client):
    pipeline_id = get_basic_pipeline_id()
    
    try:
        result = await mcp_client.call_tool(
            "get_pipeline_run",
            {
                "project_id": "00000000-0000-0000-0000-000000000000",
                "pipeline_id": pipeline_id,
                "run_id": 123456,
            },
        )

        if result.data is None:
            assert True, "Invalid project correctly returned None"
        else:
            assert False, f"Expected None for invalid project but got {result.data}"
    except Exception:
        assert True, "Invalid project correctly raised exception"


@requires_ado_creds
async def test_get_pipeline_run_wrong_pipeline_id(mcp_client: Client, pipeline_run_id: int):
    project_id = get_project_id()
    
    try:
        result = await mcp_client.call_tool(
            "get_pipeline_run",
            {"project_id": project_id, "pipeline_id": 999, "run_id": pipeline_run_id},
        )

        if result.data is None:
            assert True, "Wrong pipeline ID correctly returned None"
        else:
            assert False, f"Expected None for wrong pipeline ID but got {result.data}"
    except Exception:
        assert True, "Wrong pipeline ID correctly raised exception"


async def test_get_pipeline_run_tool_registration():
    async with Client(mcp) as client:
        tools_response = await client.list_tools()
        if hasattr(tools_response, "tools"):
            tools = tools_response.tools
        else:
            tools = tools_response
        tool_names = [tool.name for tool in tools]
        assert "get_pipeline_run" in tool_names, (
            f"Expected 'get_pipeline_run' in tool names but got {tool_names}"
        )
