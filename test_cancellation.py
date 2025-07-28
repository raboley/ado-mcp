#!/usr/bin/env python3
"""
Test script to understand cancellation behavior of MCP tools.
"""

import asyncio
import signal
import sys
import os
from server import mcp
from fastmcp.client import Client


async def test_tool_cancellation():
    """Test what happens when a tool is cancelled mid-execution."""
    async with Client(mcp) as client:
        # Set up organization
        initial_org_url = os.environ.get('ADO_ORGANIZATION_URL', 'https://dev.azure.com/RussellBoley')
        await client.call_tool('set_ado_organization', {'organization_url': initial_org_url})
        
        print('Starting pipeline run that will be cancelled...')
        try:
            result = await client.call_tool('run_pipeline_and_get_outcome_by_name', {
                'project_name': 'ado-mcp',
                'pipeline_name': 'test_run_and_get_pipeline_run_details',
                'timeout_seconds': 300
            })
            print('Pipeline completed (this should not print):', result.data)
        except asyncio.CancelledError:
            print('❌ CancelledError caught - this is what users see!')
            raise
        except KeyboardInterrupt:
            print('❌ KeyboardInterrupt caught - this is what users see!')
            raise
        except Exception as e:
            print(f'❌ Other exception: {type(e).__name__}: {e}')
            raise


def handle_interrupt(signum, frame):
    """Handle interrupt signal."""
    print(f'\n📡 Received signal {signum}')
    sys.exit(1)


if __name__ == '__main__':
    # Set up signal handler
    signal.signal(signal.SIGINT, handle_interrupt)
    signal.signal(signal.SIGTERM, handle_interrupt)
    
    try:
        asyncio.run(test_tool_cancellation())
    except KeyboardInterrupt:
        print('💥 Main KeyboardInterrupt - this is the final user experience')
    except asyncio.CancelledError:
        print('💥 Main CancelledError - this is the final user experience')
    except Exception as e:
        print(f'💥 Main Exception: {type(e).__name__}: {e}')