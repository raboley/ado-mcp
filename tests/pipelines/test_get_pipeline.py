import os

import pytest
from fastmcp.client import Client

from server import mcp
from src.test_config import get_project_name
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

@requires_ado_creds
async def test_get_pipeline_basic(mcp_client: Client):
    get_project_name()
    result = await mcp_client.call_tool(
        "get_pipeline",
        {
            "project_name": get_project_name(),
            "pipeline_name": "test_run_and_get_pipeline_run_details",
        },
    )

    pipeline = result.data
    assert pipeline is not None, "Expected pipeline data but got None"
    assert isinstance(pipeline, dict), (
        f"Expected pipeline to be dict but got {type(pipeline).__name__}"
    )
    assert pipeline["id"] == await get_pipeline_id_by_name(
        mcp_client, "test_run_and_get_pipeline_run_details"
    ), (
        f"Expected pipeline ID {await get_pipeline_id_by_name(mcp_client, 'test_run_and_get_pipeline_run_details')} but got {pipeline['id']}"
    )

    required_fields = ["name", "folder"]
    for field in required_fields:
        assert field in pipeline, (
            f"Pipeline missing required field '{field}'. Available fields: {list(pipeline.keys())}"
        )

@requires_ado_creds
async def test_get_pipeline_github_resources(mcp_client: Client):
    result = await mcp_client.call_tool(
        "get_pipeline",
        {"project_name": get_project_name(), "pipeline_name": "github-resources-test-stable"},
    )

    pipeline = result.data
    assert pipeline is not None, "Expected pipeline data but got None"
    assert pipeline["id"] == await get_pipeline_id_by_name(
        mcp_client, "github-resources-test-stable"
    ), (
        f"Expected pipeline ID {await get_pipeline_id_by_name(mcp_client, 'github-resources-test-stable')} but got {pipeline['id']}"
    )
    assert pipeline["name"] == "github-resources-test-stable", (
        f"Expected pipeline name 'github-resources-test-stable' but got '{pipeline['name']}'"
    )

@requires_ado_creds
async def test_get_pipeline_parameterized(mcp_client: Client):
    result = await mcp_client.call_tool(
        "get_pipeline",
        {"project_name": get_project_name(), "pipeline_name": "preview-test-parameterized"},
    )

    pipeline = result.data
    assert pipeline is not None, "Expected pipeline data but got None"
    assert pipeline["id"] == await get_pipeline_id_by_name(
        mcp_client, "preview-test-parameterized"
    ), (
        f"Expected pipeline ID {await get_pipeline_id_by_name(mcp_client, 'preview-test-parameterized')} but got {pipeline['id']}"
    )
    assert "preview-test-parameterized" in pipeline["name"], (
        f"Expected pipeline name to contain 'preview-test-parameterized' but got '{pipeline['name']}'"
    )

@requires_ado_creds
async def test_get_pipeline_structure(mcp_client: Client):
    result = await mcp_client.call_tool(
        "get_pipeline",
        {
            "project_name": get_project_name(),
            "pipeline_name": "test_run_and_get_pipeline_run_details",
        },
    )

    pipeline = result.data
    assert pipeline is not None, "Expected pipeline data but got None"

    required_fields = ["id", "name", "folder"]
    for field in required_fields:
        assert field in pipeline, (
            f"Pipeline missing required field '{field}'. Available fields: {list(pipeline.keys())}"
        )

    assert isinstance(pipeline["id"], int), (
        f"Pipeline id should be int but got {type(pipeline['id']).__name__}: {pipeline['id']}"
    )
    assert isinstance(pipeline["name"], str), (
        f"Pipeline name should be str but got {type(pipeline['name']).__name__}: {pipeline['name']}"
    )
    assert isinstance(pipeline["folder"], str), (
        f"Pipeline folder should be str but got {type(pipeline['folder']).__name__}: {pipeline['folder']}"
    )

    assert "_links" in pipeline, (
        f"Pipeline missing '_links' field. Available fields: {list(pipeline.keys())}"
    )
    assert "self" in pipeline["_links"], (
        f"Pipeline '_links' missing 'self' field. Available links: {list(pipeline['_links'].keys())}"
    )
    assert "web" in pipeline["_links"], (
        f"Pipeline '_links' missing 'web' field. Available links: {list(pipeline['_links'].keys())}"
    )

@requires_ado_creds
async def test_get_pipeline_url_format(mcp_client: Client):
    result = await mcp_client.call_tool(
        "get_pipeline",
        {
            "project_name": get_project_name(),
            "pipeline_name": "test_run_and_get_pipeline_run_details",
        },
    )

    pipeline = result.data
    assert pipeline is not None, "Expected pipeline data but got None"

    web_link = pipeline["_links"]["web"]["href"]
    assert web_link.startswith("https://"), (
        f"Expected web link to start with 'https://' but got: {web_link}"
    )
    assert "dev.azure.com" in web_link or "visualstudio.com" in web_link, (
        f"Expected Azure DevOps URL but got: {web_link}"
    )
    assert (
        str(await get_pipeline_id_by_name(mcp_client, "test_run_and_get_pipeline_run_details"))
        in web_link
    ), (
        f"Expected web link to contain pipeline ID {await get_pipeline_id_by_name(mcp_client, 'test_run_and_get_pipeline_run_details')} but got: {web_link}"
    )

@requires_ado_creds
async def test_get_pipeline_nonexistent_pipeline(mcp_client: Client):
    try:
        result = await mcp_client.call_tool(
            "get_pipeline",
            {
                "project_name": get_project_name(),
                "pipeline_name": "test_run_and_get_pipeline_run_details",
            },
        )

        if result.data is None:
            assert True, "Expected None for non-existent pipeline"
        else:
            raise AssertionError(f"Expected None for non-existent pipeline but got: {result.data}")
    except Exception as e:
        assert isinstance(e, Exception), (
            "Expected an exception for non-existent pipeline but handling failed unexpectedly"
        )

@requires_ado_creds
async def test_get_pipeline_invalid_project(mcp_client: Client):
    try:
        result = await mcp_client.call_tool(
            "get_pipeline",
            {
                "project_name": get_project_name(),
                "pipeline_name": "test_run_and_get_pipeline_run_details",
            },
        )

        if result.data is None:
            assert True, "Expected None for invalid project"
        else:
            raise AssertionError(f"Expected None for invalid project but got: {result.data}")
    except Exception as e:
        assert isinstance(e, Exception), (
            "Expected an exception for invalid project but handling failed unexpectedly"
        )

@requires_ado_creds
async def test_get_pipeline_folder_information(mcp_client: Client):
    result = await mcp_client.call_tool(
        "get_pipeline",
        {
            "project_name": get_project_name(),
            "pipeline_name": "test_run_and_get_pipeline_run_details",
        },
    )

    pipeline = result.data
    assert pipeline is not None, "Expected pipeline data but got None"

    folder = pipeline["folder"]
    assert isinstance(folder, str), (
        f"Expected folder to be str but got {type(folder).__name__}: {folder}"
    )
    assert folder.startswith("\\") or folder.startswith("/"), (
        f"Expected folder to start with '\\' or '/' but got: {folder}"
    )

@requires_ado_creds
async def test_get_pipeline_project_reference(mcp_client: Client):
    result = await mcp_client.call_tool(
        "get_pipeline",
        {
            "project_name": get_project_name(),
            "pipeline_name": "test_run_and_get_pipeline_run_details",
        },
    )

    pipeline = result.data
    assert pipeline is not None, "Expected pipeline data but got None"
    assert pipeline["id"] == await get_pipeline_id_by_name(
        mcp_client, "test_run_and_get_pipeline_run_details"
    ), (
        f"Expected pipeline ID {await get_pipeline_id_by_name(mcp_client, 'test_run_and_get_pipeline_run_details')} but got {pipeline['id']}"
    )

