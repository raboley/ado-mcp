import os

import pytest
from fastmcp.client import Client

from server import mcp
from tests.ado.test_client import requires_ado_creds

pytestmark = pytest.mark.asyncio

TEST_PROJECT_NAME = "ado-mcp"
BASIC_PIPELINE_NAME = "test_run_and_get_pipeline_run_details"


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
async def running_pipeline_run_id(mcp_client: Client):
    """Start a pipeline and return its run ID for watch tests."""
    result = await mcp_client.call_tool(
        "run_pipeline_by_name",
        {"project_name": TEST_PROJECT_NAME, "pipeline_name": BASIC_PIPELINE_NAME},
    )
    pipeline_run = result.data
    return pipeline_run["id"]


@requires_ado_creds
async def test_watch_pipeline_tool_registration(mcp_client: Client):
    """Test that watch_pipeline tools are properly registered."""
    tools = await mcp_client.list_tools()
    tool_names = [tool.name for tool in tools]

    assert "watch_pipeline" in tool_names, "watch_pipeline tool should be registered"
    assert "watch_pipeline_by_name" in tool_names, (
        "watch_pipeline_by_name tool should be registered"
    )


@requires_ado_creds
async def test_watch_pipeline_by_name_monitors_running_pipeline(
    mcp_client: Client, running_pipeline_run_id: int
):
    """Test that watch_pipeline_by_name successfully monitors a running pipeline."""
    result = await mcp_client.call_tool(
        "watch_pipeline_by_name",
        {
            "project_name": TEST_PROJECT_NAME,
            "pipeline_name": BASIC_PIPELINE_NAME,
            "run_id": running_pipeline_run_id,
            "timeout_seconds": 120,
        },
    )

    outcome = result.data
    assert outcome is not None, "Expected pipeline outcome but got None"
    assert isinstance(outcome, dict), f"Expected dict but got {type(outcome)}"

    # Verify outcome structure
    assert "success" in outcome, (
        f"Expected 'success' field in outcome but got fields: {list(outcome.keys())}"
    )
    assert "pipeline_run" in outcome, (
        f"Expected 'pipeline_run' field in outcome but got fields: {list(outcome.keys())}"
    )
    assert "execution_time_seconds" in outcome, (
        f"Expected 'execution_time_seconds' field in outcome but got fields: {list(outcome.keys())}"
    )

    # Verify pipeline run details
    pipeline_run = outcome["pipeline_run"]
    assert pipeline_run["id"] == running_pipeline_run_id, (
        f"Expected run ID {running_pipeline_run_id} but got {pipeline_run['id']}"
    )

    # For the basic test pipeline, it should succeed
    if outcome["success"]:
        assert pipeline_run["result"] == "succeeded", (
            f"Expected 'succeeded' result but got {pipeline_run['result']}"
        )
        assert outcome["failure_summary"] is None, (
            "Expected no failure summary for successful pipeline"
        )
    else:
        assert outcome["failure_summary"] is not None, (
            "Expected failure summary for failed pipeline"
        )


@requires_ado_creds
async def test_watch_pipeline_monitors_already_completed_pipeline(mcp_client: Client):
    """Test that watch_pipeline handles already completed pipelines correctly."""
    # First run a pipeline and wait for it to complete
    run_result = await mcp_client.call_tool(
        "run_pipeline_and_get_outcome_by_name",
        {
            "project_name": TEST_PROJECT_NAME,
            "pipeline_name": BASIC_PIPELINE_NAME,
            "timeout_seconds": 120,
        },
    )

    completed_run = run_result.data
    completed_run_id = completed_run["pipeline_run"]["id"]

    # Now watch the already completed pipeline
    watch_result = await mcp_client.call_tool(
        "watch_pipeline_by_name",
        {
            "project_name": TEST_PROJECT_NAME,
            "pipeline_name": BASIC_PIPELINE_NAME,
            "run_id": completed_run_id,
            "timeout_seconds": 30,  # Short timeout since it's already done
        },
    )

    outcome = watch_result.data
    assert outcome is not None, "Expected pipeline outcome but got None"
    assert outcome["success"] == completed_run["success"], (
        f"Watch result success should match original run: {completed_run['success']} vs {outcome['success']}"
    )
    assert outcome["pipeline_run"]["id"] == completed_run_id, (
        f"Expected run ID {completed_run_id} but got {outcome['pipeline_run']['id']}"
    )


@requires_ado_creds
async def test_watch_pipeline_with_project_and_pipeline_ids(
    mcp_client: Client, running_pipeline_run_id: int
):
    """Test watch_pipeline tool with project and pipeline IDs."""
    # Get project and pipeline IDs first
    projects_result = await mcp_client.call_tool("list_projects", {})
    projects = projects_result.data
    test_project = next(p for p in projects if p["name"] == TEST_PROJECT_NAME)
    project_id = test_project["id"]

    pipelines_result = await mcp_client.call_tool("list_pipelines", {"project_id": project_id})
    pipelines = pipelines_result.data
    test_pipeline = next(p for p in pipelines if p["name"] == BASIC_PIPELINE_NAME)
    pipeline_id = test_pipeline["id"]

    # Watch using IDs
    result = await mcp_client.call_tool(
        "watch_pipeline",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "run_id": running_pipeline_run_id,
            "timeout_seconds": 120,
        },
    )

    outcome = result.data
    assert outcome is not None, "Expected pipeline outcome but got None"
    assert outcome["pipeline_run"]["id"] == running_pipeline_run_id, (
        f"Expected run ID {running_pipeline_run_id} but got {outcome['pipeline_run']['id']}"
    )


@requires_ado_creds
async def test_watch_pipeline_with_custom_timeout(mcp_client: Client, running_pipeline_run_id: int):
    """Test watch_pipeline with custom timeout setting."""
    result = await mcp_client.call_tool(
        "watch_pipeline_by_name",
        {
            "project_name": TEST_PROJECT_NAME,
            "pipeline_name": BASIC_PIPELINE_NAME,
            "run_id": running_pipeline_run_id,
            "timeout_seconds": 180,  # 3 minutes
            "max_lines": 50,  # Custom log lines limit
        },
    )

    outcome = result.data
    assert outcome is not None, "Expected pipeline outcome but got None"
    assert isinstance(outcome["execution_time_seconds"], int | float), (
        f"Expected numeric execution time but got {type(outcome['execution_time_seconds'])}"
    )


@requires_ado_creds
async def test_watch_pipeline_by_name_fuzzy_matching(
    mcp_client: Client, running_pipeline_run_id: int
):
    """Test that watch_pipeline_by_name supports fuzzy matching for project and pipeline names."""
    # Test with slight typos that should still match
    result = await mcp_client.call_tool(
        "watch_pipeline_by_name",
        {
            "project_name": "ado-mc",  # Missing 'p' at end
            "pipeline_name": "test_run_and_get_pipeline",  # Partial name
            "run_id": running_pipeline_run_id,
            "timeout_seconds": 60,
        },
    )

    outcome = result.data
    assert outcome is not None, "Fuzzy matching should find the correct pipeline"
    assert outcome["pipeline_run"]["id"] == running_pipeline_run_id, (
        f"Expected run ID {running_pipeline_run_id} but got {outcome['pipeline_run']['id']}"
    )


async def test_watch_pipeline_no_authentication(mcp_client_no_auth: Client):
    """Test watch_pipeline tools fail gracefully without authentication."""
    from fastmcp.exceptions import ToolError

    with pytest.raises(ToolError):  # Should raise a ToolError when no auth is available
        await mcp_client_no_auth.call_tool(
            "watch_pipeline_by_name",
            {
                "project_name": TEST_PROJECT_NAME,
                "pipeline_name": BASIC_PIPELINE_NAME,
                "run_id": 12345,
            },
        )


@requires_ado_creds
async def test_watch_pipeline_nonexistent_run_id(mcp_client: Client):
    """Test watch_pipeline with a non-existent run ID."""
    from fastmcp.exceptions import ToolError

    with pytest.raises(ToolError):  # Should raise a ToolError for non-existent run
        await mcp_client.call_tool(
            "watch_pipeline_by_name",
            {
                "project_name": TEST_PROJECT_NAME,
                "pipeline_name": BASIC_PIPELINE_NAME,
                "run_id": 999999999,  # Non-existent run ID
                "timeout_seconds": 30,
            },
        )


@requires_ado_creds
async def test_watch_pipeline_validates_outcome_structure(
    mcp_client: Client, running_pipeline_run_id: int
):
    """Test that watch_pipeline returns properly structured outcome data."""
    result = await mcp_client.call_tool(
        "watch_pipeline_by_name",
        {
            "project_name": TEST_PROJECT_NAME,
            "pipeline_name": BASIC_PIPELINE_NAME,
            "run_id": running_pipeline_run_id,
            "timeout_seconds": 120,
        },
    )

    outcome = result.data

    # Validate required fields
    required_fields = ["success", "pipeline_run", "execution_time_seconds"]
    for field in required_fields:
        assert field in outcome, (
            f"Expected '{field}' in outcome but got fields: {list(outcome.keys())}"
        )

    # Validate types
    assert isinstance(outcome["success"], bool), (
        f"Expected boolean success but got {type(outcome['success'])}"
    )
    assert isinstance(outcome["pipeline_run"], dict), (
        f"Expected dict pipeline_run but got {type(outcome['pipeline_run'])}"
    )
    assert isinstance(outcome["execution_time_seconds"], int | float), (
        f"Expected numeric execution_time_seconds but got {type(outcome['execution_time_seconds'])}"
    )

    # Validate pipeline_run structure
    pipeline_run = outcome["pipeline_run"]
    pipeline_run_required_fields = ["id", "state", "result"]
    for field in pipeline_run_required_fields:
        assert field in pipeline_run, (
            f"Expected '{field}' in pipeline_run but got fields: {list(pipeline_run.keys())}"
        )

    # If failed, should have failure_summary
    if not outcome["success"] and pipeline_run.get("state") == "completed":
        assert outcome.get("failure_summary") is not None, (
            "Expected failure_summary for failed completed pipeline"
        )
