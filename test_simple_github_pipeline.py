#!/usr/bin/env python3
"""
Test the simple GitHub resources pipeline
"""
import asyncio
import time
from fastmcp.client import Client
from server import mcp
import os

async def test_simple_github_pipeline():
    """Test the simple GitHub resources pipeline"""
    
    async with Client(mcp) as client:
        # Set the organization
        org_url = os.environ.get("ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley")
        await client.call_tool("set_ado_organization", {"organization_url": org_url})
        
        project_id = "49e895da-15c6-4211-97df-65c547a59c22"
        pipeline_id = 201  # github-resources-simple
        
        print("=== Testing Simple GitHub Resources Pipeline ===")
        
        # Test 1: Preview with template parameters
        print("\n1. Testing preview with template parameters...")
        try:
            preview_result = await client.call_tool("preview_pipeline", {
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "template_parameters": {
                    "testBranch": "main",
                    "testVariable": "preview-test"
                }
            })
            print(f"✓ Preview successful: {preview_result.data is not None}")
            if preview_result.data and "finalYaml" in preview_result.data:
                yaml_length = len(preview_result.data["finalYaml"])
                print(f"  Final YAML length: {yaml_length} characters")
        except Exception as e:
            print(f"✗ Preview failed: {e}")
        
        # Test 2: Run with template parameters
        print("\n2. Testing run with template parameters...")
        try:
            run_result = await client.call_tool("run_pipeline", {
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "template_parameters": {
                    "testBranch": "main",
                    "testVariable": "run-test"
                },
                "variables": {
                    "additionalVar": "extra-value"
                }
            })
            print(f"✓ Run successful: {run_result.data['id']}")
            print(f"  State: {run_result.data.get('state', 'unknown')}")
            
            # Wait for completion
            run_id = run_result.data['id']
            print(f"  Waiting for completion...")
            await wait_for_completion(client, project_id, pipeline_id, run_id)
            
        except Exception as e:
            print(f"✗ Run failed: {e}")
        
        # Test 3: Run with resources parameter
        print("\n3. Testing run with resources parameter...")
        try:
            run_result = await client.call_tool("run_pipeline", {
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "resources": {
                    "repositories": {
                        "self": {
                            "refName": "refs/heads/main"
                        }
                    }
                },
                "template_parameters": {
                    "testBranch": "main",
                    "testVariable": "resources-test"
                }
            })
            print(f"✓ Run with resources successful: {run_result.data['id']}")
            print(f"  State: {run_result.data.get('state', 'unknown')}")
            
            # Check if resources were applied
            if "resources" in run_result.data and run_result.data["resources"]:
                resources = run_result.data["resources"]
                print(f"  Resources applied: {resources}")
                
        except Exception as e:
            print(f"✗ Run with resources failed: {e}")
        
        # Test 4: Run with branch parameter
        print("\n4. Testing run with branch parameter...")
        try:
            run_result = await client.call_tool("run_pipeline", {
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "branch": "refs/heads/main",
                "template_parameters": {
                    "testBranch": "main",
                    "testVariable": "branch-test"
                }
            })
            print(f"✓ Run with branch successful: {run_result.data['id']}")
            print(f"  State: {run_result.data.get('state', 'unknown')}")
            
        except Exception as e:
            print(f"✗ Run with branch failed: {e}")
        
        print("\n=== GitHub Resources Tests Complete ===")

async def wait_for_completion(client, project_id, pipeline_id, run_id, timeout=120):
    """Wait for pipeline completion"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            result = await client.call_tool("get_pipeline_run", {
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "run_id": run_id
            })
            
            state = result.data.get("state", "unknown")
            if state == "completed":
                result_status = result.data.get("result", "unknown")
                print(f"  ✓ Pipeline completed with result: {result_status}")
                return
            elif state in ["cancelling", "cancelled"]:
                print(f"  ✗ Pipeline was cancelled: {state}")
                return
            
            await asyncio.sleep(5)
            
        except Exception as e:
            print(f"  Error checking status: {e}")
            break
    
    print(f"  ⚠ Pipeline did not complete within {timeout} seconds")

if __name__ == "__main__":
    asyncio.run(test_simple_github_pipeline())