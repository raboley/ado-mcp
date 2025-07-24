#!/usr/bin/env python3
"""Debug script to test preview_pipeline with template_parameters."""

import asyncio
import json


async def test_preview_pipeline():
    """Test preview_pipeline with different parameter formats."""

    # Initialize MCP client using stdio transport
    from fastmcp.client import Client
    from fastmcp.client.transports import StdioTransport

    # Create the client with stdio transport
    transport = StdioTransport(
        command=["python", "-m", "server"], cwd="/Users/russellboley/PycharmProjects/ado-mcp"
    )

    async with Client(transport) as mcp_client:
        project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
        pipeline_id = 75  # preview-test-parameterized pipeline

        print("Testing preview_pipeline with template_parameters...")

        # Test 1: Dict format (what the test uses)
        print("\n1. Testing with dict format:")
        try:
            template_parameters = {"testEnvironment": "prod", "enableDebug": True}
            result = await mcp_client.call_tool(
                "preview_pipeline",
                {
                    "project_id": project_id,
                    "pipeline_id": pipeline_id,
                    "template_parameters": template_parameters,
                },
            )
            print("✓ Success with dict format")
            print(f"  Result type: {type(result)}")
            if hasattr(result, "data"):
                print(f"  Has finalYaml: {'finalYaml' in result.data}")
        except Exception as e:
            print(f"✗ Failed with dict format: {e}")
            print(f"  Error type: {type(e)}")

        # Test 2: JSON string format (might be what's causing the error)
        print("\n2. Testing with JSON string format:")
        try:
            template_parameters_json = json.dumps({"testEnvironment": "prod", "enableDebug": True})
            result = await mcp_client.call_tool(
                "preview_pipeline",
                {
                    "project_id": project_id,
                    "pipeline_id": pipeline_id,
                    "template_parameters": template_parameters_json,
                },
            )
            print("✓ Success with JSON string format")
            print(f"  Result type: {type(result)}")
        except Exception as e:
            print(f"✗ Failed with JSON string format: {e}")
            print(f"  Error type: {type(e)}")

        # Test 3: Check how MCP client serializes the request
        print("\n3. Checking MCP request serialization:")
        params = {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "template_parameters": {"testEnvironment": "prod", "enableDebug": True},
        }
        print(f"  Original params: {params}")
        print(f"  JSON serialized: {json.dumps(params, indent=2)}")


if __name__ == "__main__":
    asyncio.run(test_preview_pipeline())
