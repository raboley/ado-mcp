"""Tests for cache telemetry and metrics."""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastmcp.client import Client

from server import mcp
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
    return "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before and after each test."""
    ado_cache.clear_all()
    yield
    ado_cache.clear_all()


@pytest.mark.asyncio
@requires_ado_creds
async def test_cache_hit_miss_telemetry(mcp_client, project_id):
    """Test that cache hits and misses are tracked with telemetry."""
    # Mock the metrics counters to track calls
    with (
        patch.object(ado_cache._cache_hit_counter, "add") as mock_hit_counter,
        patch.object(ado_cache._cache_miss_counter, "add") as mock_miss_counter,
    ):
        # First call - should be a cache miss
        result1 = await mcp_client.call_tool("list_work_item_types", {"project_id": project_id})

        assert result1.data is not None, "First call should return data"

        # Verify cache miss was recorded
        mock_miss_counter.assert_called_with(
            1, {"cache_type": "work_item_types", "reason": "not_found"}
        )
        assert mock_hit_counter.call_count == 0, "Should not have any cache hits yet"

        # Reset mocks
        mock_hit_counter.reset_mock()
        mock_miss_counter.reset_mock()

        # Second call - should be a cache hit
        result2 = await mcp_client.call_tool("list_work_item_types", {"project_id": project_id})

        assert result2.data is not None, "Second call should return data"

        # Verify cache hit was recorded
        mock_hit_counter.assert_called_with(1, {"cache_type": "work_item_types"})
        assert mock_miss_counter.call_count == 0, "Should not have any cache misses for second call"


@pytest.mark.asyncio
@requires_ado_creds
async def test_cache_size_telemetry(mcp_client, project_id):
    """Test that cache size is tracked correctly."""
    # Mock the cache size gauge
    with patch.object(ado_cache._cache_size_gauge, "add") as mock_size_gauge:
        # Clear cache to ensure clean state
        ado_cache.clear_all()

        # First call - should add entries to cache
        await mcp_client.call_tool("list_work_item_types", {"project_id": project_id})

        # Should have added at least 2 entries (work_item_types and name_map)
        assert mock_size_gauge.call_count >= 2, "Should have tracked cache size increases"

        # Verify positive increments
        for call in mock_size_gauge.call_args_list:
            args = call[0]
            kwargs = call[1] if len(call) > 1 else {}
            assert args[0] == 1, "Should increment by 1 for each new cache entry"
            assert len(args) > 1 and isinstance(args[1], dict) and "cache_type" in args[1], (
                "Should include cache_type in metrics"
            )


@pytest.mark.asyncio
@requires_ado_creds
async def test_cache_eviction_telemetry():
    """Test that cache evictions are tracked correctly."""
    # Create a mock expired entry directly in the cache
    import time
    from ado.cache import CacheEntry

    # Add an already-expired entry
    expired_key = "test_type:test_id"
    ado_cache._cache[expired_key] = CacheEntry(
        data={"test": "data"},
        expires_at=time.time() - 1,  # Already expired
    )

    with (
        patch.object(ado_cache._cache_eviction_counter, "add") as mock_eviction_counter,
        patch.object(ado_cache._cache_size_gauge, "add") as mock_size_gauge,
    ):
        # Try to get the expired entry
        result = ado_cache._get(expired_key)

        assert result is None, "Should not return expired data"

        # Verify eviction was tracked
        mock_eviction_counter.assert_called_with(
            1, {"cache_type": "test_type", "reason": "expired"}
        )
        mock_size_gauge.assert_called_with(-1, {"cache_type": "test_type"})


@pytest.mark.asyncio
@requires_ado_creds
async def test_cache_clear_all_telemetry():
    """Test that clearing all cache entries updates telemetry correctly."""
    # Add some entries to the cache
    ado_cache._set("projects:123", {"data": "project"}, 60)
    ado_cache._set("work_item_types:123", {"data": "types"}, 60)
    ado_cache._set("area_paths:123", {"data": "paths"}, 60)

    with (
        patch.object(ado_cache._cache_size_gauge, "add") as mock_size_gauge,
        patch.object(ado_cache._cache_eviction_counter, "add") as mock_eviction_counter,
    ):
        # Clear all cache
        ado_cache.clear_all()

        # Should have tracked decrements for each cache type
        assert mock_size_gauge.call_count == 3, "Should track size decrease for each cache type"
        assert mock_eviction_counter.call_count == 3, "Should track evictions for each cache type"

        # Verify all were negative decrements
        for call in mock_size_gauge.call_args_list:
            args = call[0]
            assert args[0] < 0, "Should decrement cache size"
            assert len(args) > 1 and isinstance(args[1], dict), "Should have metrics dict"
            cache_type = args[1].get("cache_type")
            assert cache_type in ["projects", "work_item_types", "area_paths"], (
                f"Unexpected cache type: {cache_type}"
            )


@pytest.mark.asyncio
@requires_ado_creds
async def test_cache_stats_includes_type_breakdown():
    """Test that cache stats include breakdown by cache type."""
    # Add various types of cache entries
    ado_cache._set("projects:123", {"data": "project"}, 60)
    ado_cache._set("projects:456", {"data": "project2"}, 60)
    ado_cache._set("work_item_types:123", {"data": "types"}, 60)
    ado_cache._set("area_paths:123", {"data": "paths"}, 60)

    stats = ado_cache.get_stats()

    assert stats["total_entries"] == 4, "Should have 4 total entries"
    assert stats["active_entries"] == 4, "All entries should be active"
    assert stats["expired_entries"] == 0, "No entries should be expired"

    # Check entries by type
    assert stats["entries_by_type"]["projects"] == 2, "Should have 2 project entries"
    assert stats["entries_by_type"]["work_item_types"] == 1, "Should have 1 work item type entry"
    assert stats["entries_by_type"]["area_paths"] == 1, "Should have 1 area path entry"

    assert "metrics_info" in stats, "Should include info about metrics"


@pytest.mark.asyncio
@requires_ado_creds
async def test_different_cache_types_tracked_separately(mcp_client, project_id):
    """Test that different cache types are tracked separately in telemetry."""
    with (
        patch.object(ado_cache._cache_hit_counter, "add") as mock_hit_counter,
        patch.object(ado_cache._cache_miss_counter, "add") as mock_miss_counter,
    ):
        # Call different cache types
        await mcp_client.call_tool("list_work_item_types", {"project_id": project_id})
        await mcp_client.call_tool("list_area_paths", {"project_id": project_id})
        await mcp_client.call_tool("list_iteration_paths", {"project_id": project_id})

        # Each should record a miss with different cache_type
        miss_calls = mock_miss_counter.call_args_list
        cache_types_missed = []
        for call in miss_calls:
            args = call[0]
            if len(args) > 1 and isinstance(args[1], dict) and "cache_type" in args[1]:
                cache_types_missed.append(args[1]["cache_type"])

        assert "work_item_types" in cache_types_missed, "Should track work_item_types misses"
        assert "area_paths" in cache_types_missed, "Should track area_paths misses"
        assert "iteration_paths" in cache_types_missed, "Should track iteration_paths misses"
