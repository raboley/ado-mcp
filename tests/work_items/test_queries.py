import os
import pytest
from fastmcp.client import Client

from server import mcp
from src.test_config import get_project_id
from tests.ado.test_client import requires_ado_creds
from ado.cache import ado_cache

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
def project_id():
    return get_project_id()

@pytest.fixture(autouse=True)
def clear_cache():
    ado_cache.clear_all()
    yield
    ado_cache.clear_all()

@pytest.mark.asyncio
@requires_ado_creds
async def test_query_work_items_default_query(mcp_client, project_id):
    result = await mcp_client.call_tool("query_work_items", {"project_id": project_id})

    assert result.data is not None, "Query should return data"
    query_result = result.data

    assert "queryType" in query_result, "Should include queryType"
    assert "workItems" in query_result, "Should include workItems"
    assert "columns" in query_result, "Should include columns"
    assert isinstance(query_result["workItems"], list), "workItems should be a list"

@pytest.mark.asyncio
@requires_ado_creds
async def test_query_work_items_with_wiql(mcp_client, project_id):
    wiql_query = (
        "SELECT [System.Id], [System.Title] "
        "FROM WorkItems "
        "WHERE [System.WorkItemType] = 'Bug' "
        "ORDER BY [System.Id]"
    )

    result = await mcp_client.call_tool(
        "query_work_items", {"project_id": project_id, "wiql_query": wiql_query}
    )

    assert result.data is not None, "WIQL query should return data"
    query_result = result.data

    assert query_result["queryType"] == "flat", "Should be flat query type"
    assert isinstance(query_result["workItems"], list), "workItems should be a list"

@pytest.mark.asyncio
@requires_ado_creds
async def test_query_work_items_with_simple_filter(mcp_client, project_id):
    result = await mcp_client.call_tool(
        "query_work_items",
        {"project_id": project_id, "simple_filter": {"work_item_type": "Task", "state": "New"}},
    )

    assert result.data is not None, "Simple filter query should return data"
    query_result = result.data

    assert isinstance(query_result["workItems"], list), "workItems should be a list"

@pytest.mark.asyncio
@requires_ado_creds
async def test_query_work_items_with_pagination(mcp_client, project_id):
    result1 = await mcp_client.call_tool("query_work_items", {"project_id": project_id, "top": 5})

    assert result1.data is not None, "Query with top should return data"

    result2 = await mcp_client.call_tool(
        "query_work_items", {"project_id": project_id, "skip": 0, "top": 3}
    )

    assert result2.data is not None, "Query with skip and top should return data"

@pytest.mark.asyncio
@requires_ado_creds
async def test_query_work_items_with_page_parameters(mcp_client, project_id):
    result = await mcp_client.call_tool(
        "query_work_items", {"project_id": project_id, "page_size": 10, "page_number": 1}
    )

    assert result.data is not None, "Query with page parameters should return data"
    query_result = result.data

    assert isinstance(query_result["workItems"], list), "workItems should be a list"

@pytest.mark.asyncio
@requires_ado_creds
async def test_get_work_items_page_default(mcp_client, project_id):
    result = await mcp_client.call_tool("get_work_items_page", {"project_id": project_id})

    assert result.data is not None, "Page query should return data"
    page_result = result.data

    assert "work_items" in page_result, "Should include work_items"
    assert "pagination" in page_result, "Should include pagination"
    assert "query_metadata" in page_result, "Should include query_metadata"

    pagination = page_result["pagination"]
    assert "page_number" in pagination, "pagination should include page_number"
    assert "page_size" in pagination, "pagination should include page_size"
    assert "has_more" in pagination, "pagination should include has_more"
    assert "has_previous" in pagination, "pagination should include has_previous"

@pytest.mark.asyncio
@requires_ado_creds
async def test_get_work_items_page_basic_functionality(mcp_client, project_id):
    result = await mcp_client.call_tool(
        "get_work_items_page", {"project_id": project_id, "page_number": 1, "page_size": 20}
    )

    assert result.data is not None, "Basic page query should return data"
    page_result = result.data

    assert isinstance(page_result["work_items"], list), "work_items should be a list"
    assert page_result["pagination"]["page_number"] == 1, "Should return correct page number"
    assert page_result["pagination"]["page_size"] == 20, "Should return correct page size"

@pytest.mark.asyncio
@requires_ado_creds
async def test_get_work_items_page_pagination_navigation(mcp_client, project_id):
    result1 = await mcp_client.call_tool(
        "get_work_items_page", {"project_id": project_id, "page_number": 1, "page_size": 5}
    )

    assert result1.data is not None, "First page should return data"
    page1 = result1.data

    assert page1["pagination"]["page_number"] == 1, "Should be page 1"
    assert page1["pagination"]["has_previous"] is False, "First page should not have previous"

    if page1["pagination"]["has_more"]:
        result2 = await mcp_client.call_tool(
            "get_work_items_page", {"project_id": project_id, "page_number": 2, "page_size": 5}
        )

        assert result2.data is not None, "Second page should return data"
        page2 = result2.data

        assert page2["pagination"]["page_number"] == 2, "Should be page 2"
        assert page2["pagination"]["has_previous"] is True, "Second page should have previous"

@pytest.mark.asyncio
@requires_ado_creds
async def test_query_work_items_invalid_wiql(mcp_client, project_id):
    invalid_wiql = "INVALID WIQL SYNTAX"

    try:
        result = await mcp_client.call_tool(
            "query_work_items", {"project_id": project_id, "wiql_query": invalid_wiql}
        )
        if result.data is not None:
            assert False, "Invalid WIQL should not return valid data"
    except Exception as e:
        assert "failed" in str(e).lower() or "error" in str(e).lower(), (
            f"Should get meaningful error for invalid WIQL: {e}"
        )

@pytest.mark.asyncio
@requires_ado_creds
async def test_query_work_items_invalid_project(mcp_client):
    invalid_project_id = "00000000-0000-0000-0000-000000000000"

    try:
        result = await mcp_client.call_tool("query_work_items", {"project_id": invalid_project_id})
        if result.data is not None:
            query_result = result.data
            assert isinstance(query_result["workItems"], list), (
                "Should return empty list for invalid project"
            )
    except Exception as e:
        assert "failed" in str(e).lower() or "not found" in str(e).lower(), (
            f"Should get meaningful error for invalid project: {e}"
        )

@pytest.mark.asyncio
@requires_ado_creds
async def test_query_work_items_large_skip_value(mcp_client, project_id):
    result = await mcp_client.call_tool(
        "query_work_items", {"project_id": project_id, "skip": 10000, "top": 10}
    )

    assert result.data is not None, "Query with large skip should return data (possibly empty)"
    query_result = result.data

    assert isinstance(query_result["workItems"], list), "workItems should be a list"

@pytest.mark.asyncio
@requires_ado_creds
async def test_query_work_items_custom_wiql_simple(mcp_client, project_id):
    wiql_query = "SELECT [System.Id], [System.Title] FROM WorkItems ORDER BY [System.Id]"

    result = await mcp_client.call_tool(
        "query_work_items", {"project_id": project_id, "wiql_query": wiql_query, "top": 10}
    )

    assert result.data is not None, "Simple WIQL query should return data"
    query_result = result.data

    assert isinstance(query_result["workItems"], list), "workItems should be a list"
    assert len(query_result["workItems"]) <= 10, "Should respect top parameter"

@pytest.mark.asyncio
@requires_ado_creds
async def test_get_work_items_page_parameter_validation(mcp_client, project_id):
    result = await mcp_client.call_tool(
        "get_work_items_page", {"project_id": project_id, "page_size": 15}
    )

    assert result.data is not None, "Query with page_size should return data"
    page_result = result.data

    assert isinstance(page_result["work_items"], list), "work_items should be a list"
    assert page_result["pagination"]["page_size"] == 15, "Should respect page_size parameter"

@pytest.mark.asyncio
@requires_ado_creds
async def test_query_work_items_small_top_parameter(mcp_client, project_id):
    result = await mcp_client.call_tool("query_work_items", {"project_id": project_id, "top": 1})

    assert result.data is not None, "Query with top=1 should return data"
    query_result = result.data

    assert len(query_result["workItems"]) <= 1, "Should return at most 1 workItem when top=1"

@pytest.mark.asyncio
@requires_ado_creds
async def test_get_work_items_page_small_page_size(mcp_client, project_id):
    result = await mcp_client.call_tool(
        "get_work_items_page",
        {
            "project_id": project_id,
            "page_size": 0,
        },
    )

    assert result.data is not None, "Query with page_size=0 should return data"
    page_result = result.data

    assert isinstance(page_result["work_items"], list), "work_items should be a list"
    assert page_result["pagination"]["page_size"] >= 1, (
        "Should auto-correct page_size to minimum value"
    )

@pytest.mark.asyncio
@requires_ado_creds
async def test_query_work_items_both_wiql_and_filter(mcp_client, project_id):
    wiql_query = "SELECT [System.Id] FROM WorkItems WHERE [System.WorkItemType] = 'Task'"

    result = await mcp_client.call_tool(
        "query_work_items",
        {
            "project_id": project_id,
            "wiql_query": wiql_query,
            "simple_filter": {
                "work_item_type": "Bug"
            },
        },
    )

    assert result.data is not None, "Query with both WIQL and filter should return data"
    query_result = result.data

    assert isinstance(query_result["workItems"], list), "workItems should be a list"

@pytest.mark.asyncio
@requires_ado_creds
async def test_get_work_items_page_high_page_number(mcp_client, project_id):
    first_page = await mcp_client.call_tool(
        "get_work_items_page", {"project_id": project_id, "page_number": 1, "page_size": 10}
    )

    high_page_number = 5000

    result = await mcp_client.call_tool(
        "get_work_items_page",
        {"project_id": project_id, "page_number": high_page_number, "page_size": 10},
    )

    assert result.data is not None, "Query with high page number should return data"
    page_result = result.data

    assert isinstance(page_result["work_items"], list), "work_items should be a list"
    assert page_result["pagination"]["page_number"] == high_page_number, (
        f"Should return requested page number {high_page_number}"
    )
    assert page_result["pagination"]["has_previous"] is True, (
        "High page number should have previous page"
    )
    assert isinstance(page_result["pagination"]["has_more"], bool), "has_more should be a boolean"
