"""
Retry helpers for handling Azure DevOps API eventual consistency in tests.

These utilities help make tests more robust by handling:
- Pipeline creation/deletion propagation delays
- Cache invalidation for fresh API calls
- Fuzzy matching retries when exact names fail
"""

import asyncio
import logging
from collections.abc import Callable
from typing import Any, TypeVar

from fastmcp.client import Client

from ado.cache import ado_cache

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def wait_for_pipeline_deletion(
    mcp_client: Client,
    project_id: str,
    pipeline_id: int,
    max_retries: int = 15,
    retry_delay: int = 3,
):
    """
    Wait for pipeline deletion to be reflected in the API with retry mechanism.

    Args:
        mcp_client: The MCP client for API calls
        project_id: Project ID where the pipeline was deleted
        pipeline_id: ID of the deleted pipeline
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds

    Returns:
        None if successful

    Raises:
        AssertionError: If pipeline still appears after all retries
    """
    for attempt in range(max_retries):
        # Aggressive cache clearing for parallel test isolation
        ado_cache.clear_all()
        await asyncio.sleep(0.5)  # Small delay to ensure cache clearing propagates

        pipelines_list = await mcp_client.call_tool("list_pipelines", {"project_id": project_id})
        pipeline_ids = [p["id"] for p in pipelines_list.data]

        if pipeline_id not in pipeline_ids:
            # Pipeline successfully deleted and no longer appears in list
            return

        if attempt < max_retries - 1:  # Don't sleep on the last attempt
            await asyncio.sleep(retry_delay)

    # If we get here, all retries failed
    raise AssertionError(
        f"Pipeline {pipeline_id} should be deleted but still appears in list after {max_retries} attempts. "
        f"Current pipeline IDs: {pipeline_ids}"
    )


async def wait_for_pipeline_creation(
    mcp_client: Client,
    project_id: str,
    pipeline_id: int,
    max_retries: int = 15,
    retry_delay: int = 3,
):
    """
    Wait for pipeline creation to be reflected in the API with retry mechanism.

    Args:
        mcp_client: The MCP client for API calls
        project_id: Project ID where the pipeline was created
        pipeline_id: ID of the created pipeline
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds

    Returns:
        None if successful

    Raises:
        AssertionError: If pipeline doesn't appear after all retries
    """
    for attempt in range(max_retries):
        # Aggressive cache clearing for parallel test isolation
        ado_cache.clear_all()
        await asyncio.sleep(0.5)  # Small delay to ensure cache clearing propagates

        pipelines_list = await mcp_client.call_tool("list_pipelines", {"project_id": project_id})
        pipeline_ids = [p["id"] for p in pipelines_list.data]

        if pipeline_id in pipeline_ids:
            # Pipeline successfully created and appears in list
            return

        if attempt < max_retries - 1:  # Don't sleep on the last attempt
            await asyncio.sleep(retry_delay)

    # If we get here, all retries failed
    raise AssertionError(
        f"Pipeline {pipeline_id} should appear in pipelines list but was not found after {max_retries} attempts. "
        f"Current pipeline IDs: {pipeline_ids}"
    )


async def retry_with_cache_invalidation(
    mcp_client: Client,
    tool_name: str,
    tool_params: dict,
    project_id: str = None,
    max_retries: int = 3,
    retry_delay: int = 1,
    expected_success: bool = True,
) -> Any:
    """
    Retry a tool call with cache invalidation between attempts.

    This is useful for tools that depend on cached data that might be stale,
    particularly when running tests in parallel where cache state can be inconsistent.

    Args:
        mcp_client: The MCP client for API calls
        tool_name: Name of the tool to call
        tool_params: Parameters for the tool call
        project_id: Project ID for cache invalidation (if applicable)
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        expected_success: Whether the call should succeed (True) or fail (False)

    Returns:
        The result from the successful tool call

    Raises:
        The last exception encountered if all retries fail
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            # Invalidate relevant caches before each attempt
            if project_id:
                ado_cache.invalidate_pipelines(project_id)
                ado_cache.invalidate_projects()

            result = await mcp_client.call_tool(tool_name, tool_params)

            if expected_success:
                # If we expected success and got here, we succeeded
                return result
            else:
                # If we expected failure but got success, that's unexpected
                raise AssertionError(f"Expected {tool_name} to fail but it succeeded")

        except Exception as e:
            last_exception = e

            if not expected_success:
                # If we expected failure and got an exception, that's success
                return e

            # Log the attempt for debugging
            logger.debug(f"Attempt {attempt + 1} failed for {tool_name}: {e}")

            if attempt < max_retries - 1:  # Don't sleep on the last attempt
                await asyncio.sleep(retry_delay)

    # If we get here, all retries failed
    raise last_exception


async def retry_pipeline_operation(
    mcp_client: Client,
    operation_func: Callable,
    operation_name: str,
    max_retries: int = 3,
    retry_delay: int = 1,
) -> Any:
    """
    Retry a pipeline operation with exponential backoff and cache invalidation.

    This is a generic retry wrapper for any pipeline-related operation that might
    be affected by cache inconsistency or API propagation delays.

    Args:
        mcp_client: The MCP client for API calls
        operation_func: The operation function to retry (should be async)
        operation_name: Name of the operation for logging
        max_retries: Maximum number of retry attempts
        retry_delay: Base delay between retries in seconds (with exponential backoff)

    Returns:
        The result from the successful operation

    Raises:
        The last exception encountered if all retries fail
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            # Clear caches before each attempt
            ado_cache.clear_all()

            result = await operation_func()
            logger.debug(f"{operation_name} succeeded on attempt {attempt + 1}")
            return result

        except Exception as e:
            last_exception = e
            logger.debug(f"{operation_name} attempt {attempt + 1} failed: {e}")

            if attempt < max_retries - 1:  # Don't sleep on the last attempt
                # Exponential backoff
                sleep_time = retry_delay * (2**attempt)
                await asyncio.sleep(sleep_time)

    # If we get here, all retries failed
    logger.error(f"{operation_name} failed after {max_retries} attempts")
    raise last_exception
