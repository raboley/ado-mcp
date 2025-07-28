#!/usr/bin/env python3
"""
Direct test of real cancellation behavior - simulates actual Ctrl+C.
"""

import asyncio
import os
import signal
import sys
from server import mcp
from fastmcp.client import Client


class CancellationCapturer:
    """Captures and analyzes cancellation behavior."""
    
    def __init__(self):
        self.cancelled_cleanly = False
        self.received_stack_trace = False  
        self.exception_type = None
        self.exception_message = ""
        self.output_lines = []
    
    def analyze_exception(self, e: Exception):
        """Analyze an exception for user experience issues."""
        self.exception_type = type(e).__name__
        self.exception_message = str(e)
        
        # Check for stack trace indicators that users shouldn't see
        stack_trace_indicators = [
            "traceback", "exception group", "baseexceptiongroup", 
            "systemexpit", "unhandled exception", "task: <task finished",
            "file \"/users/", "line ", "in ", "^^^^^", "raise"
        ]
        
        self.received_stack_trace = any(
            indicator in self.exception_message.lower() 
            for indicator in stack_trace_indicators
        )
        
        if self.exception_type == "CancelledError":
            self.cancelled_cleanly = True
    
    def report(self):
        """Report the cancellation experience."""
        print(f"\n{'='*60}")
        print("CANCELLATION ANALYSIS REPORT")
        print(f"{'='*60}")
        print(f"Exception type: {self.exception_type}")
        print(f"Cancelled cleanly: {self.cancelled_cleanly}")
        print(f"User sees stack trace: {self.received_stack_trace}")
        
        if self.exception_message:
            print(f"\nException message (first 300 chars):")
            print(f"{self.exception_message[:300]}...")
        
        print(f"\n{'='*60}")
        if self.cancelled_cleanly and not self.received_stack_trace:
            print("✅ GOOD: Clean cancellation experience")
        else:
            print("❌ PROBLEM: Poor user experience on cancellation")
            if self.received_stack_trace:
                print("   - User sees internal stack traces")
            if not self.cancelled_cleanly:
                print("   - Exception not handled gracefully")


async def test_long_running_operation():
    """Test cancellation of a long-running operation."""
    capturer = CancellationCapturer()
    
    try:
        async with Client(mcp) as client:
            # Set up organization
            initial_org_url = os.environ.get('ADO_ORGANIZATION_URL', 'https://dev.azure.com/RussellBoley')
            await client.call_tool('set_ado_organization', {'organization_url': initial_org_url})
            
            print("🚀 Starting long-running pipeline operation...")
            print("   (This will be cancelled in 2 seconds)")
            
            # Start the operation that will be cancelled
            result = await client.call_tool('run_pipeline_and_get_outcome_by_name', {
                'project_name': 'ado-mcp',
                'pipeline_name': 'test_run_and_get_pipeline_run_details',
                'timeout_seconds': 300
            })
            
            print("❌ This shouldn't print - operation should be cancelled")
            
    except KeyboardInterrupt as e:
        print("📡 Caught KeyboardInterrupt")
        capturer.analyze_exception(e)
    except asyncio.CancelledError as e:
        print("📡 Caught CancelledError")
        capturer.analyze_exception(e)
    except Exception as e:
        print(f"📡 Caught {type(e).__name__}")
        capturer.analyze_exception(e)
    
    capturer.report()
    return capturer


def setup_cancellation_timer():
    """Set up automatic cancellation after 2 seconds."""
    def cancel_handler(signum, frame):
        print(f"\n⚡ Cancellation signal received (signal {signum})")
        # Don't call sys.exit() here - let the exception propagate naturally
        raise KeyboardInterrupt("Operation cancelled by user")
    
    # Set up the signal handler
    signal.signal(signal.SIGALRM, cancel_handler)
    signal.alarm(2)  # Cancel after 2 seconds


async def main():
    """Main test function."""
    print("Testing real cancellation behavior...")
    print("This simulates what happens when users press Ctrl+C")
    
    # Set up automatic cancellation
    setup_cancellation_timer()
    
    try:
        capturer = await test_long_running_operation()
        
        # Analysis
        if capturer.received_stack_trace:
            print("\n🎯 TARGET: Eliminate stack traces from user output")
        if not capturer.cancelled_cleanly:
            print("🎯 TARGET: Provide clean cancellation handling")
            
    except KeyboardInterrupt:
        print("\n💥 KeyboardInterrupt reached main() - this is what users see!")
    except Exception as e:
        print(f"\n💥 Exception reached main(): {type(e).__name__}: {e}")
    finally:
        # Cancel any remaining alarm
        signal.alarm(0)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🏁 Final KeyboardInterrupt handling")
    except Exception as e:
        print(f"\n🏁 Final exception: {type(e).__name__}: {e}")