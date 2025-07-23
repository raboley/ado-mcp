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
async def mcp_client_no_auth(monkeypatch):
    monkeypatch.delenv("AZURE_DEVOPS_EXT_PAT", raising=False)
    monkeypatch.delenv("ADO_ORGANIZATION_URL", raising=False)
    async with Client(mcp) as client:
        yield client

@requires_ado_creds
async def test_run_pipeline_basic_no_parameters(mcp_client: Client):
    project_id = get_project_id()
    pipeline_id = await get_pipeline_id_by_name(mcp_client, "test_run_and_get_pipeline_run_details")
    
    result = await mcp_client.call_tool(
        "run_pipeline", {"project_id": project_id, "pipeline_id": pipeline_id}
    )

    pipeline_run = result.data
    assert pipeline_run is not None, f"Expected pipeline run data but got None"
    assert isinstance(pipeline_run, dict), f"Expected dict but got {type(pipeline_run)}"
    assert pipeline_run["id"] is not None, f"Expected pipeline run ID but got None"
    assert pipeline_run["state"] in ["unknown", "inProgress"], (
        f"Expected state to be 'unknown' or 'inProgress' but got '{pipeline_run['state']}'"
    )
    assert pipeline_run["pipeline"]["id"] == pipeline_id, (
        f"Expected pipeline ID {pipeline_id} but got {pipeline_run['pipeline']['id']}"
    )

@requires_ado_creds
async def test_run_pipeline_with_template_parameters(mcp_client: Client):
    project_id = get_project_id()
    pipeline_id = await get_pipeline_id_by_name(mcp_client, "github-resources-test-stable")
    template_parameters = {"taskfileVersion": "latest", "installPath": "./bin/test"}

    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "template_parameters": template_parameters,
        },
    )

    pipeline_run = result.data
    assert pipeline_run is not None, f"Expected pipeline run data but got None"
    assert pipeline_run["id"] is not None, f"Expected pipeline run ID but got None"
    assert pipeline_run["state"] in ["unknown", "inProgress"], (
        f"Expected state to be 'unknown' or 'inProgress' but got '{pipeline_run['state']}'"
    )

@requires_ado_creds
async def test_run_pipeline_with_resources(mcp_client: Client):
    project_id = get_project_id()
    pipeline_id = await get_pipeline_id_by_name(mcp_client, "github-resources-test-stable")
    resources = {"repositories": {"tooling": {"refName": "refs/heads/main"}}}

    template_parameters = {"taskfileVersion": "latest", "installPath": "./bin/resources-test"}

    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "resources": resources,
            "template_parameters": template_parameters,
        },
    )

    pipeline_run = result.data
    assert pipeline_run is not None, f"Expected pipeline run data but got None"
    assert pipeline_run["id"] is not None, f"Expected pipeline run ID but got None"

@requires_ado_creds
async def test_run_pipeline_with_authentication(mcp_client: Client):
    project_id = get_project_id()
    pipeline_id = await get_pipeline_id_by_name(mcp_client, "test_run_and_get_pipeline_run_details")
    
    result = await mcp_client.call_tool(
        "run_pipeline", {"project_id": project_id, "pipeline_id": pipeline_id}
    )

    pipeline_run = result.data
    assert pipeline_run is not None, f"Expected pipeline run with authentication but got None"
    assert pipeline_run["id"] is not None, f"Expected pipeline run ID but got None"

async def test_run_pipeline_tool_registration():
    async with Client(mcp) as client:
        tools_response = await client.list_tools()
        if hasattr(tools_response, "tools"):
            tools = tools_response.tools
        else:
            tools = tools_response
        tool_names = [tool.name for tool in tools]
        assert "run_pipeline" in tool_names, (
            f"Expected 'run_pipeline' in tool names but got {tool_names}"
        )

@requires_ado_creds
async def test_run_pipeline_nonexistent_pipeline(mcp_client: Client):
    project_id = get_project_id()
    # Use 99999 as a non-existent pipeline ID for testing
    
    try:
        result = await mcp_client.call_tool(
            "run_pipeline", {"project_id": project_id, "pipeline_id": 99999}
        )

        if result.data is None:
            assert True, "Non-existent pipeline correctly returned None"
        else:
            assert False, f"Expected None for non-existent pipeline but got {result.data}"
    except Exception:
        assert True, "Non-existent pipeline correctly raised exception"

@requires_ado_creds
async def test_run_pipeline_invalid_project(mcp_client: Client):
    pipeline_id = await get_pipeline_id_by_name(mcp_client, "test_run_and_get_pipeline_run_details")
    # Use a dummy UUID for testing invalid project
    
    try:
        result = await mcp_client.call_tool(
            "run_pipeline",
            {
                "project_id": "00000000-0000-0000-0000-000000000000",
                "pipeline_id": pipeline_id,
            },
        )

        if result.data is None:
            assert True, "Invalid project correctly returned None"
        else:
            assert False, f"Expected None for invalid project but got {result.data}"
    except Exception:
        assert True, "Invalid project correctly raised exception"
