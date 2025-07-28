#!/usr/bin/env python3
"""
Demo script showing the improved cancellation behavior.

Run this to see how tools now handle cancellation gracefully with
clean user messages instead of ugly stack traces.
"""

import asyncio
import os
import signal
import sys
from server import mcp
from fastmcp.client import Client


async def demo_graceful_cancellation():
    """Demonstrate the improved cancellation behavior."""
    async with Client(mcp) as client:
        # Set up organization
        initial_org_url = os.environ.get('ADO_ORGANIZATION_URL', 'https://dev.azure.com/RussellBoley')
        await client.call_tool('set_ado_organization', {'organization_url': initial_org_url})
        
        print("🎯 Testing graceful cancellation handling...")
        print("   Starting pipeline operation (will be cancelled in 1 second)")
        
        try:
            result = await client.call_tool('run_pipeline_and_get_outcome_by_name', {
                'project_name': 'ado-mcp',
                'pipeline_name': 'test_run_and_get_pipeline_run_details',
                'timeout_seconds': 300
            })
            
            print("❌ This shouldn't appear - operation should be cancelled")
            
        except Exception as e:
            exception_type = type(e).__name__
            print(f"\n✅ User-facing cancellation experience:")
            print(f"   Exception Type: {exception_type}")
            print(f"   User Message: {str(e)}")
            
            # Check if it's a clean cancellation
            if exception_type == "GracefulCancellationError":
                print("\n🎉 SUCCESS: Clean cancellation message!")
                print("   Users now see friendly messages instead of stack traces")
            else:
                print(f"\n❌ PROBLEM: Still showing technical details to users")
            
            return exception_type == "GracefulCancellationError"


def setup_auto_cancel():
    """Set up automatic cancellation after 1 second."""
    def cancel_handler(signum, frame):
        print(f"\n⚡ Auto-cancelling operation...")
        raise KeyboardInterrupt("Demo cancellation")
    
    signal.signal(signal.SIGALRM, cancel_handler)
    signal.alarm(1)  # Cancel after 1 second


async def main():
    """Main demo function."""
    print("=" * 60)
    print("GRACEFUL CANCELLATION DEMO")
    print("=" * 60)
    print("This demo shows how MCP tools now handle cancellation gracefully.")
    print("Before: Users saw ugly BaseExceptionGroup stack traces")
    print("After:  Users see clean, friendly cancellation messages")
    print("=" * 60)
    
    setup_auto_cancel()
    
    try:
        success = await demo_graceful_cancellation()
        
        if success:
            print("\n🎯 RESULT: Graceful cancellation is working correctly!")
            print("   Users now get clean messages when they press Ctrl+C")
        else:
            print("\n❌ RESULT: Cancellation needs more work")
            
    except KeyboardInterrupt:
        print("\n💭 Final KeyboardInterrupt handling (this is expected)")
    except Exception as e:
        print(f"\n⚠️ Unexpected error: {type(e).__name__}: {e}")
    finally:
        signal.alarm(0)  # Cancel any remaining alarm


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Demo completed")
    except Exception as e:
        print(f"\n💥 Demo error: {type(e).__name__}: {e}")
        sys.exit(1)