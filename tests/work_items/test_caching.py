"""Tests for work item caching functionality."""

import os
import time

import pytest
from fastmcp.client import Client

from ado.cache import ado_cache
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


@pytest.fixture
def project_id():
    return get_project_id()  # ado-mcp project


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before and after each test."""
    ado_cache.clear_all()
    yield
    ado_cache.clear_all()


@pytest.mark.asyncio
@requires_ado_creds
async def test_work_item_types_caching(mcp_client, project_id):
    """Test that work item types are cached and returned from cache on subsequent calls."""
    # Clear cache to ensure clean state
    ado_cache.clear_all()

    # First call - should hit the API
    start_time = time.time()
    result1 = await mcp_client.call_tool("list_work_item_types", {"project_id": project_id})
    first_call_duration = time.time() - start_time

    assert result1.data is not None, "First call should return data"
    work_item_types1 = result1.data
    assert isinstance(work_item_types1, list), (
        f"Should return a list but got: {type(work_item_types1)}"
    )
    assert len(work_item_types1) > 0, "Should have at least one work item type"

    # Second call - should hit the cache
    start_time = time.time()
    result2 = await mcp_client.call_tool("list_work_item_types", {"project_id": project_id})
    second_call_duration = time.time() - start_time

    assert result2.data is not None, "Second call should return data"
    work_item_types2 = result2.data

    # Verify same data returned
    assert len(work_item_types1) == len(work_item_types2), (
        "Should return same number of work item types from cache"
    )
    assert work_item_types1[0]["name"] == work_item_types2[0]["name"], (
        "Should return same work item types from cache"
    )

    # Cache should be significantly faster (at least 3x faster)
    assert second_call_duration < first_call_duration / 3, (
        f"Cache should be faster. API: {first_call_duration:.3f}s, Cache: {second_call_duration:.3f}s"
    )


@pytest.mark.asyncio
@requires_ado_creds
async def test_area_paths_caching(mcp_client, project_id):
    """Test that area paths are cached and returned from cache on subsequent calls."""
    # Clear cache to ensure clean state
    ado_cache.clear_all()

    # First call - should hit the API
    start_time = time.time()
    result1 = await mcp_client.call_tool("list_area_paths", {"project_id": project_id})
    first_call_duration = time.time() - start_time

    assert result1.data is not None, "First call should return data"
    area_paths1 = result1.data
    assert isinstance(area_paths1, list), f"Should return a list but got: {type(area_paths1)}"

    # Second call - should hit the cache
    start_time = time.time()
    result2 = await mcp_client.call_tool("list_area_paths", {"project_id": project_id})
    second_call_duration = time.time() - start_time

    assert result2.data is not None, "Second call should return data"
    area_paths2 = result2.data

    # Verify same data returned
    assert len(area_paths1) == len(area_paths2), "Should return same area paths from cache"
    if area_paths1:  # Only check if we have data
        assert area_paths1[0]["name"] == area_paths2[0]["name"], (
            "Should return same area path data from cache"
        )

    # Cache should be significantly faster
    assert second_call_duration < first_call_duration / 5, (
        f"Cache should be faster. API: {first_call_duration:.3f}s, Cache: {second_call_duration:.3f}s"
    )


@pytest.mark.asyncio
@requires_ado_creds
async def test_area_paths_caching_with_depth_parameter(mcp_client, project_id):
    """Test that area paths with depth parameter are not cached."""
    ado_cache.clear_all()

    # Verify cache is empty initially
    assert ado_cache.get_area_paths(project_id) is None, "Cache should be empty initially"

    # First call with depth=1 - should hit API and NOT populate cache
    result1 = await mcp_client.call_tool("list_area_paths", {"project_id": project_id, "depth": 1})

    assert result1.data is not None, "First call should return data"

    # Cache should still be empty since depth parameter was used
    assert ado_cache.get_area_paths(project_id) is None, (
        "Cache should remain empty when depth is specified"
    )

    # Second call with depth=2 - should also hit API and NOT populate cache
    result2 = await mcp_client.call_tool("list_area_paths", {"project_id": project_id, "depth": 2})

    assert result2.data is not None, "Second call should return data"

    # Cache should still be empty
    assert ado_cache.get_area_paths(project_id) is None, (
        "Cache should remain empty when depth is specified"
    )

    # Call without depth - should hit API and populate cache
    result3 = await mcp_client.call_tool("list_area_paths", {"project_id": project_id})

    assert result3.data is not None, "Third call should return data"

    # Now cache should be populated
    assert ado_cache.get_area_paths(project_id) is not None, (
        "Cache should be populated when no depth is specified"
    )


@pytest.mark.asyncio
@requires_ado_creds
async def test_iteration_paths_caching(mcp_client, project_id):
    """Test that iteration paths are cached and returned from cache on subsequent calls."""
    # Clear cache to ensure clean state
    ado_cache.clear_all()

    # First call - should hit the API
    start_time = time.time()
    result1 = await mcp_client.call_tool("list_iteration_paths", {"project_id": project_id})
    first_call_duration = time.time() - start_time

    assert result1.data is not None, "First call should return data"
    iteration_paths1 = result1.data
    assert isinstance(iteration_paths1, list), (
        f"Should return a list but got: {type(iteration_paths1)}"
    )

    # Second call - should hit the cache
    start_time = time.time()
    result2 = await mcp_client.call_tool("list_iteration_paths", {"project_id": project_id})
    second_call_duration = time.time() - start_time

    assert result2.data is not None, "Second call should return data"
    iteration_paths2 = result2.data

    # Verify same data returned
    assert len(iteration_paths1) == len(iteration_paths2), (
        "Should return same iteration paths from cache"
    )
    if iteration_paths1:  # Only check if we have data
        assert iteration_paths1[0]["name"] == iteration_paths2[0]["name"], (
            "Should return same iteration path data from cache"
        )

    # Cache should be significantly faster
    assert second_call_duration < first_call_duration / 5, (
        f"Cache should be faster. API: {first_call_duration:.3f}s, Cache: {second_call_duration:.3f}s"
    )


@pytest.mark.asyncio
@requires_ado_creds
async def test_cache_expiration_not_immediate(mcp_client, project_id):
    """Test that cache entries do not expire immediately."""
    # Clear cache to ensure clean state
    ado_cache.clear_all()

    # First call - populate cache
    result1 = await mcp_client.call_tool("list_work_item_types", {"project_id": project_id})

    assert result1.data is not None, "First call should return data"

    # Wait a short time (1 second)
    time.sleep(1)

    # Second call - should still hit cache (TTL is 1 hour)
    start_time = time.time()
    await mcp_client.call_tool("list_work_item_types", {"project_id": project_id})
    cache_call_duration = time.time() - start_time

    # Cache call should be very fast (less than 0.1 seconds)
    assert cache_call_duration < 0.1, (
        f"Cache call should be fast but took {cache_call_duration:.3f}s"
    )


@pytest.mark.asyncio
@requires_ado_creds
async def test_cache_different_projects_isolated(mcp_client, project_id):
    """Test that cache entries for different projects are isolated."""
    # Clear cache to ensure clean state
    ado_cache.clear_all()

    # Call for first project
    result1 = await mcp_client.call_tool("list_work_item_types", {"project_id": project_id})

    assert result1.data is not None, "First project call should return data"
    types1 = result1.data

    # Call for a different project (use a fake ID that won't exist)
    fake_project_id = "12345678-1234-1234-1234-123456789012"

    # This will fail, but that's ok - we're testing cache isolation
    try:
        await mcp_client.call_tool("list_work_item_types", {"project_id": fake_project_id})
    except Exception:
        pass  # Expected to fail

    # Call for first project again - should still hit cache
    start_time = time.time()
    result2 = await mcp_client.call_tool("list_work_item_types", {"project_id": project_id})
    cache_duration = time.time() - start_time

    assert result2.data is not None, "Should return cached data for first project"
    assert cache_duration < 0.1, f"Should hit cache but took {cache_duration:.3f}s"
    assert len(result2.data) == len(types1), "Should return same data from cache"


@pytest.mark.asyncio
@requires_ado_creds
async def test_work_item_types_cache_integration(mcp_client, project_id):
    """Test that caching integrates correctly with the MCP server and tools."""
    # Clear cache and get stats
    ado_cache.clear_all()
    initial_stats = ado_cache.get_stats()
    assert initial_stats["total_entries"] == 0, "Cache should be empty initially"

    # Make first call
    await mcp_client.call_tool("list_work_item_types", {"project_id": project_id})

    # Check cache stats
    stats_after_first = ado_cache.get_stats()
    assert stats_after_first["total_entries"] >= 2, (
        "Should have cached work item types and name map"
    )
    assert stats_after_first["active_entries"] == stats_after_first["total_entries"], (
        "All entries should be active"
    )

    # Verify cache keys are as expected
    cache_keys = stats_after_first["cache_keys"]
    assert any(f"work_item_types:{project_id}" in key for key in cache_keys), (
        "Should have work item types cache key"
    )
    assert any(f"work_item_types:{project_id}:name_map" in key for key in cache_keys), (
        "Should have name map cache key"
    )
