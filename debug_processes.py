#!/usr/bin/env python3

import asyncio
import os
from fastmcp.client import Client
from server import mcp


async def debug_processes():
    """Debug process APIs to understand data structure."""
    async with Client(mcp) as client:
        # Set organization
        org_url = os.environ.get("ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley")
        await client.call_tool("set_ado_organization", {"organization_url": org_url})

        project_id = "49e895da-15c6-4211-97df-65c547a59c22"

        print("=== Getting project process info ===")
        process_info = await client.call_tool(
            "get_project_process_info", {"project_id": project_id}
        )
        print(f"Project process info: {process_info.data}")

        print("\n=== Getting project process ID ===")
        process_id = await client.call_tool("get_project_process_id", {"project_id": project_id})
        print(f"Project process ID: {process_id.data}")

        print("\n=== Listing all processes ===")
        all_processes = await client.call_tool("list_processes", {})
        print(f"Number of processes: {len(all_processes.data)}")
        for process in all_processes.data:
            print(f"  - {process['name']}: {process['id']}")

        print(f"\n=== Looking for process ID {process_id.data} in list ===")
        found = False
        for process in all_processes.data:
            if process["id"] == process_id.data:
                found = True
                print(f"FOUND: {process}")
                break
        if not found:
            print("NOT FOUND in processes list")

        print(f"\n=== Trying to get process details for {process_id.data} ===")
        try:
            process_details = await client.call_tool(
                "get_process_details", {"process_id": process_id.data}
            )
            print(f"Process details: {process_details.data}")
        except Exception as e:
            print(f"ERROR getting process details: {e}")


if __name__ == "__main__":
    asyncio.run(debug_processes())
