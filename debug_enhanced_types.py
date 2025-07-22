#!/usr/bin/env python3

import asyncio
import os
from fastmcp.client import Client
from server import mcp


async def debug_enhanced_types():
    """Debug enhanced type tools to understand response structure."""
    async with Client(mcp) as client:
        # Set organization
        org_url = os.environ.get("ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley")
        await client.call_tool("set_ado_organization", {"organization_url": org_url})

        project_id = "49e895da-15c6-4211-97df-65c547a59c22"

        print("=== Testing get_work_item_type ===")
        try:
            result = await client.call_tool(
                "get_work_item_type", {"project_id": project_id, "work_item_type": "Bug"}
            )
            print(f"Result type: {type(result)}")
            print(f"Result.data type: {type(result.data)}")
            print(f"Result.data: {result.data}")
            print(f"Has 'name' attribute: {hasattr(result.data, 'name')}")
            if hasattr(result.data, "name"):
                print(f"Name: {result.data.name}")
        except Exception as e:
            print(f"ERROR: {e}")

        print("\n=== For comparison, testing list_work_item_types ===")
        try:
            result = await client.call_tool("list_work_item_types", {"project_id": project_id})
            print(f"Result type: {type(result)}")
            print(f"Result.data type: {type(result.data)}")
            if result.data and len(result.data) > 0:
                print(f"First item type: {type(result.data[0])}")
                print(f"First item: {result.data[0]}")
                print(f"First item has 'name' key: {'name' in result.data[0]}")
        except Exception as e:
            print(f"ERROR: {e}")


if __name__ == "__main__":
    asyncio.run(debug_enhanced_types())
