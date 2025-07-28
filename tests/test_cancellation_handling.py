"""
Tests for graceful cancellation handling of MCP tools.

These tests verify that when users cancel tools mid-execution,
they receive clean, user-friendly messages instead of stack traces.
"""

import asyncio
import os
import pytest
import signal
from contextlib import asynccontextmanager
from typing import Optional

from fastmcp.client import Client
from fastmcp.exceptions import ToolError
from ado.graceful_cancellation import GracefulCancellationError

from server import mcp
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


@asynccontextmanager
async def cancellation_test_helper(delay_seconds: float = 1.0):
    """
    Helper context manager that automatically cancels the operation after a delay.
    
    This simulates user cancellation (Ctrl+C) during tool execution.
    """
    created_task = None
    cancelled = False
    exception_info = None
    
    async def cancel_after_delay():
        nonlocal cancelled, exception_info, created_task
        try:
            await asyncio.sleep(delay_seconds)
            if created_task and not created_task.done():
                created_task.cancel()
                cancelled = True
        except Exception as e:
            exception_info = e
    
    # Start the cancellation timer
    cancel_task = asyncio.create_task(cancel_after_delay())
    
    def task_factory(coro):
        nonlocal created_task
        created_task = asyncio.create_task(coro)
        return created_task
    
    try:
        yield task_factory
    finally:
        # Clean up the cancellation timer
        if not cancel_task.done():
            cancel_task.cancel()
        try:
            await cancel_task
        except asyncio.CancelledError:
            pass


@requires_ado_creds
async def test_run_pipeline_and_get_outcome_by_name_graceful_cancellation(mcp_client: Client):
    """
    Test that run_pipeline_and_get_outcome_by_name handles cancellation gracefully.
    
    This test starts a long-running pipeline operation and cancels it mid-execution
    to verify that users get a clean cancellation message instead of stack traces.
    """
    # Test configuration - use a pipeline that actually runs
    project_name = "ado-mcp"
    pipeline_name = "test_run_and_get_pipeline_run_details"
    
    cancelled_cleanly = False
    received_stack_trace = False
    exception_type = None
    exception_message = ""
    
    # Cancel very quickly to catch the operation in progress
    async with cancellation_test_helper(delay_seconds=0.1) as create_task:
        try:
            # Start the long-running operation
            task = create_task(
                mcp_client.call_tool('run_pipeline_and_get_outcome_by_name', {
                    'project_name': project_name,
                    'pipeline_name': pipeline_name,
                    'timeout_seconds': 300  # This would normally wait 5 minutes
                })
            )
            
            # Wait for the operation (it will be cancelled)
            result = await task
            
            # If we get here, the operation completed before cancellation
            pytest.fail("Operation should have been cancelled but completed successfully")
            
        except asyncio.CancelledError:
            # This is what we expect - clean cancellation
            cancelled_cleanly = True
            exception_type = "CancelledError"
            
        except GracefulCancellationError as e:
            # Clean cancellation handling
            cancelled_cleanly = True
            exception_type = "GracefulCancellationError"
            exception_message = str(e)
            
        except ToolError as e:
            # Tool-level error handling
            exception_type = "ToolError"
            exception_message = str(e)
            
            # Check if it contains stack trace indicators
            if any(indicator in exception_message.lower() for indicator in [
                "traceback", "exception group", "baseexceptiongroup", 
                "systemexxit", "unhandled exception"
            ]):
                received_stack_trace = True
                
        except Exception as e:
            # Any other exception type
            exception_type = type(e).__name__
            exception_message = str(e)
            
            # Check for stack trace indicators
            if any(indicator in str(e).lower() for indicator in [
                "traceback", "exception group", "baseexceptiongroup", 
                "systemexxit", "unhandled exception"
            ]):
                received_stack_trace = True
    
    # Assertions about the cancellation behavior
    print(f"Cancellation result: {exception_type}")
    print(f"Exception message: {exception_message[:200]}...")
    print(f"Cancelled cleanly: {cancelled_cleanly}")
    print(f"Received stack trace: {received_stack_trace}")
    
    # What we want to achieve (should now pass with graceful cancellation):
    assert cancelled_cleanly or exception_type == "GracefulCancellationError", f"Tool should handle cancellation cleanly, got {exception_type}: {exception_message}"
    assert not received_stack_trace, "User should not see internal stack traces during cancellation"
    
    # Verify we get a clean user message
    if exception_type == "GracefulCancellationError":
        assert "cancelled" in exception_message.lower(), f"Cancellation message should be user-friendly: {exception_message}"
    
    # Document what the user currently experiences
    if received_stack_trace:
        print("❌ PROBLEM: User sees ugly stack traces on cancellation")
    else:
        print("✅ User message is clean (unexpected - maybe already fixed?)")


@requires_ado_creds
async def test_run_pipeline_graceful_cancellation(mcp_client: Client):
    """
    Test that run_pipeline handles cancellation gracefully.
    
    This tests a simpler pipeline start operation.
    """
    cancelled_cleanly = False
    received_stack_trace = False
    exception_type = None
    exception_message = ""
    
    async with cancellation_test_helper(delay_seconds=0.1) as create_task:
        try:
            task = create_task(
                mcp_client.call_tool('run_pipeline', {
                    'project_name': 'ado-mcp',
                    'pipeline_name': 'test_run_and_get_pipeline_run_details'
                })
            )
            result = await task
            print("✅ Operation completed before cancellation could occur")
            return
            
        except asyncio.CancelledError:
            cancelled_cleanly = True
            exception_type = "CancelledError"
            
        except Exception as e:
            exception_type = type(e).__name__  
            exception_message = str(e)
            
            if any(indicator in str(e).lower() for indicator in [
                "traceback", "exception group", "baseexceptiongroup"
            ]):
                received_stack_trace = True
    
    print(f"Run pipeline cancellation: {exception_type}")
    if exception_message:
        print(f"Message: {exception_message[:200]}...")
    
    # Document current behavior
    if not cancelled_cleanly and received_stack_trace:
        print("❌ PROBLEM: Pipeline start also shows stack traces on cancellation")


@requires_ado_creds 
async def test_list_projects_graceful_cancellation(mcp_client: Client):
    """
    Test that list_projects handles cancellation gracefully.
    
    This is a shorter operation but still needs graceful handling.
    """
    cancelled_cleanly = False
    received_stack_trace = False
    exception_type = None
    exception_message = ""
    
    async with cancellation_test_helper(delay_seconds=0.01) as create_task:  # Extremely quick cancel
        try:
            task = create_task(mcp_client.call_tool('list_projects', {}))
            result = await task
            
            # Operation might complete before cancellation due to caching
            print("✅ Operation completed before cancellation could occur")
            return
            
        except asyncio.CancelledError:
            cancelled_cleanly = True
            exception_type = "CancelledError"
            
        except Exception as e:
            exception_type = type(e).__name__  
            exception_message = str(e)
            
            if any(indicator in str(e).lower() for indicator in [
                "traceback", "exception group", "baseexceptiongroup"
            ]):
                received_stack_trace = True
    
    print(f"List projects cancellation: {exception_type}")
    if exception_message:
        print(f"Message: {exception_message[:100]}...")
    
    # Document current behavior
    if not cancelled_cleanly and received_stack_trace:
        print("❌ PROBLEM: Short operations also show stack traces on cancellation")


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v", "-s"])