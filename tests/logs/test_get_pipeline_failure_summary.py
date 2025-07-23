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
async def completed_run_id(mcp_client):
    project_id = get_project_id()
    pipeline_id = await get_pipeline_id_by_name(mcp_client, "test_run_and_get_pipeline_run_details")
    
    result = await mcp_client.call_tool(
        "run_pipeline", {"project_id": project_id, "pipeline_id": pipeline_id}
    )

    pipeline_run = result.data
    assert pipeline_run is not None, f"Expected pipeline run to be created, got {pipeline_run}"
    assert pipeline_run["id"] is not None, (
        f"Expected pipeline run to have ID, got run data: {pipeline_run}"
    )

    return pipeline_run["id"]

@requires_ado_creds
async def test_get_pipeline_failure_summary_basic_structure(
    mcp_client: Client, completed_run_id: int
):
    project_id = get_project_id()
    pipeline_id = await get_pipeline_id_by_name(mcp_client, "test_run_and_get_pipeline_run_details")
    
    result = await mcp_client.call_tool(
        "get_pipeline_failure_summary",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "run_id": completed_run_id,
        },
    )

    failure_summary = result.data
    assert failure_summary is not None, (
        f"Expected failure summary for run {completed_run_id}, got None"
    )
    assert isinstance(failure_summary, dict), (
        f"Expected failure summary to be dict, got {type(failure_summary)}: {failure_summary}"
    )

    required_fields = ["total_failed_steps", "root_cause_tasks", "hierarchy_failures"]
    for field in required_fields:
        assert field in failure_summary, (
            f"Expected '{field}' field in failure summary, got fields: {list(failure_summary.keys())}"
        )

    assert isinstance(failure_summary["total_failed_steps"], int), (
        f"Expected total_failed_steps to be int, got {type(failure_summary['total_failed_steps'])}: {failure_summary['total_failed_steps']}"
    )
    assert isinstance(failure_summary["root_cause_tasks"], list), (
        f"Expected root_cause_tasks to be list, got {type(failure_summary['root_cause_tasks'])}: {failure_summary['root_cause_tasks']}"
    )
    assert isinstance(failure_summary["hierarchy_failures"], list), (
        f"Expected hierarchy_failures to be list, got {type(failure_summary['hierarchy_failures'])}: {failure_summary['hierarchy_failures']}"
    )

@requires_ado_creds
async def test_get_pipeline_failure_summary_with_max_lines(
    mcp_client: Client, completed_run_id: int
):
    project_id = get_project_id()
    pipeline_id = await get_pipeline_id_by_name(mcp_client, "test_run_and_get_pipeline_run_details")
    
    result = await mcp_client.call_tool(
        "get_pipeline_failure_summary",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "run_id": completed_run_id,
            "max_lines": 50,
        },
    )

    failure_summary = result.data
    assert failure_summary is not None, (
        f"Expected failure summary for run {completed_run_id} with max_lines=50, got None"
    )
    assert isinstance(failure_summary, dict), (
        f"Expected failure summary to be dict, got {type(failure_summary)}: {failure_summary}"
    )

    for task in failure_summary["root_cause_tasks"]:
        if "log_content" in task and task["log_content"]:
            lines = task["log_content"].split("\n")
            assert len(lines) <= 50, (
                f"Expected log content to have at most 50 lines for max_lines=50, got {len(lines)} lines in task '{task.get('name', 'unknown')}'"
            )

@requires_ado_creds
async def test_get_pipeline_failure_summary_unlimited_lines(
    mcp_client: Client, completed_run_id: int
):
    project_id = get_project_id()
    pipeline_id = await get_pipeline_id_by_name(mcp_client, "test_run_and_get_pipeline_run_details")
    
    result = await mcp_client.call_tool(
        "get_pipeline_failure_summary",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "run_id": completed_run_id,
            "max_lines": 0,
        },
    )

    failure_summary = result.data
    assert failure_summary is not None, (
        f"Expected failure summary for run {completed_run_id} with unlimited lines, got None"
    )
    assert isinstance(failure_summary, dict), (
        f"Expected failure summary to be dict, got {type(failure_summary)}: {failure_summary}"
    )

@requires_ado_creds
async def test_get_pipeline_failure_summary_task_structure(
    mcp_client: Client, completed_run_id: int
):
    project_id = get_project_id()
    pipeline_id = await get_pipeline_id_by_name(mcp_client, "test_run_and_get_pipeline_run_details")
    
    result = await mcp_client.call_tool(
        "get_pipeline_failure_summary",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "run_id": completed_run_id,
        },
    )

    failure_summary = result.data
    assert failure_summary is not None, (
        f"Expected failure summary for run {completed_run_id}, got None"
    )

    for task in failure_summary["root_cause_tasks"]:
        assert isinstance(task, dict), (
            f"Expected each root_cause_task to be dict, got {type(task)}: {task}"
        )
        task_fields = ["name", "result"]
        for field in task_fields:
            assert field in task, (
                f"Expected '{field}' field in root_cause_task, got fields: {list(task.keys())}"
            )

    for failure in failure_summary["hierarchy_failures"]:
        assert isinstance(failure, dict), (
            f"Expected each hierarchy_failure to be dict, got {type(failure)}: {failure}"
        )
        failure_fields = ["name", "result"]
        for field in failure_fields:
            assert field in failure, (
                f"Expected '{field}' field in hierarchy_failure, got fields: {list(failure.keys())}"
            )

@requires_ado_creds
async def test_get_pipeline_failure_summary_nonexistent_run(mcp_client: Client):
    try:
        result = await mcp_client.call_tool(
            "get_pipeline_failure_summary",
            {"project_id": get_project_id(), "pipeline_id": await get_pipeline_id_by_name(mcp_client, "test_run_and_get_pipeline_run_details"), "run_id": 999999999},
        )

        if result.data is not None:
            assert False, f"Expected None for non-existent run 999999999, got {result.data}"
    except Exception as e:
        assert True, (
            f"Expected exception for non-existent run 999999999, got {type(e).__name__}: {e}"
        )

@requires_ado_creds
async def test_get_pipeline_failure_summary_invalid_project(mcp_client: Client):
    try:
        result = await mcp_client.call_tool(
            "get_pipeline_failure_summary",
            {
                "project_id": "00000000-0000-0000-0000-000000000000",
                "pipeline_id": await get_pipeline_id_by_name(mcp_client, "test_run_and_get_pipeline_run_details"),
                "run_id": 123456,
            },
        )

        if result.data is not None:
            assert False, (
                f"Expected None for invalid project 00000000-0000-0000-0000-000000000000, got {result.data}"
            )
    except Exception as e:
        assert True, (
            f"Expected exception for invalid project 00000000-0000-0000-0000-000000000000, got {type(e).__name__}: {e}"
        )

@requires_ado_creds
async def test_get_pipeline_failure_summary_wrong_pipeline_id(
    mcp_client: Client, completed_run_id: int
):
    try:
        result = await mcp_client.call_tool(
            "get_pipeline_failure_summary",
            {"project_id": get_project_id(), "pipeline_id": 999, "run_id": completed_run_id},
        )

        if result.data is not None:
            assert False, (
                f"Expected None for wrong pipeline ID 999 with run {completed_run_id}, got {result.data}"
            )
    except Exception as e:
        assert True, (
            f"Expected exception for wrong pipeline ID 999 with run {completed_run_id}, got {type(e).__name__}: {e}"
        )

@requires_ado_creds
async def test_get_pipeline_failure_summary_successful_run_handling(
    mcp_client: Client, completed_run_id: int
):
    project_id = get_project_id()
    pipeline_id = await get_pipeline_id_by_name(mcp_client, "test_run_and_get_pipeline_run_details")
    
    result = await mcp_client.call_tool(
        "get_pipeline_failure_summary",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "run_id": completed_run_id,
        },
    )

    failure_summary = result.data
    assert failure_summary is not None, (
        f"Expected failure summary for run {completed_run_id} even if successful, got None"
    )

    total_failed = failure_summary["total_failed_steps"]
    root_cause_count = len(failure_summary["root_cause_tasks"])
    hierarchy_count = len(failure_summary["hierarchy_failures"])

    if total_failed == 0:
        assert root_cause_count == 0, (
            f"Expected 0 root_cause_tasks for successful run with 0 failed steps, got {root_cause_count}"
        )
        assert hierarchy_count == 0, (
            f"Expected 0 hierarchy_failures for successful run with 0 failed steps, got {hierarchy_count}"
        )

async def test_get_pipeline_failure_summary_tool_registration():
    async with Client(mcp) as client:
        tools_response = await client.list_tools()
        if hasattr(tools_response, "tools"):
            tools = tools_response.tools
        else:
            tools = tools_response
        tool_names = [tool.name for tool in tools]
        assert "get_pipeline_failure_summary" in tool_names, (
            f"Expected 'get_pipeline_failure_summary' in registered tools, got tools: {tool_names}"
        )
