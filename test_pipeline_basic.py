#!/usr/bin/env python3
"""
Basic pipeline test to verify pipeline 200 works
"""
import asyncio
from fastmcp.client import Client
from server import mcp
import os

async def test_basic_pipeline():
    """Test the basic pipeline functionality"""
    
    async with Client(mcp) as client:
        # Set the organization
        org_url = os.environ.get("ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley")
        await client.call_tool("set_ado_organization", {"organization_url": org_url})
        
        project_id = "49e895da-15c6-4211-97df-65c547a59c22"
        pipeline_id = 200
        
        # First, get pipeline details
        print("Getting pipeline details...")
        pipeline_result = await client.call_tool("get_pipeline", {
            "project_id": project_id,
            "pipeline_id": pipeline_id
        })
        
        print(f"Pipeline: {pipeline_result.data}")
        
        # Try preview without any parameters
        print("\nTesting preview without parameters...")
        try:
            preview_result = await client.call_tool("preview_pipeline", {
                "project_id": project_id,
                "pipeline_id": pipeline_id
            })
            print(f"Preview successful: {preview_result.data is not None}")
        except Exception as e:
            print(f"Preview failed: {e}")
        
        # Try running without parameters 
        print("\nTesting run without parameters...")
        try:
            run_result = await client.call_tool("run_pipeline", {
                "project_id": project_id,
                "pipeline_id": pipeline_id
            })
            print(f"Run successful: {run_result.data}")
        except Exception as e:
            print(f"Run failed: {e}")
        
        # Try with just variables (no template parameters)
        print("\nTesting run with just variables...")
        try:
            run_result = await client.call_tool("run_pipeline", {
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "variables": {"testVariable": "basic-test"}
            })
            print(f"Run with variables successful: {run_result.data}")
        except Exception as e:
            print(f"Run with variables failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_basic_pipeline())