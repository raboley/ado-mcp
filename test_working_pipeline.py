#!/usr/bin/env python3
"""
Test with a known working pipeline
"""
import asyncio
from fastmcp.client import Client
from server import mcp
import os

async def test_working_pipeline():
    """Test with a known working pipeline"""
    
    async with Client(mcp) as client:
        # Set the organization
        org_url = os.environ.get("ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley")
        await client.call_tool("set_ado_organization", {"organization_url": org_url})
        
        project_id = "49e895da-15c6-4211-97df-65c547a59c22"
        
        # List pipelines to find a working one
        print("Listing pipelines...")
        pipelines_result = await client.call_tool("list_pipelines", {"project_id": project_id})
        
        for pipeline in pipelines_result.data:
            print(f"Pipeline {pipeline['id']}: {pipeline['name']}")
        
        # Try pipeline 59 (known working one)
        pipeline_id = 59
        
        print(f"\nTesting pipeline {pipeline_id}...")
        
        # First, get pipeline details
        pipeline_result = await client.call_tool("get_pipeline", {
            "project_id": project_id,
            "pipeline_id": pipeline_id
        })
        
        print(f"Pipeline details: {pipeline_result.data}")
        
        # Try running it
        print("\nTrying to run pipeline...")
        try:
            run_result = await client.call_tool("run_pipeline", {
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "variables": {"testVariable": "test-value"}
            })
            print(f"Run successful: {run_result.data['id']}")
            print(f"State: {run_result.data.get('state', 'unknown')}")
        except Exception as e:
            print(f"Run failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_working_pipeline())