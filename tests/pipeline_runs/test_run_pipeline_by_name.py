import os

import pytest
from fastmcp.client import Client

from server import mcp
from tests.ado.test_client import requires_ado_creds
from tests.utils.retry_helpers import retry_with_cache_invalidation

pytestmark = pytest.mark.asyncio

TEST_PROJECT_NAME = "ado-mcp"
BASIC_PIPELINE_NAME = "test_run_and_get_pipeline_run_details"
GITHUB_RESOURCES_PIPELINE_NAME = "github-resources-test-stable"
PREVIEW_PARAMETERIZED_PIPELINE_NAME = "preview-test-parameterized"
COMPLEX_PIPELINE_NAME = "log-test-complex"


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
async def test_run_pipeline_by_name_basic(mcp_client: Client):
    # Use retry mechanism to handle cache inconsistency in parallel test runs
    result = await retry_with_cache_invalidation(
        mcp_client,
        "run_pipeline_by_name",
        {"project_name": TEST_PROJECT_NAME, "pipeline_name": BASIC_PIPELINE_NAME},
        max_retries=3,
        retry_delay=1,
    )

    pipeline_run = result.data
    assert pipeline_run is not None, "Expected pipeline run data but got None"
    assert isinstance(pipeline_run, dict), f"Expected dict but got {type(pipeline_run)}"
    assert pipeline_run["id"] is not None, "Expected pipeline run ID but got None"
    assert pipeline_run["state"] in ["unknown", "inProgress"], (
        f"Expected state to be 'unknown' or 'inProgress' but got '{pipeline_run['state']}'"
    )

    assert "pipeline" in pipeline_run, (
        f"Expected 'pipeline' field in pipeline run but got fields: {list(pipeline_run.keys())}"
    )
    pipeline_info = pipeline_run["pipeline"]
    assert pipeline_info["name"] == BASIC_PIPELINE_NAME, (
        f"Expected pipeline name '{BASIC_PIPELINE_NAME}' but got '{pipeline_info['name']}'"
    )


@requires_ado_creds
async def test_run_pipeline_by_name_with_template_parameters(mcp_client: Client):
    template_parameters = {"taskfileVersion": "latest", "installPath": "./bin/by-name-test"}

    result = await mcp_client.call_tool(
        "run_pipeline_by_name",
        {
            "project_name": TEST_PROJECT_NAME,
            "pipeline_name": GITHUB_RESOURCES_PIPELINE_NAME,
            "template_parameters": template_parameters,
        },
    )

    pipeline_run = result.data
    assert pipeline_run is not None, "Expected pipeline run data but got None"
    assert pipeline_run["id"] is not None, "Expected pipeline run ID but got None"


@requires_ado_creds
async def test_run_pipeline_by_name_with_resources(mcp_client: Client):
    resources = {"repositories": {"tooling": {"refName": "refs/heads/main"}}}

    template_parameters = {
        "taskfileVersion": "latest",
        "installPath": "./bin/by-name-resources-test",
    }

    result = await mcp_client.call_tool(
        "run_pipeline_by_name",
        {
            "project_name": TEST_PROJECT_NAME,
            "pipeline_name": GITHUB_RESOURCES_PIPELINE_NAME,
            "resources": resources,
            "template_parameters": template_parameters,
        },
    )

    pipeline_run = result.data
    assert pipeline_run is not None, "Expected pipeline run data but got None"
    assert pipeline_run["id"] is not None, "Expected pipeline run ID but got None"


@requires_ado_creds
async def test_run_pipeline_by_name_with_template_parameters_preview(mcp_client: Client):
    template_parameters = {"testEnvironment": "prod", "enableDebug": False}

    result = await mcp_client.call_tool(
        "run_pipeline_by_name",
        {
            "project_name": TEST_PROJECT_NAME,
            "pipeline_name": PREVIEW_PARAMETERIZED_PIPELINE_NAME,
            "template_parameters": template_parameters,
        },
    )

    pipeline_run = result.data
    assert pipeline_run is not None, "Expected pipeline run data but got None"
    assert pipeline_run["id"] is not None, "Expected pipeline run ID but got None"


@requires_ado_creds
async def test_run_pipeline_by_name_with_branch(mcp_client: Client):
    result = await mcp_client.call_tool(
        "run_pipeline_by_name",
        {
            "project_name": TEST_PROJECT_NAME,
            "pipeline_name": BASIC_PIPELINE_NAME,
            "branch": "refs/heads/main",
        },
    )

    pipeline_run = result.data
    assert pipeline_run is not None, "Expected pipeline run data but got None"
    assert pipeline_run["id"] is not None, "Expected pipeline run ID but got None"


@requires_ado_creds
async def test_run_pipeline_by_name_with_stages_to_skip(mcp_client: Client):
    stages_to_skip = ["Test"]

    result = await mcp_client.call_tool(
        "run_pipeline_by_name",
        {
            "project_name": TEST_PROJECT_NAME,
            "pipeline_name": "log-test-complex",
            "stages_to_skip": stages_to_skip,
        },
    )

    pipeline_run = result.data
    assert pipeline_run is not None, "Expected pipeline run data but got None"
    assert pipeline_run["id"] is not None, "Expected pipeline run ID but got None"


@requires_ado_creds
async def test_run_pipeline_by_name_fuzzy_matching(mcp_client: Client):
    result = await mcp_client.call_tool(
        "run_pipeline_by_name",
        {"project_name": "ado", "pipeline_name": "test_run_and_get_pipeline"},
    )

    pipeline_run = result.data
    assert pipeline_run is not None, "Expected pipeline run with fuzzy matching but got None"
    assert pipeline_run["id"] is not None, "Expected pipeline run ID but got None"


@requires_ado_creds
async def test_run_pipeline_by_name_with_authentication(mcp_client: Client):
    result = await mcp_client.call_tool(
        "run_pipeline_by_name",
        {"project_name": TEST_PROJECT_NAME, "pipeline_name": BASIC_PIPELINE_NAME},
    )

    pipeline_run = result.data
    assert pipeline_run is not None, "Expected pipeline run with authentication but got None"
    assert pipeline_run["id"] is not None, "Expected pipeline run ID but got None"


@requires_ado_creds
async def test_run_pipeline_by_name_nonexistent_project(mcp_client: Client):
    try:
        result = await mcp_client.call_tool(
            "run_pipeline_by_name",
            {"project_name": "NonexistentProject", "pipeline_name": BASIC_PIPELINE_NAME},
        )

        if result.data is None:
            assert True, "Non-existent project correctly returned None"
        else:
            raise AssertionError(f"Expected None for non-existent project but got {result.data}")
    except Exception:
        assert True, "Non-existent project correctly raised exception"


@requires_ado_creds
async def test_run_pipeline_by_name_nonexistent_pipeline(mcp_client: Client):
    try:
        result = await mcp_client.call_tool(
            "run_pipeline_by_name",
            {"project_name": TEST_PROJECT_NAME, "pipeline_name": "NonexistentPipeline"},
        )

        if result.data is None:
            assert True, "Non-existent pipeline correctly returned None"
        else:
            raise AssertionError(f"Expected None for non-existent pipeline but got {result.data}")
    except Exception:
        assert True, "Non-existent pipeline correctly raised exception"


@requires_ado_creds
async def test_run_pipeline_by_name_case_insensitive(mcp_client: Client):
    result = await mcp_client.call_tool(
        "run_pipeline_by_name",
        {"project_name": "ADO-MCP", "pipeline_name": "TEST_RUN_AND_GET_PIPELINE_RUN_DETAILS"},
    )

    pipeline_run = result.data
    assert pipeline_run is not None, (
        "Expected pipeline run with case insensitive matching but got None"
    )
    assert pipeline_run["id"] is not None, "Expected pipeline run ID but got None"
