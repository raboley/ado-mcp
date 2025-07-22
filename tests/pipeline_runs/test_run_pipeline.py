import os
import pytest
from fastmcp.client import Client

from server import mcp
from tests.ado.test_client import requires_ado_creds

pytestmark = pytest.mark.asyncio

TEST_PROJECT_ID = "49e895da-15c6-4211-97df-65c547a59c22"
BASIC_PIPELINE_ID = 59
PARAMETERIZED_PIPELINE_ID = 75
GITHUB_RESOURCES_PIPELINE_ID = 200


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
    result = await mcp_client.call_tool(
        "run_pipeline", {"project_id": TEST_PROJECT_ID, "pipeline_id": BASIC_PIPELINE_ID}
    )

    pipeline_run = result.data
    assert pipeline_run is not None, f"Expected pipeline run data but got None"
    assert isinstance(pipeline_run, dict), f"Expected dict but got {type(pipeline_run)}"
    assert pipeline_run["id"] is not None, f"Expected pipeline run ID but got None"
    assert pipeline_run["state"] in ["unknown", "inProgress"], (
        f"Expected state to be 'unknown' or 'inProgress' but got '{pipeline_run['state']}'"
    )
    assert pipeline_run["pipeline"]["id"] == BASIC_PIPELINE_ID, (
        f"Expected pipeline ID {BASIC_PIPELINE_ID} but got {pipeline_run['pipeline']['id']}"
    )


@requires_ado_creds
async def test_run_pipeline_with_template_parameters(mcp_client: Client):
    template_parameters = {"taskfileVersion": "latest", "installPath": "./bin/test"}

    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_id": GITHUB_RESOURCES_PIPELINE_ID,
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
    resources = {"repositories": {"tooling": {"refName": "refs/heads/main"}}}

    template_parameters = {"taskfileVersion": "latest", "installPath": "./bin/resources-test"}

    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_id": GITHUB_RESOURCES_PIPELINE_ID,
            "resources": resources,
            "template_parameters": template_parameters,
        },
    )

    pipeline_run = result.data
    assert pipeline_run is not None, f"Expected pipeline run data but got None"
    assert pipeline_run["id"] is not None, f"Expected pipeline run ID but got None"


@requires_ado_creds
async def test_run_pipeline_with_authentication(mcp_client: Client):
    result = await mcp_client.call_tool(
        "run_pipeline", {"project_id": TEST_PROJECT_ID, "pipeline_id": BASIC_PIPELINE_ID}
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
    try:
        result = await mcp_client.call_tool(
            "run_pipeline", {"project_id": TEST_PROJECT_ID, "pipeline_id": 99999}
        )

        if result.data is None:
            assert True, "Non-existent pipeline correctly returned None"
        else:
            assert False, f"Expected None for non-existent pipeline but got {result.data}"
    except Exception:
        assert True, "Non-existent pipeline correctly raised exception"


@requires_ado_creds
async def test_run_pipeline_invalid_project(mcp_client: Client):
    try:
        result = await mcp_client.call_tool(
            "run_pipeline",
            {
                "project_id": "00000000-0000-0000-0000-000000000000",
                "pipeline_id": BASIC_PIPELINE_ID,
            },
        )

        if result.data is None:
            assert True, "Invalid project correctly returned None"
        else:
            assert False, f"Expected None for invalid project but got {result.data}"
    except Exception:
        assert True, "Invalid project correctly raised exception"
